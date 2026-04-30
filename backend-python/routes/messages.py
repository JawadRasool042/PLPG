"""
Messaging Routes - Student/Teacher Communication
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from database import get_collection
from middleware.auth import authenticate_token
from models.user import User

messages_bp = Blueprint('messages', __name__)


def serialize(doc):
    """Convert MongoDB doc to JSON-safe dict"""
    if doc is None:
        return None
    doc['_id'] = str(doc['_id'])
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ── GET /api/messages/contacts ──────────────────────────────
@messages_bp.route('/contacts', methods=['GET'])
@authenticate_token
def get_contacts():
    """Return all users the current user can message (everyone except self)"""
    me = g.user['id']
    users_col = get_collection('users')

    users = list(users_col.find(
        {'_id': {'$ne': ObjectId(me)}, 'isActive': True},
        {'hashedPassword': 0, 'emailVerificationTokenHash': 0, 'passwordResetTokenHash': 0}
    ))

    msgs_col = get_collection('messages')
    contacts = []
    for u in users:
        uid = str(u['_id'])
        # Last message between me and this user
        last_msg = msgs_col.find_one(
            {'$or': [
                {'senderId': me, 'receiverId': uid},
                {'senderId': uid, 'receiverId': me}
            ]},
            sort=[('createdAt', -1)]
        )
        # Unread count
        unread = msgs_col.count_documents({
            'senderId': uid,
            'receiverId': me,
            'read': False
        })
        contacts.append({
            '_id': uid,
            'firstName': u.get('firstName', ''),
            'lastName': u.get('lastName', ''),
            'email': u.get('email', ''),
            'role': u.get('role', 'Student'),
            'avatar': u.get('avatar'),
            'lastMessage': last_msg.get('text', '') if last_msg else '',
            'lastMessageAt': last_msg['createdAt'].isoformat() if last_msg and last_msg.get('createdAt') else None,
            'unread': unread
        })

    # Sort by lastMessageAt desc
    contacts.sort(key=lambda x: x['lastMessageAt'] or '', reverse=True)
    return jsonify({'success': True, 'data': contacts})


# ── GET /api/messages/conversation/<user_id> ────────────────
@messages_bp.route('/conversation/<other_id>', methods=['GET'])
@authenticate_token
def get_conversation(other_id):
    """Get all messages between current user and another user"""
    me = g.user['id']
    msgs_col = get_collection('messages')

    messages = list(msgs_col.find(
        {'$or': [
            {'senderId': me, 'receiverId': other_id},
            {'senderId': other_id, 'receiverId': me}
        ]},
        sort=[('createdAt', 1)]
    ))

    # Mark received messages as read
    msgs_col.update_many(
        {'senderId': other_id, 'receiverId': me, 'read': False},
        {'$set': {'read': True}}
    )

    return jsonify({
        'success': True,
        'data': [serialize(m) for m in messages]
    })


# ── POST /api/messages/send ──────────────────────────────────
@messages_bp.route('/send', methods=['POST'])
@authenticate_token
def send_message():
    """Send a message to another user"""
    me = g.user['id']
    data = request.get_json() or {}
    receiver_id = data.get('receiverId', '').strip()
    text = data.get('text', '').strip()

    if not receiver_id or not text:
        return jsonify({'success': False, 'message': 'receiverId and text are required'}), 400

    if len(text) > 2000:
        return jsonify({'success': False, 'message': 'Message too long (max 2000 chars)'}), 400

    # Verify receiver exists
    receiver = User.find_by_id(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Receiver not found'}), 404

    msgs_col = get_collection('messages')
    msg = {
        'senderId': me,
        'receiverId': receiver_id,
        'text': text,
        'read': False,
        'createdAt': datetime.utcnow()
    }
    result = msgs_col.insert_one(msg)
    msg['_id'] = str(result.inserted_id)
    msg['createdAt'] = msg['createdAt'].isoformat()

    return jsonify({'success': True, 'data': msg}), 201


# ── DELETE /api/messages/<message_id> ───────────────────────
@messages_bp.route('/<message_id>', methods=['DELETE'])
@authenticate_token
def delete_message(message_id):
    """Delete own message"""
    me = g.user['id']
    msgs_col = get_collection('messages')

    msg = msgs_col.find_one({'_id': ObjectId(message_id)})
    if not msg:
        return jsonify({'success': False, 'message': 'Message not found'}), 404
    if str(msg['senderId']) != me:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    msgs_col.delete_one({'_id': ObjectId(message_id)})
    return jsonify({'success': True, 'message': 'Message deleted'})


# ── GET /api/messages/unread-count ──────────────────────────
@messages_bp.route('/unread-count', methods=['GET'])
@authenticate_token
def unread_count():
    me = g.user['id']
    msgs_col = get_collection('messages')
    count = msgs_col.count_documents({'receiverId': me, 'read': False})
    return jsonify({'success': True, 'count': count})
