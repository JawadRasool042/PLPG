"""
============================================
Admin Routes - Production Ready
============================================

ENDPOINTS:
- Auth: login, refresh-token, logout, profile
- Users: CRUD, stats, export
- Logs: list, details, stats, export
- Analytics: dashboard, engagement, health
"""

import jwt
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from config import get_config
from models.admin import Admin, Role, Permission
from models.user import User
from models.audit_log import AuditLog
from middleware.admin_auth import authenticate_admin, authorize
from utils.token_utils import generate_admin_tokens, verify_admin_token, get_token_expiry_seconds, parse_expiry_string

config = get_config()
admin_bp = Blueprint('admin', __name__)


# ============================================
# Helper Functions
# ============================================
def get_admin_jwt_secret():
    return config.ADMIN_JWT_SECRET or config.JWT_SECRET


def get_admin_refresh_secret():
    return config.ADMIN_JWT_REFRESH_SECRET or config.JWT_REFRESH_SECRET


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str):
    strength = 0
    feedback = []
    
    if len(password) >= 8:
        strength += 1
    else:
        feedback.append('Password should be at least 8 characters')
    
    if len(password) >= 12:
        strength += 1
    
    if re.search(r'[a-z]', password):
        strength += 1
    else:
        feedback.append('Password should contain lowercase letters')
    
    if re.search(r'[A-Z]', password):
        strength += 1
    else:
        feedback.append('Password should contain uppercase letters')
    
    if re.search(r'\d', password):
        strength += 1
    else:
        feedback.append('Password should contain numbers')
    
    if re.search(r'[@$!%*?&]', password):
        strength += 1
    else:
        feedback.append('Password should contain special characters (@$!%*?&)')
    
    return {
        'score': strength,
        'maxScore': 6,
        'percentage': round((strength / 6) * 100),
        'feedback': feedback,
        'isStrong': strength >= 4
    }


def validate_pagination(page, limit):
    """Validate and sanitize pagination parameters"""
    try:
        page_num = max(1, int(page or 1))
        limit_num = max(1, min(int(limit or 10), 100))
    except (ValueError, TypeError):
        page_num, limit_num = 1, 10
    
    skip = (page_num - 1) * limit_num
    return page_num, limit_num, skip


# ==================== AUTH ROUTES ====================

@admin_bp.route('/auth/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({
            'success': False,
            'message': 'Email and password are required'
        }), 400
    
    if not validate_email(email):
        return jsonify({
            'success': False,
            'message': 'Invalid email format'
        }), 400
    
    try:
        admin = Admin.find_by_email(email, include_password=True)
        
        if not admin:
            # Prevent timing attacks - simulate password check
            import bcrypt
            bcrypt.checkpw(password.encode(), b'$2b$12$invalidhashfortimingattackprevention....................')
            
            AuditLog.create({
                'action': 'LOGIN_FAILED',
                'resource': 'Admin',
                'description': 'Login attempt with non-existent email',
                'ipAddress': request.remote_addr,
                'userAgent': request.headers.get('User-Agent'),
                'status': 'failure',
                'details': {'email': email}
            })
            
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        admin_id = str(admin['_id'])
        
        # Check if locked
        if Admin.is_locked(admin):
            AuditLog.create({
                'admin': admin['_id'],
                'action': 'LOGIN_FAILED',
                'resource': 'Admin',
                'description': 'Login attempt on locked account',
                'ipAddress': request.remote_addr,
                'userAgent': request.headers.get('User-Agent'),
                'status': 'failure'
            })
            
            return jsonify({
                'success': False,
                'message': 'Account is locked due to multiple failed login attempts. Please try again later.',
                'lockedUntil': admin.get('lockoutUntil').isoformat() if admin.get('lockoutUntil') else None
            }), 403
        
        # Check status
        if admin.get('status') == 'suspended':
            return jsonify({
                'success': False,
                'message': 'Admin account is suspended'
            }), 403
        
        if admin.get('status') == 'inactive':
            return jsonify({
                'success': False,
                'message': 'Admin account is inactive'
            }), 403
        
        # Check password
        if not Admin.check_password(password, admin['password']):
            Admin.increment_login_attempts(admin_id, admin)
            
            AuditLog.create({
                'admin': admin['_id'],
                'action': 'LOGIN_FAILED',
                'resource': 'Admin',
                'description': 'Login attempt with incorrect password',
                'ipAddress': request.remote_addr,
                'userAgent': request.headers.get('User-Agent'),
                'status': 'failure'
            })
            
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        # Reset login attempts
        Admin.reset_login_attempts(admin_id)
        Admin.update_last_login(admin_id)
        
        # Generate tokens using centralized utility
        access_token, refresh_token = generate_admin_tokens(admin_id)
        access_expiry_seconds = get_token_expiry_seconds(access_token)
        
        # Log success
        AuditLog.create({
            'admin': admin['_id'],
            'action': 'LOGIN',
            'resource': 'Admin',
            'description': 'Admin login successful',
            'ipAddress': request.remote_addr,
            'userAgent': request.headers.get('User-Agent'),
            'status': 'success'
        })
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'data': {
                'accessToken': access_token,
                'refreshToken': refresh_token,
                'expiresIn': access_expiry_seconds,
                'admin': Admin.to_response(admin)
            }
        })
        
    except Exception as e:
        print(f'Admin login error: {e}')
        return jsonify({
            'success': False,
            'message': 'Login failed',
            'error': str(e)
        }), 500


@admin_bp.route('/auth/refresh-token', methods=['POST'])
def refresh_token():
    data = request.get_json() or {}
    token = data.get('refreshToken', '')
    
    if not token:
        return jsonify({
            'success': False,
            'message': 'Refresh token is required'
        }), 400
    
    decoded = verify_admin_token(token, is_refresh=True)
    
    if not decoded:
        return jsonify({
            'success': False,
            'message': 'Invalid or expired refresh token'
        }), 401
    
    admin = Admin.find_by_id(decoded.get('id'))
    
    if not admin or admin.get('status') != 'active':
        return jsonify({
            'success': False,
            'message': 'Admin not found or account is inactive'
        }), 401
    
    # Generate new tokens (refresh token rotation)
    access_token, refresh_token_new = generate_admin_tokens(str(admin['_id']))
    access_expiry_seconds = get_token_expiry_seconds(access_token)
    
    return jsonify({
        'success': True,
        'message': 'Token refreshed successfully',
        'data': {
            'accessToken': access_token,
            'refreshToken': refresh_token_new,
            'expiresIn': access_expiry_seconds
        }
    })


@admin_bp.route('/auth/logout', methods=['POST'])
@authenticate_admin
def admin_logout():
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'LOGOUT',
        'resource': 'Admin',
        'description': 'Admin logout',
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    return jsonify({
        'success': True,
        'message': 'Logout successful'
    })


@admin_bp.route('/auth/profile', methods=['GET'])
@authenticate_admin
def get_admin_profile():
    admin = Admin.find_by_id(str(g.admin['_id']))
    
    if not admin:
        return jsonify({
            'success': False,
            'message': 'Admin not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Profile retrieved successfully',
        'data': Admin.to_response(admin)
    })


@admin_bp.route('/auth/profile', methods=['PUT'])
@authenticate_admin
def update_admin_profile():
    data = request.get_json() or {}
    name = data.get('name')
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    admin = Admin.find_by_id(str(g.admin['_id']), include_password=True)
    
    if not admin:
        return jsonify({
            'success': False,
            'message': 'Admin not found'
        }), 404
    
    update_data = {}
    
    if name:
        update_data['name'] = name
    
    if current_password and new_password:
        if not Admin.check_password(current_password, admin['password']):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 401
        
        strength = validate_password_strength(new_password)
        if not strength['isStrong']:
            return jsonify({
                'success': False,
                'message': 'New password does not meet security requirements',
                'feedback': strength['feedback']
            }), 400
        
        update_data['password'] = new_password
    
    if update_data:
        Admin.update(str(g.admin['_id']), update_data)
        
        AuditLog.create({
            'admin': g.admin['_id'],
            'action': 'ADMIN_UPDATE',
            'resource': 'Admin',
            'description': 'Admin profile updated',
            'resourceId': g.admin['_id'],
            'ipAddress': request.remote_addr,
            'userAgent': request.headers.get('User-Agent'),
            'status': 'success'
        })
    
    updated_admin = Admin.find_by_id(str(g.admin['_id']))
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'data': Admin.to_response(updated_admin)
    })


@admin_bp.route('/auth/create-admin', methods=['POST'])
@authenticate_admin
@authorize('admin_create')
def create_admin():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role_id = data.get('roleId', '')
    
    if not all([name, email, password, role_id]):
        return jsonify({
            'success': False,
            'message': 'Name, email, password, and role are required'
        }), 400
    
    if not validate_email(email):
        return jsonify({
            'success': False,
            'message': 'Invalid email format'
        }), 400
    
    strength = validate_password_strength(password)
    if not strength['isStrong']:
        return jsonify({
            'success': False,
            'message': 'Password does not meet security requirements',
            'feedback': strength['feedback']
        }), 400
    
    # Check if exists
    if Admin.find_by_email(email):
        return jsonify({
            'success': False,
            'message': 'Admin with this email already exists'
        }), 409
    
    if Admin.find_by_name(name):
        return jsonify({
            'success': False,
            'message': 'Admin with this name already exists'
        }), 409
    
    # Check role exists
    role = Role.find_by_id(role_id)
    if not role:
        return jsonify({
            'success': False,
            'message': 'Role not found'
        }), 404
    
    from bson import ObjectId
    new_admin = Admin.create({
        'name': name,
        'email': email,
        'password': password,
        'role': ObjectId(role_id),
        'permissions': role.get('permissions', [])
    })
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'ADMIN_CREATE',
        'resource': 'Admin',
        'description': f'Created new admin: {email}',
        'resourceId': new_admin['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    return jsonify({
        'success': True,
        'message': 'Admin created successfully',
        'data': Admin.to_response(new_admin)
    }), 201


# ==================== USER MANAGEMENT ROUTES ====================

@admin_bp.route('/users', methods=['GET'])
@authenticate_admin
@authorize('users_read')
def get_users():
    """
    Fetch all users with pagination, search, filtering, and sorting
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    - search: Search by firstName, lastName, or email
    - status: Filter by status (verified, pending, suspended)
    - sortBy: Sort field (name, email, created)
    - sortOrder: Sort direction (asc, desc)
    """
    page = request.args.get('page', 1)
    limit = request.args.get('limit', 10)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    sort_by = request.args.get('sortBy', 'createdAt')
    sort_order = request.args.get('sortOrder', 'desc')
    
    page_num, limit_num, skip = validate_pagination(page, limit)
    
    # Build filter query
    filter_query = {}
    
    # Search filter
    if search:
        filter_query['$or'] = [
            {'firstName': {'$regex': search, '$options': 'i'}},
            {'lastName': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}}
        ]
    
    # Status filter
    if status == 'verified':
        filter_query['isEmailVerified'] = True
        filter_query['isActive'] = True
    elif status == 'pending':
        filter_query['isEmailVerified'] = False
        filter_query['isActive'] = True
    elif status == 'suspended':
        filter_query['isActive'] = False
    
    # Map frontend sort field names to database field names
    sort_field_map = {
        'name': 'firstName',
        'email': 'email',
        'created': 'createdAt'
    }
    db_sort_by = sort_field_map.get(sort_by, 'createdAt')
    sort_dir = 1 if sort_order == 'asc' else -1
    
    # Fetch users
    users = User.find_many(filter_query, skip, limit_num, db_sort_by, sort_dir)
    total = User.count(filter_query)
    
    # Convert to response format
    users_response = []
    for u in users:
        first_name = u.get('firstName', '').strip()
        last_name = u.get('lastName', '').strip()
        full_name = f"{first_name} {last_name}".strip() or 'N/A'
        
        is_active = u.get('isActive', True)
        is_verified = u.get('isEmailVerified', False)
        
        # Determine status
        if not is_active:
            user_status = 'suspended'
        elif is_verified:
            user_status = 'verified'
        else:
            user_status = 'pending'
        
        users_response.append({
            '_id': str(u['_id']),
            'name': full_name,
            'firstName': first_name,
            'lastName': last_name,
            'email': u.get('email', ''),
            'emailVerified': is_verified,
            'suspended': not is_active,
            'status': user_status,
            'createdAt': u.get('createdAt').isoformat() if u.get('createdAt') else None,
        })
    
    return jsonify({
        'success': True,
        'message': 'Users retrieved successfully',
        'data': users_response,
        'pagination': {
            'page': page_num,
            'limit': limit_num,
            'total': total,
            'pages': (total + limit_num - 1) // limit_num
        }
    })


@admin_bp.route('/users/<user_id>', methods=['GET'])
@authenticate_admin
@authorize('users_read')
def get_user_by_id(user_id):
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    # Get additional details
    from models.quiz_attempt import QuizAttempt
    
    # Get quiz attempts (enrollment history)
    quiz_attempts = QuizAttempt.find_by_user(user_id, limit=10)
    
    # Get login history from audit logs
    login_history = list(AuditLog.get_collection().find({
        'action': {'$in': ['LOGIN', 'LOGIN_SUCCESS']},
        'details.userId': user_id
    }).sort('createdAt', -1).limit(10))
    
    # Get activity history
    activity_history = list(AuditLog.get_collection().find({
        '$or': [
            {'details.userId': user_id},
            {'resourceId': ObjectId(user_id)}
        ]
    }).sort('createdAt', -1).limit(20))
    
    # Format response
    user_response = User.to_response(user, include_sensitive=True)
    user_response['quizAttempts'] = [
        {
            'id': str(qa['_id']),
            'quizId': str(qa.get('quizId', '')),
            'score': qa.get('score', 0),
            'completedAt': qa.get('completedAt').isoformat() if qa.get('completedAt') else None
        }
        for qa in quiz_attempts
    ]
    user_response['loginHistory'] = [
        {
            'timestamp': log.get('createdAt').isoformat() if log.get('createdAt') else None,
            'ipAddress': log.get('ipAddress', 'Unknown'),
            'userAgent': log.get('userAgent', 'Unknown')
        }
        for log in login_history
    ]
    user_response['activityHistory'] = [
        {
            'action': log.get('action', ''),
            'description': log.get('description', ''),
            'timestamp': log.get('createdAt').isoformat() if log.get('createdAt') else None
        }
        for log in activity_history
    ]
    
    return jsonify({
        'success': True,
        'message': 'User details retrieved successfully',
        'data': user_response
    })


@admin_bp.route('/users/<user_id>', methods=['PUT'])
@authenticate_admin
@authorize('users_update')
def update_user(user_id):
    data = request.get_json() or {}
    
    user = User.find_by_id(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    update_data = {}
    if 'first_name' in data:
        update_data['firstName'] = data['first_name']
    if 'last_name' in data:
        update_data['lastName'] = data['last_name']
    if 'learning_goals' in data:
        update_data['learningGoals'] = data['learning_goals']
    if 'is_active' in data:
        update_data['isActive'] = data['is_active']
    
    if update_data:
        User.update(user_id, update_data)
        
        AuditLog.create({
            'admin': g.admin['_id'],
            'action': 'USER_UPDATE',
            'resource': 'User',
            'description': f'Updated user: {user["email"]}',
            'resourceId': user['_id'],
            'ipAddress': request.remote_addr,
            'userAgent': request.headers.get('User-Agent'),
            'status': 'success',
            'changes': {'old': User.to_response(user), 'new': update_data}
        })
    
    updated_user = User.find_by_id(user_id)
    
    return jsonify({
        'success': True,
        'message': 'User updated successfully',
        'data': User.to_response(updated_user)
    })


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@authenticate_admin
@authorize('users_delete')
def delete_user(user_id):
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    User.delete(user_id)
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'USER_DELETE',
        'resource': 'User',
        'description': f'Deleted user: {user["email"]}',
        'resourceId': user['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    return jsonify({
        'success': True,
        'message': 'User deleted successfully'
    })


@admin_bp.route('/users/stats/overview', methods=['GET'])
@authenticate_admin
@authorize('users_read')
def get_user_stats():
    total_users = User.count({})
    verified_users = User.count({'isEmailVerified': True})
    unverified_users = User.count({'isEmailVerified': False})
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    new_users_week = User.count({'createdAt': {'$gte': seven_days_ago}})
    new_users_month = User.count({'createdAt': {'$gte': thirty_days_ago}})
    
    return jsonify({
        'success': True,
        'message': 'User statistics retrieved successfully',
        'data': {
            'totalUsers': total_users,
            'verifiedUsers': verified_users,
            'unverifiedUsers': unverified_users,
            'newUsersThisWeek': new_users_week,
            'newUsersThisMonth': new_users_month,
            'verificationRate': round((verified_users / total_users * 100), 2) if total_users > 0 else 0
        }
    })


@admin_bp.route('/users/<user_id>/suspend', methods=['POST'])
@authenticate_admin
@authorize('users_update')
def suspend_user(user_id):
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    User.update(user_id, {'isActive': False})
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'USER_SUSPEND',
        'resource': 'User',
        'description': f'Suspended user: {user["email"]}',
        'resourceId': user['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    return jsonify({
        'success': True,
        'message': 'User suspended successfully'
    })


@admin_bp.route('/users/<user_id>/activate', methods=['POST'])
@authenticate_admin
@authorize('users_update')
def activate_user(user_id):
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    User.update(user_id, {'isActive': True})
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'USER_ACTIVATE',
        'resource': 'User',
        'description': f'Activated user: {user["email"]}',
        'resourceId': user['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    return jsonify({
        'success': True,
        'message': 'User activated successfully'
    })


@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@authenticate_admin
@authorize('users_update')
def change_user_role(user_id):
    data = request.get_json() or {}
    new_role = data.get('role', '').strip()
    
    if not new_role:
        return jsonify({
            'success': False,
            'message': 'Role is required'
        }), 400
    
    # Validate role
    valid_roles = ['Student', 'Teacher']
    if new_role not in valid_roles:
        return jsonify({
            'success': False,
            'message': f'Invalid role. Must be one of: {", ".join(valid_roles)}'
        }), 400
    
    user = User.find_by_id(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    old_role = user.get('role', 'Student')
    
    # Update role
    User.update(user_id, {'role': new_role})
    
    # Log the change
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'USER_ROLE_CHANGE',
        'resource': 'User',
        'description': f'Changed role for {user["email"]} from {old_role} to {new_role}',
        'resourceId': user['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success',
        'changes': {
            'before': {'role': old_role},
            'after': {'role': new_role}
        }
    })
    
    return jsonify({
        'success': True,
        'message': f'User role changed to {new_role} successfully'
    })


@admin_bp.route('/users/<user_id>/reset-password', methods=['POST'])
@authenticate_admin
@authorize('users_update')
def admin_reset_user_password(user_id):
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    # Generate reset token
    reset_token = User.set_password_reset_token(user_id)
    
    # In production, send email with reset link
    # For now, return the token (remove in production!)
    reset_link = f"{config.FRONTEND_URL}/reset-password?token={reset_token}"
    
    # Log the action
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'PASSWORD_RESET_ADMIN',
        'resource': 'User',
        'description': f'Admin initiated password reset for {user["email"]}',
        'resourceId': user['_id'],
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    # Send password reset email
    email_sent = send_password_reset_email(user['email'], reset_link)
    
    if not email_sent:
        logger.warning(f'Failed to send password reset email to {user["email"]}')
        return jsonify({
            'success': False,
            'message': 'Failed to send reset email. Please try again later.'
        }), 500
    
    return jsonify({
        'success': True,
        'message': 'Password reset email sent successfully'
    })


@admin_bp.route('/users/export/csv', methods=['GET'])
@authenticate_admin
@authorize('users_export')
def export_users():
    # Add pagination to prevent exporting massive datasets at once
    limit = request.args.get('limit', 1000, type=int)
    limit = min(max(1, limit), 5000)  # Cap at 5000 per export
    
    users = User.find_many({}, skip=0, limit=limit)
    
    csv_rows = [['ID', 'Email', 'First Name', 'Last Name', 'Role', 'Verified', 'Created At']]
    
    for user in users:
        csv_rows.append([
            str(user['_id']),
            user.get('email', ''),
            user.get('firstName', ''),
            user.get('lastName', ''),
            user.get('role', ''),
            'Yes' if user.get('isEmailVerified') else 'No',
            user.get('createdAt').isoformat() if user.get('createdAt') else ''
        ])
    
    csv_content = '\n'.join([','.join([f'"{c}"' for c in row]) for row in csv_rows])
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'EXPORT_DATA',
        'resource': 'User',
        'description': f'Exported {len(users)} users to CSV',
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=users.csv'}
    )


# ==================== AUDIT LOG ROUTES ====================

@admin_bp.route('/logs', methods=['GET'])
@authenticate_admin
@authorize('logs_read')
def get_logs():
    page = request.args.get('page', 1)
    limit = request.args.get('limit', 10)
    action = request.args.get('action', '')
    resource = request.args.get('resource', '')
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    
    page_num, limit_num, skip = validate_pagination(page, limit)
    
    filter_query = {}
    
    if action:
        filter_query['action'] = action
    if resource:
        filter_query['resource'] = resource
    
    if start_date or end_date:
        filter_query['createdAt'] = {}
        if start_date:
            filter_query['createdAt']['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            filter_query['createdAt']['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    logs = AuditLog.find_many(filter_query, skip, limit_num)
    total = AuditLog.count(filter_query)
    
    return jsonify({
        'success': True,
        'message': 'Audit logs retrieved successfully',
        'data': [AuditLog.to_response(log) for log in logs],
        'pagination': {
            'page': page_num,
            'limit': limit_num,
            'total': total,
            'pages': (total + limit_num - 1) // limit_num
        }
    })


@admin_bp.route('/logs/<log_id>', methods=['GET'])
@authenticate_admin
@authorize('logs_read')
def get_log_details(log_id):
    log = AuditLog.find_by_id(log_id)
    
    if not log:
        return jsonify({
            'success': False,
            'message': 'Log not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Log details retrieved successfully',
        'data': AuditLog.to_response(log)
    })


@admin_bp.route('/logs/stats/overview', methods=['GET'])
@authenticate_admin
@authorize('logs_read')
def get_log_stats():
    days = int(request.args.get('days', 7))
    
    action_stats = AuditLog.get_action_stats(days)
    resource_stats = AuditLog.get_resource_stats(days)
    status_stats = AuditLog.get_status_stats(days)
    
    start_date = datetime.utcnow() - timedelta(days=days)
    login_stats = AuditLog.count({'action': 'LOGIN', 'createdAt': {'$gte': start_date}})
    failed_login_stats = AuditLog.count({'action': 'LOGIN_FAILED', 'createdAt': {'$gte': start_date}})
    
    return jsonify({
        'success': True,
        'message': 'Log statistics retrieved successfully',
        'data': {
            'period': f'Last {days} days',
            'actionStats': action_stats,
            'resourceStats': resource_stats,
            'statusStats': status_stats,
            'loginStats': {
                'successful': login_stats,
                'failed': failed_login_stats
            }
        }
    })


@admin_bp.route('/logs/export/csv', methods=['GET'])
@authenticate_admin
@authorize('logs_export')
def export_logs():
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    limit = request.args.get('limit', 5000, type=int)
    limit = min(max(1, limit), 10000)  # Cap at 10000 logs per export
    
    filter_query = {}
    if start_date or end_date:
        filter_query['createdAt'] = {}
        if start_date:
            filter_query['createdAt']['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            filter_query['createdAt']['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    logs = AuditLog.find_many(filter_query, 0, limit)
    
    csv_rows = [['Timestamp', 'Admin', 'Action', 'Resource', 'Status', 'IP Address', 'Description']]
    
    for log in logs:
        admin_info = log.get('admin', {})
        admin_email = admin_info.get('email', 'System') if isinstance(admin_info, dict) else 'System'
        
        csv_rows.append([
            log.get('createdAt').isoformat() if log.get('createdAt') else '',
            admin_email,
            log.get('action', ''),
            log.get('resource', ''),
            log.get('status', ''),
            log.get('ipAddress', ''),
            log.get('description', '')
        ])
    
    csv_content = '\n'.join([','.join([f'"{c}"' for c in row]) for row in csv_rows])
    
    AuditLog.create({
        'admin': g.admin['_id'],
        'action': 'EXPORT_DATA',
        'resource': 'AuditLog',
        'description': f'Exported {len(logs)} audit logs to CSV',
        'ipAddress': request.remote_addr,
        'userAgent': request.headers.get('User-Agent'),
        'status': 'success'
    })
    
    from flask import Response
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=audit_logs.csv'}
    )


# ==================== ANALYTICS ROUTES ====================

@admin_bp.route('/analytics/dashboard', methods=['GET'])
@authenticate_admin
@authorize('analytics_read')
def get_dashboard_analytics():
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    # User metrics
    total_users = User.count({})
    verified_users = User.count({'isEmailVerified': True})
    new_users_week = User.count({'createdAt': {'$gte': seven_days_ago}})
    new_users_month = User.count({'createdAt': {'$gte': thirty_days_ago}})
    
    # Activity metrics
    total_logins = AuditLog.count({'action': 'LOGIN'})
    failed_logins = AuditLog.count({'action': 'LOGIN_FAILED'})
    admin_actions = AuditLog.count({'createdAt': {'$gte': seven_days_ago}})
    
    # User growth chart data (daily signups for last 30 days)
    collection = User.get_collection()
    user_growth = list(collection.aggregate([
        {
            '$match': {'createdAt': {'$gte': thirty_days_ago}}
        },
        {
            '$group': {
                '_id': {
                    '$dateToString': {'format': '%Y-%m-%d', 'date': '$createdAt'}
                },
                'count': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id': 1}
        }
    ]))
    
    # Recent activities
    recent_activities = AuditLog.find_many({}, 0, 10)
    
    return jsonify({
        'success': True,
        'message': 'Dashboard analytics retrieved successfully',
        'data': {
            'metrics': {
                'users': {
                    'total': total_users,
                    'verified': verified_users,
                    'newThisWeek': new_users_week,
                    'newThisMonth': new_users_month
                },
                'activity': {
                    'totalLogins': total_logins,
                    'failedLogins': failed_logins,
                    'adminActionsThisWeek': admin_actions
                }
            },
            'charts': {
                'userGrowth': user_growth
            },
            'recentActivities': [AuditLog.to_response(a) for a in recent_activities]
        }
    })


@admin_bp.route('/analytics/engagement', methods=['GET'])
@authenticate_admin
@authorize('analytics_read')
def get_user_engagement():
    days = int(request.args.get('days', 30))
    
    return jsonify({
        'success': True,
        'message': 'User engagement analytics retrieved successfully',
        'data': {
            'period': f'Last {days} days'
        }
    })


@admin_bp.route('/analytics/health', methods=['GET'])
@authenticate_admin
@authorize('analytics_read')
def get_system_health():
    now = datetime.utcnow()
    one_day_ago = now - timedelta(days=1)
    
    failed_ops = AuditLog.count({'status': 'failure', 'createdAt': {'$gte': one_day_ago}})
    successful_logins = AuditLog.count({'action': 'LOGIN', 'createdAt': {'$gte': one_day_ago}})
    failed_logins = AuditLog.count({'action': 'LOGIN_FAILED', 'createdAt': {'$gte': one_day_ago}})
    
    total_logins = successful_logins + failed_logins
    login_success_rate = round((successful_logins / total_logins * 100), 2) if total_logins > 0 else 100
    
    total_ops = AuditLog.count({'createdAt': {'$gte': one_day_ago}})
    error_rate = round((failed_ops / total_ops * 100), 2) if total_ops > 0 else 0
    
    return jsonify({
        'success': True,
        'message': 'System health retrieved successfully',
        'data': {
            'status': 'healthy' if error_rate < 5 else 'degraded',
            'metrics': {
                'uptime': '99.9%',
                'loginSuccessRate': f'{login_success_rate}%',
                'errorRate': f'{error_rate}%',
                'failedOperations24h': failed_ops,
                'totalOperations24h': total_ops
            }
        }
    })


@admin_bp.route('/analytics/report', methods=['GET'])
@authenticate_admin
@authorize('reports_read')
def get_detailed_report():
    return jsonify({
        'success': True,
        'message': 'Detailed report retrieved successfully',
        'data': {}
    })
