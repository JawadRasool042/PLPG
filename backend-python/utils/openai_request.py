"""Shared OpenAI Chat Completions helpers (GPT-5 / reasoning-model compatible)."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

DEFAULT_FALLBACK_MODELS: Tuple[str, ...] = ("gpt-4o-mini", "gpt-4.1-mini")

_RETRYABLE_STATUS = frozenset({404, 429})


def is_reasoning_model(model: str) -> bool:
    """True for o-series, GPT-5 family, and other reasoning-only models."""
    name = (model or "").strip().lower()
    return bool(re.match(r"^(o[0-9]|gpt-5|codex-mini)", name))


def build_chat_payload(
    model: str,
    messages: List[Dict[str, Any]],
    *,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    response_format: Optional[Dict[str, str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build a Chat Completions body with correct token/temperature fields per model family."""
    body: Dict[str, Any] = {"model": model, "messages": messages}

    if max_tokens is not None:
        if is_reasoning_model(model):
            body["max_completion_tokens"] = max_tokens
        else:
            body["max_tokens"] = max_tokens

    if temperature is not None and not is_reasoning_model(model):
        body["temperature"] = temperature

    if response_format is not None:
        body["response_format"] = response_format

    body.update(extra)
    return body


def get_model_chain(primary: Optional[str] = None, fallbacks: Optional[Sequence[str]] = None) -> Tuple[str, ...]:
    primary_model = (primary or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
    extras = fallbacks if fallbacks is not None else DEFAULT_FALLBACK_MODELS
    chain: List[str] = []
    seen: set[str] = set()
    for model_name in (primary_model, *extras):
        if model_name and model_name not in seen:
            chain.append(model_name)
            seen.add(model_name)
    return tuple(chain)


def extract_chat_content(data: Dict[str, Any]) -> str:
    return (
        ((((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or "")
        .strip()
    )


def chat_completions(
    *,
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    response_format: Optional[Dict[str, str]] = None,
    timeout: float = 30,
    fallback_models: Optional[Sequence[str]] = None,
    retry_on_status: frozenset[int] = _RETRYABLE_STATUS,
) -> Tuple[str, str]:
    """
    Call OpenAI Chat Completions with model fallback.

    Returns:
        (model_used, response_text)

    Raises:
        RuntimeError on auth failure or when all models fail.
    """
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or key.lower() in {"your_openai_api_key_here", "changeme"}:
        raise RuntimeError("OPENAI_API_KEY is missing or a placeholder")

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    models = get_model_chain(model, fallback_models)
    last_error = "All OpenAI models failed"

    for model_name in models:
        payload = build_chat_payload(
            model_name,
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
        try:
            response = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_error = f"{model_name} network error: {exc}"
            logger.warning(last_error)
            continue

        if response.status_code == 200:
            try:
                text = extract_chat_content(response.json())
            except (ValueError, KeyError, IndexError) as exc:
                last_error = f"{model_name} bad response shape: {exc}"
                logger.warning(last_error)
                continue
            if text:
                return model_name, text
            last_error = f"{model_name} returned empty text"
            logger.warning(last_error)
            continue

        if response.status_code in (401, 403):
            raise RuntimeError("OpenAI API key rejected")

        err_msg = ""
        try:
            err_msg = (response.json().get("error") or {}).get("message", "")
        except ValueError:
            err_msg = response.text[:200]

        last_error = f"{model_name} HTTP {response.status_code}: {err_msg or response.text[:200]}"
        if response.status_code in retry_on_status:
            logger.info("%s — trying next model", last_error)
            continue
        logger.warning(last_error)

    raise RuntimeError(last_error)
