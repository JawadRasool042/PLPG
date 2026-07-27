"""
Community REST API routes.

Provides endpoints for:
- Listing / joining / leaving communities
- Fetching messages with pagination and search
- Uploading and serving file attachments
- Listing members (for @mention autocomplete)
"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, g, send_from_directory
from werkzeug.utils import secure_filename
from bson import ObjectId
from database import get_collection
from middleware.auth import authenticate_token

community_bp = Blueprint('community', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'zip', 'mp4', 'mp3'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def serialize(doc):
    """Serialize a MongoDB document for JSON response."""
    if doc is None:
        return None
    doc['_id'] = str(doc['_id'])
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def _safe_object_id(id_str):
    """Safely convert string to ObjectId, returns None on failure."""
    try:
        return ObjectId(id_str) if ObjectId.is_valid(id_str) else None
    except Exception:
        return None


# ============================================
# Community CRUD
# ============================================

@community_bp.route('/', methods=['GET'])
@authenticate_token
def get_communities():
    """List all available communities with member counts."""
    col = get_collection('communities')
    members_col = get_collection('community_members')

    communities = list(col.find({}))
    if not communities:
        return jsonify({'success': True, 'data': []})

    # Single aggregation to get all member counts at once (avoids N+1 queries)
    counts_cursor = members_col.aggregate([
        {'$group': {'_id': '$community_id', 'count': {'$sum': 1}}}
    ])
    count_map = {doc['_id']: doc['count'] for doc in counts_cursor}

    result = []
    for c in communities:
        doc = serialize(c)
        doc['memberCount'] = count_map.get(str(c['_id']), 0)
        result.append(doc)

    return jsonify({'success': True, 'data': result})


@community_bp.route('/my', methods=['GET'])
@authenticate_token
def get_my_communities():
    """List communities the current user has joined."""
    user_id = g.user['id']
    members_col = get_collection('community_members')
    comms_col = get_collection('communities')

    my_memberships = list(members_col.find({'user_id': user_id}))
    community_ids = []
    for m in my_memberships:
        oid = _safe_object_id(m['community_id'])
        if oid:
            community_ids.append(oid)

    communities = list(comms_col.find({'_id': {'$in': community_ids}}))
    return jsonify({'success': True, 'data': [serialize(c) for c in communities]})


@community_bp.route('/<community_id>/join', methods=['POST'])
@authenticate_token
def join_community(community_id):
    """Join a community."""
    user_id = g.user['id']
    comms_col = get_collection('communities')
    members_col = get_collection('community_members')

    # Verify community exists
    comm = comms_col.find_one({'_id': _safe_object_id(community_id)})
    if not comm:
        return jsonify({'success': False, 'message': 'Community not found'}), 404

    existing = members_col.find_one({'user_id': user_id, 'community_id': community_id})
    if not existing:
        members_col.insert_one({
            'user_id': user_id,
            'community_id': community_id,
            'joined_at': datetime.utcnow(),
            'last_read_at': datetime.utcnow()
        })
    return jsonify({'success': True, 'message': 'Joined successfully'})


@community_bp.route('/<community_id>/leave', methods=['POST'])
@authenticate_token
def leave_community(community_id):
    """Leave a community."""
    user_id = g.user['id']
    members_col = get_collection('community_members')
    members_col.delete_one({'user_id': user_id, 'community_id': community_id})
    return jsonify({'success': True, 'message': 'Left successfully'})


# ============================================
# Messages
# ============================================

@community_bp.route('/<community_id>/messages', methods=['GET'])
@authenticate_token
def get_messages(community_id):
    """
    Fetch messages for a community with pagination and optional search.
    
    Query params:
        search  — text filter (regex, case-insensitive)
        skip    — number of messages to skip (default 0)
        limit   — max messages to return (default 50, max 100)
    """
    user_id = g.user['id']
    search_query = request.args.get('search', '').strip()
    skip = max(0, int(request.args.get('skip', 0)))
    limit = min(100, max(1, int(request.args.get('limit', 50))))

    msgs_col = get_collection('community_messages')
    members_col = get_collection('community_members')

    query = {'community_id': community_id, 'deleted': {'$ne': True}}
    if search_query:
        query['text'] = {'$regex': search_query, '$options': 'i'}

    total = msgs_col.count_documents(query)
    messages = list(
        msgs_col.find(query)
        .sort('createdAt', -1)
        .skip(skip)
        .limit(limit)
    )
    messages.reverse()  # Oldest first for UI

    # Enrich messages with sender info
    users_col = get_collection('users')
    for m in messages:
        sender_oid = _safe_object_id(m.get('sender_id', ''))
        if sender_oid:
            sender = users_col.find_one({'_id': sender_oid})
            if sender:
                m['sender'] = {
                    '_id': str(sender['_id']),
                    'firstName': sender.get('firstName', ''),
                    'lastName': sender.get('lastName', ''),
                    'avatar': sender.get('avatar', '')
                }

    # Update read receipt
    members_col.update_one(
        {'user_id': user_id, 'community_id': community_id},
        {'$set': {'last_read_at': datetime.utcnow()}}
    )

    return jsonify({
        'success': True,
        'data': [serialize(m) for m in messages],
        'total': total,
        'skip': skip,
        'limit': limit,
        'hasMore': (skip + limit) < total
    })


# ============================================
# Members (for @mention autocomplete)
# ============================================

@community_bp.route('/<community_id>/members', methods=['GET'])
@authenticate_token
def get_members(community_id):
    """Get all members of a community for @mention and member list."""
    members_col = get_collection('community_members')
    users_col = get_collection('users')

    memberships = list(members_col.find({'community_id': community_id}))
    members = []
    for m in memberships:
        user_oid = _safe_object_id(m['user_id'])
        if not user_oid:
            continue
        user = users_col.find_one({'_id': user_oid})
        if user:
            members.append({
                '_id': str(user['_id']),
                'firstName': user.get('firstName', ''),
                'lastName': user.get('lastName', ''),
                'email': user.get('email', ''),
                'avatar': user.get('avatar', ''),
                'joinedAt': m.get('joined_at', '').isoformat() if isinstance(m.get('joined_at'), datetime) else ''
            })

    return jsonify({'success': True, 'data': members})


# ============================================
# File Upload
# ============================================

@community_bp.route('/upload', methods=['POST'])
@authenticate_token
def upload_file():
    """Upload a file to share in community chat."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    # Validate extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'message': f'File type .{ext} not allowed'}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    # Check file size after save
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        os.remove(file_path)
        return jsonify({'success': False, 'message': 'File too large (max 10MB)'}), 400

    file_url = f"/api/community/files/{unique_filename}"
    return jsonify({'success': True, 'fileUrl': file_url})


@community_bp.route('/files/<filename>', methods=['GET'])
def get_file(filename):
    """Serve uploaded files."""
    return send_from_directory(UPLOAD_FOLDER, filename)
