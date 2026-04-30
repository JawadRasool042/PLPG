"""
============================================
Seed Chat Messages - Development Only
============================================

Creates starter direct-message records so chat UI shows real DB-backed data.
"""

from datetime import datetime, timedelta

from database import init_db, get_collection


def seed_chat_messages():
    init_db()

    users_collection = get_collection('users')
    chat_collection = get_collection('chat_messages')

    if chat_collection.count_documents({}) > 0:
        print('✓ Chat messages already exist, skipping seed')
        return

    users = list(users_collection.find({'isActive': True}).sort('createdAt', 1).limit(4))
    if len(users) < 2:
        print('⚠ Not enough active users to seed chat messages')
        return

    user_a = users[0]
    user_b = users[1]

    now = datetime.utcnow()
    messages = [
        {
            'senderId': user_b['_id'],
            'receiverId': user_a['_id'],
            'text': 'Hey! Kya tumne latest quiz attempt kiya?',
            'readAt': now - timedelta(minutes=35),
            'createdAt': now - timedelta(minutes=40),
            'updatedAt': now - timedelta(minutes=35),
        },
        {
            'senderId': user_a['_id'],
            'receiverId': user_b['_id'],
            'text': 'Haan, score 88% aaya. Kal discuss karte hain?',
            'readAt': now - timedelta(minutes=32),
            'createdAt': now - timedelta(minutes=34),
            'updatedAt': now - timedelta(minutes=32),
        },
        {
            'senderId': user_b['_id'],
            'receiverId': user_a['_id'],
            'text': 'Perfect. 5 baje online ho jao.',
            'readAt': None,
            'createdAt': now - timedelta(minutes=30),
            'updatedAt': now - timedelta(minutes=30),
        },
    ]

    # If third user exists, create another conversation for list variety.
    if len(users) >= 3:
        user_c = users[2]
        messages.extend([
            {
                'senderId': user_c['_id'],
                'receiverId': user_a['_id'],
                'text': 'Assignment ki PDF mil gayi?',
                'readAt': None,
                'createdAt': now - timedelta(minutes=15),
                'updatedAt': now - timedelta(minutes=15),
            },
            {
                'senderId': user_a['_id'],
                'receiverId': user_c['_id'],
                'text': 'Yes, upload kar di hai group pe.',
                'readAt': None,
                'createdAt': now - timedelta(minutes=12),
                'updatedAt': now - timedelta(minutes=12),
            },
        ])

    chat_collection.insert_many(messages)
    print(f'✓ Seeded {len(messages)} chat messages')


if __name__ == '__main__':
    seed_chat_messages()
