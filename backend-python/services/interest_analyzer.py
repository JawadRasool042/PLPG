"""
============================================
Interest Analyzer Service - LLM-Powered
============================================

This service uses Google Gemini API to provide advanced interest analysis
with detailed explanations and personalized recommendations.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime

from database import get_collection
from bson import ObjectId

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Domain information for context
DOMAIN_INFO = {
    "Coding": {
        "description": "Programming fundamentals and software development",
        "skills": ["Problem solving", "Logic", "Debugging", "Algorithms"],
        "careers": ["Software Developer", "Backend Engineer", "Systems Programmer", "Embedded Systems Engineer"],
        "prerequisites": ["Logical thinking", "Patience", "Problem-solving mindset"]
    },
    "Web Development": {
        "description": "Creating websites and web applications",
        "skills": ["HTML/CSS", "JavaScript", "Backend frameworks", "Databases", "UI/UX"],
        "careers": ["Frontend Developer", "Full Stack Developer", "Web Designer", "Backend Engineer"],
        "prerequisites": ["Creativity", "Attention to detail", "Understanding of user experience"]
    },
    "Game Development": {
        "description": "Creating interactive games and experiences",
        "skills": ["Game engines", "3D graphics", "Physics", "Sound design", "Game mechanics"],
        "careers": ["Game Developer", "Game Designer", "Graphics Programmer", "Technical Artist"],
        "prerequisites": ["Creativity", "Understanding of gameplay", "Technical skills"]
    },
    "Cybersecurity": {
        "description": "Security, ethical hacking, and protecting systems",
        "skills": ["Network security", "Cryptography", "Vulnerability assessment", "Penetration testing"],
        "careers": ["Security Engineer", "Penetration Tester", "Security Analyst", "CISO"],
        "prerequisites": ["System knowledge", "Attention to detail", "Ethical mindset"]
    },
    "Data Science": {
        "description": "Analyzing data and extracting insights",
        "skills": ["Statistics", "Python/R", "Data visualization", "Machine learning", "SQL"],
        "careers": ["Data Scientist", "Data Analyst", "ML Engineer", "Business Analyst"],
        "prerequisites": ["Math skills", "Curiosity", "Statistical thinking"]
    },
    "Mobile Development": {
        "description": "Building apps for smartphones and tablets",
        "skills": ["Native languages", "Mobile frameworks", "UI design", "Performance optimization"],
        "careers": ["iOS Developer", "Android Developer", "Mobile Engineer", "App Developer"],
        "prerequisites": ["Knowledge of mobile platforms", "UI/UX understanding"]
    },
    "Cloud Computing": {
        "description": "Cloud platforms, DevOps, and infrastructure",
        "skills": ["Cloud platforms", "Docker", "Kubernetes", "Infrastructure", "CI/CD"],
        "careers": ["Cloud Engineer", "DevOps Engineer", "Infrastructure Engineer", "SRE"],
        "prerequisites": ["System administration knowledge", "Understanding of networking"]
    },
    "AI & Machine Learning": {
        "description": "Artificial intelligence and machine learning",
        "skills": ["Deep learning", "Neural networks", "Natural language processing", "Computer vision"],
        "careers": ["ML Engineer", "AI Researcher", "Data Scientist", "Research Engineer"],
        "prerequisites": ["Strong math/statistics", "Programming proficiency", "Research mindset"]
    },
}


class InterestAnalyzer:
    """Service for analyzing user interests using LLM"""
    
    @staticmethod
    def call_gemini_api(prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Call Google Gemini API"""
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
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        url = f"{GEMINI_API_URL}?key={api_key}"
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
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
    
    @staticmethod
    def analyze_interest_profile(user_id: str, interest_scores: Dict[str, float], 
                                user_analytics: Dict[str, Any] = None,
                                user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user interest profile and generate detailed analysis using LLM
        
        Args:
            user_id: User ID
            interest_scores: { domain: score } (0-10 scale)
            user_analytics: User performance analytics
            user_info: User profile information
            
        Returns:
            Comprehensive interest analysis with LLM insights
        """
        
        # Find primary and secondary interests
        sorted_interests = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
        primary_interest = sorted_interests[0]
        secondary_interests = sorted_interests[1:3]
        
        # Determine confidence
        primary_score = primary_interest[1]
        second_score = secondary_interests[0][1] if secondary_interests else 0
        confidence = min(100, (primary_score / 10) * 100)  # Convert to percentage
        
        # Build context for LLM
        context_text = InterestAnalyzer._build_analysis_context(
            primary_interest[0], 
            interest_scores, 
            user_analytics, 
            user_info
        )
        
        # Generate LLM analysis
        analysis_text = InterestAnalyzer._generate_llm_analysis(
            primary_interest[0],
            context_text
        )
        
        # Parse LLM response
        parsed_analysis = InterestAnalyzer._parse_analysis_response(analysis_text)
        
        return {
            'primary_interest': primary_interest[0],
            'primary_score': primary_interest[1],
            'confidence': confidence,
            'secondary_interests': [
                {
                    'domain': sec[0],
                    'score': sec[1],
                    'percentile': round((sec[1] / 10) * 100, 1)
                }
                for sec in secondary_interests
            ],
            'all_scores': {k: v for k, v in sorted_interests},
            'analysis': parsed_analysis,
            'generatedAt': datetime.utcnow(),
            'expiresAt': datetime.utcnow().replace(day=datetime.utcnow().day + 30)
        }
    
    @staticmethod
    def _build_analysis_context(primary_domain: str, interest_scores: Dict[str, float],
                               user_analytics: Dict[str, Any] = None,
                               user_info: Dict[str, Any] = None) -> str:
        """Build context for LLM analysis"""
        
        context = f"User's Primary Interest: {primary_domain}\n"
        context += f"Interest Scores (0-10 scale): {json.dumps(interest_scores, indent=2)}\n\n"
        
        if user_analytics:
            context += f"Quiz Performance:\n"
            context += f"  - Total Quizzes: {user_analytics.get('totalQuizzesAttempted', 0)}\n"
            context += f"  - Overall Accuracy: {user_analytics.get('overallAccuracy', 0):.1f}%\n"
            context += f"  - Average Score: {user_analytics.get('averageQuizScore', 0):.1f}/100\n"
            
            strong_areas = user_analytics.get('strongAreas', [])
            weak_areas = user_analytics.get('weakAreas', [])
            
            if strong_areas:
                context += f"  - Strong Areas: {', '.join([a.get('domain', 'Unknown') for a in strong_areas[:3]])}\n"
            if weak_areas:
                context += f"  - Areas to Improve: {', '.join([a.get('domain', 'Unknown') for a in weak_areas[:3]])}\n"
        
        if user_info:
            context += f"\nUser Information:\n"
            if user_info.get('firstName'):
                context += f"  - Name: {user_info.get('firstName')} {user_info.get('lastName', '')}\n"
            if user_info.get('learningLevel'):
                context += f"  - Learning Level: {user_info.get('learningLevel')}\n"
            if user_info.get('learningGoals'):
                context += f"  - Goals: {', '.join(user_info.get('learningGoals', []))}\n"
        
        return context
    
    @staticmethod
    def _generate_llm_analysis(primary_domain: str, context: str) -> str:
        """Generate LLM analysis"""
        
        domain_info = DOMAIN_INFO.get(primary_domain, {})
        
        prompt = f"""You are an expert educational counselor. Based on the following user profile, provide a detailed personalized interest analysis.

{context}

About {primary_domain}:
- Description: {domain_info.get('description', 'N/A')}
- Key Skills: {', '.join(domain_info.get('skills', []))}
- Career Paths: {', '.join(domain_info.get('careers', []))}

Please provide the response in the following JSON format (ensure valid JSON):
{{
    "why_this_field": "Explain specifically why this field matches the user's profile (2-3 sentences)",
    "benefits": ["Benefit 1", "Benefit 2", "Benefit 3", "Benefit 4"],
    "current_strengths": ["Strength 1 relevant to {primary_domain}", "Strength 2", "Strength 3"],
    "skills_to_develop": ["Skill 1 to learn", "Skill 2 to learn", "Skill 3 to learn"],
    "recommended_path": "A brief recommended learning path (2-3 sentences)",
    "success_factors": ["Factor 1 for success", "Factor 2 for success", "Factor 3 for success"],
    "time_to_competency": "Estimated time to reach competency level",
    "career_outlook": "Brief overview of career opportunities in this field"
}}

Generate a thoughtful, personalized analysis based on the user's specific profile and interest patterns."""
        
        response_text = InterestAnalyzer.call_gemini_api(prompt, temperature=0.7, max_tokens=1200)
        
        return response_text
    
    @staticmethod
    def _parse_analysis_response(response_text: str) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        
        try:
            # Try to extract JSON from the response
            import json
            
            # Try direct JSON parse
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    return json.loads(json_str)
                
                # Fallback structure
                return {
                    "why_this_field": response_text[:200],
                    "benefits": ["Skill development", "Career opportunities", "Personal growth"],
                    "current_strengths": ["Problem solving", "Analytical thinking"],
                    "skills_to_develop": ["Technical skills", "Project experience"],
                    "recommended_path": "Start with fundamentals and build gradually",
                    "success_factors": ["Consistent practice", "Real projects", "Community engagement"],
                    "time_to_competency": "6-12 months with dedicated learning",
                    "career_outlook": "Strong demand in the industry"
                }
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                "why_this_field": "This field matches your demonstrated interests",
                "benefits": ["Career development", "Technical growth", "Innovation opportunities"],
                "current_strengths": ["Analytical mindset", "Learning ability"],
                "skills_to_develop": ["Domain-specific technical skills", "Practical experience"],
                "recommended_path": "Follow a structured learning path with projects",
                "success_factors": ["Dedication", "Practice", "Mentorship"],
                "time_to_competency": "6-12 months",
                "career_outlook": "Growing opportunities in this field"
            }
    
    @staticmethod
    def generate_detailed_recommendations(primary_domain: str, 
                                         user_analytics: Dict[str, Any] = None,
                                         user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate detailed recommendations for learning path
        
        Returns:
            Detailed recommendations with resources and roadmap
        """
        
        domain_info = DOMAIN_INFO.get(primary_domain, {})
        
        prompt = f"""Generate a detailed learning recommendation for someone interested in {primary_domain}.

Domain Information:
- Description: {domain_info.get('description', 'N/A')}
- Key Skills: {', '.join(domain_info.get('skills', []))}
- Career Paths: {', '.join(domain_info.get('careers', []))}

Please provide recommendations in this JSON format:
{{
    "learning_path": [
        {{"level": "Beginner", "duration": "1-2 months", "topics": ["Topic 1", "Topic 2"], "resources": ["Resource 1", "Resource 2"]}},
        {{"level": "Intermediate", "duration": "2-3 months", "topics": ["Topic 1", "Topic 2"], "resources": ["Resource 1", "Resource 2"]}},
        {{"level": "Advanced", "duration": "3-6 months", "topics": ["Topic 1", "Topic 2"], "resources": ["Resource 1", "Resource 2"]}}
    ],
    "top_resources": [
        {{"title": "Resource Title", "type": "course|book|platform", "url": "https://example.com", "why_recommended": "Reason"}},
        {{"title": "Resource 2", "type": "practice|project", "url": "https://example.com", "why_recommended": "Reason"}}
    ],
    "project_ideas": [
        {{"name": "Project 1", "difficulty": "Beginner", "duration": "2 weeks", "description": "Description"}},
        {{"name": "Project 2", "difficulty": "Intermediate", "duration": "4 weeks", "description": "Description"}}
    ],
    "skills_required": ["Skill 1", "Skill 2", "Skill 3"],
    "estimated_time_to_job_ready": "Time estimate",
    "certification_options": [
        {{"name": "Certification 1", "provider": "Provider", "value": "Value"}}
    ]
}}

Make recommendations practical, specific, and achievable."""
        
        response_text = InterestAnalyzer.call_gemini_api(prompt, temperature=0.7, max_tokens=1500)
        
        try:
            import json
            # Parse JSON response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
        
        # Fallback response
        return {
            "learning_path": [
                {
                    "level": "Beginner",
                    "duration": "1-2 months",
                    "topics": ["Fundamentals", "Core concepts"],
                    "resources": ["Official documentation", "Online tutorials"]
                },
                {
                    "level": "Intermediate",
                    "duration": "2-3 months",
                    "topics": ["Advanced topics", "Best practices"],
                    "resources": ["Advanced courses", "Practice projects"]
                },
                {
                    "level": "Advanced",
                    "duration": "3-6 months",
                    "topics": ["Specialization", "Mastery"],
                    "resources": ["Expert mentorship", "Real-world projects"]
                }
            ],
            "top_resources": [
                {
                    "title": "Official Documentation",
                    "type": "documentation",
                    "why_recommended": "Comprehensive and authoritative"
                }
            ],
            "project_ideas": [
                {
                    "name": "Beginner Project",
                    "difficulty": "Beginner",
                    "duration": "2 weeks"
                }
            ]
        }
