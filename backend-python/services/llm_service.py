import os
import json
import httpx
from typing import List, Dict, Any, Optional

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = os.getenv("DEEPSEEK_API_KEY")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _clean_json_text(raw: str) -> str:
    """
    Attempt to remove common markdown code fences and whitespace noise.
    """
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return cleaned


async def generate_quiz_with_deepseek(
    topic: str,
    level: str,
    num_questions: int = 12,
) -> List[Dict[str, Any]]:
    """
    Generate a quiz using DeepSeek API.

    Returns a list of question objects:
      [{ "id": 1, "question": "...", "options": ["A","B","C","D"], "correctAnswer": "Option A" }]
    """
    if not API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not set in environment")

    topic = (topic or "").strip()
    level = (level or "").strip()
    if not topic:
        raise ValueError("topic is required")
    if not level:
        raise ValueError("level is required")

    prompt = (
        f'Generate {num_questions} multiple-choice questions about "{topic}" at {level} level.\n'
        'Return ONLY valid JSON in this exact format (no extra text, no markdown):\n'
        "[\n"
        '  {\n'
        '    "id": 1,\n'
        '    "question": "Question text here",\n'
        '    "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '    "correctAnswer": "Option A"\n'
        "  }\n"
        "]"
    )

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "You output only valid JSON. No markdown, no extra text."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 3000,
            },
        )
        response.raise_for_status()
        data = response.json()

    raw_content: Optional[str] = None
    try:
        raw_content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise ValueError("DeepSeek response missing expected message content") from e

    if not raw_content:
        raise ValueError("DeepSeek returned empty content")

    clean_json = _clean_json_text(raw_content)
    return json.loads(clean_json)
