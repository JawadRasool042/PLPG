"""
============================================
Token Utilities
============================================

Centralized token generation, parsing, and validation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import jwt
from config import get_config

config = get_config()
logger = logging.getLogger(__name__)


def parse_expiry_string(expiry_str: str) -> timedelta:
    """
    Parse expiry string to timedelta
    
    Formats:
    - "30m" = 30 minutes
    - "24h" = 24 hours
    - "7d" = 7 days
    - "3600s" = 3600 seconds
    
    Args:
        expiry_str: Expiry string
        
    Returns:
        timedelta object
    """
    if not expiry_str:
        return timedelta(minutes=30)
    
    expiry_str = expiry_str.strip().lower()
    
    try:
        if expiry_str.endswith('m'):
            minutes = int(expiry_str[:-1])
            return timedelta(minutes=minutes)
        elif expiry_str.endswith('h'):
            hours = int(expiry_str[:-1])
            return timedelta(hours=hours)
        elif expiry_str.endswith('d'):
            days = int(expiry_str[:-1])
            return timedelta(days=days)
        elif expiry_str.endswith('s'):
            seconds = int(expiry_str[:-1])
            return timedelta(seconds=seconds)
        else:
            # Default to minutes if no unit specified
            minutes = int(expiry_str)
            return timedelta(minutes=minutes)
    except (ValueError, IndexError):
        return timedelta(minutes=30)


def generate_user_tokens(user_id: str) -> Tuple[str, str]:
    """
    Generate access and refresh tokens for regular user
    
    Args:
        user_id: User ID
        
    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_delta = parse_expiry_string(config.JWT_EXPIRES_IN)
    refresh_delta = parse_expiry_string(config.JWT_REFRESH_EXPIRES_IN)
    
    now = datetime.utcnow()
    
    access_token = jwt.encode(
        {
            'sub': user_id,  # Subject (standard claim)
            'id': user_id,   # Keep for backward compatibility
            'type': 'user_access',
            'aud': 'plpg-user',  # Audience
            'iss': config.APP_DOMAIN,  # Issuer
            'iat': now,
            'exp': now + access_delta,
            'v': config.JWT_VERSION  # Token version
        },
        config.JWT_SECRET,
        algorithm='HS256'
    )
    
    refresh_token = jwt.encode(
        {
            'sub': user_id,
            'id': user_id,
            'type': 'user_refresh',
            'aud': 'plpg-user',
            'iss': config.APP_DOMAIN,
            'iat': now,
            'exp': now + refresh_delta,
            'v': config.JWT_VERSION
        },
        config.JWT_REFRESH_SECRET,
        algorithm='HS256'
    )
    
    return access_token, refresh_token


def generate_admin_tokens(admin_id: str) -> Tuple[str, str]:
    """
    Generate access and refresh tokens for admin
    
    Args:
        admin_id: Admin ID
        
    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_delta = parse_expiry_string(config.ADMIN_JWT_EXPIRE)
    refresh_delta = parse_expiry_string(config.ADMIN_JWT_REFRESH_EXPIRE)
    
    now = datetime.utcnow()
    
    access_token = jwt.encode(
        {
            'sub': admin_id,
            'id': admin_id,
            'isAdmin': True,
            'type': 'admin_access',
            'aud': 'plpg-admin',
            'iss': config.APP_DOMAIN,
            'iat': now,
            'exp': now + access_delta,
            'v': config.ADMIN_JWT_VERSION
        },
        config.ADMIN_JWT_SECRET,
        algorithm='HS256'
    )
    
    refresh_token = jwt.encode(
        {
            'sub': admin_id,
            'id': admin_id,
            'isAdmin': True,
            'type': 'admin_refresh',
            'aud': 'plpg-admin',
            'iss': config.APP_DOMAIN,
            'iat': now,
            'exp': now + refresh_delta,
            'v': config.ADMIN_JWT_VERSION
        },
        config.ADMIN_JWT_REFRESH_SECRET,
        algorithm='HS256'
    )
    
    return access_token, refresh_token


def verify_user_token(token: str, is_refresh: bool = False) -> Dict[str, Any] | None:
    """
    Verify user token
    
    Args:
        token: JWT token
        is_refresh: Whether this is a refresh token
        
    Returns:
        Decoded token or None if invalid
    """
    try:
        secret = config.JWT_REFRESH_SECRET if is_refresh else config.JWT_SECRET
        
        # Verify that secrets are properly configured
        if not secret:
            logger.error("JWT secret not configured")
            return None
        
        decoded = jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            audience='plpg-user',
            issuer=config.APP_DOMAIN,
            options={'verify_aud': True, 'verify_iss': True}
        )
        
        # Verify token version
        if decoded.get('v') != config.JWT_VERSION:
            logger.warning(f"Token version mismatch: {decoded.get('v')} vs {config.JWT_VERSION}")
            return None
        
        # Verify token type
        expected_type = 'user_refresh' if is_refresh else 'user_access'
        if decoded.get('type') != expected_type:
            logger.warning(f"Unexpected token type: {decoded.get('type')}")
            return None
        
        return decoded
    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def verify_admin_token(token: str, is_refresh: bool = False) -> Dict[str, Any] | None:
    """
    Verify admin token
    
    Args:
        token: JWT token
        is_refresh: Whether this is a refresh token
        
    Returns:
        Decoded token or None if invalid
    """
    try:
        secret = config.ADMIN_JWT_REFRESH_SECRET if is_refresh else config.ADMIN_JWT_SECRET
        
        # Verify that secrets are properly configured
        if not secret:
            logger.error("ADMIN_JWT secret not configured")
            return None
        
        decoded = jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            audience='plpg-admin',
            issuer=config.APP_DOMAIN,
            options={'verify_aud': True, 'verify_iss': True}
        )
        
        # Verify token version
        if decoded.get('v') != config.ADMIN_JWT_VERSION:
            logger.warning(f"Admin token version mismatch: {decoded.get('v')} vs {config.ADMIN_JWT_VERSION}")
            return None
        
        # Verify token type
        expected_type = 'admin_refresh' if is_refresh else 'admin_access'
        if decoded.get('type') != expected_type:
            logger.warning(f"Unexpected admin token type: {decoded.get('type')}")
            return None
        
        # Verify admin flag
        if not decoded.get('isAdmin'):
            logger.warning("Token missing admin flag")
            return None
        
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("Admin token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid admin token: {e}")
        return None


def get_token_expiry_seconds(token: str) -> int | None:
    """
    Get remaining seconds until token expiry (without verification)
    
    Args:
        token: JWT token
        
    Returns:
        Seconds remaining or None if invalid
    """
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp')
        if exp:
            remaining = exp - datetime.utcnow().timestamp()
            return max(0, int(remaining))
        return None
    except:
        return None
