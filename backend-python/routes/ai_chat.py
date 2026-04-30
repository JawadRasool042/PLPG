"""
AI Chat Route - Powered by Google Gemini
"""
import os
import requests
from typing import Optional, List
from flask import Blueprint, request, jsonify, g
from middleware.auth import authenticate_token
from database import get_collection
from bson import ObjectId

ai_chat_bp = Blueprint('ai_chat', __name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """You are an AI Learning Assistant for PLPG (Personalized Learning Path Generator), an educational platform that helps students discover their interests and learn tech skills.

Your role:
- Help students with learning tech topics: AI/ML, Web Development, Cybersecurity, Data Science, Mobile Development, Cloud Computing, Game Development, Programming/Coding
- Provide clear, concise explanations of concepts
- Suggest learning resources, roadmaps, and projects
- Answer quiz-related questions and explain concepts
- Give career guidance in tech fields
- Be encouraging and supportive

Guidelines:
- Keep responses focused and educational
- Use bullet points and structure for clarity
- If asked about non-tech topics, politely redirect to learning
- Personalize responses based on the student's interest if provided
- Respond in the same language the student uses (Urdu/English)
- Keep responses concise (max 300 words unless detailed explanation needed)
"""


def call_gemini_api(prompt: str) -> str:
    """Call Google Gemini API via REST"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 500,
        }
    }
    
    url = f"{GEMINI_API_URL}?key={api_key}"
    response = requests.post(url, json=payload, headers=headers, timeout=15)
    
    if response.status_code == 429:
        raise Exception("API_QUOTA_EXCEEDED: Daily quota reached")
    elif response.status_code == 403:
        raise ValueError("API Key Error: Invalid or revoked API key")
    elif response.status_code != 200:
        error_text = response.text
        raise Exception(f"API Error ({response.status_code}): {error_text[:200]}")
    
    data = response.json()
    
    if 'candidates' not in data or not data['candidates']:
        raise Exception("No response from API")
    
    content = data['candidates'][0].get('content', {})
    parts = content.get('parts', [])
    if not parts:
        raise Exception("No text content in response")
    
    return parts[0].get('text', '').strip()


def get_user_interest(user_id: str):
    try:
        col = get_collection('users')
        user = col.find_one({'_id': ObjectId(user_id)})
        if user:
            assessment = user.get('interestAssessment', {})
            if assessment.get('completed'):
                return assessment.get('primaryInterest')
    except Exception:
        pass
    return None


def build_prompt(message: str, user_interest: Optional[str] = None, history: Optional[List] = None) -> str:
    context = SYSTEM_PROMPT
    if user_interest:
        context += f"\n\nStudent's primary interest: {user_interest}"
    if history:
        context += "\n\nConversation history:"
        for msg in history[-6:]:
            role = "Student" if msg['role'] == 'user' else "Assistant"
            context += f"\n{role}: {msg['text']}"
    context += f"\n\nStudent: {message}\nAssistant:"
    return context


@ai_chat_bp.route('/chat', methods=['POST'])
@authenticate_token
def ai_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])

    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400
    if len(message) > 1000:
        return jsonify({'success': False, 'message': 'Message too long'}), 400

    user_id = g.user.get('id', '')
    user_interest = get_user_interest(user_id)

    try:
        prompt = build_prompt(message, user_interest, history)
        response_text = call_gemini_api(prompt)
        return jsonify({'success': True, 'response': response_text})

    except ValueError as e:
        error_msg = str(e)
        print(f"Configuration error: {error_msg}")
        return jsonify({'success': False, 'message': f'API configuration error: {error_msg}'}), 500
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API error: {error_msg}")
        if 'QUOTA_EXCEEDED' in error_msg:
            return jsonify({'success': True, 'response': "Sorry, the AI service has reached its daily limit. Please try again tomorrow or contact support."}), 200
        if 'API Key' in error_msg or 'Invalid' in error_msg:
            return jsonify({'success': False, 'message': 'API key issue - please check your configuration'}), 500
        return jsonify({'success': True, 'response': "Sorry, I had trouble processing that. Please try again."}), 200


@ai_chat_bp.route('/chat/guest', methods=['POST'])
def ai_chat_guest():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])

    if not message:
        return jsonify({'success': False, 'message': 'Message is required'}), 400

    try:
        prompt = build_prompt(message, None, history)
        response_text = call_gemini_api(prompt)
        return jsonify({'success': True, 'response': response_text})

    except Exception as e:
        print(f"Gemini guest error: {e}")
        return jsonify({'success': True, 'response': "Sorry, I'm having trouble right now. Please try again."}), 200
