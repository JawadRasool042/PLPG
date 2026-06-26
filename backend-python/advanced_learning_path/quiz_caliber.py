"""Load quiz performance signals used to personalize learning paths and quiz difficulty."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database import get_collection


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def recommended_difficulty_from_scores(avg_score: float, recent: List[float]) -> str:
    """Map performance to quiz difficulty band."""
    recent_avg = sum(recent) / len(recent) if recent else avg_score
    blended = (avg_score * 0.4) + (recent_avg * 0.6)
    if blended < 45:
        return "beginner"
    if blended < 72:
        return "intermediate"
    return "advanced"


def load_user_quiz_caliber(user_id: Optional[str], domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Build quiz-caliber payload from unified quiz_attempts collection.
    Used by roadmap generation and mixed-quiz difficulty selection.
    """
    if not user_id:
        return {
            "attempt_count": 0,
            "average_score": 0.0,
            "best_score": 0.0,
            "recent_scores": [],
            "mastery_level": 0.0,
            "recommended_quiz_difficulty": "beginner",
            "by_topic": {},
        }

    coll = get_collection("quiz_attempts")
    query: Dict[str, Any] = {
        "userId": user_id,
        "$or": [
            {"status": {"$in": ["completed", "finished"]}},
            {"completedAt": {"$exists": True, "$ne": None}},
        ],
    }
    if domain:
        query["interest"] = {"$regex": f"^{domain}$", "$options": "i"}

    attempts = list(coll.find(query).sort("completedAt", -1).limit(30))
    if not attempts and domain:
        query.pop("interest", None)
        attempts = list(coll.find(query).sort("completedAt", -1).limit(30))

    scores = [_safe_float(a.get("score")) for a in attempts]
    recent = scores[:5]
    avg = sum(scores) / len(scores) if scores else 0.0
    best = max(scores) if scores else 0.0
    mastery = max(0.0, min(1.0, avg / 100.0))

    by_topic: Dict[str, Dict[str, Any]] = {}
    for attempt in attempts:
        topic = str(attempt.get("interest") or "General").strip() or "General"
        entry = by_topic.setdefault(
            topic,
            {"attempts": 0, "score_sum": 0.0, "best_score": 0.0, "recent_scores": []},
        )
        score = _safe_float(attempt.get("score"))
        entry["attempts"] += 1
        entry["score_sum"] += score
        entry["best_score"] = max(entry["best_score"], score)
        if len(entry["recent_scores"]) < 5:
            entry["recent_scores"].append(score)

    for topic, entry in by_topic.items():
        attempts_n = max(1, int(entry["attempts"]))
        entry["average_score"] = round(entry["score_sum"] / attempts_n, 2)
        entry["recommended_quiz_difficulty"] = recommended_difficulty_from_scores(
            entry["average_score"], entry["recent_scores"]
        )
        del entry["score_sum"]

    domain_key = (domain or "").strip()
    topic_avg = by_topic.get(domain_key, {}).get("average_score", avg) if domain_key else avg
    topic_recent = by_topic.get(domain_key, {}).get("recent_scores", recent) if domain_key else recent

    return {
        "attempt_count": len(attempts),
        "average_score": round(avg, 2),
        "best_score": round(best, 2),
        "recent_scores": recent,
        "mastery_level": round(mastery, 4),
        "recommended_quiz_difficulty": recommended_difficulty_from_scores(topic_avg, topic_recent),
        "by_topic": by_topic,
    }
