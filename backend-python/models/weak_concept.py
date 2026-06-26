"""
============================================
Weak Concept Model - MongoDB
============================================

Tracks the topics/concepts a learner has answered incorrectly so the AI
quiz generator can target them in subsequent questions. Each (user, topic,
concept) tuple is upserted, with counters for failures, last-seen time and
mastery.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


COLLECTION_NAME = "weak_concepts"


class WeakConcept:
    """Helper around the ``weak_concepts`` collection."""

    @staticmethod
    def collection():
        return get_collection(COLLECTION_NAME)

    # ------------------------------------------------------------------
    # Recording weakness / mastery
    # ------------------------------------------------------------------
    @staticmethod
    def record_failure(
        user_id: str,
        concept: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        question: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Increment the failure counter for ``concept`` (creates if missing)."""
        if not concept:
            return {}

        coll = WeakConcept.collection()
        now = datetime.utcnow()
        concept_key = concept.strip().lower()

        coll.update_one(
            {"userId": user_id, "conceptKey": concept_key},
            {
                "$set": {
                    "userId": user_id,
                    "conceptKey": concept_key,
                    "concept": concept.strip(),
                    "topic": topic,
                    "difficulty": difficulty,
                    "lastWrongQuestion": question,
                    "lastSeenAt": now,
                    "mastered": False,
                },
                "$inc": {"failureCount": 1},
                "$setOnInsert": {"firstSeenAt": now, "successCount": 0},
            },
            upsert=True,
        )
        return coll.find_one({"userId": user_id, "conceptKey": concept_key})

    @staticmethod
    def record_success(user_id: str, concept: str) -> None:
        """Increment success counter; mark mastered after 2 consecutive wins."""
        if not concept:
            return
        coll = WeakConcept.collection()
        concept_key = concept.strip().lower()
        existing = coll.find_one({"userId": user_id, "conceptKey": concept_key})
        if not existing:
            return

        success_count = int(existing.get("successCount", 0)) + 1
        mastered = success_count >= 2

        coll.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "successCount": success_count,
                    "mastered": mastered,
                    "lastSeenAt": datetime.utcnow(),
                }
            },
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @staticmethod
    def top_weak_concepts(
        user_id: str,
        topic: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """Return concept names ordered by failure frequency (excluding mastered)."""
        query: Dict[str, Any] = {"userId": user_id, "mastered": False}
        if topic:
            query["topic"] = topic

        cursor = (
            WeakConcept.collection()
            .find(query)
            .sort([("failureCount", -1), ("lastSeenAt", -1)])
            .limit(int(limit))
        )
        return [doc.get("concept") for doc in cursor if doc.get("concept")]

    @staticmethod
    def list_for_user(
        user_id: str,
        include_mastered: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"userId": user_id}
        if not include_mastered:
            query["mastered"] = False

        cursor = (
            WeakConcept.collection()
            .find(query)
            .sort([("failureCount", -1), ("lastSeenAt", -1)])
            .limit(int(limit))
        )
        return [WeakConcept.to_response(doc) for doc in cursor]

    @staticmethod
    def to_response(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(doc.get("_id")) if isinstance(doc.get("_id"), ObjectId) else None,
            "concept": doc.get("concept"),
            "topic": doc.get("topic"),
            "difficulty": doc.get("difficulty"),
            "failureCount": int(doc.get("failureCount", 0)),
            "successCount": int(doc.get("successCount", 0)),
            "mastered": bool(doc.get("mastered", False)),
            "lastSeenAt": doc.get("lastSeenAt").isoformat() if doc.get("lastSeenAt") else None,
            "firstSeenAt": doc.get("firstSeenAt").isoformat() if doc.get("firstSeenAt") else None,
            "lastWrongQuestion": doc.get("lastWrongQuestion"),
        }


__all__ = ["WeakConcept"]
