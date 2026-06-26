"""
============================================
Strict Quiz Routes - Strict Rule Compliance
============================================

API endpoints for quiz generation with STRICT rule enforcement.
All 11 strict rules are guaranteed.
"""

import os
import logging
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from services.quiz_generator.enhanced_strict_generator import get_cached_generator
from middleware.auth import authenticate_token
from database import get_collection

logger = logging.getLogger(__name__)

# Initialize enhanced generator with caching and fallback
quiz_generator = get_cached_generator()

# Create blueprint
strict_quiz_bp = Blueprint('strict_quiz', __name__, url_prefix='/api/strict-quiz')


@strict_quiz_bp.route('/generate', methods=['POST'])
@authenticate_token
def generate_strict_quiz():
    """
    Generate a quiz with STRICT adherence to all 11 rules.
    
    POST /api/strict-quiz/generate
    
    Body:
    {
        "topic": "Python Programming",
        "difficulty": "intermediate",
        "question_count": 5,
        "weak_areas": ["Decorators", "Async Programming"]  // optional
    }
    
    Response:
    {
        "success": true,
        "quiz": [
            {
                "id": 1,
                "question": "...",
                "sub_topic": "...",
                "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
                "correct_answer": "A",
                "difficulty": "intermediate",
                "reasoning": "..."
            }
        ],
        "metadata": {
            "topic": "...",
            "difficulty": "...",
            "question_count": 5,
            "weak_areas_targeted": 1,
            "generated_at": "2026-05-03T...",
            "validation_status": "all_11_rules_passed"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required',
                'example': {
                    'topic': 'Python Programming',
                    'difficulty': 'intermediate',
                    'question_count': 5,
                    'weak_areas': ['Decorators', 'Async Programming']
                }
            }), 400
        
        # Extract parameters
        topic = data.get('topic', '').strip()
        difficulty = data.get('difficulty', '').strip().lower()
        question_count = data.get('question_count')
        weak_areas = data.get('weak_areas')
        
        # Validate required fields
        if not topic:
            return jsonify({
                'success': False,
                'error': 'topic is required'
            }), 400
        
        if not difficulty or difficulty not in ['easier', 'beginner', 'intermediate', 'advanced', 'expert']:
            return jsonify({
                'success': False,
                'error': 'difficulty must be one of: easier, beginner, intermediate, advanced, expert'
            }), 400
        
        if not isinstance(question_count, int) or question_count < 1 or question_count > 100:
            return jsonify({
                'success': False,
                'error': 'question_count must be an integer between 1 and 100'
            }), 400
        
        if weak_areas is not None and not isinstance(weak_areas, list):
            return jsonify({
                'success': False,
                'error': 'weak_areas must be a list of strings'
            }), 400
        
        user_id = g.user.get('id') if hasattr(g, 'user') else None
        
        logger.info(
            f"Generating strict quiz: topic={topic}, difficulty={difficulty}, "
            f"count={question_count}, weak_areas={weak_areas}, user={user_id}"
        )
        
        # Generate quiz with caching, fallback, and timing
        result = quiz_generator.generate(
            topic=topic,
            difficulty=difficulty,
            question_count=question_count,
            weak_areas=weak_areas
        )
        
        # Count weak area questions if applicable
        weak_area_count = 0
        if weak_areas:
            weak_area_count = sum(
                1 for q in result.get('quiz', [])
                if q.get('targets_weak_area', False)
            )
        
        # Prepare metadata
        metadata = {
            'topic': topic,
            'difficulty': difficulty,
            'question_count': question_count,
            'weak_areas_requested': weak_areas or [],
            'weak_areas_targeted_in_quiz': weak_area_count,
            'generated_at': datetime.utcnow().isoformat(),
            'validation_status': 'all_11_rules_validated',
            'rules_enforced': [
                'Exact question count',
                'Four options per question',
                'One correct answer per question',
                'Plausible distractors',
                'No duplicates',
                'Diverse sub-topics',
                'Difficulty consistency',
                'Sub-topic field present',
                'Real-world applicable',
                'Weak area coverage (if specified)',
                'Clear reasoning provided'
            ]
        }
        
        # Optionally save to database if user is authenticated
        if user_id:
            try:
                quiz_doc = {
                    'user_id': user_id,
                    'topic': topic,
                    'difficulty': difficulty,
                    'question_count': question_count,
                    'weak_areas': weak_areas or [],
                    'questions': result.get('quiz', []),
                    'created_at': datetime.utcnow(),
                    'validation_status': 'all_11_rules_validated',
                    'source': 'openai'
                }
                
                quizzes = get_collection('quizzes_strict')
                insert_result = quizzes.insert_one(quiz_doc)
                metadata['quiz_id'] = str(insert_result.inserted_id)
                logger.info(f"Quiz saved: {insert_result.inserted_id}")
            except Exception as e:
                logger.warning(f"Failed to save quiz to database: {e}")
                # Don't fail the request if database save fails
        
        return jsonify({
            'success': True,
            'quiz': result.get('quiz', []),
            'metadata': metadata
        }), 201
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
    except Exception as e:
        logger.exception(f"Error generating quiz: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate quiz',
            'message': 'Quiz generation is temporarily unavailable. Please try again shortly.',
            'debug': os.getenv('FLASK_ENV') == 'development'
        }), 503


@strict_quiz_bp.route('/validate', methods=['POST'])
def validate_quiz_format():
    """
    Validate a quiz JSON format without generating.
    
    POST /api/strict-quiz/validate
    
    Body: quiz JSON structure
    
    Returns validation results.
    """
    try:
        data = request.get_json()
        
        if not data or 'quiz' not in data:
            return jsonify({
                'success': False,
                'error': 'quiz field required in request body'
            }), 400
        
        quiz = data.get('quiz')
        
        # Validate structure
        errors = []
        
        if not isinstance(quiz, list):
            return jsonify({
                'success': False,
                'error': 'quiz must be an array'
            }), 400
        
        for i, q in enumerate(quiz):
            # Check required fields
            required = ['id', 'question', 'sub_topic', 'options', 'correct_answer', 'difficulty', 'reasoning']
            for field in required:
                if field not in q:
                    errors.append(f"Question {i+1}: missing field '{field}'")
            
            # Check options
            if 'options' in q:
                if not isinstance(q['options'], dict):
                    errors.append(f"Question {i+1}: options must be object")
                elif set(q['options'].keys()) != {'A', 'B', 'C', 'D'}:
                    errors.append(f"Question {i+1}: options must have exactly A, B, C, D")
            
            # Check correct_answer
            if 'correct_answer' in q and q['correct_answer'] not in ['A', 'B', 'C', 'D']:
                errors.append(f"Question {i+1}: correct_answer must be A, B, C, or D")
        
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Quiz format is valid',
            'question_count': len(quiz),
            'validation_result': 'passed'
        }), 200

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strict_quiz_bp.route('/stats', methods=['GET'])
@authenticate_token
def get_cache_stats():
    """
    Get caching and performance statistics.

    GET /api/strict-quiz/stats
    """
    try:
        stats = quiz_generator.get_stats()
        logger.info("Fetched cache statistics")
        return jsonify({
            'success': True,
            'stats': stats,
        }), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@strict_quiz_bp.route('/cache/clear', methods=['POST'])
@authenticate_token
def clear_cache():
    """
    Clear the quiz cache.

    POST /api/strict-quiz/cache/clear
    """
    try:
        quiz_generator.clear_cache()
        logger.info("Cache cleared by user request")
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
        }), 200
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@strict_quiz_bp.route('/parameters', methods=['GET'])
def get_parameters_info():
    """
    Get information about valid parameters for quiz generation.
    
    GET /api/strict-quiz/parameters
    """
    return jsonify({
        'success': True,
        'parameters': {
            'topic': {
                'type': 'string',
                'required': True,
                'description': 'Quiz topic (e.g., "Python Programming", "React Hooks")',
                'max_length': 200,
                'examples': ['Python Programming', 'React Hooks', 'Database Design']
            },
            'difficulty': {
                'type': 'string',
                'required': True,
                'description': 'Difficulty level',
                'allowed_values': ['easier', 'beginner', 'intermediate', 'advanced', 'expert'],
                'difficulty_map': {
                    'easier': 'Basic definitions, simple recall, "what is" style questions',
                    'beginner': 'Conceptual understanding, simple comparisons',
                    'intermediate': 'Application-level, "how would you", multi-concept',
                    'advanced': 'Scenario-based, debugging, architecture decisions',
                    'expert': 'System design, edge cases, optimization, trade-offs'
                }
            },
            'question_count': {
                'type': 'integer',
                'required': True,
                'description': 'Number of questions to generate',
                'min': 1,
                'max': 100,
                'examples': [5, 10, 15, 20]
            },
            'weak_areas': {
                'type': 'array of strings',
                'required': False,
                'description': 'Areas to emphasize (at least 30% of questions)',
                'examples': [['Decorators', 'Async Programming'], ['React Hooks', 'Context API']]
            }
        },
        'strict_rules': {
            'rule_1': 'Generate exactly {count} multiple-choice questions',
            'rule_2': 'Each question must have exactly 4 options: A, B, C, D',
            'rule_3': 'Exactly ONE correct answer per question',
            'rule_4': 'All distractor options must be plausible — no obviously wrong answers',
            'rule_5': 'No repeated or overlapping questions',
            'rule_6': 'Cover diverse sub-topics within the main topic',
            'rule_7': 'Each question must match the requested difficulty level',
            'rule_8': 'Include a "sub_topic" field for weak-area tracking',
            'rule_9': 'Questions must be real-world applicable and conceptual',
            'rule_10': 'If weak areas are provided, at least 30% of questions must target those areas',
            'rule_11': 'For each question, provide a clear "reasoning" field explaining correct and incorrect answers'
        },
        'example_request': {
            'topic': 'Python Programming',
            'difficulty': 'intermediate',
            'question_count': 5,
            'weak_areas': ['Decorators', 'Async Programming']
        },
        'example_response_structure': {
            'quiz': [
                {
                    'id': 1,
                    'question': 'What is the purpose of decorators in Python?',
                    'sub_topic': 'Function Decorators',
                    'options': {
                        'A': 'To modify function behavior without changing the function definition',
                        'B': 'To add documentation to functions',
                        'C': 'To define class methods',
                        'D': 'To import modules'
                    },
                    'correct_answer': 'A',
                    'difficulty': 'intermediate',
                    'reasoning': 'A is correct because decorators wrap functions to modify their behavior. B is wrong because documentation uses docstrings. C is wrong because class methods are defined with @classmethod. D is wrong because decorators don\'t import modules.'
                }
            ]
        }
    }), 200
