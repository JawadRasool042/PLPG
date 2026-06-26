"""
============================================
AI Quiz Routes - Real-Time OpenAI Quiz API
============================================

Production-ready endpoints that drive the AI quiz feature:

- POST /api/ai-quiz/start        Start a session, return the first question.
- POST /api/ai-quiz/next         Generate the next question (targets weak
                                 concepts when present).
- POST /api/ai-quiz/answer       Submit an answer, get instant feedback,
                                 and have weak concepts persisted.
- POST /api/ai-quiz/finish       Mark the session complete and return the
                                 final score + weak concept summary.
- GET  /api/ai-quiz/session/<id> Inspect a previous session (with answers).
- GET  /api/ai-quiz/weak-concepts List the user's outstanding weak concepts.

Questions are generated dynamically — nothing is pre-stored.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from flask import Blueprint, g, jsonify, request

from database import get_collection
from middleware.auth import authenticate_token
from models.ai_quiz_session import AIQuizSession
from models.weak_concept import WeakConcept
from services.quiz_generator.ai_quiz_service import (
    AIQuizError,
    AIQuizService,
    ALLOWED_DIFFICULTIES,
)


logger = logging.getLogger(__name__)

ai_quiz_bp = Blueprint("ai_quiz", __name__)
LEVEL_ORDER = ["basic", "intermediate", "advanced", "expert"]

# AI quizzes are capped to a fixed length so each session is short, focused,
# and stays within provider free-tier/rate limits.
AI_QUIZ_QUESTION_LIMIT = 10


# Lazy singleton — instantiated on first request so missing OPENAI_API_KEY
# doesn't crash the app at import time.
_service: Optional[AIQuizService] = None


def _get_service() -> AIQuizService:
    global _service
    if _service is None:
        _service = AIQuizService()
    return _service


def _public_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """Return the user-facing slice of a question (no answers, no reasoning)."""
    options = question.get("options")
    if isinstance(options, dict):
        options = [
            f"{letter}) {options.get(letter, '')}" for letter in ("A", "B", "C", "D")
        ]
    return {
        "question": question.get("question"),
        "options": options,
        "topic": question.get("topic"),
        "difficulty": question.get("difficulty"),
    }


def _resolve_topic(payload: Dict[str, Any]) -> str:
    topic = (payload.get("topic") or payload.get("interest") or "").strip()
    if topic:
        return topic
    user = getattr(g, "user_doc", None) or {}
    assessment = user.get("interestAssessment") or {}
    primary = (assessment.get("primaryInterest") or "").strip()
    return primary


def _normalise_difficulty(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in ALLOWED_DIFFICULTIES else "basic"


def _level_up(level: str) -> str:
    try:
        idx = LEVEL_ORDER.index(level)
    except ValueError:
        return "basic"
    return LEVEL_ORDER[min(idx + 1, len(LEVEL_ORDER) - 1)]


def _level_down(level: str) -> str:
    try:
        idx = LEVEL_ORDER.index(level)
    except ValueError:
        return "basic"
    return LEVEL_ORDER[max(idx - 1, 0)]


def _level_recommendation(score: float, current_level: str) -> str:
    """Backwards-compatible wrapper: returns just the recommended level string."""
    return _build_level_recommendation(score, current_level)["recommended"]


def _build_level_recommendation(score: float, current_level: str) -> Dict[str, Any]:
    """Choose the next-quiz difficulty based on the user's percentage.

    Bands (relative to the level the user just played):
      <  40 %  → demote one level   ("Struggled — let's reinforce basics")
      40-60 %  → repeat same level  ("Solid progress — try once more")
      60-80 %  → promote one level  ("Great work — step up")
      80-90 %  → promote two levels ("Excellent — jump ahead")
      ≥  90 %  → expert             ("Mastery — try the hardest questions")

    Returns ``{recommended, change, reason, score_band, from}``.
    """
    score = max(0.0, min(100.0, float(score or 0)))
    current = current_level if current_level in LEVEL_ORDER else "basic"
    current_idx = LEVEL_ORDER.index(current)

    if score < 40:
        target = LEVEL_ORDER[max(0, current_idx - 1)]
        change = "demote" if target != current else "repeat"
        reason = (
            f"Score {score:.0f}% is below 40%. "
            f"We'll drop back to **{target.title()}** so you can reinforce the basics."
            if change == "demote"
            else f"Score {score:.0f}% is low — let's stay on **{target.title()}** and rebuild confidence."
        )
        band = "struggling"
    elif score < 60:
        target = current
        change = "repeat"
        reason = (
            f"Score {score:.0f}% shows real progress on **{target.title()}**. "
            "Run another session at the same level to lock it in."
        )
        band = "developing"
    elif score < 80:
        target = LEVEL_ORDER[min(len(LEVEL_ORDER) - 1, current_idx + 1)]
        change = "promote" if target != current else "repeat"
        reason = (
            f"Score {score:.0f}% — you're ready for harder questions. "
            f"Stepping up to **{target.title()}**."
            if change == "promote"
            else f"Score {score:.0f}% — you're already at the top level. Keep practising on **{target.title()}**."
        )
        band = "on-track"
    elif score < 90:
        target = LEVEL_ORDER[min(len(LEVEL_ORDER) - 1, current_idx + 2)]
        change = "jump" if target != current else "repeat"
        reason = (
            f"Score {score:.0f}% is excellent. "
            f"Jumping ahead to **{target.title()}** — you've earned it."
            if change == "jump"
            else f"Score {score:.0f}% — already at the top level. Try a new topic at **{target.title()}**."
        )
        band = "excellent"
    else:
        target = "expert"
        change = "promote" if target != current else "repeat"
        reason = (
            f"Score {score:.0f}% — true mastery. "
            f"Taking on **{target.title()}**-tier questions next."
            if change != "repeat"
            else f"Score {score:.0f}% — you're already running at **{target.title()}** level. Keep the streak going."
        )
        band = "mastery"

    return {
        "recommended": target,
        "from": current,
        "change": change,        # "demote" | "repeat" | "promote" | "jump"
        "reason": reason,
        "score_band": band,      # "struggling" | "developing" | "on-track" | "excellent" | "mastery"
        "score": round(score, 2),
    }


def _attempts_collection():
    return get_collection("ai_quiz_attempts")


def _unified_attempts_collection():
    """The collection ``getQuizHistory`` reads from.

    Writing AI quiz attempts here in real time means the user's dashboard
    history shows AI sessions alongside legacy quiz attempts.
    """
    return get_collection("quiz_attempts")


def _ensure_unified_indexes() -> None:
    """Index sessionId in quiz_attempts so we can upsert by it (idempotent)."""
    try:
        coll = _unified_attempts_collection()
        coll.create_index("sessionId", background=True, sparse=True)
    except Exception:  # noqa: BLE001
        pass


def _question_result_doc(question: Dict[str, Any], idx: int, user_answer: str = "", is_correct: Optional[bool] = None) -> Dict[str, Any]:
    """Map an AI-quiz question to the legacy ``results[]`` shape used in quiz_attempts."""
    options = question.get("options")
    if isinstance(options, dict):
        options_list = [
            f"{letter}) {options.get(letter, '')}" for letter in ("A", "B", "C", "D")
        ]
    elif isinstance(options, list):
        options_list = list(options)
    else:
        options_list = []

    reasoning = question.get("reasoning") or {}
    if isinstance(reasoning, dict):
        explanation = (
            reasoning.get("explanation")
            or reasoning.get("why_correct")
            or reasoning.get("why_correct_short")
            or question.get("why_correct")
            or ""
        )
    else:
        explanation = str(reasoning)

    return {
        "questionIndex": idx,
        "question": question.get("question"),
        "options": options_list,
        "userAnswer": user_answer,
        "correctAnswer": str(question.get("correct_answer", "")).strip().upper(),
        "isCorrect": bool(is_correct) if is_correct is not None else False,
        "explanation": explanation,
    }


def _upsert_unified_attempt(
    *,
    session_id: str,
    user_id: str,
    topic: str,
    difficulty: str,
    questions: list,
    answers_map: Dict[str, str],
    target_count: int,
    started_at: datetime,
    status: str,
    completed_at: Optional[datetime] = None,
) -> str:
    """Real-time write to the unified ``quiz_attempts`` collection.

    Called from /start (initial in-progress row), /answer (incremental update),
    and /finish (final state). The same ``sessionId`` always upserts the same
    document so we never get duplicates, even on retry.
    """
    _ensure_unified_indexes()

    results = []
    correct_count = 0
    total_answered = 0
    for idx, q in enumerate(questions or []):
        user_answer_raw = answers_map.get(str(idx)) or ""
        normalized_user = (user_answer_raw or "").strip().upper().rstrip(")")
        correct_answer = str(q.get("correct_answer", "")).strip().upper()
        is_answered = bool(normalized_user)
        is_correct = is_answered and normalized_user == correct_answer
        if is_answered:
            total_answered += 1
            if is_correct:
                correct_count += 1
        results.append(
            _question_result_doc(
                q,
                idx,
                user_answer=normalized_user if is_answered else "",
                is_correct=is_correct if is_answered else None,
            )
        )

    total_questions = max(target_count, len(results))
    score = round((correct_count / total_questions) * 100, 2) if total_questions else 0.0

    capitalized_level = (difficulty or "basic").capitalize()
    doc = {
        "userId": user_id,
        "sessionId": session_id,
        "quizId": session_id,  # legacy clients key on quizId; reuse the session id
        "quizType": "ai",
        "interest": topic,
        "level": capitalized_level,
        "answers": answers_map,
        "score": score,
        "correctCount": correct_count,
        "totalAnswered": total_answered,
        "totalQuestions": total_questions,
        "results": results,
        "estimatedDifficulty": capitalized_level,
        "actualDifficulty": capitalized_level,
        "isAdaptiveDifficulty": True,
        "status": status,
        "startedAt": started_at,
        "completedAt": completed_at or (datetime.utcnow() if status == "completed" else None),
        "updatedAt": datetime.utcnow(),
    }

    coll = _unified_attempts_collection()
    res = coll.update_one(
        {"sessionId": session_id, "quizType": "ai"},
        {
            "$set": doc,
            "$setOnInsert": {"createdAt": datetime.utcnow()},
        },
        upsert=True,
    )

    if res.upserted_id is not None:
        return str(res.upserted_id)
    existing = coll.find_one({"sessionId": session_id, "quizType": "ai"}, {"_id": 1})
    return str(existing["_id"]) if existing else session_id


def _consecutive_failures_same_level(user_id: str, level: str, limit: int = 2) -> int:
    docs = list(
        _attempts_collection()
        .find({"userId": user_id, "level": level})
        .sort("completedAt", -1)
        .limit(limit)
    )
    streak = 0
    for item in docs:
        if item.get("failedAtLevel"):
            streak += 1
        else:
            break
    return streak


def _build_dashboard(user_id: str, limit: int = 20) -> Dict[str, Any]:
    attempts = list(
        _attempts_collection()
        .find({"userId": user_id})
        .sort("completedAt", -1)
        .limit(max(1, min(int(limit), 100)))
    )
    attempts = list(reversed(attempts))

    score_history = [
        {
            "attemptId": str(a.get("_id")),
            "topic": a.get("topic"),
            "score": float(a.get("score", 0)),
            "level": a.get("level"),
            "completedAt": a.get("completedAt").isoformat() if a.get("completedAt") else None,
        }
        for a in attempts
    ]

    level_progress = [
        {
            "attemptId": str(a.get("_id")),
            "fromLevel": a.get("level"),
            "recommendedLevel": a.get("recommendedNextLevel"),
            "easierQuizTriggered": bool(a.get("easierQuizTriggered", False)),
        }
        for a in attempts
    ]

    weak_topics = WeakConcept.list_for_user(user_id=user_id, include_mastered=False, limit=10)
    recommendations = []
    if attempts:
        last = attempts[-1]
        recommendations.append(
            f"Next quiz level: {str(last.get('recommendedNextLevel', 'basic')).title()}."
        )
        if last.get("easierQuizTriggered"):
            recommendations.append(
                "Two failures detected at the same level. Easier quiz has been auto-selected."
            )
    if weak_topics:
        top = weak_topics[0].get("concept")
        if top:
            recommendations.append(f"Focus on weak topic: {top}.")

    return {
        "scoreHistory": score_history,
        "levelProgress": level_progress,
        "weakTopics": weak_topics,
        "recommendations": recommendations,
    }


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@ai_quiz_bp.route("/start", methods=["POST"])
@authenticate_token
def start_session():
    """Start a new AI quiz session and return the first question."""
    payload = request.get_json(silent=True) or {}
    user_id = g.user.get("id")

    topic = _resolve_topic(payload)
    if not topic:
        return jsonify({
            "success": False,
            "message": "topic is required (or complete the interest assessment first)",
        }), 400

    requested_difficulty = _normalise_difficulty(payload.get("difficulty", "basic"))
    recent_failures = _consecutive_failures_same_level(user_id, requested_difficulty)
    easier_quiz_triggered = recent_failures >= 2 and requested_difficulty != "basic"
    difficulty = _level_down(requested_difficulty) if easier_quiz_triggered else requested_difficulty

    # AI quizzes are hard-capped to 10 MCQs per session (configurable via
    # ``AI_QUIZ_QUESTION_LIMIT`` at the top of this module).
    try:
        requested_count = int(payload.get("question_count", AI_QUIZ_QUESTION_LIMIT) or AI_QUIZ_QUESTION_LIMIT)
    except (TypeError, ValueError):
        requested_count = AI_QUIZ_QUESTION_LIMIT
    target_count = max(1, min(requested_count, AI_QUIZ_QUESTION_LIMIT))

    try:
        service = _get_service()
    except AIQuizError as exc:
        logger.error("AI quiz service unavailable: %s", exc)
        return jsonify({
            "success": False,
            "message": "AI quiz service is not configured (missing OPENAI_API_KEY).",
        }), 503

    session = AIQuizSession.create(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        target_question_count=target_count,
    )

    weak_concepts = WeakConcept.top_weak_concepts(user_id=user_id, topic=topic, limit=5)

    try:
        question = service.generate_question(
            topic=topic,
            difficulty=difficulty,
            weak_concepts=weak_concepts,
            previous_questions=AIQuizSession.previous_question_stems(session),
        )
    except AIQuizError as exc:
        logger.exception("Initial AI quiz question generation failed")
        AIQuizSession.finalize(str(session["_id"]), status="abandoned")
        return jsonify({
            "success": False,
            "message": "Unable to generate a quiz question right now. Please try again in a moment.",
        }), 502

    updated_session = AIQuizSession.append_question(str(session["_id"]), question)
    questions_so_far = (updated_session or session).get("questions") or [question]

    started_at = session.get("createdAt") or datetime.utcnow()
    attempt_id = _upsert_unified_attempt(
        session_id=str(session["_id"]),
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        questions=questions_so_far,
        answers_map={},
        target_count=target_count,
        started_at=started_at,
        status="in_progress",
    )

    return jsonify({
        "success": True,
        "session_id": str(session["_id"]),
        "attempt_id": attempt_id,
        "topic": topic,
        "difficulty": difficulty,
        "requested_difficulty": requested_difficulty,
        "easier_quiz_triggered": easier_quiz_triggered,
        "target_question_count": target_count,
        "question_limit": AI_QUIZ_QUESTION_LIMIT,
        "question_index": 0,
        "question": _public_question(question),
        "weak_concepts": weak_concepts,
    }), 201


@ai_quiz_bp.route("/next", methods=["POST"])
@authenticate_token
def next_question():
    """Generate the next question in an active session."""
    payload = request.get_json(silent=True) or {}
    user_id = g.user.get("id")
    session_id = (payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"success": False, "message": "session_id is required"}), 400

    session = AIQuizSession.find(session_id, user_id=user_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404
    if session.get("status") != "active":
        return jsonify({"success": False, "message": "Session is no longer active"}), 409

    # Enforce the per-session question limit.
    target_count = min(int(session.get("targetQuestionCount") or AI_QUIZ_QUESTION_LIMIT), AI_QUIZ_QUESTION_LIMIT)
    answered = int(session.get("totalAnswered") or 0)
    questions_already = len(session.get("questions") or [])
    if answered >= target_count or questions_already >= target_count:
        return jsonify({
            "success": False,
            "message": f"This AI quiz is limited to {target_count} questions. Please finish the session.",
            "code": "QUESTION_LIMIT_REACHED",
            "limit": target_count,
        }), 409

    topic = session.get("topic")
    # Keep session difficulty stable after /start. Do not allow client overrides
    # mid-session, otherwise levels can drift question-to-question.
    difficulty = _normalise_difficulty(session.get("difficulty"))

    weak_concepts = WeakConcept.top_weak_concepts(user_id=user_id, topic=topic, limit=5)
    # Always prepend session-local weak concepts so retraining is immediate.
    session_weak = list(session.get("weakConcepts") or [])
    combined_weak = list(dict.fromkeys(session_weak + weak_concepts))

    try:
        service = _get_service()
        question = service.generate_question(
            topic=topic,
            difficulty=difficulty,
            weak_concepts=combined_weak,
            previous_questions=AIQuizSession.previous_question_stems(session),
        )
    except AIQuizError as exc:
        logger.exception("Next AI quiz question generation failed")
        return jsonify({
            "success": False,
            "message": "Unable to generate the next question right now. Please try again in a moment.",
        }), 502

    updated = AIQuizSession.append_question(session_id, question)
    question_index = max(0, len(updated.get("questions", [])) - 1)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "question_index": question_index,
        "question": _public_question(question),
        "weak_concepts": combined_weak,
    }), 200


@ai_quiz_bp.route("/answer", methods=["POST"])
@authenticate_token
def submit_answer():
    """Evaluate an answer, return instant feedback, persist weak concept on miss."""
    payload = request.get_json(silent=True) or {}
    user_id = g.user.get("id")
    session_id = (payload.get("session_id") or "").strip()
    question_index = payload.get("question_index")
    user_answer = (payload.get("answer") or "").strip().upper()
    time_spent_ms = int(payload.get("time_spent_ms") or 0)

    if not session_id or question_index is None or not user_answer:
        return jsonify({
            "success": False,
            "message": "session_id, question_index and answer are required",
        }), 400

    try:
        question_index = int(question_index)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "question_index must be an integer"}), 400

    if user_answer.endswith(")"):
        user_answer = user_answer[:-1]
    # Accept values like "option b" or "B - ..."
    user_answer = user_answer[:1] if user_answer[:1] in {"A", "B", "C", "D"} else user_answer

    session = AIQuizSession.find(session_id, user_id=user_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404

    questions = session.get("questions") or []
    if not questions:
        return jsonify({
            "success": False,
            "message": "Quiz session has no questions. Please start a new quiz.",
        }), 400

    if not 0 <= question_index < len(questions):
        answered_indices = {
            int(a.get("questionIndex", -1)) for a in (session.get("answers") or [])
        }
        fallback = next(
            (idx for idx in range(len(questions)) if idx not in answered_indices),
            None,
        )
        if fallback is None:
            return jsonify({
                "success": False,
                "message": "All questions in this session are already answered.",
            }), 400
        logger.warning(
            "AI quiz answer index %s out of range (question_count=%s); using %s",
            question_index,
            len(questions),
            fallback,
        )
        question_index = fallback

    question = questions[question_index]
    correct_answer = str(question.get("correct_answer", "")).strip().upper()
    is_correct = user_answer == correct_answer
    options_map = question.get("options") or {}
    chosen_option_text = str(options_map.get(user_answer, "")).strip() if isinstance(options_map, dict) else ""
    correct_option_text = str(options_map.get(correct_answer, "")).strip() if isinstance(options_map, dict) else ""
    why_wrong_map = question.get("why_wrong") or {}
    selected_reason = str(why_wrong_map.get(user_answer, "")).strip() if isinstance(why_wrong_map, dict) else ""
    answer_reasoning = (
        question.get("why_correct")
        if is_correct
        else selected_reason
    ) or ""
    realtime_memory_tip = (
        f"Great choice: anchor on \"{correct_option_text}\" when you see this concept again."
        if is_correct and correct_option_text
        else (
            f"Next time compare your choice \"{chosen_option_text}\" against the key phrase \"{correct_option_text}\" before submitting."
            if chosen_option_text and correct_option_text
            else question.get("memory_tip")
        )
    )

    updated_session = AIQuizSession.record_answer(
        session_id=session_id,
        question_index=question_index,
        user_answer=user_answer,
        is_correct=is_correct,
        time_spent_ms=time_spent_ms,
    ) or session

    concept_summary = (question.get("concept_summary") or "").strip()
    topic = session.get("topic")
    difficulty = question.get("difficulty") or session.get("difficulty")

    if is_correct:
        WeakConcept.record_success(user_id=user_id, concept=concept_summary)
    elif concept_summary:
        WeakConcept.record_failure(
            user_id=user_id,
            concept=concept_summary,
            topic=topic,
            difficulty=difficulty,
            question=question.get("question"),
        )
        AIQuizSession.add_weak_concept(session_id, concept_summary)

    # Real-time write to the unified quiz_attempts collection so the user's
    # dashboard "Recent Quizzes" reflects progress without waiting for /finish.
    target_count = min(
        int(updated_session.get("targetQuestionCount") or AI_QUIZ_QUESTION_LIMIT),
        AI_QUIZ_QUESTION_LIMIT,
    )
    answers_map = {
        str(a.get("questionIndex")): str(a.get("userAnswer", "")).strip().upper()
        for a in (updated_session.get("answers") or [])
    }
    started_at = updated_session.get("createdAt") or datetime.utcnow()
    total_answered = int(updated_session.get("totalAnswered") or 0)
    limit_reached = total_answered >= target_count

    _upsert_unified_attempt(
        session_id=session_id,
        user_id=user_id,
        topic=topic,
        difficulty=_normalise_difficulty(updated_session.get("difficulty")),
        questions=updated_session.get("questions") or [],
        answers_map=answers_map,
        target_count=target_count,
        started_at=started_at,
        status="completed" if limit_reached else "in_progress",
        completed_at=datetime.utcnow() if limit_reached else None,
    )

    feedback = {
        "is_correct": is_correct,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "answer_reasoning": answer_reasoning,
        "why_correct": question.get("why_correct"),
        "why_wrong": question.get("why_wrong") or {},
        "reasoning": question.get("reasoning") or {},
        "concept_summary": concept_summary,
        "memory_tip": realtime_memory_tip,
        "topic": topic,
        "difficulty": difficulty,
    }

    return jsonify({
        "success": True,
        "session_id": session_id,
        "question_index": question_index,
        "feedback": feedback,
        "total_answered": total_answered,
        "target_question_count": target_count,
        "limit_reached": limit_reached,
    }), 200


@ai_quiz_bp.route("/finish", methods=["POST"])
@authenticate_token
def finish_session():
    """Mark a session complete and return the final summary."""
    payload = request.get_json(silent=True) or {}
    user_id = g.user.get("id")
    session_id = (payload.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"success": False, "message": "session_id is required"}), 400

    session = AIQuizSession.find(session_id, user_id=user_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404

    if session.get("status") == "active":
        session = AIQuizSession.finalize(session_id, status="completed") or session

    total = int(session.get("totalAnswered") or 0)
    correct = int(session.get("correctCount") or 0)
    score = round((correct / total) * 100, 2) if total > 0 else 0.0
    level = _normalise_difficulty(session.get("difficulty"))

    # Score-band based recommendation (used unless the user is on a losing streak).
    recommendation = _build_level_recommendation(score, level)
    recommended_level = recommendation["recommended"]

    failed_at_level = score < 50
    previous_fails = _consecutive_failures_same_level(user_id, level)
    easier_quiz_triggered = failed_at_level and previous_fails >= 1 and level != "basic"
    if easier_quiz_triggered:
        forced = _level_down(level)
        recommendation = {
            "recommended": forced,
            "from": level,
            "change": "demote" if forced != level else "repeat",
            "reason": (
                f"Score {score:.0f}% — second consecutive low score on **{level.title()}**. "
                f"We're stepping back to **{forced.title()}** to rebuild fundamentals before you try this level again."
            ),
            "score_band": "struggling",
            "score": score,
            "easier_triggered": True,
        }
        recommended_level = forced

    attempt_doc = {
        "userId": user_id,
        "sessionId": session_id,
        "topic": session.get("topic"),
        "level": level,
        "score": score,
        "correctCount": correct,
        "totalAnswered": total,
        "weakConcepts": session.get("weakConcepts", []),
        "recommendedNextLevel": recommended_level,
        "failedAtLevel": failed_at_level,
        "easierQuizTriggered": easier_quiz_triggered,
        "completedAt": datetime.utcnow(),
    }

    # Idempotent finish: a second /finish call for the same session must not
    # create a duplicate aggregate row (Requirement C6).
    attempts = _attempts_collection()
    try:
        attempts.create_index("sessionId", unique=True, background=True)
    except Exception:  # noqa: BLE001
        pass

    result = attempts.update_one(
        {"sessionId": session_id},
        {"$set": attempt_doc, "$setOnInsert": {"firstFinishedAt": datetime.utcnow()}},
        upsert=True,
    )
    if result.upserted_id is not None:
        attempt_id = str(result.upserted_id)
    else:
        existing = attempts.find_one({"sessionId": session_id}, {"_id": 1})
        attempt_id = str(existing["_id"]) if existing else session_id

    # Mirror the final state into the unified quiz_attempts collection so the
    # dashboard's quiz history shows AI sessions alongside legacy attempts.
    target_count = min(
        int(session.get("targetQuestionCount") or AI_QUIZ_QUESTION_LIMIT),
        AI_QUIZ_QUESTION_LIMIT,
    )
    answers_map = {
        str(a.get("questionIndex")): str(a.get("userAnswer", "")).strip().upper()
        for a in (session.get("answers") or [])
    }
    unified_attempt_id = _upsert_unified_attempt(
        session_id=session_id,
        user_id=user_id,
        topic=session.get("topic"),
        difficulty=level,
        questions=session.get("questions") or [],
        answers_map=answers_map,
        target_count=target_count,
        started_at=session.get("createdAt") or datetime.utcnow(),
        status="completed",
        completed_at=datetime.utcnow(),
    )

    return jsonify({
        "success": True,
        "session": AIQuizSession.to_response(session, include_answers=True),
        "attempt_id": unified_attempt_id,
        "ai_attempt_id": attempt_id,
        "score": score,
        "recommended_next_level": recommended_level,
        "level_recommendation": recommendation,
        "easier_quiz_triggered": easier_quiz_triggered,
        "idempotent": result.upserted_id is None,
        "remediation": _safe_remediation_hook(user_id, unified_attempt_id, score=score),
    }), 200


def _safe_remediation_hook(user_id: str, attempt_id: str, *, score: float | None = None) -> dict:
    try:
        from services.remediation_service import process_attempt_after_scoring
        return process_attempt_after_scoring(user_id, str(attempt_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Remediation hook failed for AI quiz user %s: %s", user_id, exc)
        try:
            from services.remediation_service import PASSING_SCORE, is_passing
            if score is not None and not is_passing(score):
                return {
                    "passed": False,
                    "passingScore": PASSING_SCORE,
                    "needsRemediation": True,
                    "canContinue": False,
                    "score": score,
                    "attemptId": str(attempt_id),
                }
        except Exception:  # noqa: BLE001
            pass
        return {
            "passed": True,
            "passingScore": 70,
            "needsRemediation": False,
            "canContinue": True,
        }


@ai_quiz_bp.route("/session/<session_id>", methods=["GET"])
@authenticate_token
def get_session(session_id: str):
    user_id = g.user.get("id")
    session = AIQuizSession.find(session_id, user_id=user_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404
    return jsonify({
        "success": True,
        "session": AIQuizSession.to_response(session, include_answers=True),
    }), 200


@ai_quiz_bp.route("/weak-concepts", methods=["GET"])
@authenticate_token
def list_weak_concepts():
    user_id = g.user.get("id")
    include_mastered = request.args.get("include_mastered", "false").lower() == "true"
    limit = max(1, min(int(request.args.get("limit", 50) or 50), 200))
    concepts = WeakConcept.list_for_user(
        user_id=user_id,
        include_mastered=include_mastered,
        limit=limit,
    )
    return jsonify({"success": True, "weak_concepts": concepts}), 200


@ai_quiz_bp.route("/dashboard", methods=["GET"])
@authenticate_token
def dashboard():
    user_id = g.user.get("id")
    limit = max(1, min(int(request.args.get("limit", 20) or 20), 100))
    return jsonify({
        "success": True,
        "dashboard": _build_dashboard(user_id, limit=limit),
    }), 200


__all__ = ["ai_quiz_bp"]
