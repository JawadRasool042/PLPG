"""
============================================
AI Quiz Service - OpenAI Real-Time Generator
============================================

Production-ready OpenAI-powered quiz generator that returns ONE question at a
time using the strict JSON contract required by the AI quiz feature:

{
  "question": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "correct_answer": "A",
  "why_correct": "...",
  "why_wrong": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "concept_summary": "...",
  "memory_tip": "...",
  "difficulty": "basic",
  "topic": "..."
}

Quizzes are dynamic and generated in real time. Nothing is pre-stored.
When the user answers wrong, the caller is responsible for persisting the
weak concept so subsequent calls can target it.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
from typing import Any, Dict, Iterable, List, Optional

import requests

from utils.openai_request import chat_completions

from .prompt_helpers import (
    coding_ai_quiz_difficulty_guides,
    coding_ai_quiz_style_block,
    pick_coding_ai_quiz_category_instruction,
    topic_looks_like_coding,
)

logger = logging.getLogger(__name__)


# Difficulty taxonomy used across the AI quiz feature.
ALLOWED_DIFFICULTIES = ("basic", "intermediate", "advanced", "expert")
ANSWER_LETTERS = ("A", "B", "C", "D")


class AIQuizError(Exception):
    """Raised when the AI quiz pipeline fails to produce a usable question."""


class AIQuizService:
    """
    Real-time AI quiz generator backed by OpenAI.

    The service is intentionally stateless: callers pass in everything the
    prompt needs (topic, difficulty, weak concepts, recently asked questions)
    and receive a single question back. Session state lives in MongoDB,
    handled by ``AIQuizSession``.
    """

    DEFAULT_MODEL = os.getenv("OPENAI_AI_QUIZ_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    FALLBACK_MODELS = ("gpt-4o-mini", "gpt-4.1-mini")

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise AIQuizError("OPENAI_API_KEY is not configured")

        self.model = model or self.DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_question(
        self,
        topic: str,
        difficulty: str = "basic",
        weak_concepts: Optional[List[str]] = None,
        previous_questions: Optional[Iterable[str]] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Generate a single quiz question conforming to the AI quiz JSON schema.

        Args:
            topic: Subject/topic (e.g. "Web Development", "Python Decorators").
            difficulty: One of ``basic`` / ``intermediate`` / ``advanced``.
            weak_concepts: Concepts the user previously got wrong; the prompt
                will steer the question toward these areas when supplied.
            previous_questions: Question stems already asked in this session
                (used to avoid repetition).
            max_attempts: How many times to retry on a malformed response.

        Returns:
            A validated question dict.
        """
        topic = (topic or "").strip()
        if not topic:
            raise AIQuizError("topic is required to generate a question")

        difficulty = (difficulty or "basic").strip().lower()
        if difficulty not in ALLOWED_DIFFICULTIES:
            difficulty = "basic"

        prompt = self._build_prompt(
            topic=topic,
            difficulty=difficulty,
            weak_concepts=weak_concepts or [],
            previous_questions=list(previous_questions or []),
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._generate_with_model_fallback(
                    prompt=prompt,
                    temperature=0.8 if attempt == 1 else 0.6,
                    max_output_tokens=1200,
                )
                text = (response.text or "").strip()
                if not text:
                    raise AIQuizError("Empty response from OpenAI")

                question = self._parse_payload(text)
                question = self._normalize_question(question, topic, difficulty)
                self._validate_question(question)
                return question

            except Exception as exc:  # noqa: BLE001 - want one clean retry path
                last_error = exc
                logger.warning(
                    "AI quiz generation attempt %s/%s failed: %s",
                    attempt,
                    max_attempts,
                    exc,
                )

        logger.warning(
            "Falling back to local AI quiz question generator after provider failures: %s",
            last_error,
        )
        return self._build_local_fallback_question(
            topic=topic,
            difficulty=difficulty,
            weak_concepts=weak_concepts or [],
            previous_questions=list(previous_questions or []),
        )

    def _generate_with_model_fallback(
        self,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
    ):
        models_to_try = [self.model, *[m for m in self.FALLBACK_MODELS if m != self.model]]
        last_exc: Optional[Exception] = None

        for model_name in models_to_try:
            try:
                _, text = chat_completions(
                    messages=[
                        {"role": "system", "content": "Return ONLY valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    api_key=self.api_key,
                    model=model_name,
                    max_tokens=max_output_tokens,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    timeout=30,
                    fallback_models=(),
                )
                class _Resp:
                    def __init__(self, t: str):
                        self.text = t
                return _Resp(text)
            except RuntimeError as exc:
                last_exc = exc
                text = str(exc).lower()
                if "404" in text or "not found" in text or "429" in text or "quota" in text:
                    logger.warning("AI quiz model '%s' unavailable, trying fallback: %s", model_name, exc)
                    continue
                raise

        raise AIQuizError(f"No available OpenAI model for AI quiz generation: {last_exc}")

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        topic: str,
        difficulty: str,
        weak_concepts: List[str],
        previous_questions: List[str],
    ) -> str:
        weak_block = ""
        if weak_concepts:
            weak_list = "\n".join(f"- {c}" for c in weak_concepts[:8])
            weak_block = (
                "\nWEAK CONCEPTS (the learner has previously failed these — "
                "prioritise generating a question that targets ONE of them):\n"
                f"{weak_list}\n"
            )

        history_block = ""
        if previous_questions:
            recent = previous_questions[-6:]
            history_list = "\n".join(f"- {q}" for q in recent)
            history_block = (
                "\nALREADY ASKED IN THIS SESSION (do not repeat or paraphrase):\n"
                f"{history_list}\n"
            )

        coding_signals = [topic, *weak_concepts[:8]]
        is_coding_topic = any(topic_looks_like_coding(x) for x in coding_signals if x)

        if is_coding_topic:
            difficulty_guide = coding_ai_quiz_difficulty_guides()[difficulty]
            coding_style_block = f"\n{coding_ai_quiz_style_block()}\n"
            session_category = pick_coding_ai_quiz_category_instruction()
            coding_style_block += f"\n{session_category}\n"
        else:
            difficulty_guide = {
                "basic": "Definitions, recall, simple identification questions.",
                "intermediate": "Application of concepts, comparisons, common pitfalls.",
                "advanced": "Scenario analysis, optimisation, debugging, trade-offs.",
                "expert": "Complex architecture decisions, edge-case reasoning, and multi-step trade-off analysis.",
            }[difficulty]
            coding_style_block = ""

        return f"""You are an expert tutor generating ONE multiple-choice quiz question in real time.

TOPIC: {topic}
DIFFICULTY: {difficulty} — {difficulty_guide}
{coding_style_block}{weak_block}{history_block}
STRICT REQUIREMENTS:
1. Generate exactly ONE question.
2. Provide exactly 4 options labelled A, B, C, D.
3. Exactly ONE option is correct.
4. All distractors must be plausible — never silly.
5. Reasoning must explain WHY the correct option is right AND why each
   wrong option is wrong (one short sentence each).
6. Include a concise concept_summary (1-2 sentences) explaining the
   underlying idea.
7. Include a short memory_tip (mnemonic, analogy, or rule of thumb).
8. Difficulty must be exactly "{difficulty}".
9. Topic must be exactly "{topic}".
10. Output VALID JSON only — no markdown, no commentary.

Return EXACTLY this JSON shape:
{{
  "question": "string",
  "options": {{
    "A": "first option text",
    "B": "second option text",
    "C": "third option text",
    "D": "fourth option text"
  }},
  "correct_answer": "A",
  "why_correct": "Explain specifically using topic concepts from this question only.",
  "why_wrong": {{
    "A": "Why wrong in context of this question",
    "B": "Why wrong in context of this question",
    "C": "Why wrong in context of this question",
    "D": "Why wrong in context of this question"
  }},
  "concept_summary": "string",
  "memory_tip": "string",
  "difficulty": "{difficulty}",
  "topic": "{topic}"
}}

Rules:
- Never use generic phrases.
- Mention exact keywords from the question/options.
- Every explanation must be unique.
- Wrong-answer explanations must describe the concrete mistake.
- Use topic-specific terminology only."""

    # ------------------------------------------------------------------
    # Parsing & validation
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_payload(text: str) -> Dict[str, Any]:
        """Best-effort JSON extraction from an OpenAI response."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Last resort: pull out the outermost { ... } block.
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise AIQuizError(f"Could not parse OpenAI JSON: {exc}") from exc

        raise AIQuizError("OpenAI response did not contain valid JSON")

    @staticmethod
    def _question_keywords(question_text: str, topic: str) -> List[str]:
        base = f"{question_text} {topic}".lower()
        tokens = re.findall(r"[a-z][a-z0-9_&/-]{2,}", base)
        stop = {
            "which", "what", "when", "where", "about", "with", "from", "into", "this",
            "that", "your", "best", "most", "option", "correct", "topic", "level",
        }
        cleaned = [t for t in tokens if t not in stop]
        return list(dict.fromkeys(cleaned))[:4]

    @staticmethod
    def _default_why_correct(question_text: str, topic: str, correct_option: str) -> str:
        keywords = AIQuizService._question_keywords(question_text, topic)
        focus = ", ".join(keywords) if keywords else topic
        option_excerpt = (correct_option or "the selected answer").strip().rstrip(".")
        return (
            f"This is correct because it directly applies {focus} in {topic}: "
            f"\"{option_excerpt}\" matches the decision constraints in this question."
        )

    @staticmethod
    def _default_memory_tip(question_text: str, topic: str, correct_option: str) -> str:
        keywords = AIQuizService._question_keywords(question_text, topic)
        cue = (keywords[0] if keywords else topic).replace("_", " ")
        option_excerpt = (correct_option or "").strip()
        option_excerpt = option_excerpt[:48] + ("..." if len(option_excerpt) > 48 else "")
        return f"Remember {cue}: pick the option that says \"{option_excerpt}\" first."

    @staticmethod
    def _normalize_question(
        question: Dict[str, Any],
        topic: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        """Normalise the raw payload into the canonical schema."""
        if not isinstance(question, dict):
            raise AIQuizError("Question payload must be a JSON object")

        # Options can come back as either a list or a {A,B,C,D} dict — normalise.
        options = question.get("options")
        options_map: Dict[str, str] = {}
        if isinstance(options, dict):
            for letter in ANSWER_LETTERS:
                value = options.get(letter, "")
                value = str(value).strip()
                value = re.sub(rf"^\s*{letter}\)\s*", "", value, flags=re.IGNORECASE).strip()
                options_map[letter] = value
        elif isinstance(options, list):
            for idx, value in enumerate(options[:4]):
                letter = ANSWER_LETTERS[idx]
                text_value = str(value).strip()
                text_value = re.sub(rf"^\s*{letter}\)\s*", "", text_value, flags=re.IGNORECASE).strip()
                options_map[letter] = text_value
        else:
            raise AIQuizError("options must be a list or letter->text dict")

        # Correct answer normalisation.
        correct = str(question.get("correct_answer", "")).strip().upper()
        if correct.endswith(")"):
            correct = correct[:-1]
        if correct not in ANSWER_LETTERS:
            raise AIQuizError(f"correct_answer must be one of {ANSWER_LETTERS}")

        reasoning = question.get("reasoning") or {}
        if not isinstance(reasoning, dict):
            reasoning = {"why_correct": str(reasoning), "wrong_options": []}

        question_text = str(question.get("question", "")).strip()
        correct_option_text = options_map.get(correct, "")

        why_correct = (
            str(question.get("why_correct", "")).strip()
            or str(reasoning.get("why_correct", "")).strip()
            or AIQuizService._default_why_correct(question_text, topic, correct_option_text)
        )

        why_wrong_map: Dict[str, str] = {}
        raw_why_wrong = question.get("why_wrong")
        if isinstance(raw_why_wrong, dict):
            for letter in ANSWER_LETTERS:
                value = str(raw_why_wrong.get(letter, "")).strip()
                if value:
                    why_wrong_map[letter] = value

        wrong_options_raw = reasoning.get("wrong_options") or []
        if isinstance(wrong_options_raw, list):
            for entry in wrong_options_raw:
                if isinstance(entry, dict):
                    letter = str(entry.get("option", "")).strip().upper()
                    reason = str(entry.get("reason", "")).strip()
                elif isinstance(entry, str):
                    letter, _, reason = entry.partition(":")
                    letter = letter.strip().upper()
                    reason = reason.strip()
                else:
                    continue
                if letter in ANSWER_LETTERS and reason and letter not in why_wrong_map:
                    why_wrong_map[letter] = reason

        for letter in ANSWER_LETTERS:
            option_text = options_map.get(letter, "")
            if letter == correct:
                if not why_wrong_map.get(letter):
                    why_wrong_map[letter] = (
                        f"{letter} is actually correct for this question because it matches {topic} requirements."
                    )
                continue
            if not why_wrong_map.get(letter):
                why_wrong_map[letter] = AIQuizService._build_dynamic_reasoning(
                    option_text,
                    topic,
                    difficulty,
                    is_correct=False,
                )

        wrong_options: List[Dict[str, str]] = [
            {"option": letter, "reason": why_wrong_map.get(letter, "")}
            for letter in ANSWER_LETTERS
            if letter != correct
        ]

        return {
            "question": question_text,
            "options": options_map,
            "correct_answer": correct,
            "why_correct": why_correct,
            "why_wrong": why_wrong_map,
            "reasoning": {
                "why_correct": why_correct,
                "wrong_options": wrong_options,
            },
            "concept_summary": str(question.get("concept_summary", "")).strip()
            or f"{topic} questions here focus on applying concepts to concrete decision points.",
            "memory_tip": str(question.get("memory_tip", "")).strip()
            or AIQuizService._default_memory_tip(question_text, topic, correct_option_text),
            # Enforce requested difficulty for the full session/question pipeline.
            "difficulty": difficulty,
            "topic": str(question.get("topic", topic)).strip() or topic,
        }

    @staticmethod
    def _validate_question(question: Dict[str, Any]) -> None:
        if not question.get("question"):
            raise AIQuizError("Question text is empty")
        options = question.get("options")
        if not isinstance(options, dict):
            raise AIQuizError("Question options must be an A/B/C/D object")
        if sorted(options.keys()) != list(ANSWER_LETTERS):
            raise AIQuizError("Question must have exactly 4 options")
        if question["correct_answer"] not in ANSWER_LETTERS:
            raise AIQuizError("correct_answer must be one of A/B/C/D")
        if not question.get("why_correct"):
            raise AIQuizError("why_correct is missing")
        why_wrong = question.get("why_wrong")
        if not isinstance(why_wrong, dict):
            raise AIQuizError("why_wrong must be an object keyed by A/B/C/D")
        for letter in ANSWER_LETTERS:
            reason = str(why_wrong.get(letter, "")).strip()
            if not reason:
                raise AIQuizError(f"why_wrong.{letter} is required")
        if question["difficulty"] not in ALLOWED_DIFFICULTIES:
            raise AIQuizError("difficulty must be basic/intermediate/advanced/expert")

    @staticmethod
    def _build_dynamic_reasoning(
        option_text: str,
        concept: str,
        difficulty: str,
        *,
        is_correct: bool,
    ) -> str:
        """
        Build short, option-specific reasoning to avoid repeated generic feedback.
        """
        cleaned_option = (option_text or "").strip().rstrip(".")
        lowered = cleaned_option.lower()
        concept_label = (concept or "the concept").strip()

        if is_correct:
            if difficulty == "basic":
                return (
                    f"This is correct because it starts with fundamentals for {concept_label} "
                    "before moving to harder material."
                )
            if difficulty == "advanced":
                return (
                    f"This is correct because it balances trade-offs and correctness when applying {concept_label}."
                )
            if difficulty == "expert":
                return (
                    f"This is correct because it frames constraints and edge cases before committing to a design for {concept_label}."
                )
            return (
                f"This is correct because it applies {concept_label} in context instead of relying on a one-size-fits-all rule."
            )

        if "memor" in lowered:
            return (
                f"This is incorrect because memorization alone does not show practical understanding of {concept_label}."
            )
        if "skip" in lowered or "advanced" in lowered:
            return (
                f"This is incorrect because skipping fundamentals weakens later decisions about {concept_label}."
            )
        if "tool" in lowered or "syntax" in lowered:
            return (
                f"This is incorrect because tooling syntax without concept mastery does not transfer well to new {concept_label} problems."
            )
        if "edge case" in lowered or "failure" in lowered:
            return (
                f"This is incorrect because ignoring edge cases creates fragile outcomes for {concept_label}."
            )
        if "optimiz" in lowered and "correct" in lowered:
            return (
                f"This is incorrect because optimization before correctness leads to fast but wrong results in {concept_label}."
            )
        if "first working" in lowered or "first" in lowered:
            return (
                f"This is incorrect because stopping at the first working idea prevents comparing better approaches for {concept_label}."
            )
        if "all scenarios" in lowered or "regardless of context" in lowered:
            return (
                f"This is incorrect because {concept_label} decisions depend on context, not a single fixed pattern."
            )

        return (
            f"This is incorrect because it conflicts with the expected reasoning approach for {concept_label} at {difficulty} level."
        )

    @staticmethod
    def _fallback_seed(topic: str, concept: str, difficulty: str, sequence: int) -> int:
        key = f"{topic}|{concept}|{difficulty}|{sequence}"
        return sum(ord(ch) for ch in key)

    @staticmethod
    def _build_dynamic_fallback_material(
        topic: str,
        concept: str,
        difficulty: str,
        sequence: int,
    ) -> Dict[str, Any]:
        rng = random.Random(AIQuizService._fallback_seed(topic, concept, difficulty, sequence))

        question_templates = [
            "For {topic}, which approach best handles {concept}?",
            "In a {topic} workflow, what is the strongest strategy for {concept}?",
            "When practicing {topic}, which option reflects correct reasoning about {concept}?",
            "Which statement is most accurate for {concept} in the context of {topic}?",
        ]

        correct_templates = {
            "basic": [
                "Start by defining {concept} clearly in {topic}, then validate it with a small practical example.",
                "Use the core {concept} principle first, then add complexity gradually inside {topic}.",
            ],
            "intermediate": [
                "Compare two workable {topic} approaches for {concept} and choose based on context constraints.",
                "Apply {concept} with scenario-based reasoning rather than memorized rules in {topic}.",
            ],
            "advanced": [
                "Prioritize correctness and maintainability for {concept} before performance tuning in {topic}.",
                "Evaluate trade-offs explicitly (reliability, complexity, performance) when implementing {concept} in {topic}.",
            ],
            "expert": [
                "Model failure modes and constraints first, then design {concept} for resilient behavior in {topic}.",
                "Choose an architecture for {concept} that remains correct under edge cases and scale in {topic}.",
            ],
        }

        distractor_templates = {
            "basic": [
                "Treat {concept} as theory only and skip implementation in {topic}.",
                "Jump to advanced patterns before understanding {concept} basics in {topic}.",
                "Focus only on syntax tricks instead of {concept} behavior in {topic}.",
            ],
            "intermediate": [
                "Reuse one fixed pattern for {concept} in all {topic} scenarios without comparison.",
                "Pick the first solution that works and skip trade-off checks for {concept} in {topic}.",
                "Memorize examples of {concept} but avoid applying them to real {topic} cases.",
            ],
            "advanced": [
                "Optimize performance first and verify {concept} correctness later in {topic}.",
                "Ignore edge cases so {concept} appears simpler inside {topic}.",
                "Increase abstraction for {concept} without validating maintainability in {topic}.",
            ],
            "expert": [
                "Design {concept} for the happy path only and ignore failure isolation in {topic}.",
                "Choose the fastest-looking architecture for {concept} without documenting assumptions in {topic}.",
                "Hide complexity for {concept} with extra layers before proving behavior in {topic}.",
            ],
        }

        summary_templates = [
            "{concept} in {topic} works best when decisions are justified by constraints and context.",
            "Reliable {topic} progress comes from applying {concept} with explicit reasoning, not shortcuts.",
            "Mastering {concept} in {topic} means validating correctness before scaling complexity.",
        ]
        tip_templates = [
            "{concept}: constraints first, implementation second.",
            "For {topic}, test {concept} on a small case before scaling.",
            "Rule of thumb: clarify {concept}, compare options, then optimize.",
        ]

        question_text = rng.choice(question_templates).format(topic=topic, concept=concept)
        correct = rng.choice(correct_templates.get(difficulty, correct_templates["intermediate"])).format(
            topic=topic,
            concept=concept,
        )
        distractor_pool = [d.format(topic=topic, concept=concept) for d in distractor_templates.get(difficulty, distractor_templates["intermediate"])]
        rng.shuffle(distractor_pool)
        distractors = distractor_pool[:3]
        concept_summary = rng.choice(summary_templates).format(topic=topic, concept=concept)
        memory_tip = rng.choice(tip_templates).format(topic=topic, concept=concept)

        return {
            "question_text": question_text,
            "correct": correct,
            "distractors": distractors,
            "concept_summary": concept_summary,
            "memory_tip": memory_tip,
        }

    @staticmethod
    def _build_local_fallback_question(
        topic: str,
        difficulty: str,
        weak_concepts: List[str],
        previous_questions: List[str],
    ) -> Dict[str, Any]:
        """
        Build a dynamic local fallback question when OpenAI quota/errors occur.
        This keeps quiz flow functional without relying on pre-stored question banks.
        """
        concept = (weak_concepts[0] if weak_concepts else topic).strip() or topic
        sequence = len(previous_questions) + 1

        material = AIQuizService._build_dynamic_fallback_material(
            topic=topic,
            concept=concept,
            difficulty=difficulty,
            sequence=sequence,
        )
        question_text = material["question_text"]
        correct = material["correct"]
        distractors = material["distractors"]
        summary = material["concept_summary"]
        tip = material["memory_tip"]

        options_payload = [correct, *distractors]
        random.shuffle(options_payload)

        options: Dict[str, str] = {}
        correct_letter = "A"
        for idx, text in enumerate(options_payload):
            letter = ANSWER_LETTERS[idx]
            options[letter] = text
            if text == correct:
                correct_letter = letter

        why_wrong: Dict[str, str] = {}
        wrong_options = []
        for idx, option_text in enumerate(options_payload):
            letter = ANSWER_LETTERS[idx]
            if letter == correct_letter:
                why_wrong[letter] = (
                    f"{letter} is the correct choice because it aligns with {topic} fundamentals for {concept}."
                )
                continue
            reason = AIQuizService._build_dynamic_reasoning(
                option_text,
                concept,
                difficulty,
                is_correct=False,
            )
            why_wrong[letter] = reason
            wrong_options.append({"option": letter, "reason": reason})

        why_correct = AIQuizService._build_dynamic_reasoning(
            correct,
            concept,
            difficulty,
            is_correct=True,
        )

        return {
            "question": question_text,
            "options": options,
            "correct_answer": correct_letter,
            "why_correct": why_correct,
            "why_wrong": why_wrong,
            "reasoning": {
                "why_correct": why_correct,
                "wrong_options": wrong_options,
            },
            "concept_summary": summary,
            "memory_tip": tip,
            "difficulty": difficulty,
            "topic": topic,
        }


__all__ = ["AIQuizService", "AIQuizError", "ALLOWED_DIFFICULTIES", "ANSWER_LETTERS"]
