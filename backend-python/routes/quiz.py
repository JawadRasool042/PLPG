"""
============================================
Quiz Routes - API Endpoints
============================================

RESTful API endpoints for quiz operations
"""

import logging
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt
from models.user_performance import UserPerformance
from middleware.auth import authenticate_token

logger = logging.getLogger(__name__)


quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/generate', methods=['POST'])
@authenticate_token
def generate_quiz():
    """
    Generate a new quiz
    
    POST /api/quiz/generate
    Body: {
        "interest": "AI/ML",
        "level": "Beginner"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400
        
        user = g.user_doc
        interest = data.get('interest')
        level = data.get('level', 'Beginner')
        num_questions = int(data.get('count', 10))
        
        if not interest:
            user_assessment = user.get('interestAssessment', {}) if user else {}
            interest = user_assessment.get('primaryInterest')

        if not interest or interest == 'PENDING_USER_RESOLUTION':
            return jsonify({
                'success': False,
                'message': 'Interest is required. Please complete the interest assessment.'
            }), 400
        
        # Validate interest and level
        if not Quiz.validate_interest(interest):
            return jsonify({
                'success': False,
                'message': 'Invalid interest'
            }), 400

        if not Quiz.validate_level(level):
            return jsonify({
                'success': False,
                'message': f'Invalid level. Available: {", ".join(Quiz.LEVELS)}'
            }), 400

        # Generate quiz
        quiz = Quiz.generate_quiz(interest, level, num_questions=num_questions, user_id=g.user.get('id'))
        
        return jsonify({
            'success': True,
            'message': 'AI quiz generated successfully',
            'quiz': Quiz.to_response(quiz, include_answers=False)
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        print(f'Error generating quiz: {e}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while generating the quiz'
        }), 500


@quiz_bp.route('/<quiz_id>', methods=['GET'])
@authenticate_token
def get_quiz(quiz_id):
    """
    Get a specific quiz
    
    GET /api/quiz/<quiz_id>
    """
    try:
        quiz = Quiz.find_by_id(quiz_id)
        
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz not found'
            }), 404
        
        return jsonify({
            'success': True,
            'quiz': Quiz.to_response(quiz, include_answers=False)
        }), 200
        
    except Exception as e:
        print(f'Error fetching quiz: {e}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching the quiz'
        }), 500


@quiz_bp.route('/<quiz_id>/submit', methods=['POST'])
@authenticate_token
def submit_quiz(quiz_id):
    """
    Submit quiz answers
    
    POST /api/quiz/<quiz_id>/submit
    Body: {
        "answers": {
            "0": "B",
            "1": "A",
            ...
        }
    }
    """
    try:
        user = g.user_doc
        data = request.get_json()
        
        if not data or 'answers' not in data:
            return jsonify({
                'success': False,
                'message': 'Answers are required'
            }), 400
        
        answers = data.get('answers')
        
        if not isinstance(answers, dict):
            return jsonify({
                'success': False,
                'message': 'Answers must be an object'
            }), 400
        
        # Get quiz
        quiz = Quiz.find_by_id(quiz_id)
        
        if not quiz:
            return jsonify({
                'success': False,
                'message': 'Quiz not found'
            }), 404
        
        # Create attempt and calculate score
        # Use g.user['id'] which comes from JWT token
        user_id = g.user.get('id') or str(user.get('_id'))
        attempt = QuizAttempt.create(
            user_id=user_id,
            quiz_id=quiz_id,
            answers=answers,
            quiz_data=quiz
        )
        
        # Update user performance
        UserPerformance.update_performance(
            user_id=user_id,
            attempt_data=attempt
        )
        
        return jsonify({
            'success': True,
            'message': 'Quiz submitted successfully',
            'attempt': QuizAttempt.to_response(attempt, include_results=True)
        }), 200
        
    except Exception as e:
        print(f'Error submitting quiz: {e}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting the quiz'
        }), 500


@quiz_bp.route('/available', methods=['GET'])
@authenticate_token
def get_available_quizzes():
    """
    Get list of available quiz categories
    Prioritizes user's detected interests from assessment
    
    GET /api/quiz/available
    """
    try:
        user = g.user_doc
        interests = Quiz.get_available_interests()
        logger.debug(f"Found interests: {interests}")
        
        # Get user's interest assessment
        user_assessment = user.get('interestAssessment', {})
        primary_interest = user_assessment.get('primaryInterest')
        all_user_interests = user_assessment.get('allInterests', [])
        
        # Create a mapping of user interests for prioritization
        user_interest_map = {}
        if all_user_interests:
            for interest_data in all_user_interests:
                domain = interest_data.get('domain')
                confidence = interest_data.get('confidence', 0)
                user_interest_map[domain] = confidence
        
        # Get template counts for each interest and level
        categories = []
        for interest in interests:
            beginner_count = Quiz.get_template_count(interest, 'Beginner')
            intermediate_count = Quiz.get_template_count(interest, 'Intermediate')
            advanced_count = Quiz.get_template_count(interest, 'Advanced')
            
            # Check if this is the user's primary interest
            is_primary = (primary_interest == interest)
            user_confidence = user_interest_map.get(interest, 0)
            
            category_data = {
                'interest': interest,
                'levels': {
                    'Beginner': beginner_count >= 10,
                    'Intermediate': intermediate_count >= 10,
                    'Advanced': advanced_count >= 10
                },
                'questionCounts': {
                    'Beginner': beginner_count,
                    'Intermediate': intermediate_count,
                    'Advanced': advanced_count
                },
                'isPrimary': is_primary,
                'userConfidence': round(user_confidence * 100, 1) if user_confidence > 0 else None,
                'recommended': user_confidence > 0.1  # Recommend if confidence > 10%
            }
            
            categories.append(category_data)
        
        # Sort categories: primary first, then by user confidence, then alphabetically
        def sort_key(cat):
            if cat['isPrimary']:
                return (0, -1, cat['interest'])  # Primary first
            elif cat['userConfidence']:
                return (1, -cat['userConfidence'], cat['interest'])  # Then by confidence
            else:
                return (2, 0, cat['interest'])  # Then others alphabetically
        
        categories.sort(key=sort_key)
        
        return jsonify({
            'success': True,
            'categories': categories,
            'userAssessment': {
                'completed': user_assessment.get('completed', False),
                'primaryInterest': primary_interest
            }
        }), 200
        
    except Exception as e:
        print(f'Error fetching available quizzes: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching available quizzes'
        }), 500


@quiz_bp.route('/history', methods=['GET'])
@authenticate_token
def get_quiz_history():
    """
    Get user's quiz history
    
    GET /api/quiz/history?limit=20
    """
    try:
        user = g.user
        limit = request.args.get('limit', 20, type=int)
        
        # Get user ID from JWT token
        user_id = user.get('id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User ID not found in token'
            }), 401
        
        attempts = QuizAttempt.find_by_user(user_id, limit=limit)
        
        # Handle empty attempts gracefully
        formatted_attempts = []
        for attempt in attempts:
            try:
                formatted = QuizAttempt.to_response(attempt, include_results=False)
                if formatted:
                    formatted_attempts.append(formatted)
            except Exception as e:
                print(f'Error formatting attempt: {e}')
                continue
        
        return jsonify({
            'success': True,
            'attempts': formatted_attempts
        }), 200
        
    except Exception as e:
        print(f'Error fetching quiz history: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': True,  # Return success with empty array instead of error
            'attempts': []
        }), 200


@quiz_bp.route('/performance', methods=['GET'])
@authenticate_token
def get_performance():
    """
    Get user performance analytics
    
    GET /api/quiz/performance?interest=AI/ML
    """
    try:
        user = g.user
        interest = request.args.get('interest', None)
        
        # Get user ID from JWT token
        user_id = user.get('id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User ID not found in token'
            }), 401
        
        performance = UserPerformance.get_performance(user_id, interest)
        
        # Ensure we always return valid data
        if not performance:
            performance = {
                'overallStats': {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0,
                    'totalCorrect': 0,
                    'totalQuestions': 0
                },
                'byInterest': {},
                'recentScores': [],
                'analysis': {
                    'strengths': [],
                    'weaknesses': [],
                    'recommendations': []
                }
            }
        
        return jsonify({
            'success': True,
            'performance': UserPerformance.to_response(performance) if not interest else performance
        }), 200
        
    except Exception as e:
        print(f'Error fetching performance: {e}')
        import traceback
        traceback.print_exc()
        # Return empty performance data instead of error
        return jsonify({
            'success': True,
            'performance': {
                'overallStats': {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0,
                    'totalCorrect': 0,
                    'totalQuestions': 0
                },
                'byInterest': {},
                'recentScores': [],
                'analysis': {
                    'strengths': [],
                    'weaknesses': [],
                    'recommendations': []
                },
                'updatedAt': None
            }
        }), 200


@quiz_bp.route('/attempt/<attempt_id>', methods=['GET'])
@authenticate_token
def get_attempt(attempt_id):
    """
    Get a specific quiz attempt with results
    
    GET /api/quiz/attempt/<attempt_id>
    """
    try:
        user = g.user
        attempt = QuizAttempt.find_by_id(attempt_id)
        
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            }), 404
        
        # Verify attempt belongs to the user
        user_id = user.get('id')
        if attempt.get('userId') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to this attempt'
            }), 403
        
        return jsonify({
            'success': True,
            'attempt': QuizAttempt.to_response(attempt, include_results=True)
        }), 200
        
    except Exception as e:
        print(f'Error fetching attempt: {e}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching the attempt'
        }), 500


@quiz_bp.route('/attempt/<attempt_id>/explanation', methods=['POST'])
@authenticate_token
def submit_explanation(attempt_id):
    """
    Submit explanation for why a wrong answer was chosen
    
    POST /api/quiz/attempt/<attempt_id>/explanation
    Body: {
        "question_index": 0,
        "explanation": "I thought..."
    }
    """
    try:
        user = g.user
        data = request.get_json()
        
        if not data or 'question_index' not in data or 'explanation' not in data:
            return jsonify({
                'success': False,
                'message': 'question_index and explanation are required'
            }), 400
        
        question_index = data.get('question_index')
        explanation = data.get('explanation')
        
        # Verify attempt belongs to user
        attempt = QuizAttempt.find_by_id(attempt_id)
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            }), 404
        
        user_id = user.get('id')
        if attempt.get('userId') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403
        
        # Store explanation
        QuizAttempt.add_user_explanation(attempt_id, question_index, explanation)
        
        return jsonify({
            'success': True,
            'message': 'Explanation saved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error submitting explanation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to save explanation'
        }), 500


@quiz_bp.route('/attempt/<attempt_id>/confidence', methods=['POST'])
@authenticate_token
def submit_confidence(attempt_id):
    """
    Submit confidence score for an answer
    
    POST /api/quiz/attempt/<attempt_id>/confidence
    Body: {
        "question_index": 0,
        "confidence": 3
    }
    """
    try:
        user = g.user
        data = request.get_json()
        
        if not data or 'question_index' not in data or 'confidence' not in data:
            return jsonify({
                'success': False,
                'message': 'question_index and confidence are required'
            }), 400
        
        question_index = data.get('question_index')
        confidence = data.get('confidence', 3)
        
        # Verify attempt belongs to user
        attempt = QuizAttempt.find_by_id(attempt_id)
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            }), 404
        
        user_id = user.get('id')
        if attempt.get('userId') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403
        
        # Store confidence score
        QuizAttempt.add_confidence_score(attempt_id, question_index, confidence)
        
        return jsonify({
            'success': True,
            'message': 'Confidence score saved successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error submitting confidence: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to save confidence score'
        }), 500


@quiz_bp.route('/adaptive-difficulty', methods=['GET'])
@authenticate_token
def get_adaptive_difficulty():
    """
    Get recommended difficulty for next quiz based on RL
    
    GET /api/quiz/adaptive-difficulty?interest=AI/ML
    """
    try:
        from services.quiz_adaptor import QuizAdaptor
        from models.user_analytics import UserAnalytics
        
        user = g.user
        interest = request.args.get('interest', None)
        
        if not interest:
            return jsonify({
                'success': False,
                'message': 'interest parameter is required'
            }), 400
        
        user_id = user.get('id')
        
        # Get recommended difficulty
        recommended_difficulty = QuizAdaptor.get_recommended_difficulty(user_id, interest)
        
        # Get performance metrics
        metrics = QuizAdaptor.get_performance_metrics(user_id, interest)
        
        return jsonify({
            'success': True,
            'recommendedDifficulty': recommended_difficulty,
            'performanceMetrics': metrics,
            'insight': f"Based on your performance, we recommend {recommended_difficulty} level quizzes to optimize your learning."
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting adaptive difficulty: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get adaptive difficulty recommendation'
        }), 500


@quiz_bp.route('/attempt/<attempt_id>/analyze', methods=['POST'])
@authenticate_token
def analyze_quiz_attempt(attempt_id):
    """
    Analyze quiz attempt and provide learning insights
    
    POST /api/quiz/attempt/<attempt_id>/analyze
    Body: {
        "wrongAnswersAnalysis": [
            {
                "questionIndex": 0,
                "question": "...",
                "concept": "arrays",
                "userExplanation": "...",
                "correctAnswer": "C",
                "correctExplanation": "..."
            }
        ]
    }
    """
    try:
        from services.quiz_adaptor import QuizAdaptor
        from models.user_analytics import UserAnalytics
        import os
        
        user = g.user
        data = request.get_json()
        
        # Verify attempt belongs to user
        attempt = QuizAttempt.find_by_id(attempt_id)
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            }), 404
        
        user_id = user.get('id')
        if attempt.get('userId') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403
        
        # Analyze attempt
        analysis = QuizAdaptor.analyze_quiz_attempt(user_id, attempt)
        
        # Store wrong answers analysis if provided
        if data and 'wrongAnswersAnalysis' in data:
            QuizAttempt.analyze_wrong_answers(attempt_id, data.get('wrongAnswersAnalysis', []))
            
            # Track concept mastery
            analysis_data = data.get('wrongAnswersAnalysis', [])
            concepts = [
                {
                    'concept': a.get('concept'),
                    'correct': False,
                    'difficulty': attempt.get('level', 'Beginner')
                }
                for a in analysis_data if a.get('concept')
            ]
            
            if concepts:
                QuizAdaptor.track_concept_mastery(user_id, concepts)
            
            # Update user analytics
            UserAnalytics.add_quiz_performance(
                user_id,
                attempt.get('interest'),
                attempt.get('score'),
                attempt.get('level'),
                attempt.get('correctCount'),
                attempt.get('totalQuestions')
            )
            
            # Generate LLM explanation for wrong answers if available
            if os.getenv('GEMINI_API_KEY'):
                try:
                    from services.interest_analyzer import InterestAnalyzer
                    
                    for wrong_ans in analysis_data[:3]:  # Analyze top 3 wrong answers
                        if wrong_ans.get('correctExplanation'):
                            # Already provided, so we can enhance it if needed
                            pass
                
                except Exception as e:
                    logger.warning(f"Could not generate LLM explanations: {str(e)}")
        
        return jsonify({
            'success': True,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        logger.error(f"Error analyzing quiz attempt: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to analyze quiz attempt'
        }), 500
