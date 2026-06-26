"""
Heuristics and shared prompt fragments for quiz generation.

For programming / CS topics, API-generated quizzes are steered toward PRACTICAL
skills with a fixed category mix (theory, output prediction, debugging,
logic/completion/scenario) — see coding-domain helpers below.
"""

from __future__ import annotations

import random

_CODING_SUBSTRINGS: tuple[str, ...] = (
    "programming",
    "program",
    "developer",
    "software",
    "coding",
    "code",
    "python",
    "javascript",
    "typescript",
    "java",
    "c++",
    "c#",
    "csharp",
    "golang",
    "rust",
    "ruby",
    "php",
    "kotlin",
    "swift",
    "html",
    "css",
    "react",
    "vue",
    "angular",
    "node",
    "django",
    "flask",
    "fastapi",
    "spring",
    "sql",
    "database",
    "mongodb",
    "redis",
    "algorithm",
    "data structure",
    "leetcode",
    "oop",
    "object-oriented",
    "git",
    "docker",
    "kubernetes",
    "bash",
    "shell",
    "machine learning",
    "tensorflow",
    "pytorch",
    "numpy",
    "pandas",
    "scipy",
    "api",
    "backend",
    "frontend",
    "fullstack",
    "full-stack",
    "web dev",
    "computing",
    "computer science",
)


def topic_looks_like_coding(topic: str) -> bool:
    """True when the topic string suggests programming / CS / data / web stack."""
    if not topic or not isinstance(topic, str):
        return False
    t = f" {topic.lower()} "
    return any(s in t for s in _CODING_SUBSTRINGS)


# Coding-domain question mix (strict multi-question quizzes + AI single-question bias)
_CODING_MIX: tuple[tuple[str, float], ...] = (
    ("theory", 0.20),
    ("output_prediction", 0.40),
    ("debugging", 0.25),
    ("logic_completion", 0.15),
)


def allocate_coding_question_counts(question_count: int) -> dict[str, int]:
    """
    Split ``question_count`` across categories with proportions 20/40/25/15
    using largest-remainder rounding so counts sum exactly to ``question_count``.
    """
    n = max(0, int(question_count))
    if n == 0:
        return {k: 0 for k, _ in _CODING_MIX}

    raw = [(key, n * p) for key, p in _CODING_MIX]
    counts = {key: int(val) for key, val in raw}
    fracs = sorted(((key, val - int(val)) for key, val in raw), key=lambda x: -x[1])
    remainder = n - sum(counts.values())
    for i in range(remainder):
        counts[fracs[i % len(fracs)][0]] += 1
    return counts


def coding_strict_quiz_style_block(question_count: int) -> str:
    """Extra rules for strict (API) quizzes on programming-related topics — practical mix."""
    c = allocate_coding_question_counts(question_count)
    return f"""CODING DOMAIN — PRACTICAL FOCUS (this topic is programming-related):
Overall quiz must exercise real coding skills, not trivia. Prefer short, clear
code snippets where useful (especially for output, debug, and completion items).

QUESTION DISTRIBUTION (TOTAL = {question_count} — hit these counts EXACTLY):
- theory (definitions / concepts / terminology): EXACTLY {c["theory"]} questions
- output_prediction (what prints, return value, final variable state): EXACTLY {c["output_prediction"]} questions
- debugging (errors, exceptions, incorrect behavior, find-the-bug): EXACTLY {c["debugging"]} questions
- logic_completion (code completion, choose the missing line, small scenario with code): EXACTLY {c["logic_completion"]} questions

CATEGORY RULES:
- theory: "What is…", "Which best describes…", compare concepts, when to use a feature.
- output_prediction: show a small program or expression; options are plausible outputs/states.
- debugging: broken snippet, wrong output, or error message; identify cause or fix.
- logic_completion: partial code or behavior description; pick the line/construct that completes logic.

Each question MUST set "coding_question_category" to one of:
"theory" | "output_prediction" | "debugging" | "logic_completion"
so the counts above are satisfied across the full quiz."""


def coding_ai_quiz_style_block() -> str:
    """Base rules for the single-question AI (/api/ai-quiz) prompt on coding topics."""
    return """CODING DOMAIN — PRACTICAL FOCUS (this topic is programming-related):
Generate ONE multiple-choice item that feels like a real interview or lab exercise:
prefer concrete snippets, behavior, or defects over abstract trivia when the
session category below allows it."""


def pick_coding_ai_quiz_category_instruction() -> str:
    """
    One-shot weighted draw matching the 20/40/25/15 mix (expected over many questions).
    Caller injects this so each request targets a specific category.
    """
    keys, weights = zip(*_CODING_MIX, strict=True)
    choice = random.choices(keys, weights=list(weights), k=1)[0]
    guides = {
        "theory": (
            "THIS QUESTION = theory (~20% of a full quiz): definitions, core concepts, "
            "terminology, or \"which statement is correct\" about the language/API — "
            "minimal or no code; keep it grounded in what a developer must know."
        ),
        "output_prediction": (
            "THIS QUESTION = output_prediction (~40%): include a SHORT code snippet "
            "or expression; ask what prints, what is returned, or the final value/state. "
            "Options must be plausible outputs or outcomes."
        ),
        "debugging": (
            "THIS QUESTION = debugging (~25%): snippet or description with a bug, "
            "misuse, or error; ask what fails, why, or which fix is correct. "
            "Options reflect common mistakes."
        ),
        "logic_completion": (
            "THIS QUESTION = logic_completion (~15%): missing line, correct "
            "completion, condition, or small scenario — learner picks the code/logic "
            "that makes the program behave as required."
        ),
    }
    return guides[choice]


def coding_ai_quiz_difficulty_guides() -> dict[str, str]:
    """Difficulty hints for coding topics — depth within the chosen practical category."""
    return {
        "basic": (
            "Short snippets, one main idea per question, familiar syntax — still match "
            "the assigned category (theory vs output vs debug vs completion)."
        ),
        "intermediate": (
            "Typical app or script patterns, realistic APIs/control flow; distractors "
            "reflect common learner mistakes."
        ),
        "advanced": (
            "Subtler behavior, edge cases in small snippets, or trickier defect "
            "reasoning — keep stems readable without pages of code."
        ),
        "expert": (
            "Demanding but fair: nuanced semantics, concurrency/async pitfalls, "
            "performance or correctness in compact examples — avoid gratuitous obfuscation."
        ),
    }
