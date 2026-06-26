"""Cache invalidation and retrieval for persisted learning paths."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from models.quiz_attempt import QuizAttempt
from models.user import User
from models.user_learning_path import UserLearningPath

logger = logging.getLogger(__name__)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def compute_invalidation_key(user_id: str) -> str:
    """
    Fingerprint that changes when the user retakes interest assessment
    or completes any quiz attempt.
    """
    user = None
    if user_id:
        try:
            user = User.find_by_id(user_id)
        except Exception:
            user = None
    assessment = (user or {}).get("interestAssessment") or {}

    interest_blob = {
        "primaryInterest": assessment.get("primaryInterest"),
        "domainScores": assessment.get("domainScores"),
        "allInterests": assessment.get("allInterests"),
        "completedAt": assessment.get("completedAt"),
        "lastUpdated": assessment.get("lastUpdated"),
    }

    latest_attempt_id = "none"
    attempt_count = 0
    try:
        coll = QuizAttempt.get_collection()
        attempt_count = coll.count_documents({"userId": str(user_id)})
        latest = coll.find_one({"userId": str(user_id)}, sort=[("completedAt", -1), ("_id", -1)])
        if latest and latest.get("_id") is not None:
            latest_attempt_id = str(latest["_id"])
    except Exception as exc:
        logger.warning("Could not load quiz attempts for learning-path cache key: %s", exc)

    raw = json.dumps(
        {
            "interest": interest_blob,
            "latestQuizAttemptId": latest_attempt_id,
            "quizAttemptCount": attempt_count,
        },
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_learning_path(
    user_id: str,
    domain: str,
    *,
    invalidation_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not user_id or not domain:
        return None

    doc = UserLearningPath.find_cached(user_id, domain)
    if not doc:
        return None

    key = invalidation_key or compute_invalidation_key(user_id)
    if doc.get("invalidationKey") != key:
        return None

    payload = doc.get("payload")
    if not isinstance(payload, dict):
        return None

    return {
        **payload,
        "cached": True,
        "generated_at": doc.get("updatedAt"),
    }


def get_stale_learning_path(user_id: str, domain: str) -> Optional[Dict[str, Any]]:
    """Return last saved path even when invalidation key changed (OpenAI refresh fallback)."""
    if not user_id or not domain:
        return None

    doc = UserLearningPath.find_cached(user_id, domain)
    if not doc:
        return None

    payload = doc.get("payload")
    if not isinstance(payload, dict) or not payload.get("roadmap"):
        return None

    return {
        **payload,
        "domain": payload.get("domain") or domain,
        "cached": True,
        "stale": True,
        "generated_at": doc.get("updatedAt"),
    }


def save_learning_path(
    user_id: str,
    domain: str,
    payload: Dict[str, Any],
    *,
    invalidation_key: Optional[str] = None,
) -> None:
    if not user_id or not domain:
        return

    key = invalidation_key or compute_invalidation_key(user_id)
    stored = {k: v for k, v in payload.items() if k not in {"cached", "generated_at"}}
    stored["cached"] = False
    UserLearningPath.upsert(user_id, domain, stored, key)
