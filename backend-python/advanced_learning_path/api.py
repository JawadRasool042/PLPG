"""Flask blueprint for the advanced learning intelligence API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple
from flask import Blueprint, jsonify, request

from .engine import AdvancedLearningPathEngine, build_response_payload
from .quiz_caliber import load_user_quiz_caliber, recommended_difficulty_from_scores
from .storage import LearningPathRepository
from services.quiz_generator.mixed_quiz_generator import generate_mixed_quiz
from middleware.auth import get_current_user_id
from utils.api_response import error_response, ok_response

logger = logging.getLogger(__name__)

bp = Blueprint("learning_intelligence_api", __name__)

_ALIAS_PREFIX = "/advanced"


def _engine() -> AdvancedLearningPathEngine:
    # Stateless engine; repository handles persistence.
    return AdvancedLearningPathEngine()


def _to_contract_response(pred: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert engine payload into the contract requested by the product spec.
    Keeps extra fields for backward-compatibility, but guarantees:
      - user_profile: { type, confidence }
      - prediction: { primary_domain, secondary_domains, confidence_scores }
    """
    top_domains = pred.get("top_domains") or pred.get("top_3_interests") or []
    primary = pred.get("primary_interest") or pred.get("predicted_interest")
    secondary = [d.get("domain") for d in top_domains[1:3] if isinstance(d, dict) and d.get("domain")]

    # Profile confidence is derived from top confidence if engine doesn't provide a structured one.
    profile_type = pred.get("user_profile") or "Explorer"
    profile_conf = 0.0
    try:
        profile_conf = float(pred.get("profile_confidence") or pred.get("confidence") or 0.0)
    except (TypeError, ValueError):
        profile_conf = 0.0

    return {
        "user_profile": {"type": profile_type, "confidence": round(min(1.0, max(0.0, profile_conf)), 4)},
        "prediction": {
            "primary_domain": primary,
            "secondary_domains": secondary,
            "confidence_scores": pred.get("all_probabilities") or pred.get("confidence_scores") or {},
            "explanation": (top_domains[0].get("why_matched") if top_domains and isinstance(top_domains[0], dict) else pred.get("signals")),
        },
        # Convenience fields your frontend already expects.
        "primary_interest": primary,
        "predicted_interest": primary,
        "top_domains": top_domains,
        "confidence": pred.get("confidence"),
        "model_confidence": pred.get("model_confidence"),
        # Roadmap/other intelligence (may be present from engine).
        "roadmap": pred.get("roadmap"),
        "career_paths": pred.get("career_paths"),
        "skills_gap": pred.get("skills_gap"),
        "projects": pred.get("projects"),
        "certifications": pred.get("certifications"),
        "gamification": pred.get("gamification"),
        "visual_analytics": pred.get("visual_analytics"),
        "metadata": pred.get("metadata"),
    }


def _score_open_answer(expected_keywords: List[str], user_answer: str) -> Tuple[float, List[str]]:
    if not expected_keywords:
        return 0.0, []
    answer = (user_answer or "").lower()
    hits = []
    for kw in expected_keywords:
        k = str(kw or "").strip().lower()
        if k and k in answer:
            hits.append(k)
    return (len(hits) / max(1, len(expected_keywords))), hits


def _grade_mixed_quiz(quiz: Dict[str, Any], answers: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Returns (score_percent, per_question_results).
    Scoring:
      - mcq / true_false: exact match
      - short_answer / scenario: keyword hit ratio
    """
    questions = (quiz or {}).get("quiz") or []
    results: List[Dict[str, Any]] = []
    total = len(questions) if isinstance(questions, list) else 0
    if total == 0:
        return 0.0, []

    points = 0.0
    for q in questions:
        qid = q.get("id")
        key = str(qid) if qid is not None else None
        user_answer = answers.get(key) if key else None
        q_type = q.get("type")
        correct = q.get("correct_answer")

        is_correct = False
        detail: Dict[str, Any] = {"id": qid, "type": q_type, "user_answer": user_answer}

        if q_type in {"mcq", "true_false"}:
            is_correct = str(user_answer).strip().lower() == str(correct).strip().lower()
            points += 1.0 if is_correct else 0.0
        elif q_type in {"short_answer", "scenario"}:
            ratio, hits = _score_open_answer(q.get("expected_keywords") or [], str(user_answer or ""))
            # Award partial credit; require >=50% to count as "correct" for UI.
            points += ratio
            is_correct = ratio >= 0.5
            detail["keyword_hits"] = hits
            detail["keyword_ratio"] = round(ratio, 4)
        else:
            # Unknown type; no points.
            pass

        detail["correct_answer"] = correct
        detail["is_correct"] = bool(is_correct)
        detail["explanation"] = q.get("explanation")
        detail["sub_topic"] = q.get("sub_topic")
        results.append(detail)

    score_percent = round((points / total) * 100.0, 2)
    return score_percent, results


def _graded_results_for_mongo(
    quiz: Dict[str, Any], graded: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Map mixed-quiz grading output to unified quiz_attempts.results shape."""
    questions = (quiz or {}).get("quiz") or []
    by_id = {str(q.get("id")): q for q in questions if isinstance(q, dict)}
    mongo_results: List[Dict[str, Any]] = []
    for idx, row in enumerate(graded):
        q = by_id.get(str(row.get("id")), questions[idx] if idx < len(questions) else {})
        options = q.get("options") or []
        if isinstance(options, dict):
            options = [f"{k}) {options.get(k, '')}" for k in options]
        mongo_results.append(
            {
                "questionIndex": idx,
                "question": q.get("q") or q.get("question") or "",
                "options": list(options) if isinstance(options, list) else [],
                "userAnswer": str(row.get("user_answer") or ""),
                "correctAnswer": str(row.get("correct_answer") or ""),
                "isCorrect": bool(row.get("is_correct")),
                "explanation": str(row.get("explanation") or q.get("explanation") or ""),
            }
        )
    return mongo_results


@bp.post("/predict-interest")
def predict_interest_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        include_roadmap = bool(payload.get("include_roadmap"))
        if include_roadmap:
            raw = _engine().predict_interest(payload)
        else:
            raw = _engine().score_interests_only(payload)
        result = _to_contract_response(raw)
        return ok_response(200, **result)
    except Exception as exc:
        logger.exception("predict-interest failed: %s", exc)
        msg = str(exc) or "Failed to predict interest"
        status = 502 if "openai" in msg.lower() or "OpenAI" in msg else 500
        return error_response(msg, code="PREDICT_INTEREST_FAILED", status_code=status)


def _inject_quiz_caliber(payload: Dict[str, Any], domain: str) -> Dict[str, Any]:
    """Attach live quiz performance so roadmap + quiz difficulty match student caliber."""
    merged = dict(payload)
    user_id = payload.get("user_id") or get_current_user_id()
    if user_id:
        merged["user_id"] = user_id
    caliber = payload.get("quiz_caliber")
    if not isinstance(caliber, dict) or not caliber:
        caliber = load_user_quiz_caliber(user_id, domain)
    merged["quiz_caliber"] = caliber
    merged["recommended_quiz_difficulty"] = caliber.get("recommended_quiz_difficulty")
    merged["quiz_accuracy"] = caliber.get("mastery_level")
    merged["mastery_level"] = caliber.get("mastery_level")
    return merged


@bp.post("/generate-roadmap")
def generate_roadmap_endpoint():
    payload = request.get_json(silent=True) or {}
    domain = payload.get("domain") or payload.get("primary_interest")
    if not domain:
        return error_response("domain is required", code="VALIDATION_ERROR", status_code=400)
    try:
        payload = _inject_quiz_caliber(payload, domain)
        raw = _engine().generate_roadmap(domain, payload)
        return ok_response(200, **raw)
    except Exception as exc:
        logger.exception("generate-roadmap failed: %s", exc)
        msg = str(exc) or "Failed to generate roadmap"
        status = 502 if "openai" in msg.lower() else 500
        return error_response(msg, code="ROADMAP_FAILED", status_code=status)


@bp.post("/get-user-profile")
def get_user_profile_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        result = _engine().get_user_profile(payload)
        return ok_response(200, **result)
    except Exception as exc:
        logger.exception("get-user-profile failed: %s", exc)
        return error_response("Failed to get user profile", code="USER_PROFILE_FAILED", status_code=400)


@bp.post("/get-recommendations")
def get_recommendations_endpoint():
    payload = request.get_json(silent=True) or {}
    try:
        result = _engine().get_recommendations(payload)
        return ok_response(200, **result)
    except Exception as exc:
        logger.exception("get-recommendations failed: %s", exc)
        return error_response("Failed to get recommendations", code="RECOMMENDATIONS_FAILED", status_code=400)


@bp.post("/save-progress")
def save_progress_endpoint():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or get_current_user_id()
    if user_id:
        try:
            from services.remediation_service import assert_user_can_continue

            blocked = assert_user_can_continue(str(user_id))
            if blocked:
                return jsonify(blocked), 403
        except Exception as exc:
            logger.warning("Remediation gate check failed on save-progress: %s", exc)
    try:
        result = _engine().save_progress(payload)
        return jsonify(result), 200
    except Exception as exc:
        logger.exception("save-progress failed: %s", exc)
        return error_response("Failed to save progress", code="SAVE_PROGRESS_FAILED", status_code=400)


def _resolve_quiz_difficulty(payload: dict) -> str:
    raw = (payload.get("difficulty") or payload.get("level") or "").lower()
    if raw in {"beginner", "intermediate", "advanced"}:
        return raw

    caliber = payload.get("quiz_caliber") or {}
    if isinstance(caliber, dict) and caliber.get("recommended_quiz_difficulty"):
        return str(caliber["recommended_quiz_difficulty"])

    if payload.get("recommended_quiz_difficulty"):
        return str(payload["recommended_quiz_difficulty"])

    recent = caliber.get("recent_scores") if isinstance(caliber, dict) else []
    avg = float(caliber.get("average_score") or 0) if isinstance(caliber, dict) else 0.0
    if recent or avg:
        return recommended_difficulty_from_scores(avg, list(recent or []))

    profile = str(payload.get("user_profile") or payload.get("profile") or "").lower()
    if "advanced" in profile:
        return "advanced"
    if "beginner" in profile or "explorer" in profile:
        return "beginner"
    return "intermediate"


@bp.post("/generate-quiz")
def generate_quiz_endpoint():
    payload = request.get_json(silent=True) or {}
    domain = payload.get("domain") or payload.get("primary_domain") or payload.get("primary_interest")
    if not domain:
        return error_response("domain is required", code="VALIDATION_ERROR", status_code=400)

    question_count = int(payload.get("question_count", 10))
    payload = _inject_quiz_caliber(payload, domain)
    difficulty = _resolve_quiz_difficulty(payload)
    user_profile = payload.get("user") or payload.get("user_profile") or {}
    if isinstance(user_profile, dict):
        user_profile = {
            **user_profile,
            "quiz_caliber": payload.get("quiz_caliber"),
            "recommended_quiz_difficulty": difficulty,
        }

    try:
        quiz_payload = generate_mixed_quiz(
            topic=domain,
            difficulty=difficulty,
            question_count=question_count,
            user_profile=user_profile,
            weak_areas=payload.get("weak_areas") or payload.get("skills_gap") or [],
            secondary_interests=payload.get("secondary_interests") or [],
        )

        repo = LearningPathRepository()
        user_id = payload.get("user_id") or payload.get("email") or get_current_user_id()
        quiz_id = None
        if user_id:
            quiz_id = repo.save_quiz(user_id, domain, quiz_payload)

        return ok_response(
            200,
            quiz_id=quiz_id,
            user_id=user_id,
            domain=domain,
            difficulty=difficulty,
            question_count=question_count,
            **quiz_payload,
        )
    except Exception as exc:
        logger.exception("generate-quiz failed: %s", exc)
        return error_response("Failed to generate quiz", code="GENERATE_QUIZ_FAILED", status_code=400)


@bp.post("/submit-quiz")
def submit_quiz_endpoint():
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or payload.get("email") or get_current_user_id()
    if not user_id:
        return error_response("user_id (or email) is required", code="VALIDATION_ERROR", status_code=400)

    quiz_id = payload.get("quiz_id")
    domain = payload.get("domain") or payload.get("primary_interest")
    answers = payload.get("answers") or {}
    if not quiz_id:
        return error_response("quiz_id is required", code="VALIDATION_ERROR", status_code=400)
    if not isinstance(answers, dict):
        return error_response("answers must be an object", code="VALIDATION_ERROR", status_code=400)

    repo = LearningPathRepository()
    latest = repo.get_latest_quiz(user_id)
    quiz_payload = None
    if latest and str(latest.get("quiz_id")) == str(quiz_id):
        quiz_payload = latest.get("quiz")

    if not quiz_payload:
        return error_response("Quiz not found for this user", code="QUIZ_NOT_FOUND", status_code=404)

    score, results = _grade_mixed_quiz(quiz_payload, {str(k): v for k, v in answers.items()})
    attempt_id = repo.save_quiz_attempt(user_id, int(quiz_id), domain or latest.get("domain") or "", answers, score, {"results": results})

    difficulty = payload.get("difficulty") or latest.get("difficulty") or "intermediate"
    level_label = str(difficulty).strip().capitalize() if difficulty else "Beginner"
    mongo_results = _graded_results_for_mongo(quiz_payload, results)
    remediation_payload: Dict[str, Any] = {}
    mongo_attempt_id = str(attempt_id)
    try:
        from services.remediation_service import persist_attempt_snapshot, process_attempt_after_scoring

        mongo_attempt_id = persist_attempt_snapshot(
            user_id,
            {
                "quizId": str(quiz_id),
                "interest": domain or latest.get("domain") or "General",
                "level": level_label,
                "score": score,
                "results": mongo_results,
                "totalQuestions": len(mongo_results),
            },
        )
        remediation_payload = process_attempt_after_scoring(user_id, mongo_attempt_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Mixed quiz remediation hook failed for user %s: %s", user_id, exc)

    return ok_response(
        200,
        attempt={
            "attempt_id": mongo_attempt_id,
            "sqlite_attempt_id": attempt_id,
            "quiz_id": quiz_id,
            "user_id": user_id,
            "domain": domain or latest.get("domain"),
            "difficulty": difficulty,
            "score": score,
            "results": results,
        },
        remediation=remediation_payload,
    )


@bp.get("/user-profile/<user_id>")
def get_user_profile_by_id(user_id: str):
    try:
        repo = LearningPathRepository()
        profile = repo.get_user_profile(user_id)
        if not profile:
            return error_response("User profile not found", code="NOT_FOUND", status_code=404)
        return ok_response(200, **profile)
    except Exception as exc:
        logger.exception("user-profile fetch failed: %s", exc)
        return error_response("Failed to load user profile", code="USER_PROFILE_FETCH_FAILED", status_code=400)


@bp.get("/latest-progress/<user_id>")
def latest_progress(user_id: str):
    try:
        repo = LearningPathRepository()
        progress = repo.get_latest_progress(user_id)
        return ok_response(200, progress=progress)
    except Exception as exc:
        logger.exception("latest-progress failed: %s", exc)
        return error_response("Failed to load latest progress", code="LATEST_PROGRESS_FAILED", status_code=400)


@bp.get("/latest-roadmap/<user_id>")
def latest_roadmap(user_id: str):
    try:
        repo = LearningPathRepository()
        roadmap = repo.get_latest_roadmap(user_id)
        return ok_response(200, roadmap=roadmap)
    except Exception as exc:
        logger.exception("latest-roadmap failed: %s", exc)
        return error_response("Failed to load latest roadmap", code="LATEST_ROADMAP_FAILED", status_code=400)


@bp.get("/latest-quiz/<user_id>")
def latest_quiz(user_id: str):
    try:
        repo = LearningPathRepository()
        quiz = repo.get_latest_quiz(user_id)
        return ok_response(200, quiz=quiz)
    except Exception as exc:
        logger.exception("latest-quiz failed: %s", exc)
        return error_response("Failed to load latest quiz", code="LATEST_QUIZ_FAILED", status_code=400)


# ---------------------------------------------------------------------------
# Compatibility aliases (older frontend services call /advanced/*)
# ---------------------------------------------------------------------------


@bp.post(f"{_ALIAS_PREFIX}/generate-quiz")
def generate_quiz_alias():
    return generate_quiz_endpoint()


@bp.post(f"{_ALIAS_PREFIX}/submit-quiz")
def submit_quiz_alias():
    return submit_quiz_endpoint()


@bp.get(f"{_ALIAS_PREFIX}/user-profile/<user_id>")
def user_profile_alias(user_id: str):
    return get_user_profile_by_id(user_id)


@bp.get(f"{_ALIAS_PREFIX}/latest-progress/<user_id>")
def latest_progress_alias(user_id: str):
    return latest_progress(user_id)


@bp.get(f"{_ALIAS_PREFIX}/latest-roadmap/<user_id>")
def latest_roadmap_alias(user_id: str):
    return latest_roadmap(user_id)


@bp.get(f"{_ALIAS_PREFIX}/latest-quiz/<user_id>")
def latest_quiz_alias(user_id: str):
    return latest_quiz(user_id)


@bp.get("/learning-intelligence/health")
def health_endpoint():
    return jsonify(
        {
            "success": True,
            "status": "healthy",
            "system": "Advanced Personalized Learning Path & Interest Intelligence",
            "version": "3.0",
            "capabilities": [
                "Hybrid scoring",
                "Smart user profiling",
                "OpenAI roadmap generation",
                "Quiz-caliber adaptive difficulty",
                "Career intelligence",
                "Gamification",
                "SQLite/PostgreSQL-ready storage",
            ],
        }
    ), 200
