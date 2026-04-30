#!/usr/bin/env python3
"""Test Gemini API integration after fix"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend-python'))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    print("🧪 Testing Gemini API Integration...")
    print("-" * 50)
    
    # Test 1: Check API Key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return False
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test 2: Import google.generativeai
    try:
        import google.generativeai as genai
        print("✅ google.generativeai imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import google.generativeai: {e}")
        print("   Run: pip install google-generativeai")
        return False
    
    # Test 3: Configure and test API
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured")
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Model initialized: gemini-1.5-flash")
        
        response = model.generate_content("What is 2+2?")
        print(f"✅ API Response received: {response.text[:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False


if __name__ == '__main__':
    success = test_gemini_api()
    print("-" * 50)
    if success:
        print("✅ All tests passed! Gemini API is ready.")
        print("\nNext steps:")
        print("1. Start backend:  cd backend-python && python app.py")
        print("2. Start frontend: cd my-react-app && npm run dev")
        print("3. Open: http://localhost:5173")
        print("4. Test the chatbot with the purple button")
    else:
        print("❌ Tests failed. See errors above.")
        sys.exit(1)
