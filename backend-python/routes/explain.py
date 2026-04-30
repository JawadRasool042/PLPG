from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from middleware.auth import authenticate_token
import logging
from services.llm_question_service import generate_explanation

logger = logging.getLogger(__name__)

explain_bp = Blueprint('explain', __name__)


@explain_bp.post('/generate')
@cross_origin()
@authenticate_token
def api_generate_explanation():
    """
    Generate an answer explanation and per-option explanations for a provided question_doc.

    Request JSON:
    {
      "question_doc": { ... }
    }

    Response:
    {
      "success": true,
      "explanations": { "answer_explanation": "...", "option_explanations": [...] }
    }
    """
    try:
        data = request.json or {}
        question_doc = data.get('question_doc')
        if not question_doc:
            return jsonify({'success': False, 'error': 'question_doc is required'}), 400

        current_user = request.user
        result = generate_explanation(question_doc, user_id=str(current_user.id) if current_user else None)

        if result.get('error'):
            # propagate error details
            return jsonify({'success': False, 'error': result.get('error'), 'raw': result.get('raw_response', None)}), 500

        return jsonify({'success': True, 'explanations': result.get('explanations')}), 200

    except Exception as e:
        logger.exception(f"Error in explain endpoint: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
