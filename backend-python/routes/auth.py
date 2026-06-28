"""
============================================
Authentication Routes - Production Ready
============================================

SECURITY FEATURES:
- Cryptographically secure tokens
- Rate limiting on sensitive endpoints
- Comprehensive audit logging
- IP and User-Agent tracking
- Prevents user enumeration

ENDPOINTS:
POST /register          - Create new user + send verification email
POST /verify-email      - Verify email with token (POST for frontend)
GET  /verify/<token>    - Verify email with token (GET for email links)
POST /resend-verification - Resend verification email (rate limited)
POST /login             - Authenticate user (requires verified email)
GET  /me                - Get current user info
POST /forgot-password   - Request password reset
POST /reset-password    - Set new password
"""

import os
import re
import jwt
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, redirect, g

import bcrypt

from config import get_config
from models.user import User
from middleware.auth import authenticate_token, get_client_ip, get_user_agent
from services.email_service import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
    get_email_config_status,
    EmailService,
)
from utils.token_utils import generate_user_tokens, verify_user_token, get_token_expiry_seconds

config = get_config()
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# Email verification temporarily disabled — set False to re-enable verify-email + SMTP flow
EMAIL_VERIFICATION_DISABLED = True


# ============================================
# Rate Limiting (In-Memory)
# ============================================
rate_limit_store = {}


def create_rate_limiter(window_ms: int, max_requests: int, key_func, message: str):
    """Create a rate limiter decorator"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = key_func(request)
            now = time.time() * 1000  # milliseconds
            
            # Clean expired entries
            if key in rate_limit_store:
                entry = rate_limit_store[key]
                if now > entry['resetTime']:
                    del rate_limit_store[key]
            
            if key not in rate_limit_store:
                rate_limit_store[key] = {
                    'count': 1,
                    'resetTime': now + window_ms
                }
                return f(*args, **kwargs)
            
            entry = rate_limit_store[key]
            
            if entry['count'] >= max_requests:
                retry_after = int((entry['resetTime'] - now) / 1000)
                return jsonify({
                    'detail': message,
                    'retry_after_seconds': retry_after,
                    'error_code': 'RATE_LIMIT_EXCEEDED'
                }), 429
            
            entry['count'] += 1
            return f(*args, **kwargs)
        
        return decorated
    return decorator


# Rate limiter key generators
def get_ip_key(prefix):
    return lambda req: f"{prefix}:{get_client_ip()}"


def get_email_key(prefix):
    def key_gen(req):
        email = req.get_json(silent=True) or {}
        return f"{prefix}:{email.get('email', '').lower() or get_client_ip()}"
    return key_gen


# ============================================
# Validation Functions
# ============================================
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple:
    """
    Validate password strength
    Returns: (is_valid, error_messages)
    """
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one number')
    
    return len(errors) == 0, errors


def log_security_event(event: str, details: dict):
    """Log security event"""
    timestamp = datetime.utcnow().isoformat()
    print(f'[SECURITY] {timestamp} - {event}: {details}')


def normalize_verification_token(raw) -> str:
    """Trim junk from pasted or JSON-borne tokens."""
    if raw is None:
        return ''
    return str(raw).strip().strip('"').strip("'")


def is_valid_verification_token_shape(token: str) -> bool:
    """secrets.token_hex(32) emits 64 hex chars."""
    return bool(token) and len(token) == 64 and re.fullmatch(r'[0-9a-fA-F]{64}', token) is not None


def _is_production_runtime() -> bool:
    return bool(getattr(config, 'IS_PRODUCTION', False))


def _dev_email_env_flags() -> tuple[bool, bool]:
    """(ALLOW_DEV_EMAIL_WITHOUT_SMTP, PLPG_FORCE_EMAIL_DEV_LINKS) as booleans."""
    def _truthy(name: str) -> bool:
        return os.getenv(name, '').strip().lower() in ('1', 'true', 'yes', 'on')

    return _truthy('ALLOW_DEV_EMAIL_WITHOUT_SMTP'), _truthy('PLPG_FORCE_EMAIL_DEV_LINKS')


def _dev_email_bypass_after_failed_send(not_configured: bool) -> bool:
    """
    When SMTP is missing or sending failed, optionally still complete onboarding in dev.

    - Non-production only.
    - If email is not configured: ALLOW_DEV_EMAIL_WITHOUT_SMTP or PLPG_FORCE_EMAIL_DEV_LINKS.
    - If configured but send failed: PLPG_FORCE_EMAIL_DEV_LINKS only.
    """
    if _is_production_runtime():
        return False
    allow, force = _dev_email_env_flags()
    if not_configured:
        return allow or force
    return force


def _dev_verification_dict(raw_token: str) -> dict:
    base = (config.FRONTEND_BASE_URL or os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')).rstrip('/')
    url = f'{base}/verify-email?token={raw_token}'
    return {
        'verification_token': raw_token,
        'verification_url': url,
        'dev_note': (
            'Development bypass: open verification_url in the browser. '
            'For production, set EMAIL_USER, EMAIL_PASSWORD (Gmail App Password), and EMAIL_FROM.'
        ),
    }


def _dev_password_reset_dict(reset_token: str) -> dict:
    base = (config.FRONTEND_BASE_URL or os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')).rstrip('/')
    url = f'{base}/reset-password?token={reset_token}'
    return {
        'reset_token': reset_token,
        'reset_url': url,
        'dev_note': (
            'Development bypass: SMTP not used; use reset_url to set a new password. '
            'Configure EMAIL_USER / EMAIL_PASSWORD for production.'
        ),
    }


# ============================================
# ROUTE: Register a new user
# ============================================
@auth_bp.route('/register', methods=['POST'])
@create_rate_limiter(
    window_ms=60 * 60 * 1000,  # 1 hour
    max_requests=50,  # increased for development
    key_func=get_ip_key('register'),
    message='Too many registration attempts. Please try again in an hour.'
)
def register():
    data = request.get_json() or {}
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    role = data.get('role', 'Student')
    
    # Validation
    errors = []
    
    if not email or not validate_email(email):
        errors.append({'field': 'email', 'message': 'Valid email is required'})
    
    is_valid_password, password_errors = validate_password(password)
    if not is_valid_password:
        errors.append({'field': 'password', 'message': '; '.join(password_errors)})
    
    if not first_name or len(first_name) > 50:
        errors.append({'field': 'first_name', 'message': 'First name is required (max 50 characters)'})
    
    if not last_name or len(last_name) > 50:
        errors.append({'field': 'last_name', 'message': 'Last name is required (max 50 characters)'})
    
    if role not in ['Student', 'Teacher']:
        errors.append({'field': 'role', 'message': 'Role must be Student or Teacher'})
    
    if errors:
        return jsonify({
            'detail': 'Validation failed',
            'errors': errors
        }), 400
    
    client_ip = get_client_ip()
    
    try:
        # Check if user already exists
        existing_user = User.find_by_email(email)
        if existing_user:
            log_security_event('REGISTRATION_DUPLICATE_EMAIL', {'email': email, 'ip': client_ip})
            return jsonify({'detail': 'An account with this email already exists'}), 400
        
        # Hash password
        hashed_password = User.hash_password(password)
        
        # Create user
        user = User.create({
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'hashedPassword': hashed_password,
            'role': role,
            'isActive': True,
            'isEmailVerified': True,  # verification disabled — users can log in immediately
        })
        
        user_id = str(user['_id'])
        
        log_security_event('USER_REGISTERED', {
            'userId': user_id,
            'email': email,
            'ip': client_ip
        })

        # EMAIL VERIFICATION DISABLED — set EMAIL_VERIFICATION_DISABLED=False to re-enable
        if not EMAIL_VERIFICATION_DISABLED:
            raw_token = User.set_verification_token(user_id)

            email_status = get_email_config_status()
            email_sent = False

            if email_status.get('configured'):
                try:
                    email_sent = bool(send_verification_email(email, raw_token, first_name))
                    if email_sent:
                        User.mark_verification_email_dispatched(user_id)
                    else:
                        last_err = EmailService.get_last_error()
                        log_security_event('VERIFICATION_EMAIL_FAILED', {
                            'email': email,
                            'error': 'SMTP send returned false',
                            'smtp_last_error': last_err,
                        })
                except Exception as e:
                    log_security_event('VERIFICATION_EMAIL_FAILED', {'email': email, 'error': str(e)})

            if email_sent:
                response_payload = {
                    'id': user_id,
                    'email': user['email'],
                    'first_name': user['firstName'],
                    'last_name': user['lastName'],
                    'role': user['role'],
                    'is_active': user['isActive'],
                    'is_email_verified': False,
                    'message': 'Registration successful! Please check your email to verify your account.',
                    'email_sent': True,
                    'created_at': user['createdAt'].isoformat() if user.get('createdAt') else None,
                }
                return jsonify(response_payload), 201

            not_configured = not email_status.get('configured')
            if _dev_email_bypass_after_failed_send(not_configured):
                log_security_event('REGISTER_DEV_EMAIL_BYPASS', {
                    'userId': user_id,
                    'email': email,
                    'ip': client_ip,
                    'not_configured': not_configured,
                })
                logger.warning(
                    'REGISTER_DEV_EMAIL_BYPASS user=%s email=%s not_configured=%s',
                    user_id,
                    email,
                    not_configured,
                )
                response_payload = {
                    'id': user_id,
                    'email': user['email'],
                    'first_name': user['firstName'],
                    'last_name': user['lastName'],
                    'role': user['role'],
                    'is_active': user['isActive'],
                    'is_email_verified': False,
                    'message': (
                        'Registration successful. SMTP is skipped in development — use the verification link '
                        'returned in this response to verify your email.'
                    ),
                    'email_sent': False,
                    'dev_fallback': True,
                    'verification': _dev_verification_dict(raw_token),
                    'created_at': user['createdAt'].isoformat() if user.get('createdAt') else None,
                }
                return jsonify(response_payload), 201

            if not_configured:
                logger.error("Email service not configured - missing EMAIL_USER / EMAIL_PASSWORD (or EMAIL_PASS)")
                return jsonify({
                    'success': False,
                    'detail': (
                        'Email service is not configured. Set EMAIL_USER / EMAIL_PASSWORD (Gmail App Password) '
                        'and EMAIL_FROM in .env, then restart Flask. For local testing without SMTP, set '
                        'ALLOW_DEV_EMAIL_WITHOUT_SMTP=true (non-production only).'
                    ),
                    'message': 'Email service is not configured. Registration temporarily unavailable.',
                    'error_code': 'EMAIL_NOT_CONFIGURED',
                    'missing_settings': email_status.get('issues', []),
                    'email_provider': email_status.get('provider', 'gmail'),
                    'hint': (
                        'Gmail: use an App Password (Google Account → Security → App passwords). '
                        'Set EMAIL_USER, EMAIL_PASSWORD, and EMAIL_FROM to real Gmail values, then restart the server.'
                    ),
                }), 500

            last_err = EmailService.get_last_error()
            logger.error(
                'REGISTER_EMAIL_SEND_FAILED email=%s smtp_last_error=%s',
                email,
                last_err,
            )
            return jsonify({
                'success': False,
                'detail': (
                    'Failed to send verification email. Check Gmail App Password, EMAIL_FROM, and SMTP settings. '
                    'In non-production you may set PLPG_FORCE_EMAIL_DEV_LINKS=true to receive a verification URL in the API response.'
                ),
                'message': 'Verification email could not be sent.',
                'error_code': 'EMAIL_SEND_FAILED',
                'smtp_last_error': last_err,
            }), 500

        return jsonify({
            'id': user_id,
            'email': user['email'],
            'first_name': user['firstName'],
            'last_name': user['lastName'],
            'role': user['role'],
            'is_active': user['isActive'],
            'is_email_verified': True,
            'message': 'Registration successful! You can log in now.',
            'email_sent': False,
            'created_at': user['createdAt'].isoformat() if user.get('createdAt') else None,
        }), 201

    except Exception as e:
        print(f'Registration error: {e}')
        log_security_event('REGISTRATION_ERROR', {'email': email, 'error': str(e), 'ip': client_ip})
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500


# ============================================
# ROUTE: Verify email (POST - for frontend)
# ============================================
@auth_bp.route('/verify-email', methods=['POST'])
@create_rate_limiter(
    window_ms=15 * 60 * 1000,  # 15 minutes
    max_requests=10,
    key_func=get_ip_key('verify'),
    message='Too many verification attempts. Please try again later.'
)
def verify_email():
    if EMAIL_VERIFICATION_DISABLED:
        return jsonify({'detail': 'Email verification is currently disabled'}), 404

    data = request.get_json() or {}
    token = normalize_verification_token(data.get('token'))

    if not is_valid_verification_token_shape(token):
        return jsonify({
            'detail': 'Invalid verification token',
            'error_code': 'INVALID_TOKEN_FORMAT'
        }), 400
    
    client_ip = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        user = User.find_by_verification_token(token)
        
        if not user:
            log_security_event('VERIFICATION_INVALID_TOKEN', {'ip': client_ip, 'userAgent': user_agent})
            return jsonify({
                'detail': 'Invalid verification token. Please request a new verification email.',
                'error_code': 'INVALID_TOKEN'
            }), 400
        
        user_id = str(user['_id'])
        
        # Check if already verified
        if user.get('isEmailVerified'):
            return jsonify({
                'detail': 'Email is already verified',
                'error_code': 'ALREADY_VERIFIED',
                'email': user['email']
            }), 400
        
        # Check if token has expired
        token_expiry = user.get('emailVerificationTokenExpiry')
        if not token_expiry or token_expiry < datetime.utcnow():
            log_security_event('VERIFICATION_TOKEN_EXPIRED', {
                'userId': user_id,
                'email': user['email'],
                'ip': client_ip
            })
            return jsonify({
                'detail': 'Verification link has expired. Please request a new verification email.',
                'error_code': 'TOKEN_EXPIRED',
                'email': user['email']
            }), 400
        
        # Mark as verified
        User.mark_email_verified(user_id, client_ip, user_agent)
        
        log_security_event('EMAIL_VERIFIED', {
            'userId': user_id,
            'email': user['email'],
            'ip': client_ip
        })
        
        # Send welcome email
        try:
            send_welcome_email(user['email'], user['firstName'])
        except Exception as e:
            print(f'Welcome email error: {e}')
        
        return jsonify({
            'message': 'Email verified successfully! You can now log in.',
            'success': True,
            'id': user_id,
            'email': user['email'],
            'is_email_verified': True
        })
        
    except Exception as e:
        print(f'Email verification error: {e}')
        log_security_event('VERIFICATION_ERROR', {'error': str(e), 'ip': client_ip})
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500


# ============================================
# ROUTE: Verify email (GET - for email links)
# ============================================
@auth_bp.route('/verify/<token>', methods=['GET'])
@create_rate_limiter(
    window_ms=15 * 60 * 1000,
    max_requests=10,
    key_func=get_ip_key('verify_get'),
    message='Too many verification attempts.'
)
def verify_email_get(token):
    frontend_url = config.FRONTEND_BASE_URL
    if EMAIL_VERIFICATION_DISABLED:
        return redirect(f'{frontend_url}/login')

    token = normalize_verification_token(token)

    if not is_valid_verification_token_shape(token):
        return redirect(f'{frontend_url}/verify-email?error=true&code=INVALID_TOKEN')
    
    client_ip = get_client_ip()
    user_agent = get_user_agent()
    
    try:
        user = User.find_by_verification_token(token)
        
        if not user:
            log_security_event('VERIFICATION_INVALID_TOKEN_GET', {'ip': client_ip})
            return redirect(f'{frontend_url}/verify-email?error=true&code=INVALID_TOKEN')
        
        user_id = str(user['_id'])
        email = user['email']
        
        if user.get('isEmailVerified'):
            return redirect(f'{frontend_url}/verify-email?success=true&already_verified=true&email={email}')
        
        token_expiry = user.get('emailVerificationTokenExpiry')
        if not token_expiry or token_expiry < datetime.utcnow():
            return redirect(f'{frontend_url}/verify-email?error=true&code=TOKEN_EXPIRED&email={email}')
        
        # Mark as verified
        User.mark_email_verified(user_id, client_ip, user_agent)
        
        log_security_event('EMAIL_VERIFIED_GET', {
            'userId': user_id,
            'email': email,
            'ip': client_ip
        })
        
        # Send welcome email
        try:
            send_welcome_email(email, user['firstName'])
        except:
            pass
        
        return redirect(f'{frontend_url}/verify-email?success=true&email={email}')
        
    except Exception as e:
        print(f'Email verification GET error: {e}')
        return redirect(f'{frontend_url}/verify-email?error=true&code=SERVER_ERROR')


# ============================================
# ROUTE: Resend verification email
# ============================================
@auth_bp.route('/resend-verification', methods=['POST'])
@create_rate_limiter(
    window_ms=5 * 60 * 1000,  # 5 minutes
    max_requests=8,
    key_func=get_email_key('resend'),
    message='Please wait 5 minutes before requesting another verification email.'
)
def resend_verification():
    if EMAIL_VERIFICATION_DISABLED:
        return jsonify({'detail': 'Email verification is currently disabled'}), 404

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email or not validate_email(email):
        return jsonify({'detail': 'Please provide a valid email address'}), 400
    
    client_ip = get_client_ip()
    
    try:
        user = User.find_by_email(email)
        
        # Always return success to prevent email enumeration
        if not user:
            log_security_event('RESEND_UNKNOWN_EMAIL', {'email': email, 'ip': client_ip})
            return jsonify({
                'message': 'If an account exists with this email, a verification link has been sent.',
                'success': True
            })
        
        if user.get('isEmailVerified'):
            return jsonify({
                'detail': 'This email is already verified. You can log in.',
                'error_code': 'ALREADY_VERIFIED'
            }), 400
        
        # Check rate limiting at user level
        can_resend = User.can_resend_verification_email(user)
        if not can_resend['allowed']:
            log_security_event('RESEND_RATE_LIMITED', {'email': email, 'ip': client_ip})
            return jsonify({
                'detail': can_resend['message'],
                'retry_after_seconds': can_resend['remainingSeconds'],
                'error_code': 'RATE_LIMITED'
            }), 429
        
        user_id = str(user['_id'])
        
        # Generate new token
        raw_token = User.set_verification_token(user_id)

        email_status = get_email_config_status()
        email_sent = False

        if email_status.get('configured'):
            email_sent = send_verification_email(email, raw_token, user['firstName'])
            if email_sent:
                User.mark_verification_email_dispatched(user_id)

        if email_sent:
            response_payload = {
                'message': 'Verification email sent! Please check your inbox.',
                'success': True,
                'email_sent': True,
                'dev_fallback': False,
            }
            log_security_event('VERIFICATION_EMAIL_RESENT', {
                'userId': user_id,
                'email': email,
                'ip': client_ip,
                'email_sent': True,
                'dev_fallback': False,
            })
            return jsonify(response_payload)

        not_configured = not email_status.get('configured')
        if _dev_email_bypass_after_failed_send(not_configured):
            log_security_event('RESEND_DEV_EMAIL_BYPASS', {
                'userId': user_id,
                'email': email,
                'ip': client_ip,
                'not_configured': not_configured,
            })
            logger.warning('RESEND_DEV_EMAIL_BYPASS user=%s email=%s', user_id, email)
            return jsonify({
                'message': (
                    'SMTP is skipped in development. Use the verification link in this response to verify your account.'
                ),
                'success': True,
                'email_sent': False,
                'dev_fallback': True,
                'verification': _dev_verification_dict(raw_token),
            })

        if not_configured:
            log_security_event('RESEND_EMAIL_NOT_CONFIGURED', {'email': email, 'ip': client_ip})
            return jsonify({
                'detail': (
                    'Email service is not configured. Set EMAIL_USER / EMAIL_PASSWORD (Gmail App Password) '
                    'and EMAIL_FROM in .env, then restart Flask. For local testing without SMTP, set '
                    'ALLOW_DEV_EMAIL_WITHOUT_SMTP=true (non-production only).'
                ),
                'error_code': 'EMAIL_NOT_CONFIGURED',
                'missing_settings': email_status.get('issues', []),
                'email_provider': email_status.get('provider', 'gmail'),
                'hint': 'Gmail uses an App Password, not your normal password.',
            }), 500

        log_security_event('RESEND_EMAIL_FAILED', {'email': email, 'ip': client_ip})
        last_err = EmailService.get_last_error()
        payload = {
            'detail': (
                'Failed to send verification email. Wrong App Password / blocked SMTP / or EMAIL_FROM mismatch. '
                'Check Flask logs; fix EMAIL_PASSWORD and EMAIL_FROM, restart the server. '
                'In non-production you may set PLPG_FORCE_EMAIL_DEV_LINKS=true to receive a verification URL in the API response.'
            ),
            'error_code': 'EMAIL_SEND_FAILED',
        }
        if last_err:
            payload['smtp_last_error'] = last_err
        return jsonify(payload), 500
        
    except Exception as e:
        print(f'Resend verification error: {e}')
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500


# ============================================
# ROUTE: Login user
# ============================================
@auth_bp.route('/login', methods=['POST'])
@create_rate_limiter(
    window_ms=15 * 60 * 1000,  # 15 minutes
    max_requests=5,
    key_func=get_email_key('login'),
    message='Too many login attempts. Please try again in 15 minutes.'
)
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'detail': 'Invalid email or password format'}), 400
    
    client_ip = get_client_ip()
    
    try:
        user = User.find_by_email(email)
        
        if not user:
            # Prevent timing attacks - simulate password check
            bcrypt.checkpw(password.encode(), b'$2a$12$invalid.hash.for.timing.attack.prevention')
            log_security_event('LOGIN_UNKNOWN_EMAIL', {'email': email, 'ip': client_ip})
            return jsonify({'detail': 'Invalid email or password'}), 401
        
        user_id = str(user['_id'])
        
        # Check if account is locked
        if User.is_locked(user):
            log_security_event('LOGIN_ACCOUNT_LOCKED', {'email': email, 'ip': client_ip})
            return jsonify({
                'detail': 'Account is temporarily locked. Please try again later.',
                'error_code': 'ACCOUNT_LOCKED'
            }), 423
        
        # Check password
        is_valid = User.check_password(password, user['hashedPassword'])
        
        if not is_valid:
            User.increment_login_attempts(user_id, user)
            log_security_event('LOGIN_INVALID_PASSWORD', {'email': email, 'ip': client_ip})
            return jsonify({'detail': 'Invalid email or password'}), 401

        # Email verification disabled — auto-verify legacy accounts so login always works
        if not user.get('isEmailVerified'):
            User.mark_email_verified(user_id, client_ip, get_user_agent())

        # --- EMAIL VERIFICATION (disabled) ---
        # if not user.get('isEmailVerified'):
        #     log_security_event('LOGIN_UNVERIFIED', {'email': email, 'ip': client_ip})
        #     return jsonify({
        #         'detail': 'Please verify your email address before logging in',
        #         'email': user['email'],
        #         'requires_verification': True,
        #         'error_code': 'EMAIL_NOT_VERIFIED'
        #     }), 403
        
        # Reset login attempts
        User.reset_login_attempts(user_id)
        
        # Generate tokens using centralized utility
        access_token, refresh_token = generate_user_tokens(user_id)
        
        # Get token expiry
        access_expiry_seconds = get_token_expiry_seconds(access_token)
        
        log_security_event('LOGIN_SUCCESS', {'userId': user_id, 'email': email, 'ip': client_ip})
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': access_expiry_seconds,
            'user': {
                'id': user_id,
                'email': user['email'],
                'first_name': user['firstName'],
                'last_name': user['lastName'],
                'role': user['role']
            }
        })
        
    except Exception as e:
        print(f'Login error: {e}')
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500


# ============================================
# ROUTE: Refresh access token
# ============================================
@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_access_token():
    """
    Refresh user access token using refresh token
    
    Request body:
    {
        "refresh_token": "..."
    }
    """
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token', '')
    
    if not refresh_token:
        return jsonify({
            'detail': 'Refresh token is required',
            'error_code': 'NO_REFRESH_TOKEN'
        }), 400
    
    client_ip = get_client_ip()
    
    try:
        # Verify refresh token
        decoded = verify_user_token(refresh_token, is_refresh=True)
        
        if not decoded:
            log_security_event('REFRESH_TOKEN_INVALID', {'ip': client_ip})
            return jsonify({
                'detail': 'Invalid or expired refresh token',
                'error_code': 'INVALID_REFRESH_TOKEN'
            }), 401
        
        user_id = decoded.get('id')
        user = User.find_by_id(user_id)
        
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
        
        # Generate new tokens (refresh token rotation)
        new_access_token, new_refresh_token = generate_user_tokens(user_id)
        access_expiry_seconds = get_token_expiry_seconds(new_access_token)
        
        log_security_event('TOKEN_REFRESHED', {'userId': user_id, 'email': user['email'], 'ip': client_ip})
        
        return jsonify({
            'access_token': new_access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'bearer',
            'expires_in': access_expiry_seconds
        })
        
    except Exception as e:
        print(f'Token refresh error: {e}')
        return jsonify({
            'detail': 'An unexpected error occurred. Please try again.',
            'error_code': 'REFRESH_ERROR'
        }), 500


# ============================================
# ROUTE: Get current user
# ============================================
@auth_bp.route('/me', methods=['GET'])
@authenticate_token
def get_me():
    try:
        user = User.find_by_email(g.user['email'])

        if not user:
            return jsonify({'detail': 'User not found'}), 404

        # Serialize the stored interestAssessment so the frontend can rehydrate
        # onboarding state from the server (Requirement C4).
        assessment_doc = user.get('interestAssessment') or {}
        interest_assessment = None
        if assessment_doc.get('completed'):
            interest_assessment = {
                'completed': True,
                'primaryInterest': assessment_doc.get('primaryInterest'),
                'confidence': assessment_doc.get('confidence', 0),
                'allInterests': assessment_doc.get('allInterests', []),
                'domainScores': assessment_doc.get('domainScores'),
                'tieResolved': bool(assessment_doc.get('tieResolved')),
                'completedAt': (
                    assessment_doc.get('completedAt').isoformat()
                    if hasattr(assessment_doc.get('completedAt'), 'isoformat')
                    else assessment_doc.get('completedAt')
                ),
                'lastUpdated': (
                    assessment_doc.get('lastUpdated').isoformat()
                    if hasattr(assessment_doc.get('lastUpdated'), 'isoformat')
                    else assessment_doc.get('lastUpdated')
                ),
                'assessmentContext': assessment_doc.get('assessmentContext'),
                'assessmentTags': assessment_doc.get('assessmentTags') or [],
            }

        return jsonify({
            'id': str(user['_id']),
            'email': user['email'],
            'first_name': user['firstName'],
            'last_name': user['lastName'],
            'role': user['role'],
            'is_active': user.get('isActive'),
            'is_email_verified': user.get('isEmailVerified'),
            'email_verified_at': user.get('emailVerifiedAt').isoformat() if user.get('emailVerifiedAt') else None,
            'created_at': user.get('createdAt').isoformat() if user.get('createdAt') else None,
            'interestAssessment': interest_assessment,
            'focusDomains': user.get('focusDomains', []),
        })

    except Exception as e:
        print(f'Get user error: {e}')
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500


# ============================================
# ROUTE: Forgot password
# ============================================
@auth_bp.route('/forgot-password', methods=['POST'])
@create_rate_limiter(
    window_ms=60 * 60 * 1000,  # 1 hour
    max_requests=3,
    key_func=get_email_key('forgot'),
    message='Too many password reset requests. Please try again in an hour.'
)
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    success_message = 'If an account exists with this email, you will receive a password reset link shortly.'
    
    if not email or not validate_email(email):
        return jsonify({'detail': 'Please provide a valid email address'}), 400
    
    client_ip = get_client_ip()
    
    try:
        user = User.find_by_email(email)
        
        if not user:
            log_security_event('FORGOT_PASSWORD_UNKNOWN_EMAIL', {'email': email, 'ip': client_ip})
            return jsonify({'message': success_message, 'success': True})
        
        user_id = str(user['_id'])
        
        # Generate password reset token
        reset_token = User.set_password_reset_token(user_id)

        email_status = get_email_config_status()
        email_sent = False
        if email_status.get('configured'):
            email_sent = send_password_reset_email(email, reset_token, user['firstName'])

        if email_sent:
            log_security_event('PASSWORD_RESET_REQUESTED', {
                'userId': user_id,
                'email': email,
                'ip': client_ip
            })
            return jsonify({'message': success_message, 'success': True, 'email_sent': True})

        not_configured = not email_status.get('configured')
        if _dev_email_bypass_after_failed_send(not_configured):
            log_security_event('FORGOT_PASSWORD_DEV_EMAIL_BYPASS', {
                'userId': user_id,
                'email': email,
                'ip': client_ip,
                'not_configured': not_configured,
            })
            logger.warning('FORGOT_PASSWORD_DEV_EMAIL_BYPASS user=%s email=%s', user_id, email)
            return jsonify({
                'message': (
                    'Development mode: no email was sent. Use the reset link in this response to set a new password.'
                ),
                'success': True,
                'email_sent': False,
                'dev_fallback': True,
                'password_reset': _dev_password_reset_dict(reset_token),
            })

        log_security_event('PASSWORD_RESET_EMAIL_FAILED', {'email': email, 'ip': client_ip})
        return jsonify({'message': success_message, 'success': True})
        
    except Exception as e:
        print(f'Forgot password error: {e}')
        # Still return success to prevent enumeration
        return jsonify({'message': success_message, 'success': True})


# ============================================
# ROUTE: Reset password
# ============================================
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    token = data.get('token', '')
    password = data.get('password', '')
    
    # Validation
    if not token or len(token) != 64:
        return jsonify({
            'detail': 'Invalid reset token',
            'error_code': 'INVALID_TOKEN'
        }), 400
    
    is_valid_password, password_errors = validate_password(password)
    if not is_valid_password:
        return jsonify({
            'detail': 'Invalid input. ' + '; '.join(password_errors),
            'errors': [{'field': 'password', 'message': msg} for msg in password_errors]
        }), 400
    
    client_ip = get_client_ip()
    
    try:
        user = User.find_by_password_reset_token(token)
        
        if not user:
            log_security_event('PASSWORD_RESET_INVALID_TOKEN', {'ip': client_ip})
            return jsonify({
                'detail': 'Invalid or expired reset token. Please request a new password reset.',
                'error_code': 'INVALID_TOKEN'
            }), 400
        
        user_id = str(user['_id'])
        
        # Hash new password
        hashed_password = User.hash_password(password)
        
        # Update user
        User.update(user_id, {
            'hashedPassword': hashed_password,
            'loginAttempts': 0,
            'lockUntil': None
        })
        User.clear_password_reset_token(user_id)
        
        log_security_event('PASSWORD_RESET_SUCCESS', {
            'userId': user_id,
            'email': user['email'],
            'ip': client_ip
        })
        
        return jsonify({
            'message': 'Password reset successfully! You can now log in with your new password.',
            'success': True
        })
        
    except Exception as e:
        print(f'Reset password error: {e}')
        return jsonify({'detail': 'An unexpected error occurred. Please try again.'}), 500
