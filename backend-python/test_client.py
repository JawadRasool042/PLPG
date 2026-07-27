import json
from app import create_app

app = create_app()

with app.app_context():
    client = app.test_client()
    
    test_email = "test6@example.com"
    # Register
    client.post("/api/auth/register", json={
        "firstName": "Test",
        "lastName": "User",
        "email": test_email, 
        "password": "password123", 
        "role": "USER"
    })
    
    # Login
    res = client.post("/api/auth/login", json={"email": test_email, "password": "password123"})
    if res.status_code != 200:
        print("Login failed!", res.json)
        exit(1)
        
    token = res.json.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Start quiz
    res = client.post("/api/ai-quiz/start", json={"topic": "Python", "difficulty": "basic"}, headers=headers)
    session_id = res.json.get("session_id")
    print("Session:", session_id)
    
    import time
    for i in range(10):
        start = time.time()
        res = client.post("/api/ai-quiz/answer", json={"session_id": session_id, "question_index": i, "answer": "A"}, headers=headers)
        if res.status_code != 200:
            print("Answer failed!", res.json)
            exit(1)
        print(f"Answer {i}: {time.time() - start:.2f}s")
        
    start = time.time()
    res = client.post("/api/ai-quiz/finish", json={"session_id": session_id}, headers=headers)
    if res.status_code != 200:
        print("Finish failed!", res.json)
        exit(1)
    print(f"Finish: {time.time() - start:.2f}s")
