"""
============================================
Configuration Module
============================================

Manages all application configuration from environment variables
"""

import os
import warnings
import secrets
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values


def _env_value_nonempty(d: dict, key: str) -> Optional[str]:
    v = d.get(key)
    if v is None or str(v).strip() == '':
        return None
    return str(v).strip()


_BACKEND_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_ROOT.parent


def bootstrap_env_files() -> None:
    """
    Merge repo-root .env with backend-python/.env:
    nonempty backend wins; otherwise use nonempty repo-root value.

    Fixes backend-python/.env empty EMAIL_* shadowing real Gmail creds in repo/.env.
    """
    backend_file = _BACKEND_ROOT / '.env'
    repo_file = _REPO_ROOT / '.env'

    rb = dotenv_values(repo_file) if repo_file.exists() else {}
    bb = dotenv_values(backend_file) if backend_file.exists() else {}
    keys = set(rb.keys()) | set(bb.keys())

    for k in keys:
        if not k or k.startswith('\ufeff'):
            continue
        bv = _env_value_nonempty(bb, k)
        rv = _env_value_nonempty(rb, k)
        val = bv if bv is not None else rv
        if val is not None:
            os.environ[k] = val


bootstrap_env_files()


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/plpg')
    MONGODB_POOL_SIZE = int(os.getenv('MONGODB_POOL_SIZE', 10))
    MONGODB_MIN_POOL_SIZE = int(os.getenv('MONGODB_MIN_POOL_SIZE', 2))
    
    # JWT Configuration - MUST be set in .env for production
    JWT_SECRET = os.getenv('JWT_SECRET')
    JWT_EXPIRES_IN = os.getenv('JWT_EXPIRES_IN', '30m')
    JWT_REFRESH_SECRET = os.getenv('JWT_REFRESH_SECRET')
    JWT_REFRESH_EXPIRES_IN = os.getenv('JWT_REFRESH_EXPIRES_IN', '7d')
    
    # Admin JWT (separate for extra security) - MUST be set in .env for production
    ADMIN_JWT_SECRET = os.getenv('ADMIN_JWT_SECRET', JWT_SECRET)
    ADMIN_JWT_EXPIRE = os.getenv('ADMIN_JWT_EXPIRE', '24h')
    ADMIN_JWT_REFRESH_SECRET = os.getenv('ADMIN_JWT_REFRESH_SECRET', JWT_REFRESH_SECRET)
    ADMIN_JWT_REFRESH_EXPIRE = os.getenv('ADMIN_JWT_REFRESH_EXPIRE', '7d')
    
    # Token versioning for future migrations
    JWT_VERSION = 1
    ADMIN_JWT_VERSION = 1
    
    # Email (EMAIL_SERVICE=gmail presets smtp.gmail.com in email_service; see .env.example)
    EMAIL_SERVICE = os.getenv('EMAIL_SERVICE', 'gmail')
    EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', EMAIL_SERVICE)
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', EMAIL_USER)
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    
    # Email Token Settings
    EMAIL_TOKEN_EXPIRY_HOURS = int(os.getenv('EMAIL_TOKEN_EXPIRY_HOURS', 24))
    RESEND_COOLDOWN_MINUTES = int(os.getenv('RESEND_COOLDOWN_MINUTES', 5))
    
    # Frontend URL
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')
    APP_DOMAIN = os.getenv('APP_DOMAIN', 'localhost')

    # Career / salary market (used by OpenAI learning-path generator)
    CAREER_MARKET_REGION = os.getenv('CAREER_MARKET_REGION', 'Pakistan')
    
    # Production
    IS_PRODUCTION = os.getenv('FLASK_ENV', 'development') == 'production'
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    
    # CORS
    CORS_ORIGINS = None  # Will be set by get_allowed_origins()
    
    @staticmethod
    def get_allowed_origins():
        """Get list of allowed CORS origins"""
        origins = []
        
        # Production domain
        app_domain = os.getenv('APP_DOMAIN')
        if app_domain:
            origins.append(f'https://{app_domain}')
            origins.append(f'https://www.{app_domain}')
        
        # Frontend URL from env
        frontend_url = os.getenv('FRONTEND_BASE_URL')
        if frontend_url:
            origins.append(frontend_url)
        
        # Development origins
        if not Config.IS_PRODUCTION:
            origins.extend([
                'http://localhost:5173',
                'http://localhost:5174',
                'http://localhost:5175',
                'http://localhost:3000',
                'http://localhost:5000',
                'http://127.0.0.1:5173',
                'http://127.0.0.1:3000',
            ])
        
        return origins


# Set CORS_ORIGINS after class definition
Config.CORS_ORIGINS = Config.get_allowed_origins()


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    CORS_ORIGINS = Config.get_allowed_origins()


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    IS_PRODUCTION = True
    CORS_ORIGINS = Config.get_allowed_origins()


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    MONGODB_URI = 'mongodb://localhost:27017/plpg_test'
    CORS_ORIGINS = Config.get_allowed_origins()


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None):
    """Get configuration based on environment or config_name"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    return config.get(config_name, config['default'])


# ============================================
# Security Warnings
# ============================================
def _check_security_config():
    """Check for weak security configuration"""
    config_obj = get_config()
    allow_insecure_dev = os.getenv("ALLOW_INSECURE_DEV_SECRETS", "false").lower() == "true"

    def _validate_secret(name: str, value: Optional[str]):
        if not value:
            return f"{name} is missing"
        if len(value) < 32:
            return f"{name} is too short (min 32 characters)"
        return None
    
    issues = []
    for secret_name, secret_value in (
        ("JWT_SECRET", config_obj.JWT_SECRET),
        ("JWT_REFRESH_SECRET", config_obj.JWT_REFRESH_SECRET),
        ("SECRET_KEY", config_obj.SECRET_KEY),
    ):
        problem = _validate_secret(secret_name, secret_value)
        if problem:
            issues.append(problem)

    if issues:
        message = (
            "Security configuration error:\n"
            + "\n".join(f"  - {item}" for item in issues)
            + "\nProvide strong environment-based values (at least 32 chars)."
        )
        if config_obj.IS_PRODUCTION or not allow_insecure_dev:
            raise ValueError(message)
        warnings.warn(
            f"{message}\nALLOW_INSECURE_DEV_SECRETS=true is set; generating temporary in-memory secrets.",
            RuntimeWarning,
        )
        if not config_obj.JWT_SECRET or len(config_obj.JWT_SECRET) < 32:
            config_obj.JWT_SECRET = secrets.token_urlsafe(48)
        if not config_obj.JWT_REFRESH_SECRET or len(config_obj.JWT_REFRESH_SECRET) < 32:
            config_obj.JWT_REFRESH_SECRET = secrets.token_urlsafe(48)
        if not config_obj.SECRET_KEY or len(config_obj.SECRET_KEY) < 32:
            config_obj.SECRET_KEY = secrets.token_urlsafe(48)


# Run security check on import
try:
    _check_security_config()
except ValueError as e:
    print(str(e))
    raise
