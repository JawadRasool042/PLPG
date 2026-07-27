from database import get_collection, init_db
from personalized_learning_path import DOMAINS

def seed_communities():
    col = get_collection('communities')
    
    # Clean up the incorrect dummy communities that might have been seeded previously
    col.delete_many({'name': {'$in': [
        'Web Development (DigiSkills)',
        'React Mastery (Coursera)',
        'Python for AI (Udemy)',
        'Data Science (Google)'
    ]}})

    # Upsert the exact domains so they always exist
    for domain in DOMAINS:
        col.update_one(
            {'name': domain},
            {
                '$setOnInsert': {
                    'course': domain,
                    'description': f'Official community for {domain} learners.'
                }
            },
            upsert=True
        )
    print("Seeded exact domain communities")

if __name__ == '__main__':
    init_db()
    seed_communities()
