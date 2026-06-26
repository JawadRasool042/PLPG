"""
============================================
Feedback Model - MongoDB
============================================

Stores user feedback submissions (Requirement #11).
Used by both end-users (POST) and admins (LIST / READ / UPDATE STATUS).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class Feedback:
    """Feedback model class"""

    collection_name = 'feedback'

    VALID_CATEGORIES = [
        'General',
        'Quiz Quality',
        'Learning Path',
        'UI/UX',
        'Bug Report',
        'Feature Request',
    ]

    VALID_STATUSES = ['new', 'in_review', 'resolved', 'dismissed']

    @staticmethod
    def get_collection():
        return get_collection(Feedback.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = Feedback.get_collection()
        col.create_index([('createdAt', -1)])
        col.create_index([('userId', 1), ('createdAt', -1)])
        col.create_index([('status', 1), ('createdAt', -1)])
        col.create_index([('category', 1)])
        col.create_index([('metadata.quizAttemptId', 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new feedback record."""
        col = Feedback.get_collection()

        category = (data.get('category') or 'General').strip()
        if category not in Feedback.VALID_CATEGORIES:
            category = 'General'

        try:
            rating = int(data.get('rating') or 0)
        except (TypeError, ValueError):
            rating = 0
        rating = max(1, min(5, rating)) if rating else 0

        base_meta = {
            'ipAddress': data.get('ipAddress'),
            'userAgent': data.get('userAgent'),
            'page': data.get('page'),
        }
        extra = data.get('metadata') or {}
        if isinstance(extra, dict):
            allowed = {
                'quizAttemptId',
                'quizId',
                'interest',
                'quizScore',
                'quizLevel',
                'quizType',
            }
            for key in allowed:
                if key not in extra:
                    continue
                val = extra[key]
                if val is None:
                    continue
                if isinstance(val, bool):
                    base_meta[key] = val
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    base_meta[key] = val
                else:
                    s = str(val).strip()[:500]
                    if s:
                        base_meta[key] = s

        doc = {
            'userId': str(data['userId']) if data.get('userId') else None,
            'userEmail': data.get('userEmail'),
            'userName': data.get('userName'),
            'category': category,
            'rating': rating,
            'subject': (data.get('subject') or '').strip()[:200],
            'message': (data.get('message') or '').strip()[:5000],
            'status': 'new',
            'adminNote': None,
            'metadata': base_meta,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
        }

        result = col.insert_one(doc)
        doc['_id'] = result.inserted_id
        return doc

    @staticmethod
    def find_by_id(feedback_id: str) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(feedback_id)
        except Exception:
            return None
        return Feedback.get_collection().find_one({'_id': obj_id})

    @staticmethod
    def find_many(
        filter_query: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 25,
        sort: int = -1,
    ) -> List[Dict[str, Any]]:
        cursor = (
            Feedback.get_collection()
            .find(filter_query or {})
            .sort('createdAt', sort)
            .skip(skip)
            .limit(limit)
        )
        return list(cursor)

    @staticmethod
    def count(filter_query: Optional[Dict] = None) -> int:
        return Feedback.get_collection().count_documents(filter_query or {})

    @staticmethod
    def update_status(
        feedback_id: str,
        status: str,
        admin_note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if status not in Feedback.VALID_STATUSES:
            return None
        try:
            obj_id = ObjectId(feedback_id)
        except Exception:
            return None

        update_doc: Dict[str, Any] = {
            'status': status,
            'updatedAt': datetime.utcnow(),
        }
        if admin_note is not None:
            update_doc['adminNote'] = admin_note.strip()[:2000]

        Feedback.get_collection().update_one(
            {'_id': obj_id},
            {'$set': update_doc},
        )
        return Feedback.get_collection().find_one({'_id': obj_id})

    @staticmethod
    def delete(feedback_id: str) -> bool:
        try:
            obj_id = ObjectId(feedback_id)
        except Exception:
            return False
        result = Feedback.get_collection().delete_one({'_id': obj_id})
        return result.deleted_count > 0

    @staticmethod
    def stats(days: int = 30) -> Dict[str, Any]:
        """Aggregate stats for admin dashboards."""
        col = Feedback.get_collection()
        since = datetime.utcnow() - timedelta(days=days)

        total = col.count_documents({})
        recent = col.count_documents({'createdAt': {'$gte': since}})

        by_category = list(col.aggregate([
            {'$match': {'createdAt': {'$gte': since}}},
            {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]))

        by_status = list(col.aggregate([
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
        ]))

        avg_rating_doc = list(col.aggregate([
            {'$match': {'rating': {'$gt': 0}}},
            {'$group': {'_id': None, 'avg': {'$avg': '$rating'}, 'count': {'$sum': 1}}},
        ]))
        avg_rating = round(avg_rating_doc[0]['avg'], 2) if avg_rating_doc else 0
        rating_count = avg_rating_doc[0]['count'] if avg_rating_doc else 0

        return {
            'total': total,
            'recent': recent,
            'averageRating': avg_rating,
            'ratingCount': rating_count,
            'byCategory': [{'category': r['_id'], 'count': r['count']} for r in by_category],
            'byStatus': {r['_id']: r['count'] for r in by_status},
            'windowDays': days,
        }

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            'id': str(doc['_id']),
            'userId': doc.get('userId'),
            'userEmail': doc.get('userEmail'),
            'userName': doc.get('userName'),
            'category': doc.get('category'),
            'rating': doc.get('rating', 0),
            'subject': doc.get('subject', ''),
            'message': doc.get('message', ''),
            'status': doc.get('status', 'new'),
            'adminNote': doc.get('adminNote'),
            'metadata': doc.get('metadata', {}),
            'createdAt': doc.get('createdAt').isoformat() if doc.get('createdAt') else None,
            'updatedAt': doc.get('updatedAt').isoformat() if doc.get('updatedAt') else None,
        }
