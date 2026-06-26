"""Persisted remediation lessons tied to a specific quiz attempt."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class RemediationLesson:
    collection_name = "remediation_lessons"

    @staticmethod
    def get_collection():
        return get_collection(RemediationLesson.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        coll = RemediationLesson.get_collection()
        coll.create_index([("userId", 1), ("attemptId", 1)], unique=True, background=True)
        coll.create_index([("userId", 1), ("status", 1), ("passed", 1)], background=True)
        coll.create_index("retakeQuizId", background=True, sparse=True)

    @staticmethod
    def find_by_attempt(user_id: str, attempt_id: str) -> Optional[Dict[str, Any]]:
        try:
            return RemediationLesson.get_collection().find_one(
                {"userId": user_id, "attemptId": str(attempt_id)}
            )
        except Exception:
            return None

    @staticmethod
    def find_by_id(lesson_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            query: Dict[str, Any] = {"_id": ObjectId(lesson_id)}
            if user_id:
                query["userId"] = user_id
            return RemediationLesson.get_collection().find_one(query)
        except Exception:
            return None

    @staticmethod
    def upsert_for_attempt(
        user_id: str,
        attempt_id: str,
        *,
        quiz_id: str,
        interest: str,
        level: str,
        score: float,
        passed: bool,
        lesson: Dict[str, Any],
        retake_quiz_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        coll = RemediationLesson.get_collection()
        existing = coll.find_one({"userId": user_id, "attemptId": str(attempt_id)})

        doc = {
            "userId": user_id,
            "attemptId": str(attempt_id),
            "quizId": str(quiz_id),
            "retakeQuizId": retake_quiz_id,
            "interest": interest,
            "level": level,
            "score": float(score),
            "passed": bool(passed),
            "lesson": lesson,
            "status": "pending" if not passed else "skipped",
            "updatedAt": now,
        }
        if existing:
            coll.update_one({"_id": existing["_id"]}, {"$set": doc})
            doc["_id"] = existing["_id"]
            doc["createdAt"] = existing.get("createdAt", now)
        else:
            doc["createdAt"] = now
            result = coll.insert_one(doc)
            doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def update_lesson_content(
        lesson_id: str,
        user_id: str,
        lesson: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        coll = RemediationLesson.get_collection()
        result = coll.update_one(
            {"_id": ObjectId(lesson_id), "userId": user_id},
            {"$set": {"lesson": lesson, "updatedAt": datetime.utcnow()}},
        )
        if result.matched_count == 0:
            return None
        return RemediationLesson.find_by_id(lesson_id, user_id)

    @staticmethod
    def mark_studied(lesson_id: str, user_id: str) -> bool:
        result = RemediationLesson.get_collection().update_one(
            {"_id": ObjectId(lesson_id), "userId": user_id},
            {"$set": {"status": "studied", "studiedAt": datetime.utcnow(), "updatedAt": datetime.utcnow()}},
        )
        return result.modified_count > 0

    @staticmethod
    def mark_passed_for_retake_quiz(user_id: str, retake_quiz_id: str, passing_attempt_id: str) -> None:
        RemediationLesson.get_collection().update_many(
            {
                "userId": user_id,
                "retakeQuizId": str(retake_quiz_id),
                "passed": False,
            },
            {
                "$set": {
                    "passed": True,
                    "status": "completed",
                    "passingAttemptId": str(passing_attempt_id),
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

    @staticmethod
    def active_lock_for_user(user_id: str) -> Optional[Dict[str, Any]]:
        """Latest remediation that still blocks progression."""
        return RemediationLesson.get_collection().find_one(
            {
                "userId": user_id,
                "passed": False,
                "status": {"$in": ["pending", "studied"]},
            },
            sort=[("createdAt", -1)],
        )

    @staticmethod
    def supersede_stale_locks(user_id: str, *, keep_attempt_id: str) -> None:
        """Mark older failed remediation locks as superseded when a new failure occurs."""
        RemediationLesson.get_collection().update_many(
            {
                "userId": user_id,
                "passed": False,
                "attemptId": {"$ne": str(keep_attempt_id)},
                "status": {"$in": ["pending", "studied"]},
            },
            {"$set": {"status": "superseded", "updatedAt": datetime.utcnow()}},
        )

    @staticmethod
    def find_lock_for_retake_quiz(user_id: str, retake_quiz_id: str) -> Optional[Dict[str, Any]]:
        """Active remediation lock tied to a specific frozen retake quiz."""
        return RemediationLesson.get_collection().find_one(
            {
                "userId": user_id,
                "retakeQuizId": str(retake_quiz_id),
                "passed": False,
                "status": {"$in": ["pending", "studied"]},
            },
            sort=[("createdAt", -1)],
        )

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "attemptId": doc.get("attemptId"),
            "quizId": doc.get("quizId"),
            "retakeQuizId": doc.get("retakeQuizId"),
            "interest": doc.get("interest"),
            "level": doc.get("level"),
            "score": doc.get("score"),
            "passed": bool(doc.get("passed")),
            "status": doc.get("status"),
            "lesson": doc.get("lesson") or {},
            "createdAt": doc.get("createdAt"),
            "studiedAt": doc.get("studiedAt"),
        }
