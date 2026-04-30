#!/usr/bin/env python
"""
Test LLM API endpoint with live backend
"""

import requests
import json
from requests.exceptions import ConnectionError

BASE_URL = "http://localhost:5000"

# Test user token (from seed_test_users.py)
# Using a test user - check backend logs for valid tokens
TEST_USER_EMAIL = "john.doe@example.com"
TEST_USER_PASSWORD = "Test@1234"

def get_auth_token():
    """Get JWT token by logging in"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✓ Got auth token: {token[:20]}...")
            return token
        else:
            print(f"✗ Login failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
    except ConnectionError:
        print("✗ Backend not running on http://localhost:5000")
        return None
    except Exception as e:
        print(f"✗ Error getting token: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_generate_questions(token):
    """Test question generation endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "topic": "Python",
        "level": "beginner",
        "concept_tag": "python_basics",
        "count": 2
    }
    
    try:
        print("\n" + "="*70)
        print("Testing: POST /api/llm/questions/generate")
        print("="*70)
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print()
        
        response = requests.post(
            f"{BASE_URL}/api/llm/questions/generate",
            json=payload,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success!")
            print(f"  Generated: {data.get('generated', 0)}")
            print(f"  Verified: {data.get('verified', 0)}")
            print(f"  Questions: {len(data.get('questions', []))}")
            
            if data.get('questions'):
                print("\n  First Question:")
                q = data['questions'][0]
                print(f"    Q: {q.get('question', '?')[:70]}...")
                print(f"    Options: {q.get('options', [])}")
                print(f"    Correct: {q.get('correct_index', '?')}")
                print(f"    Difficulty: {q.get('difficulty', '?')}")
            
            return True
        else:
            print(f"✗ Failed")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_interest_extraction(token):
    """Test interest extraction endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": "I love building web apps with React and learning about machine learning"
    }
    
    try:
        print("\n" + "="*70)
        print("Testing: POST /api/llm/interest/extract")
        print("="*70)
        print(f"Text: {payload['text']}")
        print()
        
        response = requests.post(
            f"{BASE_URL}/api/llm/interest/extract",
            json=payload,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success!")
            print(f"  Confidence: {data.get('confidence', '?')}")
            print(f"  Top Topics: {data.get('top_topics', [])}")
            print(f"  Interests: {data.get('interests', {})}")
            return True
        else:
            print(f"✗ Failed")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("="*70)
    print("LLM API ENDPOINT TEST")
    print("="*70)
    print()
    
    # Step 1: Get auth token
    print("Step 1: Authenticate")
    print("-" * 70)
    token = get_auth_token()
    
    if not token:
        print("\n✗ Cannot continue without token")
        return False
    
    # Step 2: Test endpoints
    print("\n\nStep 2: Test Endpoints")
    
    success = True
    success = test_generate_questions(token) and success
    
    # Note: Interest extraction requires Gemini API key
    # Skipping for now if no API key set
    import os
    if os.getenv("GEMINI_API_KEY"):
        success = test_interest_extraction(token) and success
    else:
        print("\n⚠️  Skipping interest extraction test (GEMINI_API_KEY not set)")
    
    # Summary
    print("\n" + "="*70)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*70)
    
    return success

if __name__ == "__main__":
    main()
