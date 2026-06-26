"""
============================================
Quiz Routes - API Endpoints
============================================

RESTful API endpoints for quiz operations with OpenAI integration
"""

import os
import logging
from datetime import datetime
from typing import Any
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt
from models.user_performance import UserPerformance
from middleware.auth import authenticate_token, get_current_user_id
from database import get_collection
from utils.api_response import error_response

logger = logging.getLogger(__name__)


quiz_bp = Blueprint('quiz', __name__)


def _normalize_answer_letter(value: str, *, strict: bool = False) -> str:
    """Normalize a free-form answer to one of A/B/C/D.

    When ``strict`` is True (used during grading) we return an empty string for
    inputs that cannot be confidently mapped, so the caller can mark the
    question wrong instead of silently coercing to 'A'.
    """
    raw = str(value or '').strip().upper()
    if raw.startswith('OPTION '):
        parts = raw.split()
        if len(parts) >= 2 and parts[1][:1] in {'A', 'B', 'C', 'D'}:
            return parts[1][:1]
    if raw[:1] in {'A', 'B', 'C', 'D'}:
        return raw[:1]
    if strict:
        return ''
    logger.warning(
        "Unrecognized MCQ answer letter %r; falling back to 'A' for non-grading use",
        value,
    )
    return 'A'


# ---------------------------------------------------------------------------
# Lightweight quiz adaptor (replaces the deleted ``services.quiz_adaptor``)
# Provides recommended-difficulty + performance-metrics + attempt-analysis
# using only the data we already have in Mongo (UserPerformance + history).
# ---------------------------------------------------------------------------

_DIFF_LADDER = ['Beginner', 'Intermediate', 'Advanced']
LOW_SCORE_THRESHOLD = 45.0
HIGH_SCORE_THRESHOLD = 82.0


def _normalize_difficulty(value: str) -> str:
    if not value:
        return 'Beginner'
    cleaned = str(value).strip().lower()
    for level in _DIFF_LADDER:
        if cleaned.startswith(level.lower()):
            return level
    return 'Beginner'


def _apply_performance_level_adjustment(user_id: str, interest: str, requested_level: str) -> tuple[str, dict]:
    """
    Adjust quiz level from recent same-topic performance:
    - lower one level if performance is low
    - raise one level if performance is strong
    """
    level = _normalize_difficulty(requested_level)
    level_idx = _DIFF_LADDER.index(level)

    history = QuizAttempt.find_by_user(user_id, limit=12) or []
    in_topic = [a for a in history if (a.get('interest') or '').lower() == (interest or '').lower()]
    recent = in_topic[:3]
    if not recent:
        return level, {'triggered': False, 'sampleSize': 0}

    avg = sum(float(a.get('score') or 0) for a in recent) / max(1, len(recent))
    if avg < LOW_SCORE_THRESHOLD and level_idx > 0:
        softened_level = _DIFF_LADDER[level_idx - 1]
        return softened_level, {
            'triggered': True,
            'direction': 'easier',
            'sampleSize': len(recent),
            'recentAverage': round(avg, 1),
            'reason': (
                f"Recent average in {interest} is {avg:.0f}% (<{LOW_SCORE_THRESHOLD:.0f}%). "
                f"Starting at {softened_level} to rebuild fundamentals."
            ),
            'from': level,
            'to': softened_level,
        }

    if avg >= HIGH_SCORE_THRESHOLD and level_idx < len(_DIFF_LADDER) - 1:
        harder_level = _DIFF_LADDER[level_idx + 1]
        return harder_level, {
            'triggered': True,
            'direction': 'harder',
            'sampleSize': len(recent),
            'recentAverage': round(avg, 1),
            'reason': (
                f"Recent average in {interest} is {avg:.0f}% (≥{HIGH_SCORE_THRESHOLD:.0f}%). "
                f"Starting at {harder_level} for a stronger challenge."
            ),
            'from': level,
            'to': harder_level,
        }

    if level_idx == 0 and avg < LOW_SCORE_THRESHOLD:
        direction = 'easier'
    elif level_idx == len(_DIFF_LADDER) - 1 and avg >= HIGH_SCORE_THRESHOLD:
        direction = 'harder'
    else:
        direction = 'stable'

    return level, {
        'triggered': False,
        'direction': direction,
        'sampleSize': len(recent),
        'recentAverage': round(avg, 1),
    }


def _recommended_difficulty(user_id: str, interest: str) -> dict:
    """Recommend a difficulty band based on the user's recent attempts."""
    history = QuizAttempt.find_by_user(user_id, limit=20) or []
    in_topic = [a for a in history if (a.get('interest') or '').lower() == (interest or '').lower()]
    if not in_topic:
        return {
            'recommended': 'Beginner',
            'reason': 'No prior attempts in this topic — start at Beginner.',
            'sampleSize': 0,
        }

    recent = in_topic[:5]
    avg = sum(float(a.get('score') or 0) for a in recent) / max(1, len(recent))
    last_level = _normalize_difficulty(recent[0].get('level', 'Beginner'))
    idx = _DIFF_LADDER.index(last_level)

    if avg >= 80 and idx < len(_DIFF_LADDER) - 1:
        recommended = _DIFF_LADDER[idx + 1]
        reason = f'Average {avg:.0f}% on {last_level} — promoting to {recommended}.'
    elif avg < 40 and idx > 0:
        recommended = _DIFF_LADDER[idx - 1]
        reason = f'Average {avg:.0f}% on {last_level} — easing back to {recommended}.'
    else:
        recommended = last_level
        reason = f'Average {avg:.0f}% on {last_level} — staying at this level.'

    return {
        'recommended': recommended,
        'reason': reason,
        'sampleSize': len(recent),
        'recentAverage': round(avg, 1),
    }


def _performance_metrics(user_id: str, interest: str) -> dict:
    """Per-topic performance summary derived from UserPerformance + history."""
    perf = UserPerformance.find_by_user_id(user_id) or {}
    by_interest = (perf.get('byInterest') or {}).get(interest, {})
    history = QuizAttempt.find_by_user(user_id, limit=10) or []
    in_topic = [a for a in history if (a.get('interest') or '').lower() == (interest or '').lower()]
    return {
        'totalQuizzes': by_interest.get('totalQuizzes', 0),
        'averageScore': by_interest.get('averageScore', 0),
        'bestScore': by_interest.get('bestScore', 0),
        'recentScores': [float(a.get('score') or 0) for a in in_topic[:5]],
    }


def _build_performance_analysis(by_interest: dict[str, dict], recent_scores: list[dict], *, user_id: str) -> dict:
    """
    Build user-facing coaching insights from recent quiz performance.
    Returns strengths, weaknesses, and actionable recommendations.
    """
    normalized = []
    for interest, stats in (by_interest or {}).items():
        total_quizzes = int(stats.get('totalQuizzes') or 0)
        avg_score = float(stats.get('averageScore') or 0)
        if total_quizzes <= 0:
            continue
        normalized.append({
            'interest': interest,
            'score': round(avg_score, 2),
            'quizzes': total_quizzes,
        })

    strengths = sorted(
        [row for row in normalized if row['score'] >= 75 and row['quizzes'] >= 1],
        key=lambda x: (x['score'], x['quizzes']),
        reverse=True,
    )[:3]

    weaknesses = sorted(
        [row for row in normalized if row['score'] < 60 and row['quizzes'] >= 1],
        key=lambda x: (x['score'], -x['quizzes']),
    )[:3]

    recommendations: list[str] = []
    if strengths:
        best = strengths[0]
        recommendations.append(
            f"Keep momentum in {best['interest']} (avg {best['score']:.0f}%). Try one harder quiz this week."
        )
    if weaknesses:
        weak_topics = ', '.join(w['interest'] for w in weaknesses[:2])
        recommendations.append(
            f"Focus revision on {weak_topics}. Re-attempt these topics at an easier level, then step up."
        )

    if recent_scores:
        window = [float(item.get('score') or 0) for item in recent_scores[:6]]
        if len(window) >= 3:
            recent_avg = sum(window[:3]) / 3
            older = window[3:6]
            older_avg = (sum(older) / len(older)) if older else recent_avg
            if recent_avg >= older_avg + 5:
                recommendations.append("Your latest scores are trending upward. Continue with progressive difficulty.")
            elif recent_avg <= older_avg - 5:
                recommendations.append("Recent scores dipped. Review recent mistakes before attempting harder quizzes.")

    # Pull weak-concept signals if available and suggest concrete improvement topics.
    try:
        weak_concepts_coll = get_collection('weak_concepts')
        weak_rows = list(
            weak_concepts_coll.find(
                {'userId': user_id, 'isMastered': {'$ne': True}},
                {'concept': 1}
            ).limit(5)
        )
        improvement_topics = [str(r.get('concept') or '').strip() for r in weak_rows if str(r.get('concept') or '').strip()]
    except Exception:  # noqa: BLE001
        improvement_topics = []

    coding_topic_map = {
        'array': 'Array traversal and indexing drills',
        'string': 'String parsing and transformation exercises',
        'loop': 'Loop control and iteration practice',
        'condition': 'Conditional branching and decision logic',
        'function': 'Function design and parameter handling',
        'recursion': 'Recursion fundamentals and trace practice',
        'object': 'Object modeling and property access',
        'class': 'Class design and OOP foundations',
        'api': 'API request/response handling basics',
        'sql': 'SQL querying fundamentals',
        'database': 'Database CRUD and schema basics',
        'algorithm': 'Core algorithm problem solving',
        'debug': 'Debugging workflows and bug isolation',
    }
    coding_suggestions: list[str] = []
    for topic in improvement_topics:
        norm = topic.lower()
        for token, suggestion in coding_topic_map.items():
            if token in norm and suggestion not in coding_suggestions:
                coding_suggestions.append(suggestion)
    if not coding_suggestions and weaknesses:
        for weak in weaknesses[:2]:
            coding_suggestions.append(
                f"{weak['interest']}: solve 3 short coding exercises focused on missed concepts."
            )
    coding_suggestions = coding_suggestions[:5]

    if improvement_topics:
        recommendations.append(
            f"Improvement topics to practice next: {', '.join(improvement_topics[:3])}."
        )
    elif weaknesses:
        recommendations.append(
            f"Improvement topics: fundamentals of {', '.join(w['interest'] for w in weaknesses[:2])}."
        )

    # Keep response concise for UI cards.
    recommendations = recommendations[:5]

    return {
        'strengths': strengths,
        'weaknesses': weaknesses,
        'recommendations': recommendations,
        'codingSuggestions': coding_suggestions,
        'improvementTopics': improvement_topics[:5],
    }


def _summarize_attempt(attempt: dict) -> dict:
    """Quick textual analysis for a single attempt (replaces QuizAdaptor.analyze_quiz_attempt)."""
    score = float(attempt.get('score') or 0)
    correct = int(attempt.get('correctCount') or 0)
    total = int(attempt.get('totalQuestions') or 0)
    if score >= 80:
        verdict = 'strong'
        message = 'Excellent performance — consider increasing difficulty or moving to the next topic.'
    elif score >= 60:
        verdict = 'on-track'
        message = 'Solid performance with room to grow. Review the explanations on missed questions.'
    elif score >= 40:
        verdict = 'developing'
        message = 'Keep practising at this level — focus on the concepts you missed.'
    else:
        verdict = 'needs-foundations'
        message = 'Drop back to fundamentals before attempting another quiz at this level.'

    return {
        'verdict': verdict,
        'message': message,
        'accuracy': round((correct / total) * 100, 1) if total else 0,
        'score': score,
        'correct': correct,
        'total': total,
        'level': attempt.get('level'),
        'interest': attempt.get('interest'),
    }


def _normalize_options_list(options: Any) -> list:
    if isinstance(options, dict):
        return [str(options.get(letter, '')).strip() for letter in ['A', 'B', 'C', 'D']]
    if isinstance(options, list):
        return [str(opt).strip() for opt in options][:4]
    return []


def _safe_quiz_fallback_response(interest: str, level: str, count: int, user_id: str):
    """Generate a resilient fallback quiz payload that never raises to clients."""
    from services.quiz_generator.openai_fallback_generator import generate_quiz_with_fallback

    questions, ok = generate_quiz_with_fallback(
        topic=interest,
        level=(level or "Beginner").lower(),
        count=max(1, int(count or 10)),
    )
    if not ok or not questions:
        return None

    formatted_questions = _format_questions(questions)
    if not formatted_questions:
        return None

    quiz_doc = {
        'interest': interest,
        'level': level,
        'questions': formatted_questions,
        'totalQuestions': len(formatted_questions),
        'createdAt': datetime.utcnow(),
        'source': 'fallback',
        'userId': user_id,
        'isAdaptive': False,
        'targetsWeakAreas': False
    }

    quizzes_coll = get_collection('quizzes')
    result = quizzes_coll.insert_one(quiz_doc)
    quiz_doc['_id'] = result.inserted_id
    return quiz_doc


def _record_rl_outcome(user_id: str, quiz: dict, attempt: dict) -> dict | None:
    """
    Bridge between the legacy quiz pipeline and the new RL service.

    Records a terminal transition for the just-finished attempt and
    returns a fresh decision for the *next* quiz so the frontend can
    show the adaptive recommendation immediately. Any failure is
    caught by the caller; this helper only encapsulates the mapping.
    """
    from rl.service import get_service
    from rl.schemas import Action

    score = float(attempt.get('score', 0.0)) / 100.0
    correct = int(attempt.get('correctCount', 0))
    total = max(1, int(attempt.get('totalQuestions', 1)))
    accuracy = correct / total

    # Build a single state snapshot summarising the attempt.
    interest = quiz.get('interest') or quiz.get('domain') or 'Coding'
    level = quiz.get('level') or quiz.get('difficulty') or 'Beginner'
    time_spent = float(attempt.get('timeSpent', 0)) or 0.0
    time_per_q = float(attempt.get('timePerQuestion') or (time_spent / total if time_spent else 0.0))

    # Approximate state signals from the attempt.
    state_payload = {
        'domain': interest,
        'profile': 'Explorer',
        'difficulty': level,
        'accuracy': accuracy,
        'response_time': time_per_q,
        'streak': correct,                       # best-effort proxy
        'wrong_answers': max(0, total - correct),
        'hints_used': 0,
        'engagement_score': accuracy,
        'dropout_risk': 1.0 - accuracy if accuracy < 0.4 else 0.0,
        'topic_performance': accuracy,
    }

    # Low score should explicitly push the model toward easier/revision actions.
    score_percent = float(attempt.get('score', 0.0))
    if score_percent < 40:
        action = Action.DECREASE_DIFFICULTY.value
    elif score_percent < 55:
        action = Action.RECOMMEND_REVISION.value
    elif score_percent >= 80:
        action = Action.INCREASE_DIFFICULTY.value
    else:
        action = Action.KEEP_DIFFICULTY.value

    feedback = {
        'is_correct': accuracy >= 0.5,
        'response_time_sec': time_per_q,
        'expected_time_sec': 25.0,
        'streak_length': correct,
        'quiz_completed': accuracy >= 0.4,
        'quiz_dropped': accuracy < 0.4,
        'score_delta': float(attempt.get('score', 0.0)) - 60.0,  # vs reasonable baseline
        'repeated_mistake': score_percent < LOW_SCORE_THRESHOLD,
        'notes': (
            f"Low-score reinforcement path ({score_percent:.0f}%)"
            if score_percent < LOW_SCORE_THRESHOLD
            else "Normal outcome update"
        ),
    }

    service = get_service()
    reward_update = service.update_reward(
        user_id=user_id,
        action=action,
        feedback_payload=feedback,
        previous_state_payload=state_payload,
        next_state_payload=state_payload,
        terminal=True,
    )

    decision = service.next_action(user_id, state_payload)
    payload = decision.to_dict()
    payload['training'] = {'updated': True, 'reward': reward_update.get('reward')}

    # Optional light replay on low outcomes so the policy absorbs poor
    # performance patterns faster without blocking quiz submission.
    if score_percent < LOW_SCORE_THRESHOLD:
        try:
            report = service.train(mode='replay', epochs=1, batch_size=64, user_id=user_id)
            payload['training']['replay'] = {
                'ran': True,
                'epochs': getattr(report, 'epochs', 1),
                'transitions': getattr(report, 'transitions_seen', None),
            }
        except Exception as train_exc:  # noqa: BLE001
            logger.warning("RL low-score replay training failed for user %s: %s", user_id, train_exc)
            payload['training']['replay'] = {'ran': False}
    else:
        payload['training']['replay'] = {'ran': False}

    return payload


@quiz_bp.route('/generate', methods=['POST'])
@authenticate_token
def generate_quiz():
    """
    Generate a new quiz with OpenAI integration.
    
    Integrates with interest checker module for personalized quiz generation.
    
    POST /api/quiz/generate
    Body: {
        "interest": "AI/ML",
        "level": "Beginner",
        "count": 10,
        "use_adaptive": false,
        "target_weak_areas": false
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
        user_id = get_current_user_id()
        if not user_id:
            return error_response('User ID not found in token', code='UNAUTHORIZED', status_code=401)
        
        # Get interest from request or user profile
        interest = data.get('interest')
        if not interest:
            user_assessment = user.get('interestAssessment', {}) if user else {}
            interest = user_assessment.get('primaryInterest')

        if not interest or interest == 'PENDING_USER_RESOLUTION':
            return jsonify({
                'success': False,
                'message': 'Interest is required. Please complete the interest assessment first.'
            }), 400
        
        # Validate interest and level
        if not Quiz.validate_interest(interest):
            return jsonify({
                'success': False,
                'message': 'Invalid interest'
            }), 400

        requested_level = data.get('level', 'Beginner')
        if not Quiz.validate_level(requested_level):
            return jsonify({
                'success': False,
                'message': f'Invalid level. Available: {", ".join(Quiz.LEVELS)}'
            }), 400

        num_questions = int(data.get('count', 10))
        use_adaptive = data.get('use_adaptive', False)
        target_weak_areas = data.get('target_weak_areas', False)
        recommended = None
        if use_adaptive:
            recommended = _recommended_difficulty(user_id, interest)
            base_level = recommended.get('recommended') or requested_level
        else:
            base_level = requested_level
        level, performance_adjustment = _apply_performance_level_adjustment(user_id, interest, base_level)
        
        logger.info(f"Generating quiz for user {user_id}: interest={interest}, level={level}, adaptive={use_adaptive}")
        
        # Generate quiz using OpenAI
        from services.quiz_generator import generate_quiz, APIError
        
        try:
            # Map level to difficulty (1-5 scale)
            level_mapping = {
                'Beginner': 2,
                'Intermediate': 3,
                'Advanced': 4
            }
            difficulty_level = level_mapping.get(level, 2)
            
            # Generate standard quiz using OpenAI
            result = generate_quiz(
                topic=interest,
                difficulty_level=difficulty_level,
                question_count=num_questions,
                weak_areas=None,
                user_id=user_id
            )
            
            if not result.get('success'):
                raise APIError(result.get('message', 'Failed to generate quiz'))
            
            questions = result.get('questions', [])
            if not questions:
                raise APIError('Failed to generate quiz - no questions returned')
            
            logger.info(f"Generated {len(questions)} questions from OpenAI")
            
            # Format questions for quiz
            formatted_questions = []
            for q in questions:
                if isinstance(q, dict):
                    options = _normalize_options_list(q.get('options', []))
                    correct_index = q.get('correct_index')
                    answer = _normalize_answer_letter(q.get('correct_answer', ''))
                    if answer == 'A' and isinstance(correct_index, int) and 0 <= correct_index < len(options):
                        answer_letters = ['A', 'B', 'C', 'D']
                        answer = answer_letters[correct_index] if correct_index < 4 else 'A'
                    
                    formatted_questions.append({
                        'q': q.get('question', ''),
                        'options': options,
                        'answer': answer,
                        'explanation': q.get('explanation', ''),
                        'concept_tag': q.get('concept_tag', ''),
                        'difficulty': q.get('difficulty', 1)
                    })
            
            # Create quiz document
            quiz_doc = {
                'interest': interest,
                'level': level,
                'questions': formatted_questions,
                'totalQuestions': len(formatted_questions),
                'createdAt': datetime.utcnow(),
                'source': 'openai',
                'userId': user_id,
                'isAdaptive': use_adaptive,
                'targetsWeakAreas': target_weak_areas
            }
            
            # Save to database
            from database import get_collection
            quizzes_coll = get_collection('quizzes')
            result = quizzes_coll.insert_one(quiz_doc)
            quiz_doc['_id'] = result.inserted_id
            
            logger.info(f"Quiz created: {result.inserted_id}")
            
            return jsonify({
                'success': True,
                'message': 'AI quiz generated successfully with OpenAI',
                'quiz': Quiz.to_response(quiz_doc, include_answers=False),
                'metadata': {
                    'source': 'openai',
                    'adaptive': use_adaptive,
                    'weak_areas_targeted': target_weak_areas,
                    'questions_generated': len(formatted_questions),
                    'requested_level': requested_level,
                    'effective_level': level,
                    'adaptive_recommendation': recommended if use_adaptive else None,
                    'performance_adjustment': performance_adjustment,
                }
            }), 201
        
        except APIError as e:
            error_msg = str(e)
            logger.error(f"API error: {error_msg}")

            fallback_quiz = _safe_quiz_fallback_response(interest, level, num_questions, user_id)
            if fallback_quiz:
                logger.info("Serving fallback quiz after generator error for user %s", user_id)
                return jsonify({
                    'success': True,
                    'message': 'Quiz generated with fallback engine',
                    'quiz': Quiz.to_response(fallback_quiz, include_answers=False),
                    'metadata': {
                        'source': 'fallback',
                        'adaptive': use_adaptive,
                        'weak_areas_targeted': target_weak_areas,
                        'questions_generated': len(fallback_quiz.get('questions', [])),
                        'fallback_reason': error_msg[:120]
                    }
                }), 201

            # Final safe response: do not expose internals, and do not crash clients.
            return error_response(
                'Quiz generation is temporarily unavailable. Please try again shortly.',
                code='QUIZ_GENERATION_UNAVAILABLE',
                status_code=503,
            )
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.exception(f'Error generating quiz: {e}')

        fallback_quiz = _safe_quiz_fallback_response(interest if 'interest' in locals() else 'General Knowledge', level if 'level' in locals() else 'Beginner', num_questions if 'num_questions' in locals() else 10, user_id if 'user_id' in locals() else 'anonymous')
        if fallback_quiz:
            return jsonify({
                'success': True,
                'message': 'Quiz generated with fallback engine',
                'quiz': Quiz.to_response(fallback_quiz, include_answers=False),
                'metadata': {
                    'source': 'fallback',
                    'questions_generated': len(fallback_quiz.get('questions', []))
                }
            }), 201

        return jsonify({
            'success': False,
            'message': 'Quiz service is temporarily unavailable. Please retry.'
        }), 503


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

        remediation_gate = None
        if quiz.get('isRetakeFrozen'):
            user_id = get_current_user_id()
            if user_id:
                from services.remediation_service import can_retake_quiz

                allowed, lock, message = can_retake_quiz(str(user_id), str(quiz_id))
                remediation_gate = {
                    'canRetake': allowed,
                    'message': message,
                    'activeLock': lock,
                }
        
        response_quiz = Quiz.to_response(quiz, include_answers=False)
        if remediation_gate is not None:
            response_quiz['remediationGate'] = remediation_gate

        return jsonify({
            'success': True,
            'quiz': response_quiz,
        }), 200
        
    except Exception as e:
        logger.exception('Error fetching quiz: %s', e)
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching the quiz'
        }), 500


@quiz_bp.route('/submit', methods=['POST'])
@authenticate_token
def submit_quiz_unified():
    """
    Unified quiz submit endpoint.

    POST /api/quiz/submit
    Body: { "quiz_id": "...", "answers": { "0": "B", ... } }
    """
    data = request.get_json() or {}
    quiz_id = data.get('quiz_id') or data.get('quizId')
    if not quiz_id:
        return jsonify({'success': False, 'message': 'quiz_id is required'}), 400
    if 'answers' not in data:
        return jsonify({'success': False, 'message': 'answers are required'}), 400
    return submit_quiz(str(quiz_id))


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

        user_id = get_current_user_id(str(user.get('_id')) if user else None)
        if not user_id:
            return error_response('User ID not found in token', code='UNAUTHORIZED', status_code=401)

        if quiz.get('isRetakeFrozen'):
            from services.remediation_service import can_retake_quiz

            allowed, lock, message = can_retake_quiz(str(user_id), str(quiz_id))
            if not allowed:
                return jsonify({
                    'success': False,
                    'message': message or 'Complete the remediation lesson before retaking this quiz.',
                    'code': 'REMEDIATION_STUDY_REQUIRED',
                    'activeLock': lock,
                }), 403
        
        # Create attempt and calculate score
        # Use g.user['id'] which comes from JWT token
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

        # Adaptive RL update: record terminal transition + fetch next-best action.
        # Failures here must never break the submit flow.
        adaptive_recommendation = None
        try:
            adaptive_recommendation = _record_rl_outcome(user_id, quiz, attempt)
        except Exception as rl_exc:  # noqa: BLE001
            logger.warning("RL post-submit hook failed for user %s: %s", user_id, rl_exc)

        # ── Full dynamic result pipeline ────────────────────────────────────
        # Builds: skillLevel, nextDifficulty, weakConcepts, courses,
        #         learningPath, resources, careerPaths, skillGapAnalysis
        pipeline_result: dict = {}
        try:
            from services.quiz_result_pipeline import build_quiz_result
            pipeline_result = build_quiz_result(user_id, quiz, attempt)
        except Exception as pipe_exc:  # noqa: BLE001
            logger.warning("Quiz result pipeline failed for user %s: %s", user_id, pipe_exc)

        response_payload = {
            'success': True,
            'message': 'Quiz submitted successfully',
            'attempt': QuizAttempt.to_response(attempt, include_results=True),
            # ── Core enrichment fields ──────────────────────────────────────
            'skillLevel':       pipeline_result.get('skillLevel'),
            'nextDifficulty':   pipeline_result.get('nextDifficulty'),
            'weakConcepts':     pipeline_result.get('weakConcepts', []),
            'coaching':         pipeline_result.get('coaching', {}),
            # ── Personalized learning path ──────────────────────────────────
            'learningPath':     pipeline_result.get('learningPath', {}),
            'courses':          pipeline_result.get('courses', []),
            'resources':        pipeline_result.get('resources', []),
            'careerPaths':      pipeline_result.get('careerPaths', []),
            'skillGapAnalysis': pipeline_result.get('skillGapAnalysis', {}),
        }

        if adaptive_recommendation is not None:
            response_payload['adaptive_recommendation'] = adaptive_recommendation

        try:
            from services.remediation_service import process_attempt_after_scoring
            response_payload['remediation'] = process_attempt_after_scoring(
                user_id, str(attempt['_id'])
            )
        except Exception as rem_exc:  # noqa: BLE001
            logger.warning("Remediation hook failed for user %s: %s", user_id, rem_exc)

        return jsonify(response_payload), 200
        
    except Exception as e:
        logger.exception('Error submitting quiz: %s', e)
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting the quiz'
        }), 500


@quiz_bp.route('/<quiz_id>/result', methods=['GET'])
@authenticate_token
def get_quiz_result(quiz_id):
    """
    Fetch the enriched result for a completed quiz attempt.

    GET /api/quiz/<quiz_id>/result

    Returns the latest attempt for this quiz by the authenticated user,
    enriched with skillLevel, nextDifficulty, weakConcepts, courses,
    learningPath, resources, careerPaths, and skillGapAnalysis.
    """
    try:
        user_id = get_current_user_id(
            str(g.user_doc.get('_id')) if g.user_doc else None
        )
        if not user_id:
            return error_response('Unauthorized', code='UNAUTHORIZED', status_code=401)

        quiz = Quiz.find_by_id(quiz_id)
        if not quiz:
            return jsonify({'success': False, 'message': 'Quiz not found'}), 404

        # Find the latest attempt for this quiz + user
        attempts_coll = get_collection('quiz_attempts')
        attempt = attempts_coll.find_one(
            {'quizId': quiz_id, 'userId': user_id},
            sort=[('completedAt', -1)],
        )
        if not attempt:
            return jsonify({'success': False, 'message': 'No attempt found for this quiz'}), 404

        # Build the enriched pipeline result
        from services.quiz_result_pipeline import build_quiz_result
        pipeline_result = build_quiz_result(user_id, quiz, attempt)

        return jsonify({
            'success': True,
            'attempt':          QuizAttempt.to_response(attempt, include_results=True),
            'skillLevel':       pipeline_result.get('skillLevel'),
            'nextDifficulty':   pipeline_result.get('nextDifficulty'),
            'weakConcepts':     pipeline_result.get('weakConcepts', []),
            'coaching':         pipeline_result.get('coaching', {}),
            'learningPath':     pipeline_result.get('learningPath', {}),
            'courses':          pipeline_result.get('courses', []),
            'resources':        pipeline_result.get('resources', []),
            'careerPaths':      pipeline_result.get('careerPaths', []),
            'skillGapAnalysis': pipeline_result.get('skillGapAnalysis', {}),
        }), 200

    except Exception as e:
        logger.exception('Error fetching quiz result: %s', e)
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


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
        logger.exception('Error fetching available quizzes: %s', e)
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
        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
        
        if not user_id:
            return error_response(
                'Your session token is invalid or missing user identity. Please log in again.',
                code='INVALID_TOKEN_CONTEXT',
                status_code=401,
            )
        
        attempts = QuizAttempt.find_by_user(user_id, limit=limit)
        
        # Handle empty attempts gracefully
        formatted_attempts = []
        for attempt in attempts:
            try:
                formatted = QuizAttempt.to_response(attempt, include_results=False)
                if formatted:
                    formatted_attempts.append(formatted)
            except Exception as e:
                logger.warning('Error formatting attempt: %s', e)
                continue
        
        return jsonify({
            'success': True,
            'attempts': formatted_attempts
        }), 200
        
    except Exception as e:
        logger.exception('Error fetching quiz history: %s', e)
        return jsonify({
            'success': False,
            'message': 'Failed to fetch quiz history',
            'attempts': []
        }), 500


@quiz_bp.route('/history/graph', methods=['GET'])
@authenticate_token
def get_quiz_history_graph():
    """
    Get all stored quiz attempts for graphing (DB real-time source).

    GET /api/quiz/history/graph?limit=0
    - limit=0 (default) => return all stored attempts
    - limit>0 => return latest N attempts
    """
    try:
        user = g.user
        limit = request.args.get('limit', 0, type=int)

        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
        if not user_id:
            return error_response(
                'Your session token is invalid or missing user identity. Please log in again.',
                code='INVALID_TOKEN_CONTEXT',
                status_code=401,
            )

        coll = get_collection('quiz_attempts')
        cursor = coll.find(
            {
                'userId': user_id,
                '$or': [
                    {'status': {'$in': ['completed', 'finished']}},
                    {'completedAt': {'$exists': True, '$ne': None}},
                ],
            }
        ).sort('completedAt', 1)

        if limit and limit > 0:
            cursor = cursor.limit(limit)

        attempts = []
        for doc in cursor:
            try:
                attempts.append({
                    'id': str(doc.get('_id')),
                    'interest': str(doc.get('interest') or 'General'),
                    'level': str(doc.get('level') or ''),
                    'score': float(doc.get('score') or 0),
                    'correctCount': int(doc.get('correctCount') or 0),
                    'totalQuestions': int(doc.get('totalQuestions') or 0),
                    'quizType': doc.get('quizType'),
                    'completedAt': QuizAttempt.completion_timestamp_iso(doc),
                })
            except Exception:
                continue

        return jsonify({
            'success': True,
            'attempts': attempts,
        }), 200

    except Exception as e:
        logger.exception('Error fetching quiz graph history: %s', e)
        return jsonify({
            'success': False,
            'message': 'Failed to fetch quiz graph history',
            'attempts': [],
        }), 500


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
        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
        
        if not user_id:
            return error_response(
                'Your session token is invalid or missing user identity. Please log in again.',
                code='INVALID_TOKEN_CONTEXT',
                status_code=401,
            )
        
        # Real-time performance from quiz_attempts collection (single source of truth),
        # instead of relying on user_performance snapshots that can become stale.
        attempts_coll = get_collection('quiz_attempts')
        attempts = list(
            attempts_coll.find(
                {
                    'userId': user_id,
                    '$or': [
                        {'status': {'$in': ['completed', 'finished']}},
                        {'completedAt': {'$exists': True, '$ne': None}},
                    ],
                }
            ).sort('completedAt', -1)
        )

        def _to_num(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        if attempts:
            overall_total_quizzes = len(attempts)
            overall_total_score = sum(_to_num(a.get('score')) for a in attempts)
            overall_best_score = max(_to_num(a.get('score')) for a in attempts)
            overall_total_correct = int(sum(_to_num(a.get('correctCount')) for a in attempts))
            overall_total_questions = int(sum(_to_num(a.get('totalQuestions')) for a in attempts))

            by_interest: dict[str, dict[str, Any]] = {}
            for attempt in attempts:
                topic = str(attempt.get('interest') or 'General').strip() or 'General'
                entry = by_interest.setdefault(
                    topic,
                    {
                        'totalQuizzes': 0,
                        'averageScore': 0.0,
                        'bestScore': 0.0,
                        'lastAttempted': None,
                        '_scoreSum': 0.0,
                    },
                )
                score_val = _to_num(attempt.get('score'))
                entry['totalQuizzes'] += 1
                entry['_scoreSum'] += score_val
                entry['bestScore'] = max(float(entry['bestScore']), score_val)
                if not entry['lastAttempted']:
                    entry['lastAttempted'] = QuizAttempt.completion_timestamp_iso(attempt)

            for topic, entry in by_interest.items():
                quizzes = max(1, int(entry['totalQuizzes']))
                entry['averageScore'] = round(float(entry['_scoreSum']) / quizzes, 2)
                del entry['_scoreSum']

            recent_scores = []
            for attempt in attempts[:10]:
                try:
                    recent_scores.append(
                        {
                            'interest': str(attempt.get('interest') or 'General'),
                            'score': round(_to_num(attempt.get('score')), 2),
                            'date': QuizAttempt.completion_timestamp_iso(attempt),
                        }
                    )
                except Exception:
                    continue

            analysis = _build_performance_analysis(
                by_interest=by_interest,
                recent_scores=recent_scores,
                user_id=user_id,
            )

            performance = {
                'overallStats': {
                    'totalQuizzes': overall_total_quizzes,
                    'averageScore': round(overall_total_score / overall_total_quizzes, 2),
                    'bestScore': round(overall_best_score, 2),
                    'totalCorrect': overall_total_correct,
                    'totalQuestions': overall_total_questions,
                },
                'byInterest': by_interest,
                'recentScores': recent_scores,
                'analysis': analysis,
            }
        else:
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

        # Keep interest-filter support for existing clients.
        if interest:
            stats = performance.get('byInterest', {}).get(
                interest,
                {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0,
                    'lastAttempted': None,
                },
            )
            performance = {'interest': interest, 'stats': stats}
        
        return jsonify({
            'success': True,
            'performance': performance
        }), 200
        
    except Exception as e:
        logger.exception('Error fetching performance: %s', e)
        return jsonify({
            'success': False,
            'message': 'Failed to fetch performance data',
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
                    'recommendations': [],
                    'codingSuggestions': [],
                    'improvementTopics': [],
                },
                'updatedAt': None
            }
        }), 500


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
        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
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
        logger.exception('Error fetching attempt: %s', e)
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
        
        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
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
        
        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
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
        user = g.user
        interest = request.args.get('interest', None)

        if not interest:
            return jsonify({
                'success': False,
                'message': 'interest parameter is required'
            }), 400

        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)

        recommendation = _recommended_difficulty(user_id, interest)
        metrics = _performance_metrics(user_id, interest)

        return jsonify({
            'success': True,
            'recommendedDifficulty': recommendation['recommended'],
            'recommendation': recommendation,
            'performanceMetrics': metrics,
            'insight': recommendation['reason'],
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
        from models.user_analytics import UserAnalytics
        from models.weak_concept import WeakConcept

        user = g.user
        data = request.get_json(silent=True) or {}

        attempt = QuizAttempt.find_by_id(attempt_id)
        if not attempt:
            return jsonify({
                'success': False,
                'message': 'Attempt not found'
            }), 404

        user_id = get_current_user_id(user.get('id') if isinstance(user, dict) else None)
        if attempt.get('userId') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        analysis = _summarize_attempt(attempt)

        if 'wrongAnswersAnalysis' in data:
            analysis_data = data.get('wrongAnswersAnalysis', []) or []
            QuizAttempt.analyze_wrong_answers(attempt_id, analysis_data)

            for entry in analysis_data:
                concept = (entry.get('concept') or '').strip()
                if not concept:
                    continue
                try:
                    WeakConcept.record_failure(
                        user_id=user_id,
                        concept=concept,
                        topic=attempt.get('interest', ''),
                        difficulty=attempt.get('level'),
                        question=entry.get('question', ''),
                    )
                except Exception as inner_exc:  # noqa: BLE001
                    logger.warning("Failed to record weak concept: %s", inner_exc)

            try:
                UserAnalytics.add_quiz_performance(
                    user_id,
                    attempt.get('interest'),
                    attempt.get('score'),
                    attempt.get('level'),
                    attempt.get('correctCount'),
                    attempt.get('totalQuestions'),
                )
            except Exception as inner_exc:  # noqa: BLE001
                logger.warning("Failed to update user analytics: %s", inner_exc)

        return jsonify({
            'success': True,
            'analysis': analysis,
        }), 200
        
    except Exception as e:
        logger.error(f"Error analyzing quiz attempt: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to analyze quiz attempt'
        }), 500


# ============================================================================
# HELPER FUNCTIONS FOR AI INTEGRATION
# ============================================================================

def _build_user_profile(user: dict) -> dict:
    """
    Build user profile from user document for AI context.
    
    Args:
        user: User document from database
        
    Returns:
        User profile dict with learning context
    """
    if not user:
        return {}
    
    profile = {
        'user_id': str(user.get('_id', '')),
        'learning_level': user.get('learningLevel', 'Beginner'),
        'learning_goals': user.get('learningGoals', []),
        'learning_pace': user.get('learningPace', 'Self-paced'),
        'content_format': user.get('contentFormat', 'Mixed'),
        'focus_domains': user.get('focusDomains', []),
        'weekly_availability_hours': user.get('weeklyAvailabilityHours', 5)
    }
    
    # Add interest assessment data
    interest_assessment = user.get('interestAssessment', {})
    if interest_assessment:
        profile['primary_interest'] = interest_assessment.get('primaryInterest')
        profile['confidence'] = interest_assessment.get('confidence', 0)
        profile['all_interests'] = interest_assessment.get('allInterests', [])
    
    # Add analytics data
    analytics = user.get('analytics', {})
    if analytics:
        profile['strong_areas'] = analytics.get('strongAreas', [])
        profile['weak_areas'] = analytics.get('weakAreas', [])
        profile['total_quizzes_attempted'] = analytics.get('totalQuizzesAttempted', 0)
        profile['average_quiz_score'] = analytics.get('averageQuizScore', 0)
        profile['learning_velocity'] = analytics.get('learningVelocity', 0)
    
    return profile


def _get_weak_areas(user: dict) -> list:
    """
    Extract weak areas from user analytics.
    
    Args:
        user: User document
        
    Returns:
        List of weak area domains
    """
    if not user:
        return []
    
    analytics = user.get('analytics', {})
    weak_areas = analytics.get('weakAreas', [])
    
    # Extract domain names from weak areas
    weak_area_domains = [area.get('domain', '') for area in weak_areas if area.get('domain')]
    
    return weak_area_domains[:3]  # Return top 3 weak areas


def _get_user_performance(user_id: str) -> dict:
    """
    Get user's performance history for adaptive quiz generation.
    
    Args:
        user_id: User ID
        
    Returns:
        Performance data dict
    """
    try:
        attempts_coll = get_collection('quiz_attempts')
        
        # Get recent attempts
        recent_attempts = list(attempts_coll.find(
            {'userId': user_id}
        ).sort('completedAt', -1).limit(20))
        
        if not recent_attempts:
            return {
                'current_level': 'Beginner',
                'total_attempts': 0,
                'average_score': 0,
                'best_score': 0
            }
        
        # Calculate statistics
        scores = [a.get('score', 0) for a in recent_attempts]
        average_score = sum(scores) / len(scores) if scores else 0
        best_score = max(scores) if scores else 0
        
        # Determine current level based on performance
        if average_score >= 80:
            current_level = 'Advanced'
        elif average_score >= 60:
            current_level = 'Intermediate'
        else:
            current_level = 'Beginner'
        
        return {
            'current_level': current_level,
            'total_attempts': len(recent_attempts),
            'average_score': round(average_score, 2),
            'best_score': best_score,
            'recent_scores': scores[:5],
            'last_attempt': recent_attempts[0].get('completedAt') if recent_attempts else None
        }
        
    except Exception as e:
        logger.error(f"Error getting user performance: {str(e)}")
        return {
            'current_level': 'Beginner',
            'total_attempts': 0,
            'average_score': 0,
            'best_score': 0
        }


def _format_questions(questions: list) -> list:
    """
    Format AI-generated questions for quiz storage.
    
    Handles both old format (with correct_index) and new format (with correct_answer letter).
    Includes reasoning field for educational explanations.
    
    Args:
        questions: List of AI-generated questions
        
    Returns:
        Formatted questions list
    """
    formatted = []
    
    for q in questions:
        # Handle both old and new formats
        if 'correct_answer' in q:
            # New format: correct_answer is a letter (A, B, C, D)
            answer = q.get('correct_answer', 'A')
            options_dict = q.get('options', {})
            options_list = [options_dict.get(letter, '') for letter in ['A', 'B', 'C', 'D']]
        else:
            # Old format: correct_index is a number
            correct_index = q.get('correct_index', 0)
            answer_map = ['A', 'B', 'C', 'D']
            answer = answer_map[correct_index] if 0 <= correct_index < 4 else 'A'
            options_list = q.get('options', [])
        
        formatted_question = {
            'q': q.get('question', ''),
            'options': options_list,
            'answer': answer,
            'explanation': q.get('explanation', ''),
            'reasoning': q.get('reasoning', ''),  # NEW: Detailed reasoning field
            'sub_topic': q.get('sub_topic', ''),  # NEW: Sub-topic for weak area tracking
            'concept_tag': q.get('concept_tag', ''),
            'difficulty': q.get('difficulty', 'intermediate'),
            'learning_objective': q.get('learning_objective', ''),
            'estimated_time': q.get('estimated_time', 45),
            'targets_weak_area': q.get('targets_weak_area', False),
            'source': 'openai',
            'confidence': q.get('confidence', 0.8),
            'verification': q.get('verification', {})
        }
        
        formatted.append(formatted_question)
    
    return formatted
