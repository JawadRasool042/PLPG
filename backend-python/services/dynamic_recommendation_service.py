"""
Dynamic Recommendation Service
==============================
Database-driven recommendation engine using user assessment data,
quiz performance, and catalog collections (careers, courses, roadmaps, rules).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from database import get_collection
from models.user import User
from models.user_analytics import UserAnalytics
from models.quiz_attempt import QuizAttempt
from models.career import Career
from models.course import Course
from models.learning_path_catalog import LearningPathCatalog

logger = logging.getLogger(__name__)

SKILL_LEVEL_BANDS = (
    (76, "Expert"),
    (41, "Intermediate"),
    (0, "Beginner"),
)


class DynamicRecommendationService:
    """Core engine for personalized, database-driven recommendations."""

    recommendations_collection = "recommendations"

    @staticmethod
    def get_collection():
        return get_collection(DynamicRecommendationService.recommendations_collection)

    @staticmethod
    def classify_skill_level(score: float) -> str:
        score = max(0.0, min(100.0, float(score or 0)))
        for threshold, label in SKILL_LEVEL_BANDS:
            if score >= threshold:
                return label
        return "Beginner"

    @staticmethod
    def _normalize_level(level: str) -> str:
        mapping = {
            "beginner": "Beginner",
            "intermediate": "Intermediate",
            "advanced": "Expert",
            "expert": "Expert",
        }
        return mapping.get((level or "").lower(), level or "Beginner")

    @staticmethod
    def build_user_snapshot(user_id: str) -> Dict[str, Any]:
        """Aggregate interest, quiz, and progress signals for a user."""
        user = User.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        assessment = user.get("interestAssessment") or {}
        domain_scores: Dict[str, float] = {}

        for item in assessment.get("allInterests") or []:
            domain = item.get("domain") or item.get("name")
            if not domain:
                continue
            score = item.get("score") or item.get("confidence") or 0
            try:
                domain_scores[domain] = float(score)
            except (TypeError, ValueError):
                continue

        if not domain_scores and assessment.get("primaryInterest"):
            domain_scores[assessment["primaryInterest"]] = float(
                assessment.get("confidence") or 7
            )

        analytics = UserAnalytics.get_analytics(user_id) or {}
        quiz_score = float(analytics.get("averageQuizScore") or 0)

        attempts = QuizAttempt.find_by_user(user_id, limit=10)
        if attempts:
            recent_scores = [
                float(a.get("score") or a.get("percentage") or 0)
                for a in attempts[:5]
            ]
            if recent_scores:
                quiz_score = sum(recent_scores) / len(recent_scores)

        if quiz_score <= 0 and attempts:
            quiz_score = float(attempts[0].get("score") or attempts[0].get("percentage") or 0)

        skill_level = DynamicRecommendationService.classify_skill_level(quiz_score)
        if user.get("skillLevel"):
            skill_level = DynamicRecommendationService._normalize_level(user["skillLevel"])

        ranked = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        strongest = ranked[0][0] if ranked else (assessment.get("primaryInterest") or "Coding")
        weakest = ranked[-1][0] if len(ranked) > 1 else strongest

        category_preferences = [d for d, _ in ranked[:3]]

        return {
            "userId": user_id,
            "domainScores": domain_scores,
            "strongestDomain": strongest,
            "weakestDomain": weakest,
            "overallScore": round(quiz_score, 1),
            "skillLevel": skill_level,
            "categoryPreferences": category_preferences,
            "primaryInterest": assessment.get("primaryInterest") or strongest,
            "analytics": analytics,
            "totalQuizzes": len(attempts),
            "learningProgress": analytics.get("learningVelocity") or 0,
        }

    @staticmethod
    def _compute_match_pct(
        item: Dict[str, Any],
        snapshot: Dict[str, Any],
        item_type: str = "career",
    ) -> float:
        domain_scores = snapshot.get("domainScores") or {}
        category = item.get("category") or ""
        base = domain_scores.get(category, 0) * 10

        demand = float(item.get("demandScore") or 50) if item_type == "career" else 60
        quiz_factor = snapshot.get("overallScore", 0) * 0.3
        level_match = 15 if item.get("level") == snapshot.get("skillLevel") else 5

        skills = item.get("requiredSkills") or item.get("skillsCovered") or []
        strong_domains = snapshot.get("categoryPreferences") or []
        skill_bonus = 5 * len([s for s in skills if any(d.lower() in s.lower() for d in strong_domains)])

        raw = base * 0.4 + demand * 0.2 + quiz_factor + level_match + skill_bonus
        return max(10.0, min(98.0, raw))

    @staticmethod
    def _build_skill_gap_analysis(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        weakest = snapshot.get("weakestDomain", "")
        strongest = snapshot.get("strongestDomain", "")
        level = snapshot.get("skillLevel", "Beginner")
        domain_scores = snapshot.get("domainScores") or {}

        weak_score = domain_scores.get(weakest, 0)
        strong_score = domain_scores.get(strongest, 0)
        gap = max(0, strong_score - weak_score)

        gaps = []
        try:
            from advanced_learning_path.engine import AdvancedLearningPathEngine

            path_result = AdvancedLearningPathEngine().generate_roadmap(
                weakest,
                {
                    "user": {},
                    "quiz_caliber": {"recommended_quiz_difficulty": level.lower()},
                },
            )
            roadmap = path_result.get("roadmap") or {}
            block = roadmap.get(level.lower()) or roadmap.get("beginner") or {}
            topics = block.get("topics") or block.get("all_topics") or []
            for topic in topics[:5]:
                gaps.append({
                    "skill": topic,
                    "domain": weakest,
                    "priority": "high" if gap > 3 else "medium",
                    "currentLevel": level,
                })
        except Exception as exc:
            logger.warning("OpenAI skill-gap roadmap failed for %s: %s", weakest, exc)

        return {
            "strongestDomain": strongest,
            "weakestDomain": weakest,
            "gapScore": round(gap, 1),
            "overallScore": snapshot.get("overallScore"),
            "skillLevel": level,
            "gaps": gaps,
            "recommendedFocus": weakest,
            "summary": (
                f"Your strongest area is {strongest}. Focus on {weakest} "
                f"to close a gap of {gap:.1f} points and reach the next milestone."
            ),
        }

    @staticmethod
    def _path_result_to_items(
        path_result: Dict[str, Any],
        category: str,
        level: str,
    ) -> Tuple[List[Dict], List[Dict], Optional[Dict]]:
        """Map OpenAI learning-path payload into catalog-shaped documents."""
        roadmap = path_result.get("roadmap") or {}
        careers_detailed = path_result.get("careers_detailed") or []
        resources = roadmap.get("resources") or {}
        course_cards = resources.get("course_cards") or []
        course_names = resources.get("courses") or []

        careers: List[Dict] = []
        for i, c in enumerate(careers_detailed):
            careers.append({
                "_id": f"ai-career-{category}-{i}",
                "title": c.get("title"),
                "category": category,
                "level": level,
                "description": c.get("resume_angle") or "",
                "requiredSkills": c.get("required_skills") or [],
                "salaryRange": c.get("salary_range"),
                "demandScore": 75,
            })

        courses: List[Dict] = []
        if course_cards:
            for i, card in enumerate(course_cards):
                if not isinstance(card, dict):
                    continue
                name = str(card.get("name") or "").strip()
                if not name:
                    continue
                courses.append({
                    "_id": f"ai-course-{category}-{i}",
                    "title": name,
                    "provider": card.get("platform") or "OpenAI recommendation",
                    "category": category,
                    "level": level,
                    "duration": card.get("difficulty") or "",
                    "url": card.get("url_hint") or "",
                    "skillsCovered": [],
                })
        else:
            for i, name in enumerate(course_names):
                title = str(name).strip()
                if not title:
                    continue
                courses.append({
                    "_id": f"ai-course-{category}-{i}",
                    "title": title,
                    "provider": "OpenAI recommendation",
                    "category": category,
                    "level": level,
                    "duration": "",
                    "url": "",
                    "skillsCovered": [],
                })

        steps: List[str] = []
        for key in ("beginner", "intermediate", "advanced"):
            block = roadmap.get(key) or {}
            steps.extend(block.get("all_topics") or block.get("topics") or [])
        beginner_block = roadmap.get("beginner") or {}
        roadmap_doc = {
            "_id": f"ai-roadmap-{category}",
            "category": category,
            "level": level,
            "title": f"{category} AI Learning Path",
            "steps": steps,
            "estimatedDuration": beginner_block.get("duration_label") or "4-6 weeks",
        }
        return careers, courses, roadmap_doc

    @staticmethod
    def _collect_recommendations_for_domain(
        category: str,
        level: str,
        quiz_score: float,
        snapshot: Dict[str, Any],
    ) -> Tuple[List[Dict], List[Dict], Optional[Dict]]:
        from advanced_learning_path.engine import AdvancedLearningPathEngine
        from advanced_learning_path.quiz_caliber import recommended_difficulty_from_scores

        user = User.find_by_id(snapshot.get("userId", "")) or {}
        assessment = user.get("interestAssessment") or {}
        ctx = assessment.get("assessmentContext") or {}

        payload = {
            "user_id": snapshot.get("userId"),
            "user": {
                "known": ctx.get("known", ""),
                "want": ctx.get("want", ""),
                "goals": ctx.get("goals", ""),
                "learning_style": user.get("learningStyle", "mixed"),
                "weekly_availability_hours": user.get("weeklyAvailabilityHours", 5),
                "assessment_tags": assessment.get("assessmentTags") or [],
            },
            "quiz_caliber": {
                "average_score": quiz_score,
                "recommended_quiz_difficulty": recommended_difficulty_from_scores(quiz_score, []),
            },
            "secondary_domains": snapshot.get("categoryPreferences") or [],
        }

        path_result = AdvancedLearningPathEngine().generate_roadmap(category, payload)
        careers, courses, roadmap = DynamicRecommendationService._path_result_to_items(
            path_result, category, level
        )

        careers.sort(
            key=lambda c: DynamicRecommendationService._compute_match_pct(c, snapshot, "career"),
            reverse=True,
        )
        courses.sort(
            key=lambda c: DynamicRecommendationService._compute_match_pct(c, snapshot, "course"),
            reverse=True,
        )
        return careers[:8], courses[:8], roadmap

    @staticmethod
    def generate_and_store(
        user_id: str,
        force_regenerate: bool = False,
    ) -> Dict[str, Any]:
        coll = DynamicRecommendationService.get_collection()

        if not force_regenerate:
            existing = coll.find_one({
                "userId": user_id,
                "status": "active",
                "expiresAt": {"$gt": datetime.utcnow()},
            })
            if existing:
                return existing

        snapshot = DynamicRecommendationService.build_user_snapshot(user_id)
        category = snapshot["strongestDomain"]
        level = snapshot["skillLevel"]
        quiz_score = snapshot["overallScore"]

        careers, courses, roadmap = DynamicRecommendationService._collect_recommendations_for_domain(
            category, level, quiz_score, snapshot,
        )

        secondary_domains = snapshot.get("categoryPreferences") or []
        for domain in secondary_domains[1:3]:
            extra_c, extra_co, _ = DynamicRecommendationService._collect_recommendations_for_domain(
                domain, level, quiz_score, snapshot,
            )
            existing_c_ids = {str(c["_id"]) for c in careers}
            existing_co_ids = {str(c["_id"]) for c in courses}
            for c in extra_c:
                if str(c["_id"]) not in existing_c_ids and len(careers) < 12:
                    careers.append(c)
            for c in extra_co:
                if str(c["_id"]) not in existing_co_ids and len(courses) < 12:
                    courses.append(c)

        skill_gap = DynamicRecommendationService._build_skill_gap_analysis(snapshot)

        career_responses = [
            Career.to_response(
                c,
                DynamicRecommendationService._compute_match_pct(c, snapshot, "career"),
            )
            for c in careers
        ]
        course_responses = [
            Course.to_response(
                c,
                DynamicRecommendationService._compute_match_pct(c, snapshot, "course"),
            )
            for c in courses
        ]
        roadmap_response = LearningPathCatalog.to_response(roadmap) if roadmap else None

        doc = {
            "userId": user_id,
            "primaryDomain": category,
            "strongestDomain": snapshot["strongestDomain"],
            "weakestDomain": snapshot["weakestDomain"],
            "overallScore": snapshot["overallScore"],
            "skillLevel": level,
            "domainScores": snapshot["domainScores"],
            "categoryPreferences": snapshot["categoryPreferences"],
            "careers": career_responses,
            "courses": course_responses,
            "roadmap": roadmap_response,
            "skillGapAnalysis": skill_gap,
            "learningProgress": snapshot.get("learningProgress", 0),
            "detailedRecommendations": {
                "career_paths": career_responses,
                "courses": course_responses,
                "skill_roadmap": roadmap_response.get("steps") if roadmap_response else [],
                "top_resources": course_responses,
                "project_ideas": [],
                "learning_path": roadmap_response,
            },
            "learningPath": {
                "domain": category,
                "currentLevel": level,
                "estimatedDuration": roadmap_response.get("estimatedDuration") if roadmap_response else "6-12 months",
                "steps": roadmap_response.get("steps") if roadmap_response else [],
                "progress": snapshot.get("learningProgress", 0),
            },
            "generatedAt": datetime.utcnow(),
            "expiresAt": datetime.utcnow() + timedelta(days=30),
            "status": "active",
            "source": "openai",
        }

        coll.update_many(
            {"userId": user_id, "status": "active"},
            {"$set": {"status": "archived", "archivedAt": datetime.utcnow()}},
        )
        result = coll.insert_one(doc)
        doc["_id"] = result.inserted_id

        User.update(user_id, {"skillLevel": level, "learningLevel": level})

        logger.info("Generated dynamic recommendations for user %s: %s / %s", user_id, category, level)
        return doc

    @staticmethod
    def get_active(user_id: str) -> Optional[Dict[str, Any]]:
        return DynamicRecommendationService.get_collection().find_one({
            "userId": user_id,
            "status": "active",
            "expiresAt": {"$gt": datetime.utcnow()},
        })

    @staticmethod
    def get_or_generate(user_id: str) -> Dict[str, Any]:
        active = DynamicRecommendationService.get_active(user_id)
        if active:
            return active
        return DynamicRecommendationService.generate_and_store(user_id, force_regenerate=True)

    @staticmethod
    def to_api_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc.get("_id", "")),
            "primaryDomain": doc.get("primaryDomain"),
            "strongestDomain": doc.get("strongestDomain"),
            "weakestDomain": doc.get("weakestDomain"),
            "overallScore": doc.get("overallScore"),
            "skillLevel": doc.get("skillLevel"),
            "domainScores": doc.get("domainScores", {}),
            "categoryPreferences": doc.get("categoryPreferences", []),
            "careers": doc.get("careers", []),
            "courses": doc.get("courses", []),
            "roadmap": doc.get("roadmap"),
            "skillGapAnalysis": doc.get("skillGapAnalysis"),
            "learningProgress": doc.get("learningProgress", 0),
            "learningPath": doc.get("learningPath"),
            "generatedAt": doc.get("generatedAt").isoformat() if doc.get("generatedAt") else None,
            "expiresAt": doc.get("expiresAt").isoformat() if doc.get("expiresAt") else None,
        }

    @staticmethod
    def on_quiz_submitted(user_id: str, attempt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Regenerate recommendations after quiz submission."""
        try:
            return DynamicRecommendationService.generate_and_store(user_id, force_regenerate=True)
        except Exception as exc:
            logger.warning("Post-quiz recommendation refresh failed for %s: %s", user_id, exc)
            return None
