"""
Community Routes
================
Interest-based and user-created communities where students can chat.

Collections used:
  communities          – community documents
  community_messages   – messages posted inside a community
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from database import get_collection
from middleware.auth import authenticate_token

community_bp = Blueprint('community', __name__)

# ── helpers ────────────────────────────────────────────────────────────────

INTEREST_DOMAINS = [
    "Coding", "Web Development", "Game Development", "Cybersecurity",
    "Data Science", "Mobile Development", "Cloud Computing",
    "AI & Machine Learning", "Physical Games / Sports",
]

def _serialize(doc):
    if doc is None:
        return None
    out = dict(doc)
    out['_id'] = str(out['_id'])
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


def _ensure_interest_communities():
    """Auto-create one community per interest domain if not already present."""
    col = get_collection('communities')
    for domain in INTEREST_DOMAINS:
        col.update_one(
            {'slug': _slugify(domain), 'type': 'interest'},
            {'$setOnInsert': {
                'name': domain,
                'slug': _slugify(domain),
                'description': f'Official community for {domain} learners',
                'type': 'interest',
                'interest': domain,
                'creatorId': None,
                'members': [],
                'memberCount': 0,
                'createdAt': datetime.utcnow(),
            }},
            upsert=True,
        )


def _slugify(text: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


# ── GET /api/community/  ────────────────────────────────────────────────────
@community_bp.route('/', methods=['GET'])
@authenticate_token
def list_communities():
    """Return all communities (interest-based + user-created)."""
    _ensure_interest_communities()
    me = g.user['id']
    col = get_collection('communities')
    docs = list(col.find({}).sort([('type', 1), ('name', 1)]))
    result = []
    for d in docs:
        s = _serialize(d)
        s['isMember'] = me in (d.get('members') or [])
        s['isCreator'] = str(d.get('creatorId') or '') == me
        result.append(s)
    return jsonify({'success': True, 'data': result})


# ── POST /api/community/  ───────────────────────────────────────────────────
@community_bp.route('/', methods=['POST'])
@authenticate_token
def create_community():
    """Create a custom community."""
    me = g.user['id']
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    interest = (data.get('interest') or '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'name is required'}), 400
    if len(name) > 80:
        return jsonify({'success': False, 'message': 'name too long (max 80 chars)'}), 400

    col = get_collection('communities')
    slug = _slugify(name)

    # prevent duplicate slugs
    if col.find_one({'slug': slug}):
        slug = f"{slug}-{str(ObjectId())[:6]}"

    doc = {
        'name': name,
        'slug': slug,
        'description': description,
        'type': 'custom',
        'interest': interest or None,
        'creatorId': me,
        'members': [me],
        'memberCount': 1,
        'createdAt': datetime.utcnow(),
    }
    result = col.insert_one(doc)
    doc['_id'] = str(result.inserted_id)
    doc['createdAt'] = doc['createdAt'].isoformat()
    doc['isMember'] = True
    doc['isCreator'] = True
    return jsonify({'success': True, 'data': doc}), 201


# ── DELETE /api/community/<id>  ─────────────────────────────────────────────
@community_bp.route('/<community_id>', methods=['DELETE'])
@authenticate_token
def delete_community(community_id):
    """Delete a custom community (creator only)."""
    me = g.user['id']
    col = get_collection('communities')
    try:
        doc = col.find_one({'_id': ObjectId(community_id)})
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid id'}), 400

    if not doc:
        return jsonify({'success': False, 'message': 'Community not found'}), 404
    if doc.get('type') == 'interest':
        return jsonify({'success': False, 'message': 'Cannot delete interest communities'}), 403
    if str(doc.get('creatorId') or '') != me:
        return jsonify({'success': False, 'message': 'Only the creator can delete this community'}), 403

    col.delete_one({'_id': ObjectId(community_id)})
    get_collection('community_messages').delete_many({'communityId': community_id})
    return jsonify({'success': True, 'message': 'Community deleted'})


# ── POST /api/community/<id>/join  ──────────────────────────────────────────
@community_bp.route('/<community_id>/join', methods=['POST'])
@authenticate_token
def join_community(community_id):
    me = g.user['id']
    col = get_collection('communities')
    try:
        doc = col.find_one({'_id': ObjectId(community_id)})
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid id'}), 400
    if not doc:
        return jsonify({'success': False, 'message': 'Community not found'}), 404

    if me not in (doc.get('members') or []):
        col.update_one(
            {'_id': ObjectId(community_id)},
            {'$addToSet': {'members': me}, '$inc': {'memberCount': 1}},
        )
    return jsonify({'success': True, 'message': 'Joined'})


# ── POST /api/community/<id>/leave  ─────────────────────────────────────────
@community_bp.route('/<community_id>/leave', methods=['POST'])
@authenticate_token
def leave_community(community_id):
    me = g.user['id']
    col = get_collection('communities')
    try:
        doc = col.find_one({'_id': ObjectId(community_id)})
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid id'}), 400
    if not doc:
        return jsonify({'success': False, 'message': 'Community not found'}), 404
    if str(doc.get('creatorId') or '') == me and doc.get('type') == 'custom':
        return jsonify({'success': False, 'message': 'Creator cannot leave. Delete the community instead.'}), 400

    col.update_one(
        {'_id': ObjectId(community_id)},
        {'$pull': {'members': me}, '$inc': {'memberCount': -1}},
    )
    return jsonify({'success': True, 'message': 'Left community'})


# ── GET /api/community/<id>/messages  ───────────────────────────────────────
@community_bp.route('/<community_id>/messages', methods=['GET'])
@authenticate_token
def get_community_messages(community_id):
    limit = min(int(request.args.get('limit', 100)), 200)
    msgs_col = get_collection('community_messages')
    msgs = list(
        msgs_col.find({'communityId': community_id})
        .sort('createdAt', 1)
        .limit(limit)
    )
    # enrich with sender info
    users_col = get_collection('users')
    result = []
    for m in msgs:
        s = _serialize(m)
        sender_id = m.get('senderId')
        if sender_id:
            try:
                u = users_col.find_one(
                    {'_id': ObjectId(sender_id)},
                    {'firstName': 1, 'lastName': 1, 'email': 1},
                )
                if u:
                    s['senderName'] = f"{u.get('firstName','')} {u.get('lastName','')}".strip() or u.get('email','')
                    s['senderInitials'] = (
                        (u.get('firstName','')[:1] + u.get('lastName','')[:1]).upper()
                        or u.get('email','')[:1].upper()
                    )
            except Exception:
                pass
        result.append(s)
    return jsonify({'success': True, 'data': result})


# ── POST /api/community/<id>/messages  ──────────────────────────────────────
@community_bp.route('/<community_id>/messages', methods=['POST'])
@authenticate_token
def post_community_message(community_id):
    me = g.user['id']
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'success': False, 'message': 'text is required'}), 400
    if len(text) > 2000:
        return jsonify({'success': False, 'message': 'Message too long'}), 400

    col = get_collection('communities')
    try:
        doc = col.find_one({'_id': ObjectId(community_id)})
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid id'}), 400
    if not doc:
        return jsonify({'success': False, 'message': 'Community not found'}), 404
    if me not in (doc.get('members') or []):
        return jsonify({'success': False, 'message': 'Join this community first'}), 403

    msgs_col = get_collection('community_messages')
    msg = {
        'communityId': community_id,
        'senderId': me,
        'text': text,
        'createdAt': datetime.utcnow(),
    }
    result = msgs_col.insert_one(msg)

    # enrich sender info for immediate response
    users_col = get_collection('users')
    sender_name = me
    sender_initials = 'U'
    try:
        u = users_col.find_one({'_id': ObjectId(me)}, {'firstName': 1, 'lastName': 1, 'email': 1})
        if u:
            sender_name = f"{u.get('firstName','')} {u.get('lastName','')}".strip() or u.get('email','')
            sender_initials = (
                (u.get('firstName','')[:1] + u.get('lastName','')[:1]).upper()
                or u.get('email','')[:1].upper()
            )
    except Exception:
        pass

    return jsonify({
        'success': True,
        'data': {
            '_id': str(result.inserted_id),
            'communityId': community_id,
            'senderId': me,
            'senderName': sender_name,
            'senderInitials': sender_initials,
            'text': text,
            'createdAt': datetime.utcnow().isoformat(),
        }
    }), 201


# ── DELETE /api/community/<cid>/messages/<mid>  ─────────────────────────────
@community_bp.route('/<community_id>/messages/<message_id>', methods=['DELETE'])
@authenticate_token
def delete_community_message(community_id, message_id):
    me = g.user['id']
    msgs_col = get_collection('community_messages')
    try:
        msg = msgs_col.find_one({'_id': ObjectId(message_id)})
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid id'}), 400
    if not msg:
        return jsonify({'success': False, 'message': 'Message not found'}), 404
    if str(msg.get('senderId') or '') != me:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    msgs_col.delete_one({'_id': ObjectId(message_id)})
    return jsonify({'success': True, 'message': 'Message deleted'})
