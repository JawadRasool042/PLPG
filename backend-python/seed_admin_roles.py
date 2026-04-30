"""
============================================
Seed Admin Roles and Permissions
============================================

Script to populate the database with admin roles and permissions
"""

from database import get_collection
from models.admin import Role, Permission, Admin
from bson import ObjectId


def seed_permissions():
    """Seed permissions into the database"""
    
    permissions_coll = get_collection('permissions')
    
    permissions_data = [
        # Users permissions
        {'name': 'users_create', 'description': 'Create new users', 'category': 'users', 'action': 'create', 'isSystem': True},
        {'name': 'users_read', 'description': 'View users', 'category': 'users', 'action': 'read', 'isSystem': True},
        {'name': 'users_update', 'description': 'Update users', 'category': 'users', 'action': 'update', 'isSystem': True},
        {'name': 'users_delete', 'description': 'Delete users', 'category': 'users', 'action': 'delete', 'isSystem': True},
        {'name': 'users_export', 'description': 'Export users', 'category': 'users', 'action': 'export', 'isSystem': True},
        
        # Content permissions
        {'name': 'content_create', 'description': 'Create content', 'category': 'content', 'action': 'create', 'isSystem': True},
        {'name': 'content_read', 'description': 'View content', 'category': 'content', 'action': 'read', 'isSystem': True},
        {'name': 'content_update', 'description': 'Update content', 'category': 'content', 'action': 'update', 'isSystem': True},
        {'name': 'content_delete', 'description': 'Delete content', 'category': 'content', 'action': 'delete', 'isSystem': True},
        
        # Learning paths permissions
        {'name': 'learning_paths_create', 'description': 'Create learning paths', 'category': 'learning_paths', 'action': 'create', 'isSystem': True},
        {'name': 'learning_paths_read', 'description': 'View learning paths', 'category': 'learning_paths', 'action': 'read', 'isSystem': True},
        {'name': 'learning_paths_update', 'description': 'Update learning paths', 'category': 'learning_paths', 'action': 'update', 'isSystem': True},
        {'name': 'learning_paths_delete', 'description': 'Delete learning paths', 'category': 'learning_paths', 'action': 'delete', 'isSystem': True},
        
        # Analytics permissions
        {'name': 'analytics_read', 'description': 'View analytics', 'category': 'analytics', 'action': 'read', 'isSystem': True},
        
        # Reports permissions
        {'name': 'reports_read', 'description': 'View reports', 'category': 'reports', 'action': 'read', 'isSystem': True},
        {'name': 'reports_export', 'description': 'Export reports', 'category': 'reports', 'action': 'export', 'isSystem': True},
        
        # Logs permissions
        {'name': 'logs_read', 'description': 'View audit logs', 'category': 'logs', 'action': 'read', 'isSystem': True},
        {'name': 'logs_export', 'description': 'Export logs', 'category': 'logs', 'action': 'export', 'isSystem': True},
        
        # Settings permissions
        {'name': 'settings_read', 'description': 'View settings', 'category': 'settings', 'action': 'read', 'isSystem': True},
        {'name': 'settings_update', 'description': 'Update settings', 'category': 'settings', 'action': 'update', 'isSystem': True},
        
        # Admin permissions
        {'name': 'admin_create', 'description': 'Create admins', 'category': 'admins', 'action': 'create', 'isSystem': True},
        {'name': 'admin_read', 'description': 'View admins', 'category': 'admins', 'action': 'read', 'isSystem': True},
        {'name': 'admin_update', 'description': 'Update admins', 'category': 'admins', 'action': 'update', 'isSystem': True},
        {'name': 'admin_delete', 'description': 'Delete admins', 'category': 'admins', 'action': 'delete', 'isSystem': True},
    ]
    
    created_permissions = {}
    for perm_data in permissions_data:
        existing = permissions_coll.find_one({'name': perm_data['name']})
        if not existing:
            result = permissions_coll.insert_one(perm_data)
            created_permissions[perm_data['name']] = result.inserted_id
            print(f"  ✓ Created permission: {perm_data['name']}")
        else:
            created_permissions[perm_data['name']] = existing['_id']
            print(f"  ✓ Permission exists: {perm_data['name']}")
    
    return created_permissions


def seed_roles(permissions_map):
    """Seed roles into the database"""
    
    roles_coll = get_collection('roles')
    
    roles_data = [
        {
            'name': 'super_admin',
            'description': 'Super Administrator with full access',
            'permissions': list(permissions_map.values()),
            'isSystem': True
        },
        {
            'name': 'admin',
            'description': 'Administrator with most permissions',
            'permissions': [
                permissions_map.get('users_read'),
                permissions_map.get('users_update'),
                permissions_map.get('content_read'),
                permissions_map.get('content_create'),
                permissions_map.get('content_update'),
                permissions_map.get('analytics_read'),
                permissions_map.get('reports_read'),
                permissions_map.get('logs_read'),
            ],
            'isSystem': True
        },
        {
            'name': 'moderator',
            'description': 'Moderator with limited permissions',
            'permissions': [
                permissions_map.get('users_read'),
                permissions_map.get('content_read'),
                permissions_map.get('content_update'),
                permissions_map.get('analytics_read'),
            ],
            'isSystem': True
        },
        {
            'name': 'viewer',
            'description': 'Viewer with read-only access',
            'permissions': [
                permissions_map.get('users_read'),
                permissions_map.get('content_read'),
                permissions_map.get('analytics_read'),
                permissions_map.get('reports_read'),
            ],
            'isSystem': True
        },
    ]
    
    created_roles = {}
    for role_data in roles_data:
        existing = roles_coll.find_one({'name': role_data['name']})
        if not existing:
            result = roles_coll.insert_one(role_data)
            created_roles[role_data['name']] = result.inserted_id
            print(f"  ✓ Created role: {role_data['name']}")
        else:
            created_roles[role_data['name']] = existing['_id']
            print(f"  ✓ Role exists: {role_data['name']}")
    
    return created_roles


def seed_default_admin(roles_map, permissions_map):
    """Seed a default super admin user"""
    
    admins_coll = get_collection('admins')
    
    # Check if admin already exists
    existing_admin = admins_coll.find_one({'email': 'admin@plpg.ai'})
    if existing_admin:
        print(f"  ✓ Default admin already exists: admin@plpg.ai")
        return
    
    # Create default admin
    admin_data = {
        'name': 'Super Admin',
        'email': 'admin@plpg.ai',
        'password': Admin.hash_password('Admin@12345'),
        'role': roles_map.get('super_admin'),
        'permissions': list(permissions_map.values()),
        'status': 'active',
        'lastLogin': None,
        'loginAttempts': 0,
        'lockoutUntil': None,
        'twoFactorEnabled': False,
        'twoFactorSecret': None,
        'sessionTokens': [],
        'createdAt': __import__('datetime').datetime.utcnow(),
        'updatedAt': __import__('datetime').datetime.utcnow()
    }
    
    result = admins_coll.insert_one(admin_data)
    print(f"  ✓ Created default admin: admin@plpg.ai (password: Admin@12345)")
    print(f"    ⚠️  IMPORTANT: Change this password immediately in production!")
    
    return result.inserted_id


def seed_admin_roles():
    """Main seeding function"""
    
    print('\n' + '='*50)
    print('Seeding Admin Roles and Permissions')
    print('='*50)
    
    print('\n1. Seeding Permissions...')
    permissions_map = seed_permissions()
    
    print('\n2. Seeding Roles...')
    roles_map = seed_roles(permissions_map)
    
    print('\n3. Seeding Default Admin...')
    seed_default_admin(roles_map, permissions_map)
    
    print('\n' + '='*50)
    print('✓ Seeding Complete!')
    print('='*50)
    print('\nDefault Admin Credentials:')
    print('  Email: admin@plpg.ai')
    print('  Password: Admin@12345')
    print('\n⚠️  IMPORTANT: Change these credentials immediately!')


if __name__ == '__main__':
    from database import init_db
    
    print('Initializing database...')
    init_db()
    
    seed_admin_roles()
