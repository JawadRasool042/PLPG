"""
============================================
Authentication Middleware
============================================

JWT token validation and role-based access control
"""

import jwt
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime

from config import get_config
from models.user import User
from utils.token_utils import verify_user_token

config = get_config()


def get_client_ip():
    """Get client IP address (handles proxies)"""
    return (
        request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or
        request.headers.get('X-Real-IP') or
        request.remote_addr or
        'unknown'
    )


def get_user_agent():
    """Get User Agent"""
    return request.headers.get('User-Agent', 'unknown')


def authenticate_token(f):
    """
    Decorator to authenticate JWT token from Authorization header
    Attaches decoded user to g.user
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'detail': 'Access token required',
                'error_code': 'NO_TOKEN'
            }), 401
        
        try:
            # Extract token from "Bearer <token>"
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({
                    'detail': 'Invalid authorization header format',
                    'error_code': 'INVALID_HEADER'
                }), 401
            
            token = parts[1]
            
            # Verify JWT using centralized utility
            decoded = verify_user_token(token, is_refresh=False)
            
            if not decoded:
                return jsonify({
                    'detail': 'Invalid token',
                    'error_code': 'INVALID_TOKEN'
                }), 401
            
            # Verify user still exists and is active
            user = User.find_by_id(decoded.get('id'))
            
            if not user:
                return jsonify({
                    'detail': 'User not found',
                    'error_code': 'USER_NOT_FOUND'
                }), 401
            
            if not user.get('isActive'):
                return jsonify({
                    'detail': 'Account is deactivated',
                    'error_code': 'ACCOUNT_INACTIVE'
                }), 403
            
            # Check if password was changed after token was issued
            password_changed_at = user.get('passwordChangedAt')
            if password_changed_at:
                token_iat = decoded.get('iat', 0)
                password_changed_timestamp = int(password_changed_at.timestamp())
                
                if token_iat < password_changed_timestamp:
                    return jsonify({
                        'detail': 'Password was recently changed. Please log in again.',
                        'error_code': 'PASSWORD_CHANGED'
                    }), 401
            
            # Attach user info to request context
            g.user = {
                'id': decoded.get('id'),
                'email': user.get('email'),  # Get email from user document, not token
                'role': user.get('role'),
                'isEmailVerified': user.get('isEmailVerified')
            }
            g.user_doc = user
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'detail': 'Token has expired. Please log in again.',
                'error_code': 'TOKEN_EXPIRED'
            }), 401
        
        except jwt.InvalidTokenError:
            return jsonify({
                'detail': 'Invalid token',
                'error_code': 'INVALID_TOKEN'
            }), 401
        
        except Exception as e:
            print(f'Auth middleware error: {e}')
            return jsonify({
                'detail': 'Authentication error',
                'error_code': 'AUTH_ERROR'
            }), 500
    
    return decorated


def require_role(*roles):
    """
    Decorator to require specific role(s) for route access
    Use after authenticate_token decorator
    
    Args:
        *roles: Allowed roles
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = g.user.get('role') if hasattr(g, 'user') else None
            
            if not user_role:
                return jsonify({
                    'detail': 'Role information not available',
                    'error_code': 'NO_ROLE'
                }), 403
            
            if user_role not in roles:
                return jsonify({
                    'detail': 'Insufficient permissions',
                    'error_code': 'FORBIDDEN',
                    'required_roles': list(roles),
                    'user_role': user_role
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator


def require_email_verified(f):
    """
    Decorator to require email verification
    Use after authenticate_token decorator
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        is_verified = g.user.get('isEmailVerified') if hasattr(g, 'user') else False
        
        if not is_verified:
            return jsonify({
                'detail': 'Email verification required',
                'error_code': 'EMAIL_NOT_VERIFIED'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated
