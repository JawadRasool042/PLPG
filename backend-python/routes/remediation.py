"""Remediation lesson API — quiz-scoped study guides and retake gating."""

from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request

from middleware.auth import authenticate_token, get_current_user_id
from services import remediation_service

logger = logging.getLogger(__name__)

remediation_bp = Blueprint("remediation", __name__)


def _user_id() -> str:
    uid = get_current_user_id()
    if not uid and isinstance(g.user, dict):
        uid = str(g.user.get("id") or "")
    return str(uid or "")


@remediation_bp.route("/status/<attempt_id>", methods=["GET"])
@authenticate_token
def remediation_status(attempt_id: str):
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    payload = remediation_service.build_status_payload(user_id, attempt_id)
    return jsonify({"success": True, **payload}), 200


@remediation_bp.route("/lesson/<attempt_id>", methods=["GET"])
@authenticate_token
def remediation_lesson(attempt_id: str):
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    payload = remediation_service.get_or_create_lesson(user_id, attempt_id)
    return jsonify({"success": True, **payload}), 200


@remediation_bp.route("/lesson/<lesson_id>/complete", methods=["POST"])
@authenticate_token
def remediation_lesson_complete(lesson_id: str):
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    ok = remediation_service.mark_lesson_studied(user_id, lesson_id)
    if not ok:
        return jsonify({"success": False, "message": "Lesson not found"}), 404
    return jsonify({"success": True, "message": "Lesson marked as studied"}), 200


@remediation_bp.route("/can-continue", methods=["GET"])
@authenticate_token
def remediation_can_continue():
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    can_continue, lock = remediation_service.user_can_continue(user_id)
    return jsonify(
        {
            "success": True,
            "canContinue": can_continue,
            "activeLock": lock,
            "passingScore": remediation_service.PASSING_SCORE,
        }
    ), 200


@remediation_bp.route("/can-retake/<retake_quiz_id>", methods=["GET"])
@authenticate_token
def remediation_can_retake(retake_quiz_id: str):
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    allowed, lock, message = remediation_service.can_retake_quiz(user_id, retake_quiz_id)
    return jsonify(
        {
            "success": True,
            "canRetake": allowed,
            "message": message,
            "activeLock": lock,
            "passingScore": remediation_service.PASSING_SCORE,
        }
    ), 200


@remediation_bp.route("/process", methods=["POST"])
@authenticate_token
def remediation_process():
    """Process an attempt snapshot (e.g. mixed quiz) and return remediation status."""
    user_id = _user_id()
    if not user_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    attempt_id = str(body.get("attempt_id") or body.get("attemptId") or "").strip()
    snapshot = body.get("attempt_snapshot") or body.get("attemptSnapshot")

    if snapshot and not attempt_id:
        attempt_id = str(snapshot.get("id") or snapshot.get("attempt_id") or "snapshot")

    if snapshot:
        from services.remediation_service import persist_attempt_snapshot

        attempt_id = persist_attempt_snapshot(user_id, snapshot, attempt_id=attempt_id or None)

    if not attempt_id:
        return jsonify({"success": False, "message": "attempt_id is required"}), 400

    payload = remediation_service.process_attempt_after_scoring(user_id, attempt_id)
    return jsonify({"success": True, **payload}), 200
