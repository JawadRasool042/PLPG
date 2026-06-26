"""Repository layer for recommendation catalog collections."""

from typing import Any, Dict, List, Optional

from bson import ObjectId

from models.career import Career
from models.course import Course
from models.learning_path_catalog import LearningPathCatalog
from models.recommendation_rule import RecommendationRule
from models.category import Category


class CatalogRepository:
    """Data access for careers, courses, roadmaps, rules, and categories."""

    @staticmethod
    def get_active_categories() -> List[Dict[str, Any]]:
        return Category.find_many(active_only=True)

    @staticmethod
    def get_careers_by_ids(career_ids: List[str]) -> List[Dict[str, Any]]:
        if not career_ids:
            return []
        obj_ids = []
        for cid in career_ids:
            try:
                obj_ids.append(ObjectId(cid))
            except Exception:
                continue
        if not obj_ids:
            return []
        return list(Career.get_collection().find({"_id": {"$in": obj_ids}, "isActive": True}))

    @staticmethod
    def get_courses_by_ids(course_ids: List[str]) -> List[Dict[str, Any]]:
        if not course_ids:
            return []
        obj_ids = []
        for cid in course_ids:
            try:
                obj_ids.append(ObjectId(cid))
            except Exception:
                continue
        if not obj_ids:
            return []
        return list(Course.get_collection().find({"_id": {"$in": obj_ids}, "isActive": True}))

    @staticmethod
    def get_roadmap_by_id(roadmap_id: str) -> Optional[Dict[str, Any]]:
        if not roadmap_id:
            return None
        try:
            return LearningPathCatalog.get_collection().find_one(
                {"_id": ObjectId(roadmap_id), "isActive": True}
            )
        except Exception:
            return None

    @staticmethod
    def find_matching_rules(
        category: str,
        level: str,
        quiz_score: float,
    ) -> List[Dict[str, Any]]:
        """Return active rules for category/level where user meets minimum score."""
        query = {
            "category": category,
            "level": level,
            "minimumScore": {"$lte": quiz_score},
            "isActive": True,
        }
        return RecommendationRule.find_many(query, limit=20)

    @staticmethod
    def find_careers_for_category(
        category: str,
        level: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return Career.find_many(
            {"category": category, "level": level, "isActive": True},
            limit=limit,
        )

    @staticmethod
    def find_courses_for_category(
        category: str,
        level: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return Course.find_many(
            {"category": category, "level": level, "isActive": True},
            limit=limit,
        )

    @staticmethod
    def find_roadmap_for_category(
        category: str,
        level: str,
    ) -> Optional[Dict[str, Any]]:
        docs = LearningPathCatalog.find_many(
            {"category": category, "level": level, "isActive": True},
            limit=1,
        )
        return docs[0] if docs else None

    @staticmethod
    def resolve_rule_catalog(
        rule: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Expand a rule document into careers, courses, and roadmap."""
        careers = CatalogRepository.get_careers_by_ids(rule.get("careers") or [])
        courses = CatalogRepository.get_courses_by_ids(rule.get("courses") or [])
        roadmap = CatalogRepository.get_roadmap_by_id(rule.get("roadmapId"))
        if not roadmap:
            roadmap = CatalogRepository.find_roadmap_for_category(
                rule.get("category", ""),
                rule.get("level", "Beginner"),
            )
        if not careers:
            careers = CatalogRepository.find_careers_for_category(
                rule.get("category", ""),
                rule.get("level", "Beginner"),
            )
        if not courses:
            courses = CatalogRepository.find_courses_for_category(
                rule.get("category", ""),
                rule.get("level", "Beginner"),
            )
        return {"careers": careers, "courses": courses, "roadmap": roadmap}
