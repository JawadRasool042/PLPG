"""
============================================
Chat Routes - Database Backed Messaging
============================================

ENDPOINTS:
GET  /chat/contacts               - list contacts with last message/unread count
GET  /chat/messages/<contact_id>  - fetch direct conversation
POST /chat/messages/<contact_id>  - send message to contact
"""

from datetime import datetime, timedelta

from bson import ObjectId
from flask import Blueprint, jsonify, request, g

from middleware.auth import authenticate_token
from models.chat_message import ChatMessage
from models.user import User


chat_bp = Blueprint('chat', __name__)


def _display_name(user_doc: dict) -> str:
    first = (user_doc.get('firstName') or '').strip()
    last = (user_doc.get('lastName') or '').strip()
    full = f"{first} {last}".strip()
    return full or user_doc.get('email', 'Unknown User')


def _avatar_from_name(name: str) -> str:
    parts = [part for part in name.split(' ') if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return 'US'


def _is_online(user_doc: dict) -> bool:
    """
    Lightweight online heuristic:
    treat a user as online if updated in last 10 minutes.
    """
    updated_at = user_doc.get('updatedAt')
    if not updated_at:
        return False
    return updated_at >= (datetime.utcnow() - timedelta(minutes=10))


@chat_bp.route('/contacts', methods=['GET'])
@authenticate_token
def get_contacts():
    from bson.errors import InvalidId
    
    current_user_id = g.user['id']
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    page = max(1, page)
    limit = min(max(1, limit), 100)  # Cap at 100 to prevent abuse
    skip = (page - 1) * limit

    users = User.find_many(
        filter_query={
            '_id': {'$ne': ObjectId(current_user_id)},
            'isActive': True,
        },
        skip=skip,
        limit=limit,
        sort_by='firstName',
        sort_order=1,
    )

    contacts = []
    for user in users:
        contact_id = str(user['_id'])
        name = _display_name(user)

        last_message_doc = ChatMessage.get_last_message(current_user_id, contact_id)
        unread_count = ChatMessage.count_unread(sender_id=contact_id, receiver_id=current_user_id)

        contacts.append({
            'id': contact_id,
            'name': name,
            'role': user.get('role', 'Student'),
            'avatar': user.get('avatar') or _avatar_from_name(name),
            'online_status': _is_online(user),
            'last_message': last_message_doc.get('text') if last_message_doc else '',
            'last_message_at': (last_message_doc.get('createdAt').isoformat() 
                               if (last_message_doc and last_message_doc.get('createdAt')) 
                               else None),
            'unread_count': unread_count,
        })

    contacts.sort(key=lambda c: c.get('last_message_at') or '', reverse=True)

    return jsonify({
        'success': True,
        'contacts': contacts,
        'page': page,
        'limit': limit,
    })


@chat_bp.route('/messages/<contact_id>', methods=['GET'])
@authenticate_token
def get_messages(contact_id: str):
    from bson.errors import InvalidId
    
    current_user_id = g.user['id']

    try:
        contact_id_obj = ObjectId(contact_id)
    except InvalidId:
        return jsonify({'success': False, 'message': 'Invalid contact ID format'}), 400

    contact = User.find_by_id(contact_id)
    if not contact or not contact.get('isActive', True):
        return jsonify({'success': False, 'message': 'Contact not found'}), 404

    limit_raw = request.args.get('limit', 100)
    try:
        limit = min(max(int(limit_raw), 1), 500)
    except (TypeError, ValueError):
        limit = 100

    messages = ChatMessage.get_conversation(current_user_id, contact_id, limit=limit)

    # Mark incoming messages as read once this conversation is opened.
    ChatMessage.mark_conversation_read(reader_id=current_user_id, contact_id=contact_id)

    return jsonify({
        'success': True,
        'messages': [ChatMessage.to_response(message) for message in messages],
    })


@chat_bp.route('/messages/<contact_id>', methods=['POST'])
@authenticate_token
def send_message(contact_id: str):
    from bson.errors import InvalidId
    
    current_user_id = g.user['id']

    try:
        contact_id_obj = ObjectId(contact_id)
    except InvalidId:
        return jsonify({'success': False, 'message': 'Invalid contact ID format'}), 400

    if current_user_id == contact_id:
        return jsonify({'success': False, 'message': 'Cannot message yourself'}), 400

    contact = User.find_by_id(contact_id)
    if not contact or not contact.get('isActive', True):
        return jsonify({'success': False, 'message': 'Contact not found'}), 404

    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify({'success': False, 'message': 'Message text is required'}), 400

    if len(text) > 2000:
        return jsonify({'success': False, 'message': 'Message text is too long'}), 400

    message = ChatMessage.create(sender_id=current_user_id, receiver_id=contact_id, text=text)

    return jsonify({
        'success': True,
        'message': ChatMessage.to_response(message),
    }), 201
