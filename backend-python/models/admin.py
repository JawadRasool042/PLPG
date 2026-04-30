"""
============================================
Admin Model - MongoDB
============================================

This model handles all admin-related database operations
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId

import bcrypt

from database import get_collection


class Admin:
    """Admin model class with static methods for database operations"""
    
    collection_name = 'admins'
    
    MAX_LOGIN_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 30
    
    @staticmethod
    def get_collection():
        """Get the admins collection"""
        return get_collection(Admin.collection_name)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    
    @staticmethod
    def check_password(password: str, hashed: str) -> bool:
        """Check if a password matches the hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    @staticmethod
    def create(admin_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new admin
        
        Args:
            admin_data: Dictionary containing admin data
            
        Returns:
            Created admin document
        """
        collection = Admin.get_collection()
        
        admin = {
            'name': admin_data.get('name'),
            'email': admin_data.get('email', '').lower(),
            'password': Admin.hash_password(admin_data.get('password')),
            'role': admin_data.get('role'),  # ObjectId reference
            'permissions': admin_data.get('permissions', []),
            'status': admin_data.get('status', 'active'),
            'lastLogin': None,
            'loginAttempts': 0,
            'lockoutUntil': None,
            'twoFactorEnabled': False,
            'twoFactorSecret': None,
            'sessionTokens': [],
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        result = collection.insert_one(admin)
        admin['_id'] = result.inserted_id
        
        return admin
    
    @staticmethod
    def find_by_id(admin_id: str, include_password: bool = False) -> Optional[Dict[str, Any]]:
        """Find an admin by ID"""
        collection = Admin.get_collection()
        
        projection = None if include_password else {'password': 0, 'twoFactorSecret': 0}
        admin = collection.find_one({'_id': ObjectId(admin_id)}, projection)
        
        if admin:
            admin = Admin._populate_references(admin)
        
        return admin
    
    @staticmethod
    def find_by_email(email: str, include_password: bool = False) -> Optional[Dict[str, Any]]:
        """Find an admin by email"""
        collection = Admin.get_collection()
        
        projection = None if include_password else {'password': 0, 'twoFactorSecret': 0}
        admin = collection.find_one({'email': email.lower()}, projection)
        
        if admin:
            admin = Admin._populate_references(admin)
        
        return admin
    
    @staticmethod
    def find_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Find an admin by name"""
        collection = Admin.get_collection()
        return collection.find_one({'name': name.strip()})
    
    @staticmethod
    def _populate_references(admin: Dict[str, Any]) -> Dict[str, Any]:
        """Populate role and permissions references"""
        if admin.get('role'):
            role = Role.find_by_id(str(admin['role']))
            admin['role'] = role
        
        if admin.get('permissions'):
            permissions = []
            for perm_id in admin['permissions']:
                perm = Permission.find_by_id(str(perm_id))
                if perm:
                    permissions.append(perm)
            admin['permissions'] = permissions
        
        return admin
    
    @staticmethod
    def update(admin_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an admin"""
        collection = Admin.get_collection()
        update_data['updatedAt'] = datetime.utcnow()
        
        # Hash password if being updated
        if 'password' in update_data:
            update_data['password'] = Admin.hash_password(update_data['password'])
        
        result = collection.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def delete(admin_id: str) -> bool:
        """Delete an admin"""
        collection = Admin.get_collection()
        result = collection.delete_one({'_id': ObjectId(admin_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def is_locked(admin: Dict[str, Any]) -> bool:
        """Check if admin account is locked"""
        lockout_until = admin.get('lockoutUntil')
        if not lockout_until:
            return False
        return lockout_until > datetime.utcnow()
    
    @staticmethod
    def increment_login_attempts(admin_id: str, admin: Dict[str, Any]) -> None:
        """Increment login attempts and lock if needed"""
        collection = Admin.get_collection()
        
        lockout_until = admin.get('lockoutUntil')
        if lockout_until and lockout_until < datetime.utcnow():
            # Previous lock expired, reset
            collection.update_one(
                {'_id': ObjectId(admin_id)},
                {'$set': {'loginAttempts': 1, 'lockoutUntil': None}}
            )
            return
        
        current_attempts = admin.get('loginAttempts', 0)
        updates = {'$inc': {'loginAttempts': 1}}
        
        if current_attempts + 1 >= Admin.MAX_LOGIN_ATTEMPTS and not Admin.is_locked(admin):
            updates['$set'] = {
                'lockoutUntil': datetime.utcnow() + timedelta(minutes=Admin.LOCK_DURATION_MINUTES)
            }
        
        collection.update_one({'_id': ObjectId(admin_id)}, updates)
    
    @staticmethod
    def reset_login_attempts(admin_id: str) -> None:
        """Reset login attempts after successful login"""
        collection = Admin.get_collection()
        collection.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'loginAttempts': 0, 'lockoutUntil': None}}
        )
    
    @staticmethod
    def update_last_login(admin_id: str) -> None:
        """Update last login timestamp"""
        collection = Admin.get_collection()
        collection.update_one(
            {'_id': ObjectId(admin_id)},
            {'$set': {'lastLogin': datetime.utcnow()}}
        )
    
    @staticmethod
    def to_response(admin: Dict[str, Any]) -> Dict[str, Any]:
        """Convert admin document to API response"""
        if not admin:
            return None

        # Safely serialize role
        role = admin.get('role')
        if role and isinstance(role, dict):
            role_data = {
                'id': str(role.get('_id', '')),
                'name': role.get('name', ''),
                'description': role.get('description', '')
            }
        elif role:
            role_data = str(role)
        else:
            role_data = None

        # Safely serialize permissions
        permissions = admin.get('permissions', [])
        permissions_data = []
        for p in permissions:
            if isinstance(p, dict):
                permissions_data.append({
                    'id': str(p.get('_id', '')),
                    'name': p.get('name', ''),
                    'category': p.get('category', '')
                })
            else:
                permissions_data.append(str(p))

        last_login = admin.get('lastLogin')
        created_at = admin.get('createdAt')

        return {
            'id': str(admin['_id']),
            'name': admin.get('name'),
            'email': admin.get('email'),
            'role': role_data,
            'permissions': permissions_data,
            'status': admin.get('status'),
            'lastLogin': last_login.isoformat() if last_login else None,
            'createdAt': created_at.isoformat() if created_at else None
        }


class Role:
    """Role model class"""
    
    collection_name = 'roles'
    
    VALID_ROLES = ['super_admin', 'admin', 'moderator', 'viewer']
    
    @staticmethod
    def get_collection():
        return get_collection(Role.collection_name)
    
    @staticmethod
    def create(role_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new role"""
        collection = Role.get_collection()
        
        role = {
            'name': role_data.get('name'),
            'description': role_data.get('description'),
            'permissions': role_data.get('permissions', []),
            'isSystem': role_data.get('isSystem', False),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        result = collection.insert_one(role)
        role['_id'] = result.inserted_id
        
        return role
    
    @staticmethod
    def find_by_id(role_id: str) -> Optional[Dict[str, Any]]:
        """Find a role by ID"""
        collection = Role.get_collection()
        try:
            return collection.find_one({'_id': ObjectId(role_id)})
        except:
            return None
    
    @staticmethod
    def find_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Find a role by name"""
        collection = Role.get_collection()
        return collection.find_one({'name': name})
    
    @staticmethod
    def find_all() -> List[Dict[str, Any]]:
        """Find all roles"""
        collection = Role.get_collection()
        return list(collection.find())


class Permission:
    """Permission model class"""
    
    collection_name = 'permissions'
    
    CATEGORIES = ['users', 'content', 'learning_paths', 'analytics', 'reports', 'logs', 'settings', 'admins']
    ACTIONS = ['create', 'read', 'update', 'delete', 'export']
    
    @staticmethod
    def get_collection():
        return get_collection(Permission.collection_name)
    
    @staticmethod
    def create(permission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new permission"""
        collection = Permission.get_collection()
        
        permission = {
            'name': permission_data.get('name'),
            'description': permission_data.get('description'),
            'category': permission_data.get('category'),
            'action': permission_data.get('action'),
            'isSystem': permission_data.get('isSystem', False),
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }
        
        result = collection.insert_one(permission)
        permission['_id'] = result.inserted_id
        
        return permission
    
    @staticmethod
    def find_by_id(permission_id: str) -> Optional[Dict[str, Any]]:
        """Find a permission by ID"""
        collection = Permission.get_collection()
        try:
            return collection.find_one({'_id': ObjectId(permission_id)})
        except:
            return None
    
    @staticmethod
    def find_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Find a permission by name"""
        collection = Permission.get_collection()
        return collection.find_one({'name': name})
    
    @staticmethod
    def find_all() -> List[Dict[str, Any]]:
        """Find all permissions"""
        collection = Permission.get_collection()
        return list(collection.find())
