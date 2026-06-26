"""
============================================
Quiz Generator Service
============================================

Core quiz generation functionality with OpenAI integration.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from bson import ObjectId

from .openai_client import OpenAIClient, OpenAIError
from .models import Question, Quiz
from .exceptions import ValidationError, APIError, DatabaseError
from .parameter_validator import validate_parameters
from .question_validator import validate_questions
from database import get_collection

logger = logging.getLogger(__name__)


def generate_quiz(
    topic: str,
    difficulty_level: int,
    question_count: int = 5,
    weak_areas: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    user_profile: Optional[Dict[str, Any]] = None,
    quiz_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete quiz using OpenAI.
    
    Args:
        topic: Main topic for quiz (e.g., "Web Development")
        difficulty_level: 1-5 scale (1=easiest, 5=expert)
        question_count: Number of questions (default: 5)
        weak_areas: Optional list of weak areas to target
        user_id: Optional user ID for tracking
        user_profile: Optional user profile for personalization
        quiz_id: Optional existing quiz ID for updates
        
    Returns:
        Generated quiz data with metadata
    """
    
    # Validate parameters
    try:
        validate_parameters(topic, difficulty_level, question_count, weak_areas)
    except ValidationError as e:
        logger.error(f"Parameter validation failed: {e}")
        raise
    
    # Initialize OpenAI client
    try:
        client = OpenAIClient()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        raise APIError(f"OpenAI client initialization failed: {e}")
    
    # Build generation prompt with user context
    prompt = _build_generation_prompt(
        topic=topic,
        difficulty_level=difficulty_level,
        question_count=question_count,
        weak_areas=weak_areas,
        user_profile=user_profile
    )
    
    # Generate questions using OpenAI with fallback
    try:
        result = client.generate_quiz(
            topic=topic,
            difficulty_level=difficulty_level,
            question_count=question_count,
            weak_areas=weak_areas,
            user_profile=user_profile
        )
        
        questions_data = result['questions']
        logger.info(f"Successfully generated {len(questions_data)} questions using OpenAI")
        
        # Validate questions
        validate_questions(
            questions=questions_data,
            requested_count=question_count,
            requested_difficulty=difficulty_level,
            weak_areas=weak_areas
        )
        
        # Format questions for storage
        formatted_questions = _format_questions_for_storage(
            questions_data, difficulty_level
        )
        
        # Create quiz document
        quiz_doc = {
            'quiz_id': quiz_id or str(ObjectId()),
            'topic': topic,
            'difficulty_level': difficulty_level,
            'question_count': question_count,
            'weak_areas': weak_areas or [],
            'questions': formatted_questions,
            'generation_timestamp': datetime.utcnow(),
            'user_id': user_id,
            'metadata': {
                'source': 'openai',
                'generated_at': datetime.utcnow().isoformat(),
                'difficulty_mapping': _get_difficulty_mapping(difficulty_level)
            }
        }
        
        # Save to database
        if user_id:
            _save_quiz_to_database(quiz_doc)
        
        logger.info(f"Generated quiz: {quiz_doc['quiz_id']} with {question_count} questions")
        
        return {
            'success': True,
            'quiz_id': quiz_doc['quiz_id'],
            'topic': topic,
            'difficulty_level': difficulty_level,
            'question_count': question_count,
            'questions': formatted_questions,
            'metadata': quiz_doc['metadata']
        }
        
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise APIError(f"OpenAI API error: {e}")


def retrieve_quiz(quiz_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a quiz from database by ID.
    
    Args:
        quiz_id: Quiz ID to retrieve
        
    Returns:
        Quiz document or None if not found
    """
    try:
        coll = get_collection('quizzes')
        quiz = coll.find_one({'quiz_id': quiz_id})
        
        if quiz:
            quiz['_id'] = str(quiz['_id'])
        
        return quiz
    except Exception as e:
        logger.error(f"Failed to retrieve quiz {quiz_id}: {e}")
        raise DatabaseError('retrieve', f"Failed to retrieve quiz: {e}")


def _build_generation_prompt(
    topic: str,
    difficulty_level: int,
    question_count: int,
    weak_areas: Optional[List[str]] = None,
    user_profile: Optional[Dict[str, Any]] = None
) -> str:
    """Build context-aware generation prompt (kept for compatibility)."""
    # This is now handled by OpenAIClient generation methods
    # Kept for backward compatibility
    return ""


def _get_generation_system_prompt() -> str:
    """Get system prompt for quiz generation (deprecated)."""
    return ""


def _parse_generation_response(response: str) -> List[Dict[str, Any]]:
    """Parse and validate JSON from LLM response."""
    
    if not response:
        raise ValidationError("Empty response from LLM API")
    
    # Try direct parse first
    try:
        data = json.loads(response)
        questions = _extract_questions(data)
        return questions
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code fences
    cleaned = response.replace("```json", "").replace("```", "").strip()
    
    # Try again
    try:
        data = json.loads(cleaned)
        questions = _extract_questions(data)
        return questions
    except json.JSONDecodeError as e:
        raise ValidationError(f"Failed to parse JSON response: {str(e)}")


def _extract_questions(data: Any) -> List[Dict[str, Any]]:
    """Extract questions from parsed JSON data."""
    
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "quiz" in data and isinstance(data["quiz"], list):
            return data["quiz"]
        elif "questions" in data:
            return data["questions"]
    
    raise ValidationError(f"Invalid response structure. Expected 'quiz' or 'questions' key.")


def _format_questions_for_storage(
    questions_data: List[Dict[str, Any]],
    difficulty_level: int
) -> List[Dict[str, Any]]:
    """Format questions for database storage."""
    
    formatted = []
    for idx, q in enumerate(questions_data):
        formatted.append({
            'id': q.get('id', idx + 1),
            'question': q.get('question'),
            'sub_topic': q.get('sub_topic'),
            'options': q.get('options', {}),
            'correct_answer': q.get('correct_answer'),
            'difficulty': difficulty_level,
            'reasoning': q.get('reasoning'),
            'created_at': datetime.utcnow()
        })
    
    return formatted


def _get_difficulty_mapping(level: int) -> str:
    """Get difficulty name from level."""
    mappings = {
        1: "very easy",
        2: "easy",
        3: "medium",
        4: "hard",
        5: "expert"
    }
    return mappings.get(level, "medium")


def _get_difficulty_name(level: int) -> str:
    """Get difficulty name for API calls."""
    mappings = {
        1: "beginner",
        2: "beginner",
        3: "intermediate",
        4: "advanced",
        5: "expert"
    }
    return mappings.get(level, "intermediate")


def _save_quiz_to_database(quiz_doc: Dict[str, Any]) -> bool:
    """Save quiz to MongoDB database."""
    
    try:
        coll = get_collection('quizzes')
        result = coll.insert_one(quiz_doc)
        quiz_doc['_id'] = result.inserted_id
        return True
    except Exception as e:
        logger.error(f"Failed to save quiz to database: {e}")
        return False


def generate_adaptive_quiz(
    topic: str,
    user_id: str,
    user_performance: Dict[str, Any],
    weak_areas: Optional[List[str]] = None,
    question_count: int = 5
) -> Tuple[List[Dict[str, Any]], str, bool]:
    """
    Generate adaptive quiz based on user performance.
    
    Args:
        topic: Subject area
        user_id: User ID
        user_performance: User's quiz performance history
        weak_areas: Areas to target
        question_count: Number of questions
        
    Returns:
        Tuple of (questions_list, recommended_level, success_flag)
    """
    
    try:
        # Determine recommended difficulty based on performance
        recommended_level = _determine_adaptive_difficulty(user_performance)
        
        # Generate quiz with adaptive difficulty
        result = generate_quiz(
            topic=topic,
            difficulty_level=recommended_level,
            question_count=question_count,
            weak_areas=weak_areas,
            user_id=user_id
        )
        
        if result['success']:
            return result['questions'], result['metadata']['difficulty_mapping'], True
        else:
            return [], 'medium', False
            
    except Exception as e:
        logger.error(f"Failed to generate adaptive quiz: {e}")
        return [], 'medium', False


def _determine_adaptive_difficulty(user_performance: Dict[str, Any]) -> int:
    """Determine adaptive difficulty based on user performance."""
    
    # Default to medium
    default_level = 3
    
    # Get recent scores
    recent_scores = user_performance.get('recent_scores', [])
    if not recent_scores:
        return default_level
    
    # Calculate average score
    avg_score = sum(recent_scores) / len(recent_scores)
    
    # Map score to difficulty level
    if avg_score >= 85:
        return 4  # Hard
    elif avg_score >= 70:
        return 3  # Medium
    elif avg_score >= 50:
        return 2  # Easy
    else:
        return 1  # Very easy
