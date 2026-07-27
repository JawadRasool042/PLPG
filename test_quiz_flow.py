import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000/api"
HEADERS = {"Content-Type": "application/json"}

print("Logging in...")
res = requests.post(f"{BASE_URL}/auth/login", json={"email": "test@example.com", "password": "password"})
if res.status_code != 200:
    print("Login failed:", res.text)
    requests.post(f"{BASE_URL}/auth/register", json={"email": "test@example.com", "password": "password", "username": "testuser"})
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": "test@example.com", "password": "password"})

token = res.json().get("access_token")
HEADERS["Authorization"] = f"Bearer {token}"

print("Starting quiz...")
res = requests.post(f"{BASE_URL}/ai-quiz/start", json={"topic": "Python", "difficulty": "basic"}, headers=HEADERS)
session_id = res.json().get("session_id")
print("Session ID:", session_id)

for i in range(10):
    start_time = time.time()
    res = requests.post(f"{BASE_URL}/ai-quiz/answer", json={
        "session_id": session_id,
        "question_index": i,
        "answer": "A",
        "time_spent_ms": 1000
    }, headers=HEADERS)
    elapsed = time.time() - start_time
    print(f"Answer {i} Response ({elapsed:.2f}s):", res.status_code)
    
print("Finishing quiz...")
start_time = time.time()
res = requests.post(f"{BASE_URL}/ai-quiz/finish", json={"session_id": session_id}, headers=HEADERS)
elapsed = time.time() - start_time
print(f"Finish Response ({elapsed:.2f}s):", res.status_code)
print("Done!")
