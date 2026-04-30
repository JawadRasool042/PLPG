"""Routes package"""

from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.admin import admin_bp
from routes.quiz import quiz_bp
from routes.recommendations import recommendations_bp

__all__ = ['auth_bp', 'profile_bp', 'admin_bp', 'quiz_bp', 'recommendations_bp']
