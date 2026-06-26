"""
Multi-type Quiz Generator
=========================

Generates quizzes with mixed question types:
- MCQ
- True/False
- Short Answer
- Scenario-based

Uses OpenAI with strict JSON validation and a fallback
to the strict MCQ generator when needed.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from utils.openai_request import chat_completions

from .strict_quiz_generator import StrictQuizGenerator

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"mcq", "true_false", "short_answer", "scenario"}
ALLOWED_DIFFICULTY = {"beginner", "intermediate", "advanced"}


@dataclass
class MixedQuizResult:
    quiz: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class MixedQuizGenerator:
    """Generates mixed-format quizzes using OpenAI with validation and fallback."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = bool(self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        user_profile: Optional[Dict[str, Any]] = None,
        weak_areas: Optional[List[str]] = None,
        secondary_interests: Optional[List[str]] = None,
    ) -> MixedQuizResult:
        self._validate_inputs(topic, difficulty, question_count)

        # Offline / no-key fallback: generate a deterministic mixed quiz.
        if not self.client:
            return self._offline_fallback(topic, difficulty, question_count)

        prompt = self._build_prompt(
            topic=topic,
            difficulty=difficulty,
            question_count=question_count,
            user_profile=user_profile or {},
            weak_areas=weak_areas or [],
            secondary_interests=secondary_interests or [],
        )

        try:
            _, raw_response = chat_completions(
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON array."},
                    {"role": "user", "content": prompt},
                ],
                api_key=self.api_key,
                model=self.model,
                max_tokens=5000,
                temperature=0.6,
                timeout=30,
            )
            questions = self._parse_response(raw_response)
            self._validate_questions(questions, question_count)

            metadata = {
                "source": "openai",
                "question_count": len(questions),
                "difficulty": difficulty,
                "topic": topic,
            }
            return MixedQuizResult(quiz=questions, metadata=metadata)

        except Exception as exc:
            logger.warning("Mixed quiz generation failed, falling back to strict MCQ: %s", exc)
            return self._fallback_to_strict(topic, difficulty, question_count, weak_areas)

    def _offline_fallback(self, topic: str, difficulty: str, question_count: int) -> MixedQuizResult:
        """
        Deterministic generator when OPENAI_API_KEY is missing.
        Produces a mixed quiz with safe, generic-but-domain-scoped prompts.
        """
        # Keep it simple and robust: MCQ + TF + short answer + scenario rotation.
        types = ["mcq", "true_false", "short_answer", "scenario"]
        quiz: List[Dict[str, Any]] = []

        for i in range(1, question_count + 1):
            q_type = types[(i - 1) % len(types)]
            sub_topic = f"{topic} fundamentals"

            if q_type == "mcq":
                quiz.append(
                    {
                        "id": i,
                        "type": "mcq",
                        "question": f"In {topic}, which option best describes a key concept you should learn first?",
                        "sub_topic": sub_topic,
                        "options": {"A": "Core terminology and basic workflow", "B": "Advanced optimization only", "C": "Unrelated tooling", "D": "Skip fundamentals"},
                        "correct_answer": "A",
                        "explanation": "Starting with core terminology and the basic workflow builds the foundation needed to understand intermediate and advanced topics.",
                        "difficulty": difficulty,
                    }
                )
            elif q_type == "true_false":
                quiz.append(
                    {
                        "id": i,
                        "type": "true_false",
                        "question": f"True or False: In {topic}, understanding fundamentals reduces errors and accelerates learning.",
                        "sub_topic": sub_topic,
                        "options": ["True", "False"],
                        "correct_answer": "True",
                        "explanation": "Fundamentals help you reason about problems, debug efficiently, and apply best practices correctly.",
                        "difficulty": difficulty,
                    }
                )
            elif q_type == "short_answer":
                quiz.append(
                    {
                        "id": i,
                        "type": "short_answer",
                        "question": f"Briefly explain (1-3 sentences) what you want to achieve in {topic}.",
                        "sub_topic": "goals and intent",
                        "correct_answer": "A clear goal statement that mentions an outcome and a constraint (time, project, or context).",
                        "expected_keywords": ["build", "learn", "project"],
                        "explanation": "Goal clarity improves focus. Mentioning an outcome (build/learn) and context (project/time) helps personalize the roadmap.",
                        "difficulty": difficulty,
                    }
                )
            else:
                quiz.append(
                    {
                        "id": i,
                        "type": "scenario",
                        "scenario": f"You are starting a new learning journey in {topic} and have limited weekly time.",
                        "question": "What is a good first-step plan for week 1?",
                        "sub_topic": "planning",
                        "correct_answer": "Pick one core topic, do a small hands-on exercise, and review mistakes.",
                        "expected_keywords": ["practice", "project", "review"],
                        "explanation": "A narrow focus with hands-on practice and reflection creates fast feedback loops and prevents overwhelm.",
                        "difficulty": difficulty,
                    }
                )

        metadata = {"source": "offline_fallback", "question_count": len(quiz), "difficulty": difficulty, "topic": topic}
        return MixedQuizResult(quiz=quiz, metadata=metadata)

    def _validate_inputs(self, topic: str, difficulty: str, question_count: int) -> None:
        if not topic or not isinstance(topic, str):
            raise ValueError("topic must be a non-empty string")
        if difficulty not in ALLOWED_DIFFICULTY:
            raise ValueError("difficulty must be one of: beginner, intermediate, advanced")
        if not isinstance(question_count, int) or not 5 <= question_count <= 15:
            raise ValueError("question_count must be between 5 and 15")

    def _build_prompt(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        user_profile: Dict[str, Any],
        weak_areas: List[str],
        secondary_interests: List[str],
    ) -> str:
        profile_summary = json.dumps(user_profile, ensure_ascii=False)
        weak_section = ", ".join(weak_areas) if weak_areas else "None"
        secondary = ", ".join(secondary_interests) if secondary_interests else "None"

        return f"""
You are an expert assessment designer for EdTech platforms.
Create a mixed-type quiz that matches the learner profile and goals.

CONTEXT
- Topic: {topic}
- Difficulty: {difficulty}
- Question count: {question_count}
- Weak areas: {weak_section}
- Secondary interests: {secondary}
- Learner profile JSON: {profile_summary}

REQUIREMENTS
1. Return ONLY valid JSON (no markdown).
2. Use a mix of question types: mcq, true_false, short_answer, scenario.
3. Provide clear explanations for each answer.
4. Ensure sub_topic is present for every question.
5. Keep questions real-world and goal-oriented.
6. Include expected_keywords for short_answer and scenario questions (3-5 keywords).

OUTPUT FORMAT (JSON ARRAY)
[
  {{
    "id": 1,
    "type": "mcq",
    "question": "...",
    "sub_topic": "...",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "correct_answer": "A",
    "explanation": "...",
    "difficulty": "{difficulty}"
  }},
  {{
    "id": 2,
    "type": "true_false",
    "question": "...",
    "sub_topic": "...",
    "options": ["True", "False"],
    "correct_answer": "True",
    "explanation": "...",
    "difficulty": "{difficulty}"
  }},
  {{
    "id": 3,
    "type": "short_answer",
    "question": "...",
    "sub_topic": "...",
    "correct_answer": "...",
    "expected_keywords": ["...", "..."],
    "explanation": "...",
    "difficulty": "{difficulty}"
  }},
  {{
    "id": 4,
    "type": "scenario",
    "scenario": "...",
    "question": "...",
    "sub_topic": "...",
    "correct_answer": "...",
    "expected_keywords": ["...", "..."],
    "explanation": "...",
    "difficulty": "{difficulty}"
  }}
]
"""

    def _parse_response(self, raw_response: str) -> List[Dict[str, Any]]:
        if not raw_response:
            raise ValueError("Empty response from OpenAI")
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        data = json.loads(cleaned)
        if not isinstance(data, list):
            raise ValueError("Response must be a JSON array")
        return data

    def _validate_questions(self, questions: List[Dict[str, Any]], expected_count: int) -> None:
        if len(questions) != expected_count:
            raise ValueError(f"Expected {expected_count} questions, got {len(questions)}")
        for idx, q in enumerate(questions):
            q_type = q.get("type")
            if q_type not in ALLOWED_TYPES:
                raise ValueError(f"Question {idx + 1}: invalid type {q_type}")
            if not q.get("question"):
                raise ValueError(f"Question {idx + 1}: missing question text")
            if not q.get("sub_topic"):
                raise ValueError(f"Question {idx + 1}: missing sub_topic")
            if not q.get("explanation"):
                raise ValueError(f"Question {idx + 1}: missing explanation")
            if q.get("difficulty") not in ALLOWED_DIFFICULTY:
                raise ValueError(f"Question {idx + 1}: invalid difficulty")

            if q_type == "mcq":
                options = q.get("options", {})
                if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
                    raise ValueError(f"Question {idx + 1}: MCQ options must be A-D")
                if q.get("correct_answer") not in {"A", "B", "C", "D"}:
                    raise ValueError(f"Question {idx + 1}: invalid MCQ correct_answer")
            elif q_type == "true_false":
                options = q.get("options", ["True", "False"])
                if not isinstance(options, list) or len(options) != 2:
                    raise ValueError(f"Question {idx + 1}: True/False options must have 2 items")
                if q.get("correct_answer") not in {"True", "False"}:
                    raise ValueError(f"Question {idx + 1}: invalid True/False correct_answer")
                q["options"] = options
            else:
                if not q.get("correct_answer"):
                    raise ValueError(f"Question {idx + 1}: missing correct_answer")
                expected_keywords = q.get("expected_keywords")
                if not isinstance(expected_keywords, list) or len(expected_keywords) < 2:
                    raise ValueError(f"Question {idx + 1}: expected_keywords required for open questions")

    def _fallback_to_strict(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        weak_areas: Optional[List[str]],
    ) -> MixedQuizResult:
        if not self.api_key:
            return self._offline_fallback(topic, difficulty, question_count)

        generator = StrictQuizGenerator(api_key=self.api_key)
        strict = generator.generate(
            topic=topic,
            difficulty=difficulty,
            question_count=question_count,
            weak_areas=weak_areas,
        )
        converted = []
        for item in strict.get("quiz", []):
            converted.append(
                {
                    "id": item.get("id"),
                    "type": "mcq",
                    "question": item.get("question"),
                    "sub_topic": item.get("sub_topic"),
                    "options": item.get("options"),
                    "correct_answer": item.get("correct_answer"),
                    "explanation": item.get("reasoning"),
                    "difficulty": difficulty,
                    "targets_weak_area": item.get("targets_weak_area", False),
                }
            )
        metadata = {
            "source": "strict_fallback",
            "question_count": len(converted),
            "difficulty": difficulty,
            "topic": topic,
        }
        return MixedQuizResult(quiz=converted, metadata=metadata)


def generate_mixed_quiz(
    topic: str,
    difficulty: str,
    question_count: int,
    user_profile: Optional[Dict[str, Any]] = None,
    weak_areas: Optional[List[str]] = None,
    secondary_interests: Optional[List[str]] = None,
) -> Dict[str, Any]:
    generator = MixedQuizGenerator()
    result = generator.generate(
        topic=topic,
        difficulty=difficulty,
        question_count=question_count,
        user_profile=user_profile,
        weak_areas=weak_areas,
        secondary_interests=secondary_interests,
    )
    return {"quiz": result.quiz, "metadata": result.metadata}
