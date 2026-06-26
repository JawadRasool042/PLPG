"""
============================================
AI Quiz Session Model - MongoDB
============================================

Stores in-flight and completed real-time AI quiz sessions. Each session
records the questions the model generated, the user's answers, instant
feedback, and any concepts the learner got wrong (so subsequent
questions can target those weak spots).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId

from database import get_collection


COLLECTION_NAME = "ai_quiz_sessions"


class AIQuizSession:
    """Helper around the ``ai_quiz_sessions`` collection."""

    @staticmethod
    def collection():
        return get_collection(COLLECTION_NAME)

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    @staticmethod
    def create(
        user_id: str,
        topic: str,
        difficulty: str = "basic",
        target_question_count: int = 10,
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        doc = {
            "userId": user_id,
            "topic": topic,
            "difficulty": difficulty,
            "targetQuestionCount": int(target_question_count or 0),
            "questions": [],          # full model payloads (with answers)
            "answers": [],            # parallel array with user answers + correctness
            "weakConcepts": [],       # concept summaries from wrong answers
            "correctCount": 0,
            "totalAnswered": 0,
            "status": "active",       # active | completed | abandoned
            "createdAt": now,
            "updatedAt": now,
            "completedAt": None,
        }
        result = AIQuizSession.collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find(session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            query: Dict[str, Any] = {"_id": ObjectId(session_id)}
        except Exception:
            return None
        if user_id:
            query["userId"] = user_id
        return AIQuizSession.collection().find_one(query)

    @staticmethod
    def find_active(user_id: str) -> Optional[Dict[str, Any]]:
        return AIQuizSession.collection().find_one(
            {"userId": user_id, "status": "active"},
            sort=[("createdAt", -1)],
        )

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------
    @staticmethod
    def append_question(session_id: str, question: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a generated question so we never re-ask it in the session."""
        coll = AIQuizSession.collection()
        coll.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"questions": question},
                "$set": {"updatedAt": datetime.utcnow()},
            },
        )
        return coll.find_one({"_id": ObjectId(session_id)})

    @staticmethod
    def record_answer(
        session_id: str,
        question_index: int,
        user_answer: str,
        is_correct: bool,
        time_spent_ms: int = 0,
    ) -> Dict[str, Any]:
        """Record an answer, idempotent on (session_id, question_index).

        If the same question is submitted twice (double-click, retry), the
        existing entry is replaced and the totals are recomputed from scratch
        instead of being double-counted.
        """
        coll = AIQuizSession.collection()
        now = datetime.utcnow()
        question_idx = int(question_index)
        existing = coll.find_one({"_id": ObjectId(session_id)}, {"answers": 1})
        existing_answers = list((existing or {}).get("answers") or [])
        new_entry = {
            "questionIndex": question_idx,
            "userAnswer": user_answer,
            "isCorrect": bool(is_correct),
            "timeSpentMs": int(time_spent_ms or 0),
            "answeredAt": now,
        }

        merged: list[Dict[str, Any]] = []
        replaced = False
        for entry in existing_answers:
            if int(entry.get("questionIndex", -1)) == question_idx:
                merged.append(new_entry)
                replaced = True
            else:
                merged.append(entry)
        if not replaced:
            merged.append(new_entry)

        total_answered = len(merged)
        correct_count = sum(1 for entry in merged if entry.get("isCorrect"))

        coll.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "answers": merged,
                    "totalAnswered": total_answered,
                    "correctCount": correct_count,
                    "updatedAt": now,
                }
            },
        )
        return coll.find_one({"_id": ObjectId(session_id)})

    @staticmethod
    def add_weak_concept(session_id: str, concept: str) -> None:
        if not concept:
            return
        AIQuizSession.collection().update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {"weakConcepts": concept},
                "$set": {"updatedAt": datetime.utcnow()},
            },
        )

    @staticmethod
    def finalize(session_id: str, status: str = "completed") -> Optional[Dict[str, Any]]:
        coll = AIQuizSession.collection()
        now = datetime.utcnow()
        coll.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "status": status,
                    "completedAt": now,
                    "updatedAt": now,
                }
            },
        )
        return coll.find_one({"_id": ObjectId(session_id)})

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    @staticmethod
    def previous_question_stems(session: Dict[str, Any]) -> List[str]:
        """Return the question stems already asked in this session."""
        return [
            (q.get("question") or "").strip()
            for q in (session.get("questions") or [])
            if (q.get("question") or "").strip()
        ]

    @staticmethod
    def to_response(
        session: Dict[str, Any],
        include_answers: bool = False,
    ) -> Dict[str, Any]:
        if not session:
            return {}

        score = 0
        total = int(session.get("totalAnswered") or 0)
        correct = int(session.get("correctCount") or 0)
        if total > 0:
            score = round((correct / total) * 100, 2)

        return {
            "id": str(session["_id"]),
            "topic": session.get("topic"),
            "difficulty": session.get("difficulty"),
            "status": session.get("status", "active"),
            "targetQuestionCount": session.get("targetQuestionCount", 0),
            "totalAnswered": total,
            "correctCount": correct,
            "score": score,
            "weakConcepts": session.get("weakConcepts", []),
            "createdAt": _iso(session.get("createdAt")),
            "completedAt": _iso(session.get("completedAt")),
            "questions": [
                _question_for_response(q, include_answers)
                for q in session.get("questions", [])
            ] if include_answers else [
                _question_summary(q) for q in session.get("questions", [])
            ],
            "answers": session.get("answers", []) if include_answers else [],
        }


def _iso(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _question_summary(q: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "question": q.get("question"),
        "topic": q.get("topic"),
        "difficulty": q.get("difficulty"),
    }


def _question_for_response(q: Dict[str, Any], include_answers: bool) -> Dict[str, Any]:
    payload = {
        "question": q.get("question"),
        "options": q.get("options"),
        "topic": q.get("topic"),
        "difficulty": q.get("difficulty"),
        "concept_summary": q.get("concept_summary"),
        "memory_tip": q.get("memory_tip"),
    }
    if include_answers:
        payload["correct_answer"] = q.get("correct_answer")
        payload["reasoning"] = q.get("reasoning")
    return payload


__all__ = ["AIQuizSession"]
