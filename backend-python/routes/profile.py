"""
============================================
Profile & Settings Routes - Production Ready
============================================

ENDPOINTS:
GET  /profile          - Get user profile
PUT  /profile          - Update user profile
PUT  /profile/avatar   - Update profile avatar
GET  /settings         - Get user settings
PUT  /settings         - Update user settings
PUT  /settings/password - Change password
DELETE /account        - Delete user account
"""

import re
from flask import Blueprint, request, jsonify, g

from models.user import User
from middleware.auth import authenticate_token, get_client_ip

profile_bp = Blueprint('profile', __name__)


# ============================================
# Validation Helpers
# ============================================
def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return True
    pattern = r'^[+]?[0-9\s()\-]{7,20}$'
    return bool(re.match(pattern, phone))


def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return True
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url, re.IGNORECASE))


# ============================================
# GET /profile - Get User Profile
# ============================================
@profile_bp.route('/profile', methods=['GET'])
@authenticate_token
def get_profile():
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify(User.to_response(user, include_sensitive=True))
        
    except Exception as e:
        print(f'Error fetching profile: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# PUT /profile - Update User Profile
# ============================================
@profile_bp.route('/profile', methods=['PUT'])
@authenticate_token
def update_profile():
    data = request.get_json() or {}
    
    # Validation
    errors = []
    
    if 'first_name' in data:
        first_name = data['first_name']
        if not first_name or len(first_name) > 50:
            errors.append({'field': 'first_name', 'message': 'First name must be between 1 and 50 characters'})
    
    if 'last_name' in data:
        last_name = data['last_name']
        if not last_name or len(last_name) > 50:
            errors.append({'field': 'last_name', 'message': 'Last name must be between 1 and 50 characters'})
    
    if 'phone' in data and data['phone'] and not validate_phone(data['phone']):
        errors.append({'field': 'phone', 'message': 'Invalid phone number format'})
    
    if 'bio' in data and data['bio'] and len(data['bio']) > 500:
        errors.append({'field': 'bio', 'message': 'Bio must not exceed 500 characters'})
    
    if 'location' in data and data['location'] and len(data['location']) > 100:
        errors.append({'field': 'location', 'message': 'Location must not exceed 100 characters'})
    
    if 'learning_level' in data and data['learning_level'] not in ['Beginner', 'Intermediate', 'Advanced']:
        errors.append({'field': 'learning_level', 'message': 'Invalid learning level'})
    
    if 'learning_goals' in data and not isinstance(data.get('learning_goals'), list):
        errors.append({'field': 'learning_goals', 'message': 'Learning goals must be an array'})
    
    if 'weekly_availability_hours' in data:
        try:
            hours = float(data['weekly_availability_hours'])
            if hours < 0 or hours > 80:
                errors.append({'field': 'weekly_availability_hours', 'message': 'Weekly availability must be between 0 and 80 hours'})
        except (TypeError, ValueError):
            errors.append({'field': 'weekly_availability_hours', 'message': 'Invalid value for weekly availability'})
    
    if 'learning_pace' in data and data['learning_pace'] not in ['Self-paced', 'Structured', 'Accelerated']:
        errors.append({'field': 'learning_pace', 'message': 'Invalid learning pace'})
    
    if 'content_format' in data and data['content_format'] not in ['Video', 'Text', 'Projects', 'Mixed']:
        errors.append({'field': 'content_format', 'message': 'Invalid content format'})
    
    if 'focus_domains' in data and not isinstance(data.get('focus_domains'), list):
        errors.append({'field': 'focus_domains', 'message': 'Focus domains must be an array'})
    
    if errors:
        return jsonify({
            'detail': 'Validation error',
            'errors': errors,
            'error_code': 'VALIDATION_ERROR'
        }), 400
    
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        # Build update data
        update_data = {}
        
        if 'first_name' in data:
            update_data['firstName'] = data['first_name']
        if 'last_name' in data:
            update_data['lastName'] = data['last_name']
        if 'phone' in data:
            update_data['phone'] = data['phone'] or None
        if 'bio' in data:
            update_data['bio'] = data['bio'] or None
        if 'date_of_birth' in data:
            update_data['dateOfBirth'] = data['date_of_birth'] or None
        if 'location' in data:
            update_data['location'] = data['location'] or None
        if 'learning_level' in data:
            update_data['learningLevel'] = data['learning_level']
        if 'learning_goals' in data:
            update_data['learningGoals'] = data['learning_goals']
        if 'weekly_availability_hours' in data:
            update_data['weeklyAvailabilityHours'] = float(data['weekly_availability_hours'])
        if 'learning_pace' in data:
            update_data['learningPace'] = data['learning_pace']
        if 'content_format' in data:
            update_data['contentFormat'] = data['content_format']
        if 'focus_domains' in data:
            update_data['focusDomains'] = data['focus_domains']
        
        User.update(g.user['id'], update_data)
        
        # Fetch updated user
        updated_user = User.find_by_id(g.user['id'])
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': User.to_response(updated_user)
        })
        
    except Exception as e:
        print(f'Error updating profile: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# PUT /profile/avatar - Update Avatar
# ============================================
@profile_bp.route('/profile/avatar', methods=['PUT'])
@authenticate_token
def update_avatar():
    data = request.get_json() or {}
    avatar = data.get('avatar', '')
    
    if not avatar or not validate_url(avatar):
        return jsonify({
            'detail': 'Validation error',
            'errors': [{'field': 'avatar', 'message': 'Avatar must be a valid URL'}],
            'error_code': 'VALIDATION_ERROR'
        }), 400
    
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        User.update(g.user['id'], {'avatar': avatar})
        
        return jsonify({
            'message': 'Avatar updated successfully',
            'avatar': avatar
        })
        
    except Exception as e:
        print(f'Error updating avatar: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# GET /settings - Get User Settings
# ============================================
@profile_bp.route('/settings', methods=['GET'])
@authenticate_token
def get_settings():
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        return jsonify({
            'email': user.get('email'),
            'first_name': user.get('firstName'),
            'last_name': user.get('lastName'),
            'preferences': user.get('preferences') or {'theme': 'light', 'language': 'en', 'timezone': 'UTC'},
            'notifications': user.get('notifications') or {'email': True, 'quizReminders': True, 'progressUpdates': True, 'newsletter': False},
            'privacy': user.get('privacy') or {'profileVisibility': 'public', 'showEmail': False}
        })
        
    except Exception as e:
        print(f'Error fetching settings: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# PUT /settings - Update User Settings
# ============================================
@profile_bp.route('/settings', methods=['PUT'])
@authenticate_token
def update_settings():
    data = request.get_json() or {}
    
    # Validation
    errors = []
    
    if 'preferences' in data:
        prefs = data['preferences']
        if prefs.get('theme') and prefs['theme'] not in ['light', 'dark', 'auto']:
            errors.append({'field': 'preferences.theme', 'message': 'Invalid theme'})
    
    if 'privacy' in data:
        privacy = data['privacy']
        if privacy.get('profileVisibility') and privacy['profileVisibility'] not in ['public', 'private', 'friends']:
            errors.append({'field': 'privacy.profileVisibility', 'message': 'Invalid profile visibility'})
    
    if errors:
        return jsonify({
            'detail': 'Validation error',
            'errors': errors,
            'error_code': 'VALIDATION_ERROR'
        }), 400
    
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        update_data = {}
        
        # Update preferences
        if 'preferences' in data:
            current_prefs = user.get('preferences') or {}
            new_prefs = data['preferences']
            
            if 'theme' in new_prefs:
                current_prefs['theme'] = new_prefs['theme']
            if 'language' in new_prefs:
                current_prefs['language'] = new_prefs['language']
            if 'timezone' in new_prefs:
                current_prefs['timezone'] = new_prefs['timezone']
            
            update_data['preferences'] = current_prefs
        
        # Update notifications
        if 'notifications' in data:
            current_notifs = user.get('notifications') or {}
            new_notifs = data['notifications']
            
            if 'email' in new_notifs:
                current_notifs['email'] = bool(new_notifs['email'])
            if 'quizReminders' in new_notifs:
                current_notifs['quizReminders'] = bool(new_notifs['quizReminders'])
            if 'progressUpdates' in new_notifs:
                current_notifs['progressUpdates'] = bool(new_notifs['progressUpdates'])
            if 'newsletter' in new_notifs:
                current_notifs['newsletter'] = bool(new_notifs['newsletter'])
            
            update_data['notifications'] = current_notifs
        
        # Update privacy
        if 'privacy' in data:
            current_privacy = user.get('privacy') or {}
            new_privacy = data['privacy']
            
            if 'profileVisibility' in new_privacy:
                current_privacy['profileVisibility'] = new_privacy['profileVisibility']
            if 'showEmail' in new_privacy:
                current_privacy['showEmail'] = bool(new_privacy['showEmail'])
            
            update_data['privacy'] = current_privacy
        
        User.update(g.user['id'], update_data)
        
        return jsonify({
            'message': 'Settings updated successfully',
            'preferences': update_data.get('preferences', user.get('preferences')),
            'notifications': update_data.get('notifications', user.get('notifications')),
            'privacy': update_data.get('privacy', user.get('privacy'))
        })
        
    except Exception as e:
        print(f'Error updating settings: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# PUT /settings/password - Change Password
# ============================================
@profile_bp.route('/settings/password', methods=['PUT'])
@authenticate_token
def change_password():
    data = request.get_json() or {}
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    # Validation
    errors = []
    
    if not current_password:
        errors.append({'field': 'current_password', 'message': 'Current password is required'})
    
    if not new_password or len(new_password) < 8:
        errors.append({'field': 'new_password', 'message': 'New password must be at least 8 characters'})
    elif not re.search(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', new_password):
        errors.append({'field': 'new_password', 'message': 'New password must contain at least one uppercase letter, one lowercase letter, and one number'})
    
    if new_password != confirm_password:
        errors.append({'field': 'confirm_password', 'message': 'Passwords do not match'})
    
    if errors:
        return jsonify({
            'detail': 'Validation error',
            'errors': errors,
            'error_code': 'VALIDATION_ERROR'
        }), 400
    
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        # Verify current password
        if not User.check_password(current_password, user['hashedPassword']):
            return jsonify({
                'detail': 'Current password is incorrect',
                'error_code': 'INVALID_PASSWORD'
            }), 400
        
        # Hash and update new password
        hashed_password = User.hash_password(new_password)
        User.update(g.user['id'], {'hashedPassword': hashed_password})
        User.clear_password_reset_token(g.user['id'])  # Also updates passwordChangedAt
        
        return jsonify({
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        print(f'Error changing password: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# DELETE /account - Delete Account
# ============================================
@profile_bp.route('/account', methods=['DELETE'])
@authenticate_token
def delete_account():
    data = request.get_json() or {}
    
    password = data.get('password', '')
    confirmation = data.get('confirmation', '')
    
    # Validation
    errors = []
    
    if not password:
        errors.append({'field': 'password', 'message': 'Password is required for account deletion'})
    
    if confirmation != 'DELETE':
        errors.append({'field': 'confirmation', 'message': 'Please type DELETE to confirm'})
    
    if errors:
        return jsonify({
            'detail': 'Validation error',
            'errors': errors,
            'error_code': 'VALIDATION_ERROR'
        }), 400
    
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        # Verify password
        if not User.check_password(password, user['hashedPassword']):
            return jsonify({
                'detail': 'Invalid password',
                'error_code': 'INVALID_PASSWORD'
            }), 400
        
        # Log deletion
        print(f'Account deleted: userId={g.user["id"]}, email={user["email"]}, ip={get_client_ip()}')
        
        # Delete user
        User.delete(g.user['id'])
        
        return jsonify({
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        print(f'Error deleting account: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500


# ============================================
# GET /interests - Get User Interest Assessment
# ============================================
@profile_bp.route('/interests', methods=['GET'])
@authenticate_token
def get_interests():
    """Get user's saved interest assessment"""
    try:
        user = User.find_by_id(g.user['id'])
        
        if not user:
            return jsonify({
                'detail': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        interest_assessment = user.get('interestAssessment', {
            'completed': False,
            'primaryInterest': None,
            'confidence': 0,
            'allInterests': [],
            'completedAt': None,
            'lastUpdated': None
        })
        
        # If no interests found, return empty state
        if not interest_assessment.get('completed'):
            return jsonify({
                'completed': False,
                'message': 'No interest assessment completed yet'
            }), 200
        
        return jsonify({
            'completed': interest_assessment.get('completed', False),
            'primaryInterest': interest_assessment.get('primaryInterest'),
            'confidence': interest_assessment.get('confidence', 0),
            'allInterests': interest_assessment.get('allInterests', []),
            'domainScores': interest_assessment.get('domainScores'),
            'completedAt': interest_assessment.get('completedAt').isoformat() if interest_assessment.get('completedAt') else None,
            'focusDomains': user.get('focusDomains', [])
        })
        
    except Exception as e:
        print(f'Error fetching interests: {e}')
        return jsonify({
            'detail': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500
