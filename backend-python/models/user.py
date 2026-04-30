"""
============================================
User Model - MongoDB
============================================

This model handles all user-related database operations
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from bson import ObjectId

import bcrypt

from database import get_collection
from config import get_config

# Configuration
config = get_config()
TOKEN_EXPIRY_HOURS = config.EMAIL_TOKEN_EXPIRY_HOURS
RESEND_COOLDOWN_MINUTES = config.RESEND_COOLDOWN_MINUTES


class User:
    """User model class with static methods for database operations"""
    
    collection_name = 'users'
    
    # Default user schema
    DEFAULT_SCHEMA = {
        'email': None,
        'firstName': None,
        'lastName': None,
        'hashedPassword': None,
        'role': 'Student',
        'isActive': True,
        
        # Profile fields
        'phone': None,
        'bio': None,
        'avatar': None,
        'dateOfBirth': None,
        'location': None,
        
        # Preferences
        'preferences': {
            'theme': 'light',
            'language': 'en',
            'timezone': 'UTC'
        },
        
        # Notifications
        'notifications': {
            'email': True,
            'quizReminders': True,
            'progressUpdates': True,
            'newsletter': False
        },
        
        # Privacy
        'privacy': {
            'profileVisibility': 'public',
            'showEmail': False
        },
        
        # Learning profile
        'learningLevel': 'Beginner',
        'learningGoals': [],
        'weeklyAvailabilityHours': 5,
        'learningPace': 'Self-paced',
        'contentFormat': 'Mixed',
        'focusDomains': [],
        
        # Interest Assessment Results
        'interestAssessment': {
            'completed': False,
            'primaryInterest': None,
            'confidence': 0,
            'allInterests': [],
            'completedAt': None,
            'lastUpdated': None
        },
        
        # Advanced Analytics & Learning Tracking
        'analytics': {
            # Knowledge map: tracks concepts and mastery levels
            'knowledgeMap': {},  # { concept: { status: 'learned'|'partial'|'unknown', level: 0-100, firstSeen: date, lastTested: date } }
            
            # Area tracking
            'strongAreas': [],  # [{ domain: string, avgScore: number, topicCount: number }]
            'weakAreas': [],    # [{ domain: string, avgScore: number, topicCount: number }]
            
            # Concept mastery tracking
            'conceptMastery': {},  # { concept: score (0-100) }
            
            # Interest trends
            'interestTrends': [],  # [{ date: timestamp, primaryInterest: string, allInterests: [{ domain, score }] }]
            
            # Quiz performance by domain
            'quizPerformance': {},  # { domain: [{ date: timestamp, score: number, difficulty: string, correct: number, total: number }] }
            
            # Overall metrics
            'totalQuizzesAttempted': 0,
            'totalCorrect': 0,
            'overallAccuracy': 0,
            'averageQuizScore': 0,
            'learningVelocity': 0,  # Progress rate (0-100)
            
            # Time tracking
            'totalLearningMinutes': 0,
            'lastActiveDate': None,
            'streakDays': 0,
            'longestStreak': 0,
            
            # Wrong answer tracking for learning
            'wrongAnswersAnalysis': [],  # [{ question: string, userExplanation: string, correctExplanation: string, domain: string, date: date }]
            
            'updatedAt': None
        },
        
        # Email verification
        'isEmailVerified': False,
        'emailVerificationTokenHash': None,
        'emailVerificationTokenExpiry': None,
        'emailVerifiedAt': None,
        
        # Rate limiting
        'lastVerificationEmailSent': None,
        'verificationEmailCount': 0,
        
        # Password reset
        'passwordResetTokenHash': None,
        'passwordResetTokenExpiry': None,
        'passwordChangedAt': None,
        
        # Resend attempts tracking
        'resendAttempts': [],
        
        # Security
        'loginAttempts': 0,
        'lockUntil': None,
        
        # Timestamps
        'createdAt': None,
        'updatedAt': None
    }
    
    @staticmethod
    def get_collection():
        """Get the users collection"""
        return get_collection(User.collection_name)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token using SHA-256"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def generate_verification_token() -> Tuple[str, str, datetime]:
        """
        Generate a verification token
        
        Returns:
            Tuple of (raw_token, hashed_token, expiry_datetime)
        """
        raw_token = secrets.token_hex(32)  # 64 character hex string
        hashed_token = User.hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
        return raw_token, hashed_token, expires_at
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    
    @staticmethod
    def check_password(password: str, hashed: str) -> bool:
        """Check if a password matches the hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    @staticmethod
    def create(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user
        
        Args:
            user_data: Dictionary containing user data
            
        Returns:
            Created user document
        """
        collection = User.get_collection()
        
        # Merge with default schema
        user = {**User.DEFAULT_SCHEMA, **user_data}
        user['createdAt'] = datetime.utcnow()
        user['updatedAt'] = datetime.utcnow()
        
        # Ensure email is lowercase
        if user.get('email'):
            user['email'] = user['email'].lower()
        
        result = collection.insert_one(user)
        user['_id'] = result.inserted_id
        
        return user
    
    @staticmethod
    def find_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Find a user by ID"""
        collection = User.get_collection()
        return collection.find_one({'_id': ObjectId(user_id)})
    
    @staticmethod
    def find_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find a user by email"""
        collection = User.get_collection()
        return collection.find_one({'email': email.lower()})
    
    @staticmethod
    def find_by_verification_token(raw_token: str) -> Optional[Dict[str, Any]]:
        """Find a user by verification token"""
        collection = User.get_collection()
        hashed_token = User.hash_token(raw_token)
        
        return collection.find_one({
            'emailVerificationTokenHash': hashed_token,
            'emailVerificationTokenExpiry': {'$gt': datetime.utcnow()}
        })
    
    @staticmethod
    def find_by_password_reset_token(raw_token: str) -> Optional[Dict[str, Any]]:
        """Find a user by password reset token"""
        collection = User.get_collection()
        hashed_token = User.hash_token(raw_token)
        
        return collection.find_one({
            'passwordResetTokenHash': hashed_token,
            'passwordResetTokenExpiry': {'$gt': datetime.utcnow()}
        })
    
    @staticmethod
    def update(user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a user
        
        Args:
            user_id: User ID
            update_data: Data to update
            
        Returns:
            True if successful
        """
        collection = User.get_collection()
        update_data['updatedAt'] = datetime.utcnow()
        
        result = collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def delete(user_id: str) -> bool:
        """Delete a user"""
        collection = User.get_collection()
        result = collection.delete_one({'_id': ObjectId(user_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def set_verification_token(user_id: str) -> str:
        """
        Set a new verification token for a user
        
        Returns:
            Raw token for email
        """
        raw_token, hashed_token, expires_at = User.generate_verification_token()
        
        # Use MongoDB update with $inc operator
        collection = User.get_collection()
        collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'emailVerificationTokenHash': hashed_token,
                    'emailVerificationTokenExpiry': expires_at,
                    'lastVerificationEmailSent': datetime.utcnow()
                },
                '$inc': {'verificationEmailCount': 1}
            }
        )
        
        return raw_token
    
    @staticmethod
    def mark_email_verified(user_id: str, ip_address: str = None, user_agent: str = None) -> bool:
        """Mark a user's email as verified"""
        return User.update(user_id, {
            'isEmailVerified': True,
            'emailVerifiedAt': datetime.utcnow(),
            'emailVerificationTokenHash': None,
            'emailVerificationTokenExpiry': None
        })
    
    @staticmethod
    def set_password_reset_token(user_id: str) -> str:
        """
        Set a password reset token
        
        Returns:
            Raw token for email
        """
        raw_token = secrets.token_hex(32)
        hashed_token = User.hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        User.update(user_id, {
            'passwordResetTokenHash': hashed_token,
            'passwordResetTokenExpiry': expires_at
        })
        
        return raw_token
    
    @staticmethod
    def clear_password_reset_token(user_id: str) -> bool:
        """Clear password reset token"""
        return User.update(user_id, {
            'passwordResetTokenHash': None,
            'passwordResetTokenExpiry': None,
            'passwordChangedAt': datetime.utcnow()
        })
    
    @staticmethod
    def can_resend_verification_email(user: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user can resend verification email"""
        last_sent = user.get('lastVerificationEmailSent')
        
        if not last_sent:
            return {'allowed': True}
        
        cooldown_ms = RESEND_COOLDOWN_MINUTES * 60 * 1000
        time_since_last = (datetime.utcnow() - last_sent).total_seconds() * 1000
        
        if time_since_last < cooldown_ms:
            remaining_seconds = int((cooldown_ms - time_since_last) / 1000)
            return {
                'allowed': False,
                'remainingSeconds': remaining_seconds,
                'message': f'Please wait {remaining_seconds} seconds before requesting another email'
            }
        
        return {'allowed': True}
    
    @staticmethod
    def is_locked(user: Dict[str, Any]) -> bool:
        """Check if user account is locked"""
        lock_until = user.get('lockUntil')
        if not lock_until:
            return False
        return lock_until > datetime.utcnow()
    
    @staticmethod
    def increment_login_attempts(user_id: str, user: Dict[str, Any]) -> None:
        """Increment login attempts and lock if needed"""
        collection = User.get_collection()
        
        lock_until = user.get('lockUntil')
        if lock_until and lock_until < datetime.utcnow():
            # Previous lock expired, reset
            collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'loginAttempts': 1, 'lockUntil': None}}
            )
            return
        
        current_attempts = user.get('loginAttempts', 0)
        updates = {'$inc': {'loginAttempts': 1}}
        
        # Lock after 5 failed attempts for 30 minutes
        if current_attempts + 1 >= 5 and not User.is_locked(user):
            updates['$set'] = {'lockUntil': datetime.utcnow() + timedelta(minutes=30)}
        
        collection.update_one({'_id': ObjectId(user_id)}, updates)
    
    @staticmethod
    def reset_login_attempts(user_id: str) -> None:
        """Reset login attempts after successful login"""
        User.update(user_id, {
            'loginAttempts': 0,
            'lockUntil': None
        })
    
    @staticmethod
    def count(filter_query: Dict = None) -> int:
        """Count users matching filter"""
        collection = User.get_collection()
        return collection.count_documents(filter_query or {})
    
    @staticmethod
    def find_many(filter_query: Dict = None, skip: int = 0, limit: int = 10, 
                  sort_by: str = 'createdAt', sort_order: int = -1) -> list:
        """Find multiple users with pagination"""
        collection = User.get_collection()
        
        cursor = collection.find(
            filter_query or {},
            {'hashedPassword': 0, 'emailVerificationTokenHash': 0, 
             'passwordResetTokenHash': 0}
        ).sort(sort_by, sort_order).skip(skip).limit(limit)
        
        return list(cursor)
    
    @staticmethod
    def to_response(user: Dict[str, Any], include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user document to API response"""
        if not user:
            return None
        
        response = {
            'id': str(user['_id']),
            'email': user.get('email'),
            'first_name': user.get('firstName'),
            'last_name': user.get('lastName'),
            'phone': user.get('phone'),
            'bio': user.get('bio'),
            'avatar': user.get('avatar'),
            'date_of_birth': user.get('dateOfBirth'),
            'location': user.get('location'),
            'role': user.get('role'),
            'learning_level': user.get('learningLevel'),
            'learning_goals': user.get('learningGoals', []),
            'weekly_availability_hours': user.get('weeklyAvailabilityHours'),
            'learning_pace': user.get('learningPace'),
            'content_format': user.get('contentFormat'),
            'focus_domains': user.get('focusDomains', []),
            'is_active': user.get('isActive'),
            'is_email_verified': user.get('isEmailVerified'),
            'created_at': user.get('createdAt'),
            'updated_at': user.get('updatedAt')
        }
        
        if include_sensitive:
            response['preferences'] = user.get('preferences')
            response['notifications'] = user.get('notifications')
            response['privacy'] = user.get('privacy')
        
        return response
