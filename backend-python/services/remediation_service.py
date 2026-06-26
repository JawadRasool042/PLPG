"""Remediation workflow: failing score → lesson → retake → pass to continue."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from models.ai_quiz_session import AIQuizSession
from models.quiz import Quiz
from models.quiz_attempt import QuizAttempt
from models.remediation_lesson import RemediationLesson
from services.remediation_lesson_generator import (
    RemediationLessonGeneratorError,
    build_fallback_lesson,
    build_quiz_review_items,
    generate_remediation_lesson,
    _is_short_explanation,
    _normalize_topic_for_dedup,
    LESSON_FORMAT_VERSION as GENERATOR_LESSON_VERSION,
)

logger = logging.getLogger(__name__)

PASSING_SCORE = float(os.getenv("QUIZ_PASSING_SCORE", "70"))
LESSON_FORMAT_VERSION = GENERATOR_LESSON_VERSION


def _lesson_needs_regeneration(lesson_content: Dict[str, Any]) -> bool:
    if not lesson_content:
        return True
    if lesson_content.get("lesson_format_version", 0) < LESSON_FORMAT_VERSION:
        return True
    sections = lesson_content.get("question_sections")
    if not isinstance(sections, list) or not sections:
        return True
    if lesson_content.get("mistake_review") or lesson_content.get("struggling_concepts"):
        return True

    topics_seen: set[str] = set()
    for section in sections:
        if not isinstance(section, dict):
            return True
        if section.get("why_your_answer_was_wrong") or section.get("why_yours_was_wrong"):
            return True
        topic = str(section.get("topic") or "").strip()
        q_idx = int(section.get("question_index", 0))
        if not topic or re.match(r"^question\s*\d+", topic, re.I) or re.match(r"^topic\s*\d+", topic, re.I):
            return True
        topic_key = _normalize_topic_for_dedup(topic, "")
        if topic_key in topics_seen:
            return True
        topics_seen.add(topic_key)
        explanation = str(section.get("explanation") or "").strip()
        if _is_short_explanation(explanation):
            return True
    return False


def _status_from_lesson_doc(
    attempt_id: str,
    attempt: Dict[str, Any],
    lesson_doc: Dict[str, Any],
) -> Dict[str, Any]:
    score = float(attempt.get("score") or lesson_doc.get("score") or 0)
    return {
        "passed": False,
        "passingScore": PASSING_SCORE,
        "needsRemediation": True,
        "canContinue": False,
        "score": score,
        "attemptId": attempt_id,
        "lessonId": str(lesson_doc["_id"]),
        "retakeQuizId": lesson_doc.get("retakeQuizId"),
        "lessonStatus": lesson_doc.get("status"),
        "lesson": RemediationLesson.to_response(lesson_doc),
    }


def is_passing(score: float) -> bool:
    return float(score) >= PASSING_SCORE


def _load_attempt(attempt_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    coll = QuizAttempt.get_collection()
    uid = str(user_id)
    queries: List[Dict[str, Any]] = []
    try:
        queries.append({"_id": ObjectId(attempt_id), "userId": uid})
    except Exception:
        pass
    queries.append({"_id": attempt_id, "userId": uid})

    for query in queries:
        attempt = coll.find_one(query)
        if attempt and str(attempt.get("userId")) == uid:
            return attempt
    return None


def _load_ai_session(attempt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session_id = attempt.get("sessionId") or attempt.get("quizId")
    user_id = attempt.get("userId")
    if not session_id or not user_id:
        return None
    return AIQuizSession.find(str(session_id), user_id=user_id)


def _format_questions_for_retake_quiz(
    attempt: Dict[str, Any],
    ai_session: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    session_questions = (ai_session or {}).get("questions") or []
    if session_questions:
        formatted: List[Dict[str, Any]] = []
        for q in session_questions:
            options = q.get("options")
            if isinstance(options, dict):
                options_list = [f"{k}) {options.get(k, '')}" for k in ("A", "B", "C", "D")]
            elif isinstance(options, list):
                options_list = list(options)
            else:
                options_list = []
            formatted.append(
                {
                    "q": q.get("question"),
                    "options": options_list,
                    "answer": str(q.get("correct_answer", "")).strip().upper(),
                    "explanation": q.get("why_correct") or (q.get("reasoning") or {}).get("why_correct", ""),
                    "concept_tag": q.get("concept_summary") or "",
                }
            )
        return formatted

    quiz = Quiz.find_by_id(str(attempt.get("quizId") or ""))
    if quiz and quiz.get("questions"):
        return list(quiz["questions"])

    formatted = []
    for row in attempt.get("results") or []:
        if not isinstance(row, dict):
            continue
        formatted.append(
            {
                "q": row.get("question"),
                "options": row.get("options") or [],
                "answer": row.get("correctAnswer"),
                "explanation": row.get("explanation") or "",
                "concept_tag": "",
            }
        )
    return formatted


def ensure_retake_quiz(attempt: Dict[str, Any], ai_session: Optional[Dict[str, Any]] = None) -> str:
    attempt_id = str(attempt["_id"])
    coll = Quiz.get_collection()
    existing = coll.find_one({"sourceAttemptId": attempt_id})
    if existing:
        return str(existing["_id"])

    questions = _format_questions_for_retake_quiz(attempt, ai_session)
    if not questions:
        raise ValueError("Cannot build retake quiz — no questions found on attempt")

    doc = {
        "interest": attempt.get("interest") or "General",
        "level": attempt.get("level") or "Beginner",
        "questions": questions,
        "totalQuestions": len(questions),
        "createdAt": datetime.utcnow(),
        "source": "remediation_retake",
        "sourceAttemptId": attempt_id,
        "isRetakeFrozen": True,
    }
    result = coll.insert_one(doc)
    return str(result.inserted_id)


def persist_attempt_snapshot(
    user_id: str,
    snapshot: Dict[str, Any],
    *,
    attempt_id: Optional[str] = None,
    quiz_type: str = "mixed",
) -> str:
    coll = QuizAttempt.get_collection()
    mongo_id: Any = None
    if attempt_id:
        try:
            mongo_id = ObjectId(attempt_id)
        except Exception:
            mongo_id = None
    if mongo_id is None:
        mongo_id = ObjectId()

    results = list(snapshot.get("results") or [])
    score = float(snapshot.get("score") or 0)
    doc = {
        "userId": user_id,
        "quizId": str(snapshot.get("quizId") or snapshot.get("quiz_id") or mongo_id),
        "quizType": snapshot.get("quizType") or quiz_type,
        "interest": snapshot.get("interest") or "General",
        "level": snapshot.get("level") or "Beginner",
        "score": score,
        "correctCount": sum(
            1 for r in results if isinstance(r, dict) and r.get("isCorrect")
        ),
        "totalQuestions": len(results) or int(snapshot.get("totalQuestions") or 0),
        "results": results,
        "completedAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }
    coll.update_one(
        {"_id": mongo_id},
        {"$set": doc, "$setOnInsert": {"createdAt": datetime.utcnow()}},
        upsert=True,
    )
    return str(mongo_id)


def _generate_lesson_for_attempt(
    attempt: Dict[str, Any],
    ai_session: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    interest = attempt.get("interest") or "General"
    level = attempt.get("level") or "Beginner"
    score = float(attempt.get("score") or 0)
    review_items = build_quiz_review_items(attempt, ai_session=ai_session)

    try:
        return generate_remediation_lesson(
            interest=interest,
            level=level,
            score=score,
            review_items=review_items,
        )
    except RemediationLessonGeneratorError as exc:
        logger.exception("Remediation lesson generation failed: %s", exc)
        lesson = build_fallback_lesson(review_items, interest=interest, level=level)
        lesson["generation_error"] = str(exc)
        return lesson


def process_attempt_after_scoring(user_id: str, attempt_id: str) -> Dict[str, Any]:
    attempt = _load_attempt(attempt_id, user_id)
    if not attempt:
        logger.warning(
            "Remediation: attempt %s not found for user %s",
            attempt_id,
            user_id,
        )
        return {
            "passed": False,
            "passingScore": PASSING_SCORE,
            "needsRemediation": True,
            "canContinue": False,
            "attemptId": attempt_id,
        }

    score = float(attempt.get("score") or 0)
    quiz_id = str(attempt.get("quizId") or "")
    interest = attempt.get("interest") or "General"
    level = attempt.get("level") or "Beginner"

    retake_source = Quiz.find_by_id(quiz_id) if quiz_id else None
    is_retake_quiz = bool(retake_source and retake_source.get("isRetakeFrozen"))

    if is_retake_quiz and is_passing(score):
        RemediationLesson.mark_passed_for_retake_quiz(user_id, quiz_id, attempt_id)
        return {
            "passed": True,
            "passingScore": PASSING_SCORE,
            "needsRemediation": False,
            "canContinue": True,
            "score": score,
            "attemptId": attempt_id,
        }

    if is_passing(score):
        return {
            "passed": True,
            "passingScore": PASSING_SCORE,
            "needsRemediation": False,
            "canContinue": True,
            "score": score,
            "attemptId": attempt_id,
        }

    ai_session = _load_ai_session(attempt) if attempt.get("quizType") == "ai" else None
    lesson = _generate_lesson_for_attempt(attempt, ai_session)

    try:
        retake_quiz_id = quiz_id if is_retake_quiz else ensure_retake_quiz(attempt, ai_session)
    except Exception as exc:
        logger.warning("Could not create retake quiz: %s", exc)
        retake_quiz_id = quiz_id

    doc = RemediationLesson.upsert_for_attempt(
        user_id,
        attempt_id,
        quiz_id=quiz_id,
        interest=interest,
        level=level,
        score=score,
        passed=False,
        lesson=lesson,
        retake_quiz_id=retake_quiz_id,
    )
    RemediationLesson.supersede_stale_locks(user_id, keep_attempt_id=attempt_id)

    return {
        "passed": False,
        "passingScore": PASSING_SCORE,
        "needsRemediation": True,
        "canContinue": False,
        "score": score,
        "attemptId": attempt_id,
        "lessonId": str(doc["_id"]),
        "retakeQuizId": retake_quiz_id,
        "lessonStatus": doc.get("status"),
        "lesson": RemediationLesson.to_response(doc),
    }


def build_status_payload(user_id: str, attempt_id: str) -> Dict[str, Any]:
    attempt = _load_attempt(attempt_id, user_id)
    if not attempt:
        return {"passed": True, "needsRemediation": False, "canContinue": True}

    score = float(attempt.get("score") or 0)
    if is_passing(score):
        lock = RemediationLesson.active_lock_for_user(user_id)
        can_continue = lock is None
        return {
            "passed": True,
            "passingScore": PASSING_SCORE,
            "needsRemediation": False,
            "canContinue": can_continue,
            "score": score,
            "attemptId": attempt_id,
            "activeLock": RemediationLesson.to_response(lock) if lock else None,
        }

    lesson_doc = RemediationLesson.find_by_attempt(user_id, attempt_id)
    if not lesson_doc:
        return process_attempt_after_scoring(user_id, attempt_id)

    lesson_content = lesson_doc.get("lesson") or {}
    if _lesson_needs_regeneration(lesson_content):
        return process_attempt_after_scoring(user_id, attempt_id)

    return _status_from_lesson_doc(attempt_id, attempt, lesson_doc)


def get_or_create_lesson(user_id: str, attempt_id: str) -> Dict[str, Any]:
    return build_status_payload(user_id, attempt_id)


def mark_lesson_studied(user_id: str, lesson_id: str) -> bool:
    return RemediationLesson.mark_studied(lesson_id, user_id)


def user_can_continue(user_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    lock = RemediationLesson.active_lock_for_user(user_id)
    if lock and not lock.get("passed"):
        return False, RemediationLesson.to_response(lock)
    return True, None


def can_retake_quiz(user_id: str, retake_quiz_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    lock = RemediationLesson.find_lock_for_retake_quiz(user_id, retake_quiz_id)
    if not lock:
        return True, None, ""
    if lock.get("status") != "studied":
        return False, RemediationLesson.to_response(lock), (
            "Complete the remediation lesson before retaking this quiz."
        )
    return True, RemediationLesson.to_response(lock), ""


def assert_user_can_continue(user_id: str) -> Optional[Dict[str, Any]]:
    can_continue, lock = user_can_continue(user_id)
    if can_continue:
        return None
    return {
        "success": False,
        "message": "Complete remediation before continuing your learning path.",
        "code": "REMEDIATION_REQUIRED",
        "canContinue": False,
        "activeLock": lock,
        "passingScore": PASSING_SCORE,
    }
