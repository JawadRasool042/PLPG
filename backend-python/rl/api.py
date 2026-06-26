"""
Flask blueprint exposing the RL system over HTTP.

Endpoints (mounted at ``/api/rl/*`` from :mod:`app`):

    POST  /api/rl/next-action      – pick the next adaptive action
    POST  /api/rl/update-reward    – record a transition + update Q-table
    GET   /api/rl/policy/<user_id> – inspect the policy + recent activity
    POST  /api/rl/train            – run replay or simulator training
    GET   /api/rl/history/<user_id>– transitions / actions audit trail
    POST  /api/rl/explain          – preview what an action would do
    GET   /api/rl/health           – module health probe

Authentication (Requirement C8)
-------------------------------
All user-scoped endpoints require an ``Authorization: Bearer …`` JWT.
``user_id`` is taken from the token; any value supplied in the body or URL
must match — otherwise we return 403 to prevent spoofing of someone else's
policy data.

The hardening can be opt-out for local scripting by setting
``RL_ALLOW_BODY_USER_ID=1``, which falls back to the legacy permissive
behavior. This flag must NOT be set in production.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, g, jsonify, request

from .schemas import Action
from .service import get_service
from middleware.auth import authenticate_token, get_current_user_id
from utils.api_response import error_response

logger = logging.getLogger(__name__)

bp = Blueprint("rl_api", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _allow_body_user_id() -> bool:
    """Insecure fallback flag for local development only."""
    return os.getenv("RL_ALLOW_BODY_USER_ID", "").strip() in {"1", "true", "yes"}


def _resolve_user_id_authenticated(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Tuple[Any, int]]]:
    """Resolve ``user_id`` from the JWT and reject mismatched body overrides.

    Returns ``(user_id, error_tuple)``. If ``error_tuple`` is not None the
    caller should return it directly.
    """
    context_id = get_current_user_id()
    if not context_id:
        if _allow_body_user_id():
            body_id = payload.get("user_id") or payload.get("userId") or payload.get("email")
            return (str(body_id), None) if body_id else (None, _bad_request("user_id is required"))
        return None, error_response(
            "Authentication required",
            code="AUTH_REQUIRED",
            status_code=401,
        )

    body_id = payload.get("user_id") or payload.get("userId") or payload.get("email")
    if body_id and str(body_id) != str(context_id):
        logger.warning(
            "RL user_id mismatch: token=%s body=%s — rejecting", context_id, body_id
        )
        return None, error_response(
            "user_id in body does not match the authenticated token",
            code="USER_ID_MISMATCH",
            status_code=403,
        )
    return str(context_id), None


def _ensure_owner(user_id: str) -> Optional[Tuple[Any, int]]:
    """Enforce that the URL ``user_id`` matches the authenticated caller."""
    context_id = get_current_user_id()
    if not context_id:
        if _allow_body_user_id():
            return None
        return error_response(
            "Authentication required",
            code="AUTH_REQUIRED",
            status_code=401,
        )
    if str(user_id) != str(context_id):
        return error_response(
            "Cannot access another user's RL data",
            code="FORBIDDEN",
            status_code=403,
        )
    return None


def _bad_request(message: str, **extra: Any) -> Tuple[Any, int]:
    return error_response(message, code="BAD_REQUEST", status_code=400, **extra)


def _internal_error(message: str, **extra: Any) -> Tuple[Any, int]:
    return error_response(message, code="INTERNAL_ERROR", status_code=500, **extra)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@bp.route("/next-action", methods=["GET", "POST"])
@bp.route("/next_action", methods=["GET", "POST"])
@authenticate_token
def next_action_endpoint():
    payload = request.get_json(silent=True) or {}
    if request.method == "GET":
        payload = {
            **payload,
            "user_id": request.args.get("user_id") or request.args.get("userId") or request.args.get("email"),
            "force_explore": request.args.get("force_explore", "false").lower() == "true",
        }
    user_id, err = _resolve_user_id_authenticated(payload)
    if err:
        return err

    state_payload = payload.get("state") or payload
    force_explore = bool(payload.get("force_explore", False))

    try:
        decision = get_service().next_action(user_id, state_payload, force_explore=force_explore)
    except ValueError as exc:
        return _bad_request(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/next-action failed: %s", exc)
        return _internal_error("Failed to compute next action")

    return jsonify({"success": True, **decision.to_dict()}), 200


@bp.post("/update-reward")
@authenticate_token
def update_reward_endpoint():
    payload = request.get_json(silent=True) or {}
    user_id, err = _resolve_user_id_authenticated(payload)
    if err:
        return err

    action = payload.get("action")
    if not action:
        return _bad_request("action is required")
    feedback = payload.get("feedback") or {}
    previous_state = payload.get("previous_state") or payload.get("state")
    next_state = payload.get("next_state")
    if not previous_state and not next_state:
        return _bad_request("previous_state or next_state is required")

    try:
        result = get_service().update_reward(
            user_id=user_id,
            action=action,
            feedback_payload=feedback,
            previous_state_payload=previous_state,
            next_state_payload=next_state,
            episode_id=payload.get("episode_id"),
            terminal=bool(payload.get("terminal", False)),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/update-reward failed: %s", exc)
        return _internal_error("Failed to record reward")

    return jsonify({"success": True, **result}), 200


@bp.get("/policy/<user_id>")
@authenticate_token
def policy_endpoint(user_id: str):
    if not user_id:
        return _bad_request("user_id is required in URL")
    err = _ensure_owner(user_id)
    if err:
        return err
    try:
        summary = get_service().get_policy_summary(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/policy failed: %s", exc)
        return _internal_error("Failed to load policy summary")
    return jsonify({"success": True, **summary}), 200


@bp.get("/policies")
@authenticate_token
def list_policies_endpoint():
    """Listing all policies is sensitive — gated behind admin role checks."""
    role = (getattr(g, "user", {}) or {}).get("role", "").lower()
    if role not in {"admin", "superadmin"} and not _allow_body_user_id():
        return error_response(
            "Admin role required to list all policies",
            code="FORBIDDEN",
            status_code=403,
        )
    try:
        policies = get_service().list_policies()
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/policies failed: %s", exc)
        return _internal_error("Failed to list policies")
    return jsonify({"success": True, "policies": policies}), 200


@bp.post("/train")
@authenticate_token
def train_endpoint():
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode") or "replay").lower()
    if mode not in {"replay", "simulator"}:
        return _bad_request("mode must be 'replay' or 'simulator'")

    role = (getattr(g, "user", {}) or {}).get("role", "").lower()
    requested_user_id = payload.get("user_id")
    caller_id = get_current_user_id()

    if requested_user_id and str(requested_user_id) != str(caller_id) and role not in {"admin", "superadmin"}:
        return error_response(
            "Only admins can train another user's policy",
            code="FORBIDDEN",
            status_code=403,
        )

    try:
        report = get_service().train(
            mode=mode,
            episodes=int(payload.get("episodes") or 200),
            epochs=payload.get("epochs"),
            batch_size=payload.get("batch_size"),
            user_id=str(requested_user_id) if requested_user_id else caller_id,
            seed=payload.get("seed"),
        )
    except ValueError as exc:
        return _bad_request(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/train failed: %s", exc)
        return _internal_error("Training failed")

    return jsonify({"success": True, "report": report.to_dict()}), 200


@bp.get("/history/<user_id>")
@authenticate_token
def history_endpoint(user_id: str):
    if not user_id:
        return _bad_request("user_id is required in URL")
    err = _ensure_owner(user_id)
    if err:
        return err
    try:
        limit = int(request.args.get("limit", 25))
    except (TypeError, ValueError):
        limit = 25
    try:
        history = get_service().history(user_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/history failed: %s", exc)
        return _internal_error("Failed to load history")
    return jsonify({"success": True, **history}), 200


@bp.post("/explain")
@authenticate_token
def explain_endpoint():
    payload = request.get_json(silent=True) or {}
    state = payload.get("state") or payload
    action = payload.get("action")
    if not action:
        return _bad_request("action is required")
    try:
        effect = get_service().explain_action_effect(state, action)
    except ValueError as exc:
        return _bad_request(str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("rl/explain failed: %s", exc)
        return _internal_error("Failed to project effect")
    return jsonify({"success": True, "effect": effect}), 200


@bp.get("/actions")
def actions_endpoint():
    """Return the canonical action set (for clients that want a dropdown)."""
    return (
        jsonify(
            {
                "success": True,
                "actions": [
                    {"id": action.value, "label": action.value.replace("_", " ").title()}
                    for action in Action
                ],
            }
        ),
        200,
    )


@bp.get("/health")
def health_endpoint():
    service = get_service()
    return (
        jsonify(
            {
                "success": True,
                "status": "healthy",
                "module": "Reinforcement Learning Adaptive Engine",
                "version": "1.0",
                "transitions_recorded": service.repository.transition_count(),
                "policies": service.list_policies(),
                "actions_supported": [a.value for a in Action],
            }
        ),
        200,
    )
