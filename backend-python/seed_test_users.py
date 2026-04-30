"""
============================================
Seed Test Users - Development Only
============================================

This script creates test users for development and testing
"""

from datetime import datetime, timedelta
from models.user import User
from database import init_db, get_collection

def seed_test_users():
    """Create test users for development"""
    
    # Initialize database
    init_db()
    
    collection = get_collection('users')
    
    # Check if test users already exist
    existing = collection.count_documents({'email': {'$in': [
        'john.doe@example.com',
        'jane.smith@example.com',
        'bob.wilson@example.com',
        'alice.johnson@example.com',
        'charlie.brown@example.com'
    ]}})
    
    if existing > 0:
        print(f"✓ Test users already exist ({existing} found)")
        return
    
    test_users = [
        {
            'email': 'john.doe@example.com',
            'firstName': 'John',
            'lastName': 'Doe',
            'hashedPassword': User.hash_password('Test@1234'),
            'isEmailVerified': True,
            'isActive': True,
            'createdAt': datetime.utcnow() - timedelta(days=30),
            'emailVerifiedAt': datetime.utcnow() - timedelta(days=29),
        },
        {
            'email': 'jane.smith@example.com',
            'firstName': 'Jane',
            'lastName': 'Smith',
            'hashedPassword': User.hash_password('Test@1234'),
            'isEmailVerified': True,
            'isActive': True,
            'createdAt': datetime.utcnow() - timedelta(days=20),
            'emailVerifiedAt': datetime.utcnow() - timedelta(days=19),
        },
        {
            'email': 'bob.wilson@example.com',
            'firstName': 'Bob',
            'lastName': 'Wilson',
            'hashedPassword': User.hash_password('Test@1234'),
            'isEmailVerified': False,
            'isActive': True,
            'createdAt': datetime.utcnow() - timedelta(days=10),
        },
        {
            'email': 'alice.johnson@example.com',
            'firstName': 'Alice',
            'lastName': 'Johnson',
            'hashedPassword': User.hash_password('Test@1234'),
            'isEmailVerified': True,
            'isActive': True,
            'createdAt': datetime.utcnow() - timedelta(days=5),
            'emailVerifiedAt': datetime.utcnow() - timedelta(days=4),
        },
        {
            'email': 'charlie.brown@example.com',
            'firstName': 'Charlie',
            'lastName': 'Brown',
            'hashedPassword': User.hash_password('Test@1234'),
            'isEmailVerified': True,
            'isActive': False,  # Suspended user
            'createdAt': datetime.utcnow() - timedelta(days=2),
            'emailVerifiedAt': datetime.utcnow() - timedelta(days=1),
        },
    ]
    
    # Add default schema fields to each user
    for user in test_users:
        user_data = {**User.DEFAULT_SCHEMA, **user}
        user_data['updatedAt'] = datetime.utcnow()
        collection.insert_one(user_data)
    
    print(f"✓ Created {len(test_users)} test users")
    print("  - john.doe@example.com (verified)")
    print("  - jane.smith@example.com (verified)")
    print("  - bob.wilson@example.com (pending)")
    print("  - alice.johnson@example.com (verified)")
    print("  - charlie.brown@example.com (suspended)")
    print("\nAll test users have password: Test@1234")

if __name__ == '__main__':
    seed_test_users()
