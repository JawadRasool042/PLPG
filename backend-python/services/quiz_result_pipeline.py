"""
============================================
Quiz Result Pipeline Service
============================================

Orchestrates the full post-quiz pipeline in one place:

  1. Score already calculated by QuizAttempt.create()
  2. Skill level classification  (score bands)
  3. Next recommended difficulty  (RL + history)
  4. Weak concept extraction      (wrong answers)
  5. Course recommendations       (DynamicRecommendationService)
  6. Learning path + resources    (AdvancedLearningPathEngine via DynamicRecommendationService)
  7. Performance coaching         (strengths / weaknesses / coaching tips)

All steps are fault-tolerant — a failure in any enrichment step
never breaks the core score response.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skill-level thresholds (aligned with DynamicRecommendationService bands)
# ---------------------------------------------------------------------------
SKILL_BANDS = [
    (85, "Advanced",     "Expert"),
    (70, "Intermediate", "Intermediate"),
    (50, "Beginner",     "Intermediate"),   # needs more practice at beginner
    (0,  "Beginner",     "Beginner"),
]

DIFFICULTY_LADDER = ["Beginner", "Intermediate", "Advanced"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_quiz_result(
    user_id: str,
    quiz: Dict[str, Any],
    attempt: Dict[str, Any],
    *,
    async_enrichment: bool = False,
) -> Dict[str, Any]:
    """
    Build the full enriched quiz result payload.

    Parameters
    ----------
    user_id:           authenticated user's string ID
    quiz:              the quiz document (from MongoDB)
    attempt:           the just-created attempt document (already scored)
    async_enrichment:  if True, heavy enrichment (learning path) runs in a
                       background thread and is omitted from the immediate
                       response (frontend polls /result later).

    Returns
    -------
    Dict with keys:
        score, skillLevel, nextDifficulty, weakConcepts,
        performanceAnalysis, courses, learningPath, resources,
        careerPaths, skillGapAnalysis, coaching
    """
    score       = float(attempt.get("score", 0))
    interest    = attempt.get("interest") or quiz.get("interest") or "General"
    level       = attempt.get("level")   or quiz.get("level")    or "Beginner"
    correct     = int(attempt.get("correctCount", 0))
    total       = int(attempt.get("totalQuestions", 1))

    # ── 1. Skill level ──────────────────────────────────────────────────────
    skill_level, next_difficulty = _classify_skill_level(score, level)

    # ── 2. Weak concepts ────────────────────────────────────────────────────
    weak_concepts = _extract_weak_concepts(attempt)

    # ── 3. Performance coaching ─────────────────────────────────────────────
    coaching = _build_coaching(score, skill_level, interest, weak_concepts, correct, total)

    # ── 4. Courses + learning path (from DynamicRecommendationService) ───────
    courses, learning_path, resources, career_paths, skill_gap = _fetch_recommendations(
        user_id, interest, score, async_enrichment=async_enrichment
    )

    # ── 5. Assemble final payload ────────────────────────────────────────────
    return {
        "score":             round(score, 1),
        "correctCount":      correct,
        "totalQuestions":    total,
        "interest":          interest,
        "level":             level,
        "skillLevel":        skill_level,
        "nextDifficulty":    next_difficulty,
        "weakConcepts":      weak_concepts,
        "coaching":          coaching,
        "courses":           courses,
        "learningPath":      learning_path,
        "resources":         resources,
        "careerPaths":       career_paths,
        "skillGapAnalysis":  skill_gap,
        "pipelineVersion":   "2.0",
    }


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def _classify_skill_level(score: float, current_level: str) -> tuple[str, str]:
    """
    Map score → (skillLevel, nextDifficulty).

    nextDifficulty is what the adaptive system recommends for the NEXT quiz.
    """
    skill_level = "Beginner"
    for threshold, label, _ in SKILL_BANDS:
        if score >= threshold:
            skill_level = label
            break

    # Determine next difficulty from current level + score
    idx = DIFFICULTY_LADDER.index(current_level) if current_level in DIFFICULTY_LADDER else 0
    if score >= 82 and idx < len(DIFFICULTY_LADDER) - 1:
        next_difficulty = DIFFICULTY_LADDER[idx + 1]
    elif score < 45 and idx > 0:
        next_difficulty = DIFFICULTY_LADDER[idx - 1]
    else:
        next_difficulty = current_level

    return skill_level, next_difficulty


def _extract_weak_concepts(attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pull weak concepts from the attempt's per-question results.

    Returns a list of:
        { concept, question, correctAnswer, userAnswer, explanation }
    """
    results = attempt.get("results") or []
    weak: List[Dict[str, Any]] = []

    for r in results:
        if r.get("isCorrect"):
            continue
        concept = r.get("concept_tag") or r.get("concept") or ""
        question_text = r.get("question") or ""

        # Try to extract concept from question text if not tagged
        if not concept and question_text:
            # Use first few significant words as a proxy concept label
            words = [w for w in question_text.split() if len(w) > 4][:4]
            concept = " ".join(words) if words else "General concept"

        weak.append({
            "concept":       concept,
            "question":      question_text[:200],
            "correctAnswer": r.get("correctAnswer"),
            "userAnswer":    r.get("userAnswer"),
            "explanation":   r.get("explanation") or "",
        })

    # Persist to weak_concepts collection for future quiz targeting
    _persist_weak_concepts(attempt.get("userId"), attempt.get("interest"), weak)

    return weak[:10]  # Cap at 10 for response size


def _persist_weak_concepts(user_id: Optional[str], interest: Optional[str], weak: List[Dict]) -> None:
    """Upsert weak concepts into the weak_concepts collection (non-blocking)."""
    if not user_id or not weak:
        return
    try:
        from database import get_collection
        from datetime import datetime

        coll = get_collection("weak_concepts")
        for item in weak:
            concept = (item.get("concept") or "").strip()
            if not concept:
                continue
            coll.update_one(
                {"userId": user_id, "concept": concept, "interest": interest},
                {
                    "$set": {
                        "userId":      user_id,
                        "interest":    interest,
                        "concept":     concept,
                        "lastSeen":    datetime.utcnow(),
                        "explanation": item.get("explanation") or "",
                    },
                    "$inc":      {"occurrences": 1},
                    "$setOnInsert": {"isMastered": False, "createdAt": datetime.utcnow()},
                },
                upsert=True,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("weak_concepts persist failed: %s", exc)


def _build_coaching(
    score: float,
    skill_level: str,
    interest: str,
    weak_concepts: List[Dict],
    correct: int,
    total: int,
) -> Dict[str, Any]:
    """Build human-readable coaching feedback."""
    accuracy = round((correct / max(total, 1)) * 100, 1)

    if score >= 85:
        verdict = "excellent"
        headline = f"Outstanding! You scored {score:.0f}% — you're operating at {skill_level} level."
        tips = [
            "Try the next difficulty level to keep challenging yourself.",
            "Consider tackling advanced projects to cement this knowledge.",
        ]
    elif score >= 70:
        verdict = "good"
        headline = f"Good work! {score:.0f}% correct — {skill_level} level confirmed."
        tips = [
            "Review the questions you missed and read the explanations.",
            "A few more quizzes at this level will solidify your foundation.",
        ]
    elif score >= 50:
        verdict = "developing"
        headline = f"Keep going — {score:.0f}% correct. You're developing your {interest} skills."
        tips = [
            "Focus on the weak concepts listed below.",
            "Revisit core topics before moving to harder questions.",
        ]
    else:
        verdict = "needs-work"
        headline = f"Score: {score:.0f}%. Don't give up — every attempt builds understanding."
        tips = [
            "Start with the fundamentals of the concepts you missed.",
            "Try a Beginner-level quiz to rebuild confidence.",
        ]

    concept_labels = list({c["concept"] for c in weak_concepts if c.get("concept")})[:5]

    return {
        "verdict":          verdict,
        "headline":         headline,
        "tips":             tips,
        "accuracy":         accuracy,
        "conceptsToReview": concept_labels,
        "skillLevel":       skill_level,
    }


def _fetch_recommendations(
    user_id: str,
    interest: str,
    score: float,
    *,
    async_enrichment: bool = False,
) -> tuple[List, Dict, List, List, Dict]:
    """
    Call DynamicRecommendationService to get courses, learning path,
    resource links, career paths, and skill-gap analysis.

    Returns (courses, learning_path, resources, career_paths, skill_gap)
    All default to safe empty values on failure.
    """
    courses: List       = []
    learning_path: Dict = {}
    resources: List     = []
    career_paths: List  = []
    skill_gap: Dict     = {}

    def _run() -> None:
        nonlocal courses, learning_path, resources, career_paths, skill_gap
        try:
            from services.dynamic_recommendation_service import DynamicRecommendationService

            rec_doc = DynamicRecommendationService.generate_and_store(
                user_id, force_regenerate=True
            )
            if not rec_doc:
                return

            courses      = rec_doc.get("courses") or []
            career_paths = rec_doc.get("careers") or []
            skill_gap    = rec_doc.get("skillGapAnalysis") or {}

            lp = rec_doc.get("learningPath") or {}
            learning_path = {
                "domain":            lp.get("domain") or interest,
                "currentLevel":      lp.get("currentLevel") or _classify_skill_level(score, "Beginner")[0],
                "nextDifficulty":    _classify_skill_level(score, lp.get("currentLevel") or "Beginner")[1],
                "estimatedDuration": lp.get("estimatedDuration") or "4-8 weeks",
                "steps":             lp.get("steps") or [],
                "progress":          lp.get("progress") or 0,
                "phases": _extract_phases(rec_doc),
            }

            # Build flat resource list from courses
            resources = _build_resource_links(rec_doc.get("courses") or [])

        except Exception as exc:  # noqa: BLE001
            logger.warning("Recommendation enrichment failed for user %s: %s", user_id, exc)

    if async_enrichment:
        threading.Thread(target=_run, daemon=True).start()
    else:
        _run()

    return courses, learning_path, resources, career_paths, skill_gap


def _extract_phases(rec_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pull roadmap phases (beginner / intermediate / advanced blocks)
    from the recommendation document returned by DynamicRecommendationService.
    """
    roadmap = rec_doc.get("roadmap") or {}
    steps   = roadmap.get("steps") or []

    # If roadmap has phased blocks (from OpenAI engine), use them
    phases = []
    for level_key in ("basic", "beginner", "intermediate", "advanced", "expert"):
        block = roadmap.get(level_key)
        if isinstance(block, dict) and block.get("topics"):
            label = "Beginner" if level_key in ("basic", "beginner") else level_key.capitalize()
            if any(p.get("level") == label for p in phases):
                continue
            phases.append({
                "level":    label,
                "topics":   block.get("topics") or [],
                "duration": block.get("duration_label") or "",
                "projects": block.get("stage_projects") or [],
            })

    # Fall back to flat steps list divided into 3 phases
    if not phases and steps:
        chunk = max(1, len(steps) // 3)
        labels = ["Beginner", "Intermediate", "Advanced"]
        for i, label in enumerate(labels):
            slice_ = steps[i * chunk: (i + 1) * chunk]
            if slice_:
                phases.append({"level": label, "topics": slice_, "duration": "", "projects": []})

    return phases


def _build_resource_links(courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Turn course cards into a normalised resource-link list.

    Each resource has: { title, url, platform, type, difficulty }
    """
    resources = []
    for c in courses:
        if not isinstance(c, dict):
            continue
        title    = str(c.get("title") or c.get("name") or "").strip()
        url      = str(c.get("url") or c.get("url_hint") or c.get("link") or "").strip()
        platform = str(c.get("provider") or c.get("platform") or "").strip()
        diff     = str(c.get("duration") or c.get("difficulty") or "").strip()

        if not title:
            continue

        # Generate a plausible search URL if none provided
        if not url and platform:
            query = "+".join(title.split()[:5])
            url = f"https://www.google.com/search?q={query}+{platform}+course"
        elif not url:
            query = "+".join(title.split()[:5])
            url = f"https://www.google.com/search?q={query}+course"

        resources.append({
            "title":      title,
            "url":        url,
            "platform":   platform,
            "type":       "course",
            "difficulty": diff,
        })

    return resources[:12]  # Cap at 12 links
