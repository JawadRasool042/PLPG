"""
============================================
Feedback Routes (Requirement #11)
============================================

User endpoints:
  POST   /api/feedback                  - Submit feedback (auth required)
  GET    /api/feedback/me               - List own feedback (auth required)

Admin endpoints (under /api/admin/feedback):
  GET    /api/admin/feedback            - List all feedback (paginated)
  GET    /api/admin/feedback/stats      - Aggregate stats
  GET    /api/admin/feedback/<id>       - Get single feedback
  PATCH  /api/admin/feedback/<id>       - Update status / admin note
  DELETE /api/admin/feedback/<id>       - Delete feedback
"""

from flask import Blueprint, g, jsonify, request

from middleware.admin_auth import authenticate_admin
from middleware.auth import authenticate_token
from models.feedback import Feedback

feedback_bp = Blueprint('feedback', __name__)
admin_feedback_bp = Blueprint('admin_feedback', __name__)


# ─────────────────────────────────────────────────────────────
# USER ENDPOINTS
# ─────────────────────────────────────────────────────────────

@feedback_bp.route('', methods=['POST'])
@authenticate_token
def submit_feedback():
    """User submits new feedback."""
    payload = request.get_json(silent=True) or {}

    message = (payload.get('message') or '').strip()
    if not message:
        return jsonify({
            'success': False,
            'message': 'Message is required',
        }), 400

    rating = payload.get('rating')
    try:
        rating_int = int(rating) if rating is not None else 0
    except (TypeError, ValueError):
        rating_int = 0

    if rating_int < 1 or rating_int > 5:
        return jsonify({
            'success': False,
            'message': 'Rating must be between 1 and 5',
        }), 400

    user = getattr(g, 'user', {}) or {}
    user_doc = getattr(g, 'user_doc', {}) or {}

    extra_meta = payload.get('metadata')
    if extra_meta is not None and not isinstance(extra_meta, dict):
        extra_meta = {}

    doc = Feedback.create({
        'userId': user.get('id'),
        'userEmail': user.get('email'),
        'userName': (
            f"{user_doc.get('firstName', '')} {user_doc.get('lastName', '')}".strip()
            or user.get('email')
        ),
        'category': payload.get('category'),
        'rating': rating_int,
        'subject': payload.get('subject'),
        'message': message,
        'ipAddress': request.headers.get('X-Forwarded-For', request.remote_addr),
        'userAgent': request.headers.get('User-Agent'),
        'page': payload.get('page'),
        'metadata': extra_meta,
    })

    return jsonify({
        'success': True,
        'message': 'Feedback submitted successfully. Thank you!',
        'data': Feedback.to_response(doc),
    }), 201


@feedback_bp.route('/me', methods=['GET'])
@authenticate_token
def list_my_feedback():
    """List the authenticated user's feedback history."""
    try:
        limit = max(1, min(50, int(request.args.get('limit', 20))))
    except (TypeError, ValueError):
        limit = 20

    user_id = (getattr(g, 'user', {}) or {}).get('id')
    docs = Feedback.find_many({'userId': str(user_id)}, limit=limit)

    return jsonify({
        'success': True,
        'data': [Feedback.to_response(d) for d in docs],
        'total': Feedback.count({'userId': str(user_id)}),
    })


# ─────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────

@admin_feedback_bp.route('', methods=['GET'])
@authenticate_admin
def admin_list_feedback():
    """List all feedback (paginated, filterable)."""
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = max(1, min(100, int(request.args.get('limit', 25))))
    except (TypeError, ValueError):
        limit = 25

    status = request.args.get('status')
    category = request.args.get('category')
    search = (request.args.get('search') or '').strip()

    query: dict = {}
    if status and status in Feedback.VALID_STATUSES:
        query['status'] = status
    if category and category in Feedback.VALID_CATEGORIES:
        query['category'] = category
    if search:
        query['$or'] = [
            {'subject': {'$regex': search, '$options': 'i'}},
            {'message': {'$regex': search, '$options': 'i'}},
            {'userEmail': {'$regex': search, '$options': 'i'}},
            {'userName': {'$regex': search, '$options': 'i'}},
        ]

    skip = (page - 1) * limit
    docs = Feedback.find_many(query, skip=skip, limit=limit)
    total = Feedback.count(query)

    return jsonify({
        'success': True,
        'data': [Feedback.to_response(d) for d in docs],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'totalPages': (total + limit - 1) // limit if limit else 1,
        },
    })


@admin_feedback_bp.route('/stats', methods=['GET'])
@authenticate_admin
def admin_feedback_stats():
    try:
        days = max(1, min(365, int(request.args.get('days', 30))))
    except (TypeError, ValueError):
        days = 30
    return jsonify({
        'success': True,
        'data': Feedback.stats(days=days),
    })


@admin_feedback_bp.route('/<feedback_id>', methods=['GET'])
@authenticate_admin
def admin_get_feedback(feedback_id: str):
    doc = Feedback.find_by_id(feedback_id)
    if not doc:
        return jsonify({'success': False, 'message': 'Feedback not found'}), 404
    return jsonify({'success': True, 'data': Feedback.to_response(doc)})


@admin_feedback_bp.route('/<feedback_id>', methods=['PATCH'])
@authenticate_admin
def admin_update_feedback(feedback_id: str):
    payload = request.get_json(silent=True) or {}
    status = payload.get('status')
    admin_note = payload.get('adminNote')

    if status and status not in Feedback.VALID_STATUSES:
        return jsonify({
            'success': False,
            'message': f"Status must be one of: {', '.join(Feedback.VALID_STATUSES)}",
        }), 400

    doc = Feedback.update_status(
        feedback_id,
        status=status or 'in_review',
        admin_note=admin_note,
    )
    if not doc:
        return jsonify({'success': False, 'message': 'Feedback not found'}), 404
    return jsonify({'success': True, 'data': Feedback.to_response(doc)})


@admin_feedback_bp.route('/<feedback_id>', methods=['DELETE'])
@authenticate_admin
def admin_delete_feedback(feedback_id: str):
    deleted = Feedback.delete(feedback_id)
    if not deleted:
        return jsonify({'success': False, 'message': 'Feedback not found'}), 404
    return jsonify({'success': True, 'message': 'Feedback deleted'})
