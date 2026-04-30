"""
Notes/Learning Content Routes
Students can read notes per topic before taking quizzes
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime
from database import get_collection
from middleware.auth import authenticate_token

notes_bp = Blueprint('notes', __name__)


def serialize(doc):
    if not doc:
        return None
    doc['_id'] = str(doc['_id'])
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


# ── GET /api/notes  (list all topics) ───────────────────────
@notes_bp.route('', methods=['GET'])
@authenticate_token
def list_notes():
    interest = request.args.get('interest', '').strip()
    col = get_collection('notes')
    query = {}
    if interest:
        query['interest'] = {'$regex': interest, '$options': 'i'}
    docs = list(col.find(query, {'content': 0}).sort([('interest', 1), ('order', 1)]))
    return jsonify({'success': True, 'data': [serialize(d) for d in docs]})


# ── GET /api/notes/<id>  (full note with content) ───────────
@notes_bp.route('/<note_id>', methods=['GET'])
@authenticate_token
def get_note(note_id):
    col = get_collection('notes')
    doc = col.find_one({'_id': ObjectId(note_id)})
    if not doc:
        return jsonify({'success': False, 'message': 'Note not found'}), 404

    # Track read progress
    progress_col = get_collection('note_progress')
    progress_col.update_one(
        {'userId': g.user['id'], 'noteId': note_id},
        {'$set': {'userId': g.user['id'], 'noteId': note_id, 'readAt': datetime.utcnow()}},
        upsert=True
    )
    return jsonify({'success': True, 'data': serialize(doc)})


# ── GET /api/notes/progress/me  (which notes user has read) ─
@notes_bp.route('/progress/me', methods=['GET'])
@authenticate_token
def my_progress():
    col = get_collection('note_progress')
    docs = list(col.find({'userId': g.user['id']}, {'noteId': 1}))
    read_ids = [d['noteId'] for d in docs]
    return jsonify({'success': True, 'readNoteIds': read_ids})
