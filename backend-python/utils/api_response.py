"""
Shared API response helpers for consistent contracts and safe errors.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
from flask import jsonify


def ok_response(status_code: int = 200, **payload: Any) -> Tuple[Any, int]:
    return jsonify({"success": True, **payload}), status_code


def error_response(
    message: str,
    *,
    code: str = "REQUEST_FAILED",
    status_code: int = 400,
    **payload: Any,
) -> Tuple[Any, int]:
    body: Dict[str, Any] = {
        "success": False,
        "code": code,
        "message": message,
    }
    body.update(payload)
    return jsonify(body), status_code
