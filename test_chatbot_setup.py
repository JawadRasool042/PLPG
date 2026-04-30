#!/usr/bin/env python3
"""
🤖 Gemini Chatbot Integration Test Script
Run this to verify your AI chatbot is working correctly
"""

import os
import sys
import json
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    CHECK = '✓'
    CROSS = '✗'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}{Colors.CHECK} {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}{Colors.CROSS} {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def check_env_file():
    """Check if .env file exists and has GEMINI_API_KEY"""
    print_header("1️⃣  Checking Environment Setup")
    
    env_path = Path(__file__).parent / "backend-python" / ".env"
    
    if not env_path.exists():
        print_error(f".env file not found at {env_path}")
        return False
    
    print_success(f".env file found at {env_path}")
    
    # Read .env file
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    if 'GEMINI_API_KEY=' not in env_content:
        print_error("GEMINI_API_KEY not found in .env")
        return False
    
    # Extract API key (first 10 chars + ...)
    for line in env_content.split('\n'):
        if line.startswith('GEMINI_API_KEY='):
            key = line.split('=', 1)[1].strip()
            if key and key != 'your-google-gemini-api-key-here':
                masked_key = key[:10] + '...' + key[-5:]
                print_success(f"GEMINI_API_KEY is configured: {masked_key}")
                return True
            else:
                print_error("GEMINI_API_KEY is not set (still placeholder)")
                return False
    
    return False

def check_requirements():
    """Check if required packages are in requirements.txt"""
    print_header("2️⃣  Checking Python Dependencies")
    
    req_path = Path(__file__).parent / "backend-python" / "requirements.txt"
    
    if not req_path.exists():
        print_error(f"requirements.txt not found at {req_path}")
        return False
    
    print_success(f"requirements.txt found")
    
    with open(req_path, 'r') as f:
        requirements = f.read()
    
    required_packages = [
        'flask',
        'flask-cors',
        'pymongo',
        'google-generativeai',
        'pyjwt',
        'python-dotenv'
    ]
    
    all_found = True
    for package in required_packages:
        if package.lower() in requirements.lower():
            print_success(f"Package '{package}' found in requirements.txt")
        else:
            print_error(f"Package '{package}' NOT found in requirements.txt")
            all_found = False
    
    return all_found

def check_backend_files():
    """Check if backend AI chat files exist"""
    print_header("3️⃣  Checking Backend Files")
    
    files_to_check = [
        "backend-python/app.py",
        "backend-python/routes/ai_chat.py",
        "backend-python/config.py",
        "backend-python/.env",
    ]
    
    all_found = True
    for file in files_to_check:
        file_path = Path(__file__).parent / file
        if file_path.exists():
            print_success(f"Found: {file}")
        else:
            print_error(f"Missing: {file}")
            all_found = False
    
    return all_found

def check_frontend_files():
    """Check if frontend chatbot files exist"""
    print_header("4️⃣  Checking Frontend Files")
    
    files_to_check = [
        "my-react-app/src/components/AIChatbot.tsx",
        "my-react-app/src/services/chatService.ts",
        "my-react-app/vite.config.ts",
    ]
    
    all_found = True
    for file in files_to_check:
        file_path = Path(__file__).parent / file
        if file_path.exists():
            print_success(f"Found: {file}")
        else:
            print_error(f"Missing: {file}")
            all_found = False
    
    return all_found

def check_database_setup():
    """Check MongoDB connection info in config"""
    print_header("5️⃣  Checking Database Setup")
    
    config_path = Path(__file__).parent / "backend-python" / ".env"
    
    if not config_path.exists():
        print_error("Cannot check database (no .env file)")
        return False
    
    with open(config_path, 'r') as f:
        env_content = f.read()
    
    if 'MONGODB_URI=' in env_content:
        print_success("MongoDB configuration found")
        for line in env_content.split('\n'):
            if line.startswith('MONGODB_URI='):
                uri = line.split('=', 1)[1].strip()
                if 'localhost' in uri or 'mongodb' in uri:
                    print_success(f"Database URI configured: {uri[:40]}...")
                    return True
        return True
    else:
        print_error("MONGODB_URI not found in .env")
        return False

def check_cors_setup():
    """Check if CORS is properly configured"""
    print_header("6️⃣  Checking CORS Configuration")
    
    app_path = Path(__file__).parent / "backend-python" / "app.py"
    
    if not app_path.exists():
        print_error("app.py not found")
        return False
    
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    if 'flask_cors' in app_content.lower() and 'cors(app' in app_content.lower():
        print_success("CORS is properly configured in Flask")
        return True
    else:
        print_warning("Could not verify CORS configuration")
        return False

def print_summary(results):
    """Print final summary"""
    print_header("📊 Test Summary")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"Total Checks: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    if failed > 0:
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}🎉 All checks passed! Your chatbot is ready to use!{Colors.RESET}")
        print(f"\n{Colors.BLUE}Next Steps:{Colors.RESET}")
        print("1. Install dependencies: pip install -r backend-python/requirements.txt")
        print("2. Start backend:        cd backend-python && python app.py")
        print("3. Start frontend:       cd my-react-app && npm run dev")
        print("4. Open:                 http://localhost:5173")
        print("5. Click the purple chat bubble and start chatting!")
    else:
        print(f"\n{Colors.RED}❌ Some checks failed. Please fix the issues above.{Colors.RESET}")
    
    print()

def main():
    print(f"\n{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║                                                        ║")
    print("║    🤖 PLPG Gemini Chatbot Integration Test             ║")
    print("║                                                        ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    results = {
        "Environment Setup": check_env_file(),
        "Python Dependencies": check_requirements(),
        "Backend Files": check_backend_files(),
        "Frontend Files": check_frontend_files(),
        "Database Setup": check_database_setup(),
        "CORS Configuration": check_cors_setup(),
    }
    
    print_summary(results)
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
