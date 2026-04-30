"""
============================================
Configuration Module
============================================

Manages all application configuration from environment variables
"""

import os
import warnings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


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
    
    # Email Configuration
    EMAIL_SERVICE = os.getenv('EMAIL_SERVICE', 'gmail')
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', EMAIL_USER)
    
    # Email Token Settings
    EMAIL_TOKEN_EXPIRY_HOURS = int(os.getenv('EMAIL_TOKEN_EXPIRY_HOURS', 24))
    RESEND_COOLDOWN_MINUTES = int(os.getenv('RESEND_COOLDOWN_MINUTES', 5))
    
    # Frontend URL
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')
    APP_DOMAIN = os.getenv('APP_DOMAIN', 'localhost')
    
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
    
    # Check for required secrets in production
    if config_obj.IS_PRODUCTION:
        missing_secrets = []
        weak_secrets = []
        
        if not config_obj.JWT_SECRET:
            missing_secrets.append('JWT_SECRET')
        elif len(config_obj.JWT_SECRET) < 32:
            weak_secrets.append('JWT_SECRET (too short, min 32 characters)')
        
        if not config_obj.JWT_REFRESH_SECRET:
            missing_secrets.append('JWT_REFRESH_SECRET')
        elif len(config_obj.JWT_REFRESH_SECRET) < 32:
            weak_secrets.append('JWT_REFRESH_SECRET (too short, min 32 characters)')
        
        if not config_obj.SECRET_KEY:
            missing_secrets.append('SECRET_KEY')
        elif len(config_obj.SECRET_KEY) < 32:
            weak_secrets.append('SECRET_KEY (too short, min 32 characters)')
        
        if missing_secrets or weak_secrets:
            error_msg = '⚠️  SECURITY ERROR in production mode:\n'
            if missing_secrets:
                error_msg += f'Missing required environment variables:\n  - {", ".join(missing_secrets)}\n'
            if weak_secrets:
                error_msg += f'Weak secrets:\n  - {", ".join(weak_secrets)}\n'
            error_msg += 'Use strong, random values (min 32 characters each)'
            raise ValueError(error_msg)


# Run security check on import
try:
    _check_security_config()
except ValueError as e:
    print(str(e))
    raise
