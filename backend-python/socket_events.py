"""
WebSocket event handlers for Community real-time chat.

Handles: join/leave rooms, send messages, typing indicators,
reactions, read receipts, online presence tracking.
"""

import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from database import get_collection
from bson import ObjectId
from datetime import datetime

from config import get_config
from utils.token_utils import verify_user_token

logger = logging.getLogger(__name__)

socketio = SocketIO()

# In-memory presence tracking (use Redis for multi-process production)
online_users = {}          # { community_id: { user_id: sid } }
user_communities = {}      # { sid: set(community_ids) }  — reverse index for disconnect cleanup


def get_user_from_token(token):
    """Verify JWT token and return user_id. Returns None on failure."""
    if not token:
        return None
    try:
        decoded = verify_user_token(token, is_refresh=False)
        if decoded:
            return decoded.get('id') or decoded.get('sub')
        return None
    except Exception as e:
        logger.error(f"Socket auth error: {e}")
        return None


def _get_user_name(user_id):
    """Fetch user display name from DB."""
    try:
        users_col = get_collection('users')
        sender = users_col.find_one({'_id': ObjectId(user_id)})
        if sender:
            return f"{sender.get('firstName', '')} {sender.get('lastName', '')}".strip() or 'Unknown'
    except Exception:
        pass
    return 'Unknown'


def _get_sender_info(user_id):
    """Fetch sender info dict for message enrichment."""
    try:
        users_col = get_collection('users')
        sender = users_col.find_one({'_id': ObjectId(user_id)})
        if sender:
            return {
                '_id': str(sender['_id']),
                'firstName': sender.get('firstName', ''),
                'lastName': sender.get('lastName', ''),
                'avatar': sender.get('avatar', '')
            }
    except Exception:
        pass
    return {'_id': user_id, 'firstName': 'Unknown', 'lastName': '', 'avatar': ''}


def _get_community_members(community_id):
    """Get list of members for a community (for @mention autocomplete)."""
    members_col = get_collection('community_members')
    users_col = get_collection('users')
    memberships = list(members_col.find({'community_id': community_id}))
    members = []
    for m in memberships:
        try:
            user = users_col.find_one({'_id': ObjectId(m['user_id'])})
            if user:
                members.append({
                    '_id': str(user['_id']),
                    'firstName': user.get('firstName', ''),
                    'lastName': user.get('lastName', ''),
                    'avatar': user.get('avatar', '')
                })
        except Exception:
            continue
    return members


def init_sockets(app):
    """Initialize SocketIO with the Flask app."""
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=True,
        engineio_logger=True
    )
    return socketio

# ============================================
# Connection Events
# ============================================

@socketio.on('connect')
def handle_connect():
    token = request.args.get('token')
    user_id = get_user_from_token(token)
    if not user_id:
        print("Socket connection rejected: No valid token")
        return False  # Reject connection
    user_communities[request.sid] = set()
    print(f"Socket connected: user={user_id}, sid={request.sid}")
    logger.info(f"Socket connected: user={user_id}, sid={request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    communities = user_communities.pop(sid, set())
    for comm_id in communities:
        if comm_id in online_users:
            disconnected_user = None
            for uid, user_sid in list(online_users[comm_id].items()):
                if user_sid == sid:
                    disconnected_user = uid
                    del online_users[comm_id][uid]
                    break
            if disconnected_user:
                emit('user_status', {
                    'user_id': disconnected_user,
                    'status': 'offline',
                    'online_count': len(online_users.get(comm_id, {}))
                }, room=comm_id)
    print(f"Socket disconnected: sid={sid}")
    logger.info(f"Socket disconnected: sid={sid}")


# ============================================
# Community Room Events
# ============================================

@socketio.on('join_community')
def handle_join(data):
    community_id = data.get('community_id')
    token = data.get('token')
    user_id = get_user_from_token(token)
    
    print(f"User {user_id} joining community {community_id}")

    if not community_id or not user_id:
        return

    # Verify membership
    members_col = get_collection('community_members')
    membership = members_col.find_one({'user_id': user_id, 'community_id': community_id})
    if not membership:
        print(f"Join rejected: {user_id} not a member of {community_id}")
        emit('error', {'message': 'Not a member of this community'})
        return

    join_room(community_id)

    # Track online presence
    if community_id not in online_users:
        online_users[community_id] = {}
    online_users[community_id][user_id] = request.sid
    user_communities.setdefault(request.sid, set()).add(community_id)

    # Update last_read_at
    members_col.update_one(
        {'user_id': user_id, 'community_id': community_id},
        {'$set': {'last_read_at': datetime.utcnow()}}
    )

    emit('user_status', {
        'user_id': user_id,
        'status': 'online',
        'online_count': len(online_users[community_id])
    }, room=community_id)


@socketio.on('leave_community')
def handle_leave(data):
    community_id = data.get('community_id')
    token = data.get('token')
    user_id = get_user_from_token(token)

    if not community_id or not user_id:
        return

    leave_room(community_id)
    if community_id in online_users and user_id in online_users[community_id]:
        del online_users[community_id][user_id]
    if request.sid in user_communities:
        user_communities[request.sid].discard(community_id)

    emit('user_status', {
        'user_id': user_id,
        'status': 'offline',
        'online_count': len(online_users.get(community_id, {}))
    }, room=community_id)


# ============================================
# Messaging Events
# ============================================

@socketio.on('send_message')
def handle_message(data):
    community_id = data.get('community_id')
    text = data.get('text', '').strip()
    token = data.get('token')
    file_url = data.get('fileUrl')
    parent_id = data.get('parentMessageId')
    mentions = data.get('mentions', [])

    user_id = get_user_from_token(token)
    print(f"Handling send_message: comm_id={community_id}, user={user_id}, text={text}")
    
    if not community_id or not user_id or (not text and not file_url):
        print(f"Message rejected: Missing required fields (community_id={community_id}, user_id={user_id}, text={text})")
        return

    msg = {
        'community_id': community_id,
        'sender_id': user_id,
        'text': text,
        'fileUrl': file_url,
        'parentMessageId': parent_id,
        'mentions': mentions,
        'reactions': {},
        'readBy': [user_id],
        'createdAt': datetime.utcnow(),
        'deleted': False
    }

    msgs_col = get_collection('community_messages')
    result = msgs_col.insert_one(msg)
    msg['_id'] = str(result.inserted_id)
    msg['createdAt'] = msg['createdAt'].isoformat()
    msg['sender'] = _get_sender_info(user_id)

    print(f"Emitting new_message to room {community_id}")
    emit('new_message', msg, room=community_id)


@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read — updates last_read_at for read receipts."""
    community_id = data.get('community_id')
    token = data.get('token')
    user_id = get_user_from_token(token)

    if not community_id or not user_id:
        return

    members_col = get_collection('community_members')
    members_col.update_one(
        {'user_id': user_id, 'community_id': community_id},
        {'$set': {'last_read_at': datetime.utcnow()}}
    )

    emit('read_receipt', {
        'user_id': user_id,
        'community_id': community_id,
        'read_at': datetime.utcnow().isoformat()
    }, room=community_id)


# ============================================
# Typing Indicator
# ============================================

@socketio.on('typing')
def handle_typing(data):
    community_id = data.get('community_id')
    is_typing = data.get('is_typing', False)
    token = data.get('token')
    user_id = get_user_from_token(token)

    if community_id and user_id:
        name = _get_user_name(user_id)
        emit('user_typing', {
            'user_id': user_id,
            'name': name,
            'is_typing': is_typing
        }, room=community_id, include_self=False)


# ============================================
# Reactions
# ============================================

@socketio.on('message_react')
def handle_react(data):
    community_id = data.get('community_id')
    message_id = data.get('message_id')
    emoji = data.get('emoji')
    token = data.get('token')
    user_id = get_user_from_token(token)

    if not all([community_id, message_id, emoji, user_id]):
        return

    try:
        msgs_col = get_collection('community_messages')
        msg = msgs_col.find_one({'_id': ObjectId(message_id)})
        if not msg:
            return

        reactions = msg.get('reactions', {})
        if emoji not in reactions:
            reactions[emoji] = []

        if user_id in reactions[emoji]:
            reactions[emoji].remove(user_id)
            if not reactions[emoji]:
                del reactions[emoji]
        else:
            reactions[emoji].append(user_id)

        msgs_col.update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {'reactions': reactions}}
        )
        emit('message_reaction_update', {
            'message_id': message_id,
            'reactions': reactions
        }, room=community_id)
    except Exception as e:
        logger.error(f"Reaction error: {e}")


# ============================================
# Community Members (for @mention)
# ============================================

@socketio.on('get_members')
def handle_get_members(data):
    community_id = data.get('community_id')
    token = data.get('token')
    user_id = get_user_from_token(token)

    if not community_id or not user_id:
        return

    members = _get_community_members(community_id)
    emit('members_list', {'community_id': community_id, 'members': members})
