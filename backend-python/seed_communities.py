from database import get_collection, init_db

init_db()
col = get_collection('communities')
if col.count_documents({}) == 0:
    col.insert_many([
        {'name': 'Web Development (DigiSkills)', 'course': 'Web Development', 'description': 'Discuss Web Dev curriculum.'},
        {'name': 'React Mastery (Coursera)', 'course': 'React', 'description': 'Advanced React concepts.'},
        {'name': 'Python for AI (Udemy)', 'course': 'Python', 'description': 'AI with Python.'},
        {'name': 'Data Science (Google)', 'course': 'Data Science', 'description': 'Data analytics.'}
    ])
    print("Seeded communities")
else:
    print("Communities already exist")
