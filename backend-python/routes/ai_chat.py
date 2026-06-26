"""
AI Chat Route - Powered by OpenAI

Improvements over v1:
- Defaults to ``gpt-4o-mini`` (cost-effective baseline model).
- Treats 429 (quota) as a per-model signal — falls through to the next
  model in the chain instead of aborting the whole request.
- Returns a ``source`` field (``"openai"`` | ``"fallback"``) so the UI
  can clearly show the user when the assistant is offline.
- Smarter local fallback: greetings get a friendly reply, off-topic
  questions get redirected, only topic queries get the static roadmap.
- Tiny in-process LRU cache keyed on (user_interest, message) to avoid
  burning quota on identical questions during a session.
"""
from __future__ import annotations

import logging
import os
import re
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Blueprint, g, jsonify, request

from utils.openai_request import chat_completions

from bson import ObjectId

from database import get_collection
from middleware.auth import authenticate_token

logger = logging.getLogger(__name__)

ai_chat_bp = Blueprint('ai_chat', __name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Keep a stable default with optional fallback chain per model availability.
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

OPENAI_CHAT_MODEL = (
    os.getenv("OPENAI_CHAT_MODEL")
    or os.getenv("OPENAI_MODEL")
    or DEFAULT_OPENAI_MODEL
)

# Order matters: try the configured/default model first, then progressively
# cheaper / older models that may still have quota.
_DEFAULT_FALLBACK_CHAIN: Tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
)

_chain_seen: dict = {}
for _m in (OPENAI_CHAT_MODEL, *_DEFAULT_FALLBACK_CHAIN):
    if _m and _m not in _chain_seen:
        _chain_seen[_m] = None
OPENAI_FALLBACK_MODELS: Tuple[str, ...] = tuple(_chain_seen.keys())

OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_CHAT_TIMEOUT", "20"))
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_CHAT_MAX_TOKENS", "600"))
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_CHAT_TEMPERATURE", "0.7"))

# ---------------------------------------------------------------------------
# Tiny LRU cache (per-process). Bypassed on greetings to keep replies fresh.
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 300
_CACHE_MAX_ENTRIES = 256
_CACHE: "OrderedDict[str, Tuple[float, str, str]]" = OrderedDict()
_CACHE_LOCK = Lock()


def _cache_key(message: str, user_interest: Optional[str]) -> str:
    return f"{(user_interest or '').lower()}::{message.strip().lower()}"


def _cache_get(key: str) -> Optional[Tuple[str, str]]:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        ts, source, text = entry
        if time.time() - ts > _CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return source, text


def _cache_put(key: str, source: str, text: str) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), source, text)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)


# ---------------------------------------------------------------------------
# Prompt + persona
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI Learning Assistant for PLPG (Personalized Learning Path Generator), an educational platform that helps students discover their interests and learn tech skills.

Your role:
- Help students with learning tech topics: AI/ML, Web Development, Cybersecurity, Data Science, Mobile Development, Cloud Computing, Game Development, Programming/Coding
- Provide clear, concise explanations of concepts
- Suggest learning resources, roadmaps, and projects
- Answer quiz-related questions and explain concepts
- Give career guidance in tech fields
- Be encouraging and supportive

Guidelines:
- Match the user's tone. If they say "hi", greet them naturally — DO NOT dump a roadmap unless asked.
- Keep responses focused and educational
- Use bullet points and structure when listing things, but use plain prose for short answers
- If asked about non-tech topics, politely redirect to learning
- Personalize responses based on the student's interest if provided
- Respond in the same language the student uses (Urdu/English)
- Keep responses concise (max 300 words unless detailed explanation is needed)
"""


# ---------------------------------------------------------------------------
# Local (offline) fallback responses
# ---------------------------------------------------------------------------

LOCAL_GUIDANCE = {
    "ai/ml": {
        "title": "AI/ML starter roadmap",
        "items": [
            "Week 1-2: Python basics + NumPy + Pandas",
            "Week 3-4: Statistics fundamentals (mean, variance, probability)",
            "Week 5-6: Supervised learning with scikit-learn",
            "Week 7-8: Build one mini project (e.g., house price predictor)",
        ],
    },
    "web": {
        "title": "Web development roadmap",
        "items": [
            "Start with HTML/CSS + responsive design",
            "Move to JavaScript fundamentals and DOM",
            "Learn React basics and routing",
            "Build and deploy one CRUD app with backend API",
        ],
    },
    "cyber": {
        "title": "Cybersecurity roadmap",
        "items": [
            "Networking + Linux basics",
            "OWASP Top 10 and web security fundamentals",
            "Practice labs on TryHackMe/HTB",
            "Document findings in a security portfolio",
        ],
    },
    "data": {
        "title": "Data science roadmap",
        "items": [
            "Python + Pandas + visualization",
            "Statistics and hypothesis testing",
            "SQL and data cleaning pipelines",
            "One dashboard + one ML mini project",
        ],
    },
    "mobile": {
        "title": "Mobile development roadmap",
        "items": [
            "Pick a stack: Flutter (Dart) or React Native (JS/TS)",
            "Learn navigation, state management, and platform APIs",
            "Build one offline-first app with REST/GraphQL",
            "Publish a beta on Play Store / TestFlight",
        ],
    },
    "cloud": {
        "title": "Cloud computing roadmap",
        "items": [
            "Pick one provider: AWS, GCP, or Azure",
            "Practice IAM, VPC, EC2/Compute, S3/Storage, IAM",
            "Learn Docker, then Kubernetes basics",
            "Earn a foundational cert (e.g. AWS CCP / AZ-900)",
        ],
    },
}

_GREETING_PREFIX_RE = re.compile(
    r"^\s*(hi|hii|hey|hello|yo|salam|salaam|assalam(?:u|o)?\s*alaikum|aoa|asalamoalaikum|"
    r"good\s*(morning|afternoon|evening|night)|how\s+are\s+you|what'?s\s+up|wassup|sup)\b",
    re.IGNORECASE,
)


class _GreetingRe:
    """Wrapper so we can keep the ``.match()`` ergonomics from the regex API."""

    @staticmethod
    def match(text: Any) -> bool:
        s = str(text or "").strip()
        if not s or len(s) > 40:
            return False
        return bool(_GREETING_PREFIX_RE.match(s))


_GREETING_RE = _GreetingRe()

_THANKS_RE = re.compile(
    r"^\s*(thanks|thank\s*you|thx|ty|shukriya|jazak\w*|appreciate(?:d)?|cool|nice|awesome)[\s.,!?]*$",
    re.IGNORECASE,
)

_BYE_RE = re.compile(
    r"^\s*(bye|goodbye|gn|good\s*night|see\s*ya|see\s*you|khuda\s*hafiz|allah\s*hafiz)[\s.,!?]*$",
    re.IGNORECASE,
)


def _detect_topic_key(text: str, user_interest: Optional[str] = None) -> Optional[str]:
    """Return a topic key if the text clearly references one, else None."""
    lowered = (text or "").lower()
    rules = (
        ("ai/ml", ("ai", "ml", "machine learning", "deep learning", "neural", "model")),
        ("cyber", ("cyber", "security", "hack", "pentest", "owasp", "ethical")),
        ("data", ("data science", "analytics", "pandas", "sql", "tableau", "power bi")),
        ("web", ("web", "html", "css", "javascript", "react", "node", "frontend", "backend")),
        ("mobile", ("mobile", "android", "ios", "flutter", "react native", "swift", "kotlin")),
        ("cloud", ("cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops")),
    )
    for key, hints in rules:
        if any(h in lowered for h in hints):
            return key

    interest = (user_interest or "").lower()
    if interest:
        if "ai" in interest or "ml" in interest:
            return "ai/ml"
        if "cyber" in interest or "security" in interest:
            return "cyber"
        if "data" in interest:
            return "data"
        if "mobile" in interest:
            return "mobile"
        if "cloud" in interest or "devops" in interest:
            return "cloud"
        if "web" in interest:
            return "web"
    return None


def _local_fallback(message: str, user_interest: Optional[str] = None) -> str:
    """Generate an offline reply that respects the user's intent."""
    text = (message or "").strip()
    interest_label = f" for **{user_interest}**" if user_interest else ""

    if _GREETING_RE.match(text):
        return (
            f"Hello! 👋 I'm your PLPG learning assistant{interest_label}.\n"
            "Ask me about a topic, study plan, project ideas, or career advice in tech."
        )

    if _THANKS_RE.match(text):
        return "You're welcome! Let me know if you'd like a roadmap, project idea, or quick concept refresher."

    if _BYE_RE.match(text):
        return "Goodbye! Keep learning — I'll be here whenever you need me. 👋"

    topic_key = _detect_topic_key(text, user_interest)
    if topic_key and topic_key in LOCAL_GUIDANCE:
        guide = LOCAL_GUIDANCE[topic_key]
        bullets = "\n".join(f"• {line}" for line in guide["items"])
        return (
            f"**{guide['title']}**\n{bullets}\n\n"
            "_(I'm temporarily in offline mode. Real-time AI replies will resume once the AI quota resets.)_"
        )

    # Generic fallback: don't dump a roadmap on an unrelated question.
    return (
        "I'm temporarily in offline mode (AI quota limit), so I can only help with broad guidance right now.\n\n"
        "Try asking about: **AI/ML**, **Web Dev**, **Cybersecurity**, **Data Science**, **Mobile**, or **Cloud** "
        "and I'll share a starter plan. Or come back in a minute and the live assistant will be back online."
    )


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------


class _OpenAIAuthError(RuntimeError):
    """Raised when the API key is bad — never recoverable by retrying."""


def _call_openai_api(prompt: str) -> Tuple[str, str]:
    """Call OpenAI and return ``(model_used, text)``.

    Falls through to the next model in the chain on 404 or 429.
    Raises ``_OpenAIAuthError`` if the key is invalid (401/403).
    Raises ``RuntimeError`` for all other unrecoverable errors.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.lower() in {"your_openai_api_key_here", "changeme"}:
        raise _OpenAIAuthError("OPENAI_API_KEY is missing or a placeholder")

    try:
        model_used, text = chat_completions(
            messages=[
                {"role": "system", "content": "You are a helpful learning assistant."},
                {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            model=OPENAI_CHAT_MODEL,
            max_tokens=OPENAI_MAX_OUTPUT_TOKENS,
            temperature=OPENAI_TEMPERATURE,
            timeout=OPENAI_TIMEOUT_SECONDS,
            fallback_models=OPENAI_FALLBACK_MODELS[1:],
        )
        return model_used, text
    except RuntimeError as exc:
        msg = str(exc)
        if "key rejected" in msg.lower():
            raise _OpenAIAuthError("OpenAI API key rejected") from exc
        raise RuntimeError(msg) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_interest(user_id: str) -> Optional[str]:
    if not user_id:
        return None
    try:
        col = get_collection("users")
        user = col.find_one({"_id": ObjectId(user_id)})
        if user:
            assessment = user.get("interestAssessment") or {}
            if assessment.get("completed"):
                return assessment.get("primaryInterest")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load user interest for %s: %s", user_id, exc)
    return None


def _build_prompt(message: str, user_interest: Optional[str], history: Optional[List[Dict[str, Any]]]) -> str:
    context = SYSTEM_PROMPT
    if user_interest:
        context += f"\n\nStudent's primary interest: {user_interest}"
    if history:
        context += "\n\nConversation so far:"
        for msg in history[-6:]:
            role = "Student" if msg.get("role") == "user" else "Assistant"
            text = (msg.get("text") or "").strip()
            if text:
                context += f"\n{role}: {text}"
    context += f"\n\nStudent: {message}\nAssistant:"
    return context


def _sanitize_message(raw: Any) -> str:
    return str(raw or "").strip()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _handle_chat(message: str, user_interest: Optional[str], history: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
    if not message:
        return {"success": False, "message": "Message is required"}, 400
    if len(message) > 1000:
        return {"success": False, "message": "Message too long (max 1000 characters)"}, 400

    cache_key = _cache_key(message, user_interest)
    is_greeting = bool(_GREETING_RE.match(message) or _THANKS_RE.match(message) or _BYE_RE.match(message))
    if not is_greeting:
        cached = _cache_get(cache_key)
        if cached:
            source, text = cached
            return {
                "success": True,
                "response": text,
                "source": source,
                "model": "cache",
                "cached": True,
            }, 200

    try:
        prompt = _build_prompt(message, user_interest, history)
        model_used, text = _call_openai_api(prompt)
        if not is_greeting:
            _cache_put(cache_key, "openai", text)
        return {
            "success": True,
            "response": text,
            "source": "openai",
            "model": model_used,
            "cached": False,
        }, 200

    except _OpenAIAuthError as exc:
        logger.error("Chat auth error: %s", exc)
        return {
            "success": False,
            "message": (
                "AI configuration error. Set OPENAI_API_KEY in the backend .env "
                "and restart the server."
            ),
            "code": "AUTH_ERROR",
        }, 500

    except Exception as exc:  # noqa: BLE001
        logger.warning("Chat falling back to local response: %s", exc)
        return {
            "success": True,
            "response": _local_fallback(message, user_interest),
            "source": "fallback",
            "model": None,
            "cached": False,
            "fallback_reason": str(exc)[:200],
        }, 200


@ai_chat_bp.route("/chat", methods=["POST"])
@authenticate_token
def ai_chat():
    data = request.get_json(silent=True) or {}
    message = _sanitize_message(data.get("message"))
    history = data.get("history") or []
    user_id = (getattr(g, "user", {}) or {}).get("id", "")
    user_interest = _get_user_interest(user_id) if user_id else None

    body, status = _handle_chat(message, user_interest, history)
    return jsonify(body), status


@ai_chat_bp.route("/chat/guest", methods=["POST"])
def ai_chat_guest():
    data = request.get_json(silent=True) or {}
    message = _sanitize_message(data.get("message"))
    history = data.get("history") or []

    body, status = _handle_chat(message, None, history)
    return jsonify(body), status


@ai_chat_bp.route("/chat/health", methods=["GET"])
def ai_chat_health():
    """Lightweight diagnostic — confirms the chat module is reachable."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return jsonify({
        "success": True,
        "module": "ai_chat",
        "default_model": OPENAI_CHAT_MODEL,
        "fallback_chain": list(OPENAI_FALLBACK_MODELS),
        "api_key_present": bool(api_key) and api_key.lower() not in {"your_openai_api_key_here", "changeme"},
    })
