"""OpenAI remediation lesson generator — one quiz attempt, tutor-style correct-answer teaching."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from utils.openai_request import chat_completions

logger = logging.getLogger(__name__)

MIN_EXPLANATION_CHARS = int(os.getenv("REMEDIATION_MIN_EXPLANATION_CHARS", "350"))
MIN_EXPLANATION_WORDS = int(os.getenv("REMEDIATION_MIN_EXPLANATION_WORDS", "100"))
LESSON_FORMAT_VERSION = 7
OPENAI_MODEL = os.getenv("OPENAI_REMEDIATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
JSON_SYSTEM = "You must respond with valid JSON only."

EXPLANATION_TEACHING_RULES = [
    "Teach the concept as if explaining to someone learning it for the first time.",
    "Clearly describe what the concept is, how it works, and why the correct answer is correct.",
    "Explain reasoning step by step.",
    "For code: walk through execution line by line, trace variables, explain final output.",
    "For theory: define the concept, its purpose, when/why it is used, and key rules.",
    "Use clear beginner-friendly language. Be comprehensive — not one or two sentences.",
    "Do NOT include a 'Why your answer was incorrect' section or explain the student's mistake.",
    "Do NOT copy short quiz feedback verbatim — expand it into real teaching.",
    "Stay strictly scoped to this one quiz question — no unrelated topics.",
]

SECTION_FIELDS = frozenset(
    {
        "question_index",
        "topic",
        "question",
        "your_answer",
        "correct_answer",
        "is_correct",
        "explanation",
    }
)


class RemediationLessonGeneratorError(Exception):
    pass


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise RemediationLessonGeneratorError("Empty OpenAI response")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise RemediationLessonGeneratorError("Could not parse lesson JSON")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise RemediationLessonGeneratorError("Could not parse lesson JSON") from exc
    if not isinstance(parsed, dict):
        raise RemediationLessonGeneratorError("Lesson root must be an object")
    return parsed


def _format_options(options: Any) -> List[str]:
    if isinstance(options, list):
        return [str(o) for o in options]
    if isinstance(options, dict):
        return [f"{k}) {options.get(k, '')}" for k in ("A", "B", "C", "D") if k in options]
    return []


def _option_text_for_letter(options: List[str], letter: str) -> str:
    letter = (letter or "").strip().upper()
    if not letter:
        return ""
    for opt in options:
        s = str(opt).strip()
        upper = s.upper()
        if upper.startswith(f"{letter})") or upper.startswith(f"{letter}."):
            return s
    return ""


def _format_answer_display(letter: str, options: List[str]) -> str:
    """Human-readable answer: letter plus full option text when available."""
    letter = (letter or "").strip().upper()
    if not letter:
        return "—"
    line = _option_text_for_letter(options, letter)
    if not line:
        return letter
    body = line.split(")", 1)[-1].strip() if ")" in line else line
    return f"{letter}) {body}" if body else letter


def build_quiz_review_items(
    attempt: Dict[str, Any],
    *,
    ai_session: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Normalize attempt data into rows for lesson generation."""
    results = list(attempt.get("results") or [])
    session_questions = (ai_session or {}).get("questions") or []
    session_answers = {
        int(a.get("questionIndex", -1)): a
        for a in ((ai_session or {}).get("answers") or [])
        if a.get("questionIndex") is not None
    }

    items: List[Dict[str, Any]] = []
    for idx, row in enumerate(results):
        if not isinstance(row, dict):
            continue
        q_idx = int(row.get("questionIndex", idx))
        sq = session_questions[q_idx] if q_idx < len(session_questions) else {}
        sa = session_answers.get(q_idx, {})
        options = _format_options(row.get("options") or sq.get("options"))
        user_letter = str(row.get("userAnswer") or sa.get("userAnswer") or "").strip().upper()
        correct_letter = str(row.get("correctAnswer") or sq.get("correct_answer") or "").strip().upper()

        items.append(
            {
                "question_index": q_idx,
                "question": str(row.get("question") or sq.get("question") or "").strip(),
                "options": options,
                "user_answer": _format_answer_display(user_letter, options),
                "correct_answer": _format_answer_display(correct_letter, options),
                "is_correct": bool(
                    row.get("isCorrect") if row.get("isCorrect") is not None else sa.get("isCorrect")
                ),
                "concept_summary": str(sq.get("concept_summary") or "").strip(),
                "memory_tip": str(sq.get("memory_tip") or "").strip(),
            }
        )
    return items


def _is_weak_topic(topic: str, question_index: int) -> bool:
    t = (topic or "").strip()
    if not t or len(t) < 2:
        return True
    if re.match(r"^question\s*\d+", t, re.I):
        return True
    if re.match(r"^topic\s*\d+", t, re.I):
        return True
    if re.match(r"^q\d+\b", t, re.I):
        return True
    if f"Q{question_index + 1}" in t:
        return True
    return False


def _extract_code_distinguisher(question: str) -> str:
    text = question or ""
    fn = re.search(r"def\s+(\w+)", text)
    if fn:
        return fn.group(1).replace("_", " ").title()
    var = re.search(r"(\w+)\s*=\s*\[\]", text)
    if var:
        return var.group(1).replace("_", " ").title()
    return ""


def _normalize_topic_for_dedup(topic: str, interest: str) -> str:
    t = (topic or "").lower().strip()
    for prefix in (interest.lower().strip(), "python", "javascript", "html", "css"):
        if prefix and t.startswith(prefix + " "):
            t = t[len(prefix):].strip()
    t = re.sub(r"\s*remediation\s*$", "", t).strip()
    return t


def _infer_topic_fallback(item: Dict[str, Any], interest: str) -> str:
    concept = str(item.get("concept_summary") or "").strip()
    q_idx = int(item.get("question_index", 0))
    if concept and not _is_weak_topic(concept, q_idx):
        return concept[:80]

    question = str(item.get("question") or "").lower()
    if "python" in question or "def " in question or "print(" in question:
        if "=[]" in question or "default" in question or "mutable" in question:
            label = _extract_code_distinguisher(str(item.get("question") or ""))
            return f"Python Mutable Default Arguments ({label})" if label else "Python Mutable Default Arguments"
        if any(k in question for k in ("list", "dict", "tuple")):
            return "Python Data Structures"
        return "Python Fundamentals"
    if any(k in question for k in ("javascript", "js ", "function", "const ", "let ", "var ")):
        if any(k in question for k in ("form", "submit", "button")):
            return "JavaScript Form Validation"
        return "JavaScript Functions"
    if any(k in question for k in ("css", "selector")):
        return "CSS Selectors"
    if any(k in question for k in ("html", "<div", "<span", "tag")):
        return "HTML Tags"
    if "validat" in question:
        return "Form Validation"
    if "sql" in question or "join" in question:
        return "SQL Joins"
    return interest[:40] if interest else "Core Concept"


def _ensure_unique_topics(
    topics: Dict[int, str],
    review_items: List[Dict[str, Any]],
    interest: str,
) -> Dict[int, str]:
    used: set[str] = set()
    result: Dict[int, str] = {}

    for item in sorted(review_items, key=lambda r: int(r.get("question_index", 0))):
        idx = int(item.get("question_index", 0))
        base = (topics.get(idx) or _infer_topic_fallback(item, interest)).strip() or "Core Concept"
        distinguisher = _extract_code_distinguisher(str(item.get("question") or ""))
        if distinguisher and distinguisher.lower() not in base.lower():
            base = f"{base} ({distinguisher})"

        candidate = base
        part = 2
        while _normalize_topic_for_dedup(candidate, interest) in {
            _normalize_topic_for_dedup(u, interest) for u in used
        }:
            candidate = f"{base} — Part {part}"
            part += 1
            if part > 10:
                candidate = f"{base} — Q{idx + 1}"
                break

        used.add(candidate)
        result[idx] = candidate
    return result


def _is_short_explanation(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    if len(stripped.split()) >= MIN_EXPLANATION_WORDS:
        return False
    return len(stripped) < MIN_EXPLANATION_CHARS


def infer_topics_for_questions(
    review_items: List[Dict[str, Any]],
    *,
    interest: str,
) -> Dict[int, str]:
    if not review_items:
        return {}

    prompt = {
        "task": (
            "For EACH quiz question assign a UNIQUE topic heading (2–6 words) for the concept "
            "that question tests. Examples: HTML Tags, CSS Selectors, Python Mutable Default "
            "Arguments, JavaScript Functions, SQL Joins."
        ),
        "subject": interest,
        "rules": [
            "Every question must have a different topic string.",
            "Never use Question 1, Topic 1, or numbering as the topic.",
            "Differentiate similar questions by code pattern, function name, or behavior.",
        ],
        "questions": [
            {
                "question_index": int(i.get("question_index", 0)),
                "question": i.get("question"),
                "concept_hint": i.get("concept_summary"),
            }
            for i in review_items
        ],
        "output_schema": {"topics": [{"question_index": 0, "topic": "string"}]},
    }

    try:
        _, content = chat_completions(
            messages=[
                {
                    "role": "system",
                    "content": "Label quiz questions with concise topic headings. " + JSON_SYSTEM,
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            model=OPENAI_MODEL,
            max_tokens=800,
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=45,
        )
        data = _extract_json(content)
        result: Dict[int, str] = {}
        for row in data.get("topics") or []:
            if not isinstance(row, dict):
                continue
            idx = int(row.get("question_index", -1))
            topic = str(row.get("topic") or "").strip()
            if idx >= 0 and topic and not _is_weak_topic(topic, idx):
                result[idx] = topic
        return result
    except Exception as exc:
        logger.warning("Topic inference failed: %s", exc)
        return {}


def _build_local_explanation(item: Dict[str, Any], topic: str) -> str:
    """Detailed fallback when OpenAI is unavailable."""
    question = str(item.get("question") or "").strip()
    correct = str(item.get("correct_answer") or "").strip()
    concept = str(item.get("concept_summary") or "").strip()
    tip = str(item.get("memory_tip") or "").strip()

    parts: List[str] = [
        f"**{topic}**\n\n"
        "This section teaches the concept behind this quiz question so you can answer it "
        "correctly on your next attempt."
    ]

    if concept:
        parts.append(f"**What this question tests**\n\n{concept}")

    if "def " in question and "=[]" in question:
        parts.append(
            "**Mutable default arguments in Python**\n\n"
            "When a function uses a mutable default like `b=[]`, that list is created once "
            "when Python defines the function—not on each call. Every call that relies on the "
            "default shares the same list object. If the function mutates that list (for example "
            "with `.append()`), later calls see the accumulated changes.\n\n"
            "**Line-by-line approach**\n\n"
            "1. Read the function definition and note which parameters have mutable defaults.\n"
            "2. Trace the first call: what gets appended, what is returned, what the variable holds.\n"
            "3. Trace the second call: the default list already has prior values.\n"
            "4. Compare what `print` outputs with each option."
        )
    elif "def " in question or "print(" in question:
        parts.append(
            "**How to solve code-output questions**\n\n"
            "Execute the code mentally line by line. After each line, record every variable's "
            "value. Watch for shared mutable objects, in-place changes, and return values."
        )
    else:
        parts.append(
            f"**Core idea: {topic}**\n\n"
            "State the definition or rule being tested. Eliminate options that break that rule. "
            "The correct choice matches both the theory and the specific scenario in the question."
        )

    if correct:
        parts.append(f"**Correct answer**\n\n{correct} — this follows from the concept above.")

    if tip:
        parts.append(f"**Remember:** {tip}")

    parts.append(
        "**Before retaking:** explain this topic in your own words, then retry the same quiz."
    )
    return "\n\n".join(parts)


def _generate_single_explanation(
    item: Dict[str, Any],
    topic: str,
    *,
    interest: str,
    level: str,
) -> str:
    q_idx = int(item.get("question_index", 0))
    prompt = {
        "task": (
            "Write a detailed tutor-style explanation of the CORRECT answer for this one "
            "quiz question. Teach only the correct answer and underlying concept."
        ),
        "subject": interest,
        "level": level,
        "topic_heading": topic,
        "question": item.get("question"),
        "student_answer": item.get("user_answer"),
        "correct_answer": item.get("correct_answer"),
        "options": item.get("options") or [],
        "concept_context": item.get("concept_summary") or "",
        "teaching_rules": EXPLANATION_TEACHING_RULES,
        "requirements": {
            "min_words": MIN_EXPLANATION_WORDS,
            "min_paragraphs": 3,
            "forbidden": [
                "Why your answer was incorrect",
                "why the student was wrong",
                "your mistake",
            ],
        },
        "output_schema": {"explanation": "string — multi-paragraph teaching text"},
    }

    try:
        _, content = chat_completions(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write thorough remediation study-guide explanations. "
                        "Multiple paragraphs only. " + JSON_SYSTEM
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            model=OPENAI_MODEL,
            max_tokens=2500,
            temperature=0.4,
            response_format={"type": "json_object"},
            timeout=120,
        )
        text = str(_extract_json(content).get("explanation") or "").strip()
        if not _is_short_explanation(text):
            return text
    except Exception as exc:
        logger.warning("Explanation gen failed for q%s: %s", q_idx, exc)
    return ""


def generate_detailed_explanations(
    review_items: List[Dict[str, Any]],
    topic_map: Dict[int, str],
    *,
    interest: str,
    level: str,
) -> Dict[int, str]:
    """Generate one detailed explanation per question (reliable per-question calls)."""
    result: Dict[int, str] = {}
    for item in review_items:
        idx = int(item.get("question_index", 0))
        topic = topic_map.get(idx) or _infer_topic_fallback(item, interest)
        text = _generate_single_explanation(item, topic, interest=interest, level=level)
        if text and not _is_short_explanation(text):
            result[idx] = text
        else:
            result[idx] = _build_local_explanation(item, topic)
    return result


def _sanitize_section(section: Dict[str, Any]) -> Dict[str, Any]:
    clean = {k: section[k] for k in SECTION_FIELDS if k in section}
    clean.setdefault("question_index", 0)
    clean.setdefault("topic", "Core Concept")
    clean.setdefault("question", "")
    clean.setdefault("your_answer", "—")
    clean.setdefault("correct_answer", "—")
    clean.setdefault("is_correct", False)
    clean.setdefault("explanation", "")
    return clean


def _build_section(
    item: Dict[str, Any],
    topic: str,
    explanation: str,
) -> Dict[str, Any]:
    return _sanitize_section(
        {
            "question_index": int(item.get("question_index", 0)),
            "topic": topic,
            "question": item.get("question") or "",
            "your_answer": item.get("user_answer") or "—",
            "correct_answer": item.get("correct_answer") or "—",
            "is_correct": bool(item.get("is_correct")),
            "explanation": explanation,
        }
    )


def build_fallback_question_sections(
    review_items: List[Dict[str, Any]],
    interest: str,
    *,
    topics: Optional[Dict[int, str]] = None,
    explanations: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    topic_map = topics or {}
    expl_map = explanations or {}
    sections: List[Dict[str, Any]] = []
    for item in review_items:
        idx = int(item.get("question_index", 0))
        topic = topic_map.get(idx) or _infer_topic_fallback(item, interest)
        expl = expl_map.get(idx) or _build_local_explanation(item, topic)
        sections.append(_build_section(item, topic, expl))
    return sections


def _sanitize_lesson(lesson: Dict[str, Any]) -> Dict[str, Any]:
    sections = lesson.get("question_sections") or []
    lesson["question_sections"] = [
        _sanitize_section(s) for s in sections if isinstance(s, dict)
    ]
    lesson["question_sections"] = sorted(
        lesson["question_sections"],
        key=lambda s: int(s.get("question_index", 0)),
    )
    for legacy_key in (
        "mistake_review",
        "struggling_concepts",
        "key_facts",
        "revision_checklist",
    ):
        lesson.pop(legacy_key, None)
    lesson["lesson_format_version"] = LESSON_FORMAT_VERSION
    return lesson


def build_fallback_lesson(
    review_items: List[Dict[str, Any]],
    *,
    interest: str,
    level: str,
    topics: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    raw_topics = topics or infer_topics_for_questions(review_items, interest=interest)
    topic_map = _ensure_unique_topics(raw_topics, review_items, interest)
    explanations = generate_detailed_explanations(
        review_items, topic_map, interest=interest, level=level
    )
    sections = build_fallback_question_sections(
        review_items, interest, topics=topic_map, explanations=explanations
    )
    return _sanitize_lesson(
        {
            "title": f"Study guide: {interest}",
            "summary": (
                "Review each topic below. Each section shows the quiz question, your answer, "
                "the correct answer, and a detailed explanation to help you pass the retake."
            ),
            "question_sections": sections,
            "quick_revision": [f"{s['topic']}: review the key rule." for s in sections[:8]],
        }
    )


def generate_remediation_lesson(
    *,
    interest: str,
    level: str,
    score: float,
    review_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not review_items:
        raise RemediationLessonGeneratorError("No quiz questions available for remediation")

    raw_topics = infer_topics_for_questions(review_items, interest=interest)
    topic_map = _ensure_unique_topics(raw_topics, review_items, interest)
    explanations = generate_detailed_explanations(
        review_items, topic_map, interest=interest, level=level
    )

    sections = [
        _build_section(
            item,
            topic_map.get(int(item.get("question_index", 0))) or _infer_topic_fallback(item, interest),
            explanations.get(int(item.get("question_index", 0)), ""),
        )
        for item in review_items
    ]

    title = f"Study guide: {interest}"
    summary = (
        "Review each topic from your quiz below. Read the full explanation for every question "
        "before retaking the same quiz."
    )
    quick = [f"{s['topic']}: know the key rule." for s in sections[:8]]

    meta_prompt = {
        "task": "Write a short lesson title, 2-sentence summary, and quick_revision bullets.",
        "subject": interest,
        "score_percent": score,
        "section_topics": [s["topic"] for s in sections],
        "rules": [
            "Title should NOT repeat every section topic verbatim.",
            "Summary encourages studying explanations before retake.",
        ],
        "output_schema": {
            "title": "string",
            "summary": "string",
            "quick_revision": ["string — 5-8 bullets"],
        },
    }

    try:
        _, content = chat_completions(
            messages=[
                {"role": "system", "content": "Brief lesson intros. " + JSON_SYSTEM},
                {"role": "user", "content": json.dumps(meta_prompt)},
            ],
            model=OPENAI_MODEL,
            max_tokens=600,
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=45,
        )
        meta = _extract_json(content)
        title = str(meta.get("title") or title)
        summary = str(meta.get("summary") or summary)
        qr = meta.get("quick_revision")
        if isinstance(qr, list) and qr:
            quick = [str(x) for x in qr]
    except Exception as exc:
        logger.warning("Lesson meta generation failed: %s", exc)

    return _sanitize_lesson(
        {
            "title": title,
            "summary": summary,
            "question_sections": sections,
            "quick_revision": quick,
        }
    )


# Kept for service-layer migration checks on stored lessons
def _normalize_lesson_payload(
    data: Dict[str, Any],
    review_items: List[Dict[str, Any]],
    interest: str,
    *,
    topics: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """Rebuild lesson sections from attempt data (drops all legacy fields)."""
    topic_map = topics or {}
    sections = build_fallback_question_sections(
        review_items,
        interest,
        topics=topic_map,
    )
    data["question_sections"] = sections
    data.setdefault("title", f"Study guide: {interest}")
    data.setdefault("summary", "")
    if not data.get("quick_revision"):
        data["quick_revision"] = [f"{s['topic']}: review." for s in sections[:8]]
    return _sanitize_lesson(data)
