import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

from utils.openai_request import chat_completions

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_FALLBACK_TIMEOUT_SECONDS = float(os.getenv("OPENAI_FALLBACK_TIMEOUT", "8"))
OPENAI_FALLBACK_MAX_TOKENS = int(os.getenv("OPENAI_FALLBACK_MAX_TOKENS", "1000"))


def _build_prompt(topic: str, level: str, count: int, weak_areas: Optional[List[str]] = None) -> str:
    weak = f"\nWeak areas: {', '.join(weak_areas)}" if weak_areas else ""
    return f"""Generate exactly {count} MCQs on {topic} at {level} level.{weak}
Return only JSON:
{{"quiz":[{{"id":1,"question":"...","sub_topic":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"correct_answer":"A","difficulty":"{level}","reasoning":"..."}}]}}"""


def _parse(text: str) -> List[Dict[str, Any]]:
    cleaned = (text or "").replace("```json", "").replace("```", "").strip()
    if not cleaned:
        return []
    data = json.loads(cleaned)
    if isinstance(data, dict) and isinstance(data.get("quiz"), list):
        return data["quiz"]
    if isinstance(data, list):
        return data
    return []


def _validate(q: Dict[str, Any]) -> bool:
    options = q.get("options")
    return isinstance(q.get("question"), str) and isinstance(options, dict) and set(options.keys()) == {"A", "B", "C", "D"}


def _try_openai(topic: str, level: str, count: int, weak_areas: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
    if not OPENAI_API_KEY:
        return None
    try:
        _, message = chat_completions(
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": _build_prompt(topic, level, count, weak_areas)},
            ],
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            max_tokens=OPENAI_FALLBACK_MAX_TOKENS,
            temperature=0.7,
            response_format={"type": "json_object"},
            timeout=OPENAI_FALLBACK_TIMEOUT_SECONDS,
        )
    except RuntimeError as exc:
        logger.warning("OpenAI quiz fallback call failed: %s", exc)
        return None
    out = [q for q in _parse(message) if _validate(q)]
    return out or None


def _template(topic: str, level: str, count: int) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for i in range(count):
        output.append(
            {
                "id": i + 1,
                "question": f"What is a foundational concept in {topic}?",
                "sub_topic": topic,
                "options": {
                    "A": "Understand core concepts first",
                    "B": "Skip directly to advanced optimization",
                    "C": "Memorize syntax without practice",
                    "D": "Ignore debugging principles",
                },
                "correct_answer": "A",
                "difficulty": level,
                "reasoning": "Foundational understanding enables better real-world application.",
            }
        )
    return output


def generate_quiz_with_fallback(
    topic: str,
    level: str,
    count: int = 10,
    user_profile: Optional[Dict[str, Any]] = None,
    weak_areas: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    questions = _try_openai(topic, level, count, weak_areas)
    if questions:
        return questions, True
    templated = _template(topic, level, count)
    return templated, bool(templated)
