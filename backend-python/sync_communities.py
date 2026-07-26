from pymongo import MongoClient
import os
from datetime import datetime
from bson import ObjectId

# Connect to DB
client = MongoClient("mongodb://localhost:27017")
db = client['plpg']
courses_col = db['courses']
comms_col = db['communities']
members_col = db['community_members']
enrollments_col = db['enrollments']
users_col = db['users']

DOMAINS = [
    'Coding',
    'Web Development',
    'Game Development',
    'Cybersecurity',
    'Data Science',
    'Mobile Development',
    'Cloud Computing',
    'AI & Machine Learning',
    'Physical Games / Sports'
]

print("Starting community synchronization with domains...")

# 1. Clear old dummy communities
comms_col.delete_many({})
members_col.delete_many({})
db['community_messages'].delete_many({})

print("Cleared old dummy communities.")

# 2. For each domain, create a community
print(f"Creating {len(DOMAINS)} domain communities.")

for domain in DOMAINS:
    # Create community
    comm_doc = {
        'name': domain,
        'course': domain,
        'course_id': domain.lower().replace(' ', '-'),
        'description': f"Official community for {domain}. Discuss topics, ask questions, and collaborate with your peers.",
        'createdAt': datetime.utcnow()
    }
    
    comms_col.insert_one(comm_doc)
    
    # 3. Find all enrollments for this course and add users
    # Wait, the plpg database might not have an 'enrollments' collection, 
    # let's check what collections exist.
    pass

# Do not auto-enroll users. They must join manually.
print(f"Created {len(DOMAINS)} domain communities.")
print("Done.")
