# routes/llm_routes.py
# Flask endpoints for LLM-powered question generation & interest extraction
# Drop into backend-python/routes/

from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import logging
from datetime import datetime
from middleware.auth import authenticate_token
from services.llm_question_service import (
    generate_and_verify_questions,
    generate_interest_weights,
    get_flagged_questions,
    compute_question_quality
)
from services.llm_question_service import generate_micro_lesson

logger = logging.getLogger(__name__)

bp = Blueprint('llm', __name__, url_prefix='/api/llm')

# ============================================================================
# QUESTION GENERATION ENDPOINTS
# ============================================================================

@bp.post('/questions/generate')
@cross_origin()
@authenticate_token
def api_generate_questions():
    """
    Generate questions for a given topic and level.
    
    Request JSON:
    {
      "topic": "Python Async/Await",
      "level": "Intermediate",  // or "Beginner", "Advanced"
      "concept_tag": "async_programming",
      "count": 5
    }
    
    Response:
    {
      "success": true,
      "generated": 5,
      "verified": 4,
      "questions": [...],
      "timestamp": "2026-04-29T14:30:00Z"
    }
    """
    try:
        data = request.json or {}
        current_user = request.user
        
        # Validate input
        topic = data.get('topic', '').strip()
        level = data.get('level', 'Beginner').lower()
        concept_tag = data.get('concept_tag', topic).strip()
        count = min(int(data.get('count', 5)), 10)  # Max 10 per request
        
        if not topic:
            return jsonify({
                'success': False,
                'error': 'topic is required'
            }), 400
        
        if level not in ['beginner', 'intermediate', 'advanced']:
            return jsonify({
                'success': False,
                'error': 'level must be beginner, intermediate, or advanced'
            }), 400
        
        logger.info(f"Generating {count} questions for {topic} ({level}) - user {current_user.id}")
        
        # Call generation service
        questions, gen_count, ver_count = generate_and_verify_questions(
            topic=topic,
            level=level,
            concept_tag=concept_tag,
            count=count,
            user_id=str(current_user.id)
        )
        
        return jsonify({
            'success': True,
            'generated': gen_count,
            'verified': ver_count,
            'final_count': len(questions),
            'questions': questions,
            'timestamp': datetime.utcnow().isoformat()
        }), 201
        
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Error generating questions: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.get('/questions/personalized')
@cross_origin()
@authenticate_token
def api_get_personalized_questions():
    """
    Get questions for a user based on topic/level.
    Tries cache first; if not enough, generates new via LLM.
    
    Query params:
      topic: "Python Async/Await"
      level: "beginner" | "intermediate" | "advanced"
      count: 5 (default)
    
    Response: { questions: [...], source: "cache"|"generated", ... }
    """
    try:
        from models import get_db
        db = get_db()
        
        current_user = request.user
        topic = request.args.get('topic', '').strip()
        level = request.args.get('level', 'beginner').lower()
        count = min(int(request.args.get('count', 5)), 10)
        
        if not topic:
            return jsonify({'success': False, 'error': 'topic required'}), 400
        
        logger.info(f"Fetching {count} questions: {topic} ({level}) - user {current_user.id}")
        
        # Try to get from cache
        cutoff = db['questions'].find_one({'created_at': {'$exists': True}})
        cached = list(db['questions'].find({
            'topic': topic,
            'level': level,
            'status': 'approved',
            'flagged': False
        }).limit(count))
        
        if len(cached) >= count:
            logger.info(f"Serving {len(cached)} cached questions")
            return jsonify({
                'success': True,
                'questions': cached,
                'source': 'cache',
                'count': len(cached)
            }), 200
        
        # Not enough cached; generate new
        logger.info(f"Insufficient cache ({len(cached)}); generating {count - len(cached)} new")
        
        questions, gen_count, ver_count = generate_and_verify_questions(
            topic=topic,
            level=level,
            concept_tag=topic.lower().replace(' ', '_'),
            count=count - len(cached),
            user_id=str(current_user.id)
        )
        
        all_questions = cached + questions
        
        return jsonify({
            'success': True,
            'questions': all_questions,
            'source': 'mixed',  # cache + generated
            'cached': len(cached),
            'generated': len(questions),
            'count': len(all_questions)
        }), 200
        
    except Exception as e:
        logger.exception(f"Error fetching questions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# INTEREST EXTRACTION ENDPOINTS
# ============================================================================

@bp.post('/interest/extract')
@cross_origin()
@authenticate_token
def api_extract_interest():
    """
    Extract and normalize user interests from free-text input.
    
    Request JSON:
    {
      "text": "I love building web apps with React...",
      "merge_with_sliders": { "AI_ML": 0.7, ... }  // optional
    }
    
    Response:
    {
      "success": true,
      "interests": { "Web_Dev": 0.9, "Data_Science": 0.5, ... },
      "top_topics": ["Web_Dev", "Data_Science"],
      "confidence": 0.87,
      "explanation": "User interested in web development with data science"
    }
    """
    try:
        data = request.json or {}
        current_user = request.user
        free_text = data.get('text', '').strip()
        slider_weights = data.get('merge_with_sliders', {})
        
        if not free_text or len(free_text) < 10:
            return jsonify({
                'success': False,
                'error': 'text must be at least 10 characters'
            }), 400
        
        logger.info(f"Extracting interests from free text - user {current_user.id}")
        
        # Call LLM extraction
        llm_result = generate_interest_weights(free_text)
        
        if not llm_result or not llm_result.get('interests'):
            logger.warning("LLM extraction failed or returned invalid format")
            return jsonify({
                'success': False,
                'error': 'Failed to extract interests'
            }), 500
        
        # Merge with slider weights if provided
        merged_interests = {**llm_result.get('interests', {}), **slider_weights}
        
        # Normalize to 0..1
        max_weight = max(merged_interests.values()) if merged_interests else 1
        if max_weight > 1:
            merged_interests = {k: v / max_weight for k, v in merged_interests.items()}
        
        # Update user's interests in DB
        from models.user import User
        user_doc = User.find_by_id(current_user.id)
        if user_doc:
            user_doc['interests'] = merged_interests
            user_doc['interests_updated_at'] = datetime.utcnow()
            user_doc['interests_confidence'] = llm_result.get('confidence', 0.5)
            user_doc.save()
            logger.info(f"Saved interests for user {current_user.id}: {merged_interests}")
        
        return jsonify({
            'success': True,
            'interests': merged_interests,
            'top_topics': llm_result.get('top_topics', []),
            'confidence': llm_result.get('confidence', 0.5),
            'explanation': llm_result.get('explanation', 'Interest extraction complete')
        }), 200
        
    except Exception as e:
        logger.exception(f"Error extracting interests: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN / QA ENDPOINTS
# ============================================================================

@bp.get('/questions/flagged')
@cross_origin()
@authenticate_token
def api_get_flagged_questions():
    """
    Admin endpoint: Get questions flagged for human review.
    """
    try:
        # TODO: Add admin check
        # if not current_user.is_admin:
        #     return jsonify({'error': 'Admin only'}), 403
        
        flagged = get_flagged_questions()
        
        return jsonify({
            'success': True,
            'count': len(flagged),
            'questions': flagged
        }), 200
        
    except Exception as e:
        logger.exception(f"Error fetching flagged: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.post('/questions/<question_id>/approve')
@cross_origin()
@authenticate_token
def api_approve_question(question_id):
    """
    Admin endpoint: Approve a flagged question.
    """
    try:
        from bson import ObjectId
        from models import get_db
        db = get_db()
        
        # TODO: Add admin check
        current_user = request.user
        
        result = db['questions'].update_one(
            {'_id': ObjectId(question_id)},
            {
                '$set': {
                    'flagged': False,
                    'reviewed_by': str(current_user.id),
                    'reviewed_at': datetime.utcnow(),
                    'reviewer_action': 'approved'
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Question not found'}), 404
        
        logger.info(f"Question {question_id} approved by {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Question approved'
        }), 200
        
    except Exception as e:
        logger.exception(f"Error approving question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.post('/questions/<question_id>/reject')
@cross_origin()
@authenticate_token
def api_reject_question(question_id):
    """
    Admin endpoint: Reject a question with reason.
    
    Request JSON:
    {
      "reason": "Ambiguous wording in option C",
      "action": "delete"|"regenerate"
    }
    """
    try:
        from bson import ObjectId
        from models import get_db
        db = get_db()
        
        data = request.json or {}
        reason = data.get('reason', 'No reason provided')
        action = data.get('action', 'delete')  # delete or regenerate
        
        current_user = request.user
        
        result = db['questions'].update_one(
            {'_id': ObjectId(question_id)},
            {
                '$set': {
                    'flagged': False,
                    'status': 'rejected',
                    'reviewed_by': str(current_user.id),
                    'reviewed_at': datetime.utcnow(),
                    'reviewer_action': 'rejected',
                    'rejection_reason': reason
                }
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'success': False, 'error': 'Question not found'}), 404
        
        logger.info(f"Question {question_id} rejected by {current_user.id}: {reason}")
        
        return jsonify({
            'success': True,
            'message': f'Question rejected. Action: {action}',
            'action': action
        }), 200
        
    except Exception as e:
        logger.exception(f"Error rejecting question: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# STATS / MONITORING ENDPOINTS
# ============================================================================

@bp.get('/stats/quality')
@cross_origin()
@authenticate_token
def api_quality_stats():
    """
    Get overall quality stats for LLM-generated questions.
    """
    try:
        from models import get_db
        db = get_db()
        
        total = db['questions'].count_documents({'source': 'llm'})
        approved = db['questions'].count_documents({'source': 'llm', 'status': 'approved'})
        flagged = db['questions'].count_documents({'source': 'llm', 'flagged': True})
        
        avg_quality = db['questions'].aggregate([
            {'$match': {'source': 'llm', 'quality_score': {'$exists': True}}},
            {'$group': {'_id': None, 'avg': {'$avg': '$quality_score'}}}
        ])
        avg_quality_val = list(avg_quality)[0]['avg'] if list(avg_quality) else None
        
        return jsonify({
            'success': True,
            'total_generated': total,
            'approved': approved,
            'flagged': flagged,
            'approval_rate': approved / total if total > 0 else 0,
            'avg_quality_score': avg_quality_val
        }), 200
        
    except Exception as e:
        logger.exception(f"Error fetching quality stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.post('/microlesson/generate')
@cross_origin()
@authenticate_token
def api_generate_microlesson():
    """
    Generate a compact micro-lesson for a concept.
    Request JSON:
    { "concept": "async_programming", "mastery": 28, "user_id": "..." }

    Response:
    { success: true, lesson: { lesson_text, examples, practice_questions } }
    """
    try:
        data = request.json or {}
        concept = data.get('concept', '').strip()
        mastery = int(data.get('mastery', 20))

        if not concept:
            return jsonify({'success': False, 'error': 'concept is required'}), 400

        result = generate_micro_lesson(concept, mastery=mastery, user_id=str(request.user.id))

        if result.get('error'):
            return jsonify({'success': False, 'error': result.get('error'), 'raw': result.get('raw_response')}), 500

        return jsonify({'success': True, 'lesson': result.get('lesson')}), 200

    except Exception as e:
        logger.exception(f"Error generating micro-lesson: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
