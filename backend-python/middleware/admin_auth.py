"""
============================================
Admin Authentication Middleware
============================================

JWT token validation for admin routes
"""

import jwt
from functools import wraps
from flask import request, jsonify, g

from config import get_config
from models.admin import Admin
from models.audit_log import AuditLog
from utils.token_utils import verify_admin_token

config = get_config()


def get_admin_jwt_secret():
    """Get admin-specific JWT secret"""
    return config.ADMIN_JWT_SECRET or config.JWT_SECRET


def authenticate_admin(f):
    """
    Decorator to authenticate admin JWT token
    Attaches decoded admin to g.admin
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            # Log unauthorized access attempt
            AuditLog.create({
                'action': 'UNAUTHORIZED_ACCESS',
                'resource': 'Admin',
                'description': 'Access attempt without token',
                'ipAddress': request.remote_addr,
                'userAgent': request.headers.get('User-Agent'),
                'status': 'failure'
            })
            
            return jsonify({
                'success': False,
                'message': 'No authentication token provided'
            }), 401
        
        try:
            # Extract token from "Bearer <token>"
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({
                    'success': False,
                    'message': 'Invalid authorization header format'
                }), 401
            
            token = parts[1]
            
            # Verify JWT using centralized utility
            decoded = verify_admin_token(token, is_refresh=False)
            
            if not decoded:
                AuditLog.create({
                    'action': 'UNAUTHORIZED_ACCESS',
                    'resource': 'Admin',
                    'description': 'Access attempt with invalid token',
                    'ipAddress': request.remote_addr,
                    'userAgent': request.headers.get('User-Agent'),
                    'status': 'failure'
                })
                
                return jsonify({
                    'success': False,
                    'message': 'Invalid authentication token'
                }), 401
            
            # Find admin
            admin = Admin.find_by_id(decoded.get('id'), include_password=False)
            
            if not admin:
                return jsonify({
                    'success': False,
                    'message': 'Admin not found'
                }), 404
            
            if admin.get('status') == 'suspended':
                AuditLog.create({
                    'admin': admin['_id'],
                    'action': 'UNAUTHORIZED_ACCESS',
                    'resource': 'Admin',
                    'description': 'Access attempt with suspended account',
                    'ipAddress': request.remote_addr,
                    'userAgent': request.headers.get('User-Agent'),
                    'status': 'failure'
                })
                
                return jsonify({
                    'success': False,
                    'message': 'Admin account is suspended'
                }), 403
            
            if admin.get('status') == 'inactive':
                return jsonify({
                    'success': False,
                    'message': 'Admin account is inactive'
                }), 403
            
            # Attach admin to request context
            g.admin = admin
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'message': 'Token has expired'
            }), 401
        
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'message': 'Invalid authentication token'
            }), 401
        
        except Exception as e:
            print(f'Admin auth middleware error: {e}')
            return jsonify({
                'success': False,
                'message': 'Authentication error'
            }), 500
    
    return decorated


def authorize(*required_permissions):
    """
    Decorator to check admin permissions
    Use after authenticate_admin decorator
    
    Args:
        *required_permissions: Required permission names
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            admin = g.admin if hasattr(g, 'admin') else None
            
            if not admin:
                return jsonify({
                    'success': False,
                    'message': 'Admin not authenticated'
                }), 401
            
            # Super admin has all permissions
            admin_role = admin.get('role', {})
            if isinstance(admin_role, dict) and admin_role.get('name') == 'super_admin':
                return f(*args, **kwargs)
            
            # Check if admin has required permissions
            admin_permissions = []
            for perm in admin.get('permissions', []):
                if isinstance(perm, dict):
                    admin_permissions.append(perm.get('name'))
                else:
                    admin_permissions.append(str(perm))
            
            has_permission = any(
                perm in admin_permissions 
                for perm in required_permissions
            )
            
            if not has_permission:
                # Log unauthorized access attempt
                AuditLog.create({
                    'admin': admin['_id'],
                    'action': 'UNAUTHORIZED_ACCESS',
                    'resource': 'Admin',
                    'description': f'Access denied. Required permissions: {", ".join(required_permissions)}',
                    'ipAddress': request.remote_addr,
                    'userAgent': request.headers.get('User-Agent'),
                    'status': 'failure'
                })
                
                return jsonify({
                    'success': False,
                    'message': 'Insufficient permissions to perform this action',
                    'requiredPermissions': list(required_permissions),
                    'adminPermissions': admin_permissions
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator
