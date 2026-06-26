import json
import logging
import os
from typing import Any, Dict, List, Optional

from utils.openai_request import chat_completions, get_model_chain

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_OPENAI_MODELS = ("gpt-4o-mini", "gpt-4.1-mini")
OPENAI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("OPENAI_QUIZ_TIMEOUT", "12"))
OPENAI_QUIZ_MAX_TOKENS = int(os.getenv("OPENAI_QUIZ_MAX_TOKENS", "1600"))


class OpenAIError(Exception):
    pass


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise OpenAIError("OPENAI_API_KEY environment variable not set")
        configured_model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
        self.model = configured_model or DEFAULT_OPENAI_MODEL
        self._fallback_models = [m for m in FALLBACK_OPENAI_MODELS if m != self.model]

    def generate_quiz(
        self,
        topic: str,
        difficulty_level: int,
        question_count: int = 5,
        weak_areas: Optional[List[str]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            f"Generate {question_count} multiple-choice questions for topic '{topic}' "
            f"at difficulty {difficulty_level}. Return JSON with 'quiz' array."
        )
        response = self._generate_with_fallback(prompt, max_tokens=OPENAI_QUIZ_MAX_TOKENS)
        data = self._parse_response(response)
        return {"success": True, "questions": data, "source": "openai"}

    def analyze_interests(
        self,
        interests: Dict[str, float],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            "Analyze interests and return JSON with: primary_interest, confidence, "
            "why_strong, market_opportunity, career_trajectory, complementary_skills, next_steps.\n"
            f"Interests: {json.dumps(interests)}\nContext: {json.dumps(user_context or {})}"
        )
        response = self._generate_with_fallback(prompt, max_tokens=2000)
        return {"success": True, "analysis": json.loads(response), "source": "openai"}

    def generate_recommendations(
        self,
        primary_interest: str,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            "Create recommendations JSON with immediate_actions, first_month_plan, resources, projects, communities, timeline.\n"
            f"Primary interest: {primary_interest}\nContext: {json.dumps(user_context or {})}"
        )
        response = self._generate_with_fallback(prompt, max_tokens=2000)
        return {"success": True, "recommendations": json.loads(response), "source": "openai"}

    def _parse_response(self, text: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"Invalid JSON response: {exc}") from exc
        if isinstance(data, dict) and isinstance(data.get("quiz"), list):
            return data["quiz"]
        if isinstance(data, list):
            return data
        raise OpenAIError("Invalid response structure")

    def _generate_with_fallback(self, prompt: str, max_tokens: int) -> str:
        try:
            _, text = chat_completions(
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                api_key=self.api_key,
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,
                timeout=OPENAI_REQUEST_TIMEOUT_SECONDS,
                fallback_models=self._fallback_models,
            )
            return text
        except RuntimeError as exc:
            raise OpenAIError(str(exc)) from exc
