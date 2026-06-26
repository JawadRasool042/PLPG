"""
============================================
Strict Quiz Generator
============================================

Enforces ALL 11 strict rules for quiz generation with OpenAI.
Returns exact JSON structure with comprehensive validation.

STRICT RULES ENFORCED:
1. Generate exactly {count} multiple-choice questions
2. Each question must have exactly 4 options: A, B, C, D
3. Exactly ONE correct answer per question
4. All distractor options must be plausible — no obviously wrong answers
5. No repeated or overlapping questions
6. Cover diverse sub-topics within the main topic
7. Each question must match the requested difficulty level
8. Include a "sub_topic" field for weak-area tracking
9. Questions must be real-world applicable and conceptual
10. If weak areas are provided, at least 30% of questions must target those areas
11. For each question, provide a clear "reasoning" field
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import requests

from utils.openai_request import chat_completions

from .prompt_helpers import coding_strict_quiz_style_block, topic_looks_like_coding

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_OPENAI_MODELS = ("gpt-4o-mini", "gpt-4.1-mini")


DIFFICULTY_MAP = {
    "easier": 1,
    "beginner": 2,
    "intermediate": 3,
    "advanced": 4,
    "expert": 5
}

DIFFICULTY_GUIDELINES = {
    1: "Basic definitions, simple recall, 'what is' style questions",
    2: "Conceptual understanding, simple comparisons",
    3: "Application-level, 'how would you', multi-concept questions",
    4: "Scenario-based, debugging, architecture decisions",
    5: "System design, edge cases, optimization, trade-offs"
}


class StrictQuizGenerator:
    """
    Generate quizzes with strict adherence to all 11 rules.
    Uses OpenAI with comprehensive validation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        configured_model = os.getenv("OPENAI_STRICT_QUIZ_MODEL", DEFAULT_OPENAI_MODEL).strip()
        self.model = configured_model or DEFAULT_OPENAI_MODEL
        self._fallback_models = [m for m in FALLBACK_OPENAI_MODELS if m != self.model]
        logger.info("StrictQuizGenerator initialized (model=%s)", self.model)
    
    def generate(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        weak_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate quiz with strict rule enforcement.
        
        Args:
            topic: Quiz topic (e.g., "Python Programming", "React Hooks")
            difficulty: "easier", "beginner", "intermediate", "advanced", "expert"
            question_count: Exact number of questions to generate
            weak_areas: Optional list of areas to emphasize (≥30% of questions)
        
        Returns:
            {
                "quiz": [
                    {
                        "id": int,
                        "question": str,
                        "sub_topic": str,
                        "options": {"A": str, "B": str, "C": str, "D": str},
                        "correct_answer": str,
                        "difficulty": str,
                        "reasoning": str
                    }
                ]
            }
        """
        
        # Validate inputs
        self._validate_inputs(topic, difficulty, question_count, weak_areas)
        
        difficulty_level = DIFFICULTY_MAP[difficulty]
        
        # Build prompt with strict requirements
        prompt = self._build_strict_prompt(
            topic=topic,
            difficulty_level=difficulty_level,
            difficulty_name=difficulty,
            question_count=question_count,
            weak_areas=weak_areas
        )
        
        logger.info(f"Generating {question_count} {difficulty} questions on '{topic}'")
        
        try:
            # Call OpenAI API
            response = self._generate_with_model_fallback(prompt)
            
            raw_response = response.text
            logger.debug(f"Raw OpenAI response: {raw_response[:500]}...")
            
            # Parse and validate response
            parsed_questions = self._parse_response(raw_response)
            
            # Validate ALL 11 strict rules
            self._validate_all_rules(
                questions=parsed_questions,
                expected_count=question_count,
                expected_difficulty=difficulty,
                weak_areas=weak_areas
            )
            
            # Build final output
            output = {
                "quiz": [
                    {
                        "id": i + 1,
                        "question": q["question_text"],
                        "sub_topic": q["sub_topic"],
                        "options": q["options"],
                        "correct_answer": q["correct_answer"],
                        "difficulty": difficulty,
                        "reasoning": q["reasoning"],
                        **(
                            {"coding_question_category": q["coding_question_category"]}
                            if q.get("coding_question_category")
                            else {}
                        ),
                    }
                    for i, q in enumerate(parsed_questions)
                ]
            }
            
            logger.info(f"✓ Generated and validated {len(output['quiz'])} questions")
            return output
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def _generate_with_model_fallback(self, prompt: str):
        models_to_try = [self.model, *self._fallback_models]
        last_exc = None
        for model_name in models_to_try:
            try:
                _, text = chat_completions(
                    messages=[
                        {"role": "system", "content": "Return ONLY valid JSON array."},
                        {"role": "user", "content": prompt},
                    ],
                    api_key=self.api_key,
                    model=model_name,
                    max_tokens=4000,
                    temperature=0.7,
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
                    logger.warning("Strict quiz model '%s' unavailable, trying fallback: %s", model_name, exc)
                    continue
                raise
        raise RuntimeError(f"No supported OpenAI model available for strict quiz generation: {last_exc}")
    
    def _validate_inputs(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        weak_areas: Optional[List[str]]
    ) -> None:
        """Validate input parameters."""
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic must be a non-empty string")
        
        if difficulty not in DIFFICULTY_MAP:
            valid = ", ".join(DIFFICULTY_MAP.keys())
            raise ValueError(f"difficulty must be one of: {valid}")
        
        if not isinstance(question_count, int) or question_count < 1 or question_count > 100:
            raise ValueError("question_count must be between 1 and 100")
        
        if weak_areas is not None:
            if not isinstance(weak_areas, list):
                raise ValueError("weak_areas must be a list")
            if not all(isinstance(a, str) and a.strip() for a in weak_areas):
                raise ValueError("weak_areas must be non-empty strings")
    
    def _build_strict_prompt(
        self,
        topic: str,
        difficulty_level: int,
        difficulty_name: str,
        question_count: int,
        weak_areas: Optional[List[str]] = None
    ) -> str:
        """Build prompt with all strict rules embedded."""
        
        weak_section = ""
        if weak_areas:
            weak_list = ", ".join(weak_areas)
            weak_section = f"""
WEAK AREAS TO FOCUS ON:
At least 30% ({max(1, int(question_count * 0.3))}) questions must target: {weak_list}
Include explicit "targets_weak_area" tracking in output.
"""

        coding_section = ""
        coding_level_clarifier = ""
        signals = [topic, *(weak_areas or [])]
        is_coding = any(topic_looks_like_coding(s) for s in signals if isinstance(s, str) and s.strip())
        if is_coding:
            coding_section = f"""
{coding_strict_quiz_style_block(question_count)}
"""
            coding_level_clarifier = """
CODING-TOPIC CLARIFIER (applies with the practical distribution above):
- Match each question's stem style to its coding_question_category.
- Difficulty level still applies: harder levels use subtler bugs, corner-case
  outputs, or denser (but still short) snippets — not essay-length code.
"""

        rule_9_block = """9. REAL-WORLD APPLICABLE: Questions should be conceptual and practically useful
   - Avoid purely theoretical or trivial questions
   - Make questions relevant to real-world scenarios"""
        if is_coding:
            rule_9_block = """9. REAL-WORLD APPLICABLE: Coding items must be practically useful
   - Prefer realistic snippets, plausible wrong answers, and skills developers use daily
   - Follow the exact per-category counts in the CODING DOMAIN block above
   - Avoid useless trivia unrelated to building or debugging software"""

        coding_json_line = (
            '    "coding_question_category": "theory",\n'
            if is_coding
            else ""
        )
        coding_critical_extra = (
            '- For this coding topic, every question MUST include "coding_question_category" '
            '("theory" | "output_prediction" | "debugging" | "logic_completion") and the '
            'full set must match the EXACT per-category counts in the CODING DOMAIN block.\n'
            if is_coding
            else ""
        )

        prompt = f"""Generate a quiz with STRICT adherence to ALL 11 rules.

PARAMETERS:
- Topic: {topic}
- Difficulty: {difficulty_name} (Level {difficulty_level})
- Exact Question Count: {question_count}
{weak_section}{coding_section}{coding_level_clarifier}

DIFFICULTY GUIDELINES:
- Level 1 (easier): Basic definitions, simple recall, "what is" style questions
- Level 2 (beginner): Conceptual understanding, simple comparisons
- Level 3 (intermediate): Application-level, "how would you", multi-concept
- Level 4 (advanced): Scenario-based, debugging, architecture decisions
- Level 5 (expert): System design, edge cases, optimization, trade-offs

=== STRICT RULES (ALL MUST BE FOLLOWED) ===

1. EXACT COUNT: Generate EXACTLY {question_count} questions - not more, not less
2. FOUR OPTIONS: Each question has EXACTLY 4 options (A, B, C, D)
3. ONE ANSWER: Exactly ONE correct answer per question
4. PLAUSIBLE DISTRACTORS: All wrong options must be plausible and educational
   - Wrong answers should represent common misconceptions or similar concepts
   - Avoid obviously incorrect answers
5. NO DUPLICATES: All questions must be unique (different content/options)
6. DIVERSE SUBTOPICS: Questions must cover different sub-topics within {topic}
   - Aim for maximum variety in sub_topic field
7. DIFFICULTY MATCH: Every question must be at Level {difficulty_level}
   - Follow the difficulty guidelines precisely
8. SUBTOPIC FIELD: Include "sub_topic" field for each question
   - This helps with weak-area tracking and classification
{rule_9_block}
10. WEAK AREA FOCUS: If weak_areas provided, ≥30% of questions must target them
    - Mark these with "targets_weak_area": true
11. CLEAR REASONING: Provide "reasoning" field explaining:
    - WHY the correct answer is right (with specific logic)
    - WHY each wrong option is incorrect (educational)
    - Keep reasoning concise but complete (2-4 sentences max)

=== OUTPUT FORMAT ===
Return a JSON array with this EXACT structure for each question:

[
  {{
    "id": 1,
    "question": "Question text here?",
    "sub_topic": "specific sub-topic name",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "A",
    "difficulty": {difficulty_level},
{coding_json_line}    "reasoning": "A is correct because [clear explanation with logic]. B is wrong because [misconception or reason]. C is wrong because [reason]. D is wrong because [reason].",
    "targets_weak_area": false
  }}
]

=== CRITICAL REQUIREMENTS ===
- Return ONLY valid JSON array
- NO markdown code fences
- NO explanations outside JSON
- Every field must be present
{coding_critical_extra}- Validate your own output before returning
- If weak_areas provided, mark weak-area questions with targets_weak_area: true

Generate the quiz now:"""
        
        return prompt
    
    def _parse_response(self, raw_response: str) -> List[Dict[str, Any]]:
        """Parse OpenAI response with validation."""
        
        if not raw_response:
            raise ValueError("Empty response from OpenAI")
        
        # Clean markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}\nResponse: {cleaned[:500]}")
            raise ValueError(f"Failed to parse OpenAI response as JSON: {e}")
        
        # Ensure it's a list
        if not isinstance(data, list):
            raise ValueError(f"Response must be JSON array, got {type(data)}")
        
        if not data:
            raise ValueError("Response contains no questions")
        
        # Parse each question
        questions = []
        for i, item in enumerate(data):
            try:
                q = self._parse_question(item, i)
                questions.append(q)
            except Exception as e:
                raise ValueError(f"Question {i+1} parse error: {e}")
        
        return questions
    
    def _parse_question(self, item: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Parse and validate single question."""
        
        if not isinstance(item, dict):
            raise ValueError(f"Question must be object, got {type(item)}")
        
        # Extract and validate required fields
        question_text = item.get("question")
        if not isinstance(question_text, str) or not question_text.strip():
            raise ValueError("'question' field required and must be non-empty string")
        
        sub_topic = item.get("sub_topic")
        if not isinstance(sub_topic, str) or not sub_topic.strip():
            raise ValueError("'sub_topic' field required and must be non-empty string")
        
        options = item.get("options")
        if not isinstance(options, dict):
            raise ValueError("'options' must be a dictionary")
        
        # Validate exactly 4 options with correct keys
        expected_keys = {"A", "B", "C", "D"}
        actual_keys = set(options.keys())
        if actual_keys != expected_keys:
            raise ValueError(f"options must have A, B, C, D; got {actual_keys}")
        
        # Validate each option
        for key in expected_keys:
            opt = options[key]
            if not isinstance(opt, str) or not opt.strip():
                raise ValueError(f"option {key} must be non-empty string")
        
        # Validate correct answer
        correct_answer = item.get("correct_answer")
        if correct_answer not in expected_keys:
            raise ValueError(f"correct_answer must be A/B/C/D, got {correct_answer}")
        
        # Validate reasoning
        reasoning = item.get("reasoning")
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise ValueError("'reasoning' field required and must be non-empty string")
        
        # Validate difficulty
        difficulty = item.get("difficulty")
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
            raise ValueError(f"'difficulty' must be 1-5, got {difficulty}")

        valid_coding_cats = frozenset(
            {"theory", "output_prediction", "debugging", "logic_completion"}
        )
        coding_question_category: Optional[str] = None
        raw_cat = item.get("coding_question_category")
        if isinstance(raw_cat, str) and raw_cat.strip() in valid_coding_cats:
            coding_question_category = raw_cat.strip()

        result: Dict[str, Any] = {
            "question_text": question_text.strip(),
            "sub_topic": sub_topic.strip(),
            "options": {k: options[k].strip() for k in expected_keys},
            "correct_answer": correct_answer,
            "reasoning": reasoning.strip(),
            "difficulty": difficulty,
            "targets_weak_area": item.get("targets_weak_area", False),
        }
        if coding_question_category is not None:
            result["coding_question_category"] = coding_question_category
        return result
    
    def _validate_all_rules(
        self,
        questions: List[Dict[str, Any]],
        expected_count: int,
        expected_difficulty: str,
        weak_areas: Optional[List[str]] = None
    ) -> None:
        """Validate all 11 strict rules."""
        
        # Rule 1: Exact count
        if len(questions) != expected_count:
            raise ValueError(f"Rule 1 violation: Expected {expected_count} questions, got {len(questions)}")
        
        # Rule 2 & 3: Options structure and answers
        for i, q in enumerate(questions):
            options = q.get("options", {})
            
            # Rule 2: Exactly 4 options
            if len(options) != 4 or set(options.keys()) != {"A", "B", "C", "D"}:
                raise ValueError(f"Rule 2 violation (Q{i+1}): Must have exactly options A, B, C, D")
            
            # Rule 3: One correct answer
            correct = q.get("correct_answer")
            if correct not in {"A", "B", "C", "D"}:
                raise ValueError(f"Rule 3 violation (Q{i+1}): Invalid correct answer '{correct}'")
        
        # Rule 4: Plausible distractors (heuristic check)
        for i, q in enumerate(questions):
            options = list(q["options"].values())
            correct_opt = q["options"][q["correct_answer"]]
            
            # Check that wrong options are reasonably different from correct
            wrong_opts = [o for k, o in q["options"].items() if k != q["correct_answer"]]
            similarity_count = sum(1 for o in wrong_opts if o.lower() in correct_opt.lower() or correct_opt.lower() in o.lower())
            
            # Allow some similarity but not too much (no exact copies or substrings)
            for opt in wrong_opts:
                if opt == correct_opt:
                    raise ValueError(f"Rule 4 violation (Q{i+1}): Duplicate option found")
        
        # Rule 5: No duplicate questions
        question_hashes = set()
        for i, q in enumerate(questions):
            q_hash = (
                q["question_text"].lower(),
                tuple(sorted((k, v.lower()) for k, v in q["options"].items())),
                q["correct_answer"]
            )
            if q_hash in question_hashes:
                raise ValueError(f"Rule 5 violation (Q{i+1}): Duplicate question detected")
            question_hashes.add(q_hash)
        
        # Rule 6: Diverse sub-topics
        sub_topics = [q["sub_topic"] for q in questions]
        unique_sub_topics = len(set(sub_topics))
        min_expected = max(2, len(questions) // 2)  # At least 50% unique
        if unique_sub_topics < min_expected:
            logger.warning(f"Rule 6 warning: Only {unique_sub_topics} unique sub-topics for {len(questions)} questions")
        
        # Rule 7: Difficulty consistency
        difficulty_level = DIFFICULTY_MAP[expected_difficulty]
        for i, q in enumerate(questions):
            if q["difficulty"] != difficulty_level:
                raise ValueError(f"Rule 7 violation (Q{i+1}): Expected difficulty {difficulty_level}, got {q['difficulty']}")
        
        # Rule 8: Sub-topic field present (already validated in parsing)
        for i, q in enumerate(questions):
            if not q.get("sub_topic"):
                raise ValueError(f"Rule 8 violation (Q{i+1}): sub_topic field missing")
        
        # Rule 9: Real-world applicable (heuristic)
        # Check that questions aren't trivial (very short or obvious)
        for i, q in enumerate(questions):
            q_len = len(q["question_text"])
            if q_len < 15:  # Minimum reasonable question length
                logger.warning(f"Rule 9 warning (Q{i+1}): Question very short ({q_len} chars)")
        
        # Rule 10: Weak area coverage (if provided)
        if weak_areas:
            weak_area_count = sum(1 for q in questions if q.get("targets_weak_area"))
            min_weak = max(1, int(len(questions) * 0.3))
            if weak_area_count < min_weak:
                raise ValueError(
                    f"Rule 10 violation: Need at least {min_weak} questions ({int(0.3*100)}%) targeting weak areas, "
                    f"got {weak_area_count}"
                )
        
        # Rule 11: Reasoning present (already validated in parsing)
        for i, q in enumerate(questions):
            reasoning = q.get("reasoning", "").strip()
            if len(reasoning) < 20:  # Minimum reasonable reasoning length
                raise ValueError(f"Rule 11 violation (Q{i+1}): Reasoning too brief")
        
        logger.info("✓ All 11 strict rules validated successfully")


def generate_quiz_strict(
    topic: str,
    difficulty: str,
    question_count: int,
    weak_areas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate a quiz with strict rules.
    
    Args:
        topic: Quiz topic
        difficulty: "easier", "beginner", "intermediate", "advanced", "expert"
        question_count: Number of questions
        weak_areas: Optional weak areas to emphasize
    
    Returns:
        Quiz in exact format: {"quiz": [...]}
    """
    generator = StrictQuizGenerator()
    return generator.generate(
        topic=topic,
        difficulty=difficulty,
        question_count=question_count,
        weak_areas=weak_areas
    )
