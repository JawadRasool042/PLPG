"""Persisted personalized learning paths (one active snapshot per user + domain)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from database import get_collection


class UserLearningPath:
    collection_name = "user_learning_paths"

    @staticmethod
    def get_collection():
        return get_collection(UserLearningPath.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = UserLearningPath.get_collection()
        col.create_index([("userId", 1), ("domain", 1)], unique=True)
        col.create_index([("updatedAt", -1)])

    @staticmethod
    def find_cached(user_id: str, domain: str) -> Optional[Dict[str, Any]]:
        if not user_id or not domain:
            return None
        return UserLearningPath.get_collection().find_one(
            {"userId": str(user_id), "domain": str(domain).strip()}
        )

    @staticmethod
    def upsert(
        user_id: str,
        domain: str,
        payload: Dict[str, Any],
        invalidation_key: str,
    ) -> None:
        now = datetime.utcnow()
        UserLearningPath.get_collection().update_one(
            {"userId": str(user_id), "domain": str(domain).strip()},
            {
                "$set": {
                    "payload": payload,
                    "invalidationKey": invalidation_key,
                    "updatedAt": now,
                },
                "$setOnInsert": {"createdAt": now},
            },
            upsert=True,
        )

    @staticmethod
    def delete_for_user(user_id: str) -> int:
        result = UserLearningPath.get_collection().delete_many({"userId": str(user_id)})
        return int(result.deleted_count)
