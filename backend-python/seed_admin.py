import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def seed_admin():
    import bcrypt
    from database import get_collection
    
    col = get_collection('admins')
    email = 'admin@plpg.com'
    password = 'Password123!'
    
    admin = col.find_one({'email': email})
    if not admin:
        try:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
            doc = {
                'name': 'Super Admin',
                'email': email,
                'password': hashed,
                'role': 'super_admin',
                'status': 'active',
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }
            col.insert_one(doc)
            logger.info("Default admin created successfully.")
        except Exception as e:
            logger.error(f"Failed to seed admin: {e}")
    else:
        logger.info("Admin account already exists.")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        seed_admin()
