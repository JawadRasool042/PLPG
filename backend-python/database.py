"""
============================================
Database Module - MongoDB
============================================
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import get_config

# Global database client
_client = None
_db = None


def init_database():
    """Initialize MongoDB connection"""
    global _client, _db

    config = get_config()

    try:
        _client = MongoClient(
            config.MONGODB_URI,
            maxPoolSize=config.MONGODB_POOL_SIZE,
            minPoolSize=config.MONGODB_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=45000,
            connectTimeoutMS=10000,
            retryWrites=True,
            retryReads=True
        )

        # Verify connection
        _client.admin.command('ping')

        # Get database name from URI or use default
        db_name = config.MONGODB_URI.split('/')[-1].split('?')[0] or 'plpg'
        _db = _client[db_name]

        print('* MongoDB connected successfully')
        print(f'  - Database: {db_name}')
        print('* Database initialized')

        _create_indexes()
        return _db

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f'ERROR: Database initialization failed: {e}')
        print(f'  - Verify MONGODB_URI in .env')
        raise
    except Exception as e:
        print(f'ERROR: Unexpected database error: {e}')
        raise


def _create_indexes():
    """Create necessary database indexes"""
    global _db
    if _db is None:
        return

    _db.users.create_index('email', unique=True)
    _db.users.create_index('emailVerificationTokenHash')
    _db.users.create_index('passwordResetTokenHash')
    _db.admins.create_index('email', unique=True)
    _db.admins.create_index('name', unique=True)
    _db.audit_logs.create_index([('admin', 1), ('createdAt', -1)])
    _db.audit_logs.create_index([('createdAt', -1)])
    _db.quizzes.create_index('interest')
    _db.quiz_templates.create_index([('interest', 1), ('level', 1)])
    _db.quiz_attempts.create_index([('userId', 1), ('completedAt', -1)])
    _db.user_performance.create_index('userId', unique=True)
    _db.messages.create_index([('senderId', 1), ('receiverId', 1), ('createdAt', -1)])
    _db.messages.create_index([('receiverId', 1), ('read', 1)])
    _db.notes.create_index([('interest', 1), ('order', 1)])
    _db.note_progress.create_index([('userId', 1), ('noteId', 1)], unique=True)

    print('* Database indexes created')


def get_database():
    """Get the database instance"""
    global _db
    if _db is None:
        init_database()
    return _db


def get_collection(collection_name: str):
    """Get a specific collection"""
    db = get_database()
    return db[collection_name]


def close_database():
    """Close the database connection"""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        print('* MongoDB connection closed')


# Aliases
init_db = init_database
close_db = close_database
