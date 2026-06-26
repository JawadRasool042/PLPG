"""Recommendation rules — maps category + level + score thresholds to catalog items."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class RecommendationRule:
    collection_name = "recommendation_rules"

    VALID_LEVELS = ("Beginner", "Intermediate", "Expert")

    @staticmethod
    def get_collection():
        return get_collection(RecommendationRule.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = RecommendationRule.get_collection()
        col.create_index([("category", 1), ("level", 1)])
        col.create_index([("minimumScore", 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "category": (data.get("category") or "").strip(),
            "minimumScore": float(data.get("minimumScore") or data.get("minimum_score") or 0),
            "level": data.get("level") or "Beginner",
            "careers": data.get("careers") or [],
            "courses": data.get("courses") or [],
            "roadmapId": data.get("roadmapId") or data.get("roadmap_id"),
            "priority": int(data.get("priority") or 0),
            "isActive": data.get("isActive", True),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = RecommendationRule.get_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
        try:
            return RecommendationRule.get_collection().find_one({"_id": ObjectId(rule_id)})
        except Exception:
            return None

    @staticmethod
    def find_many(
        filter_query: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return list(
            RecommendationRule.get_collection()
            .find(filter_query or {})
            .sort([("priority", -1), ("minimumScore", -1)])
            .skip(skip)
            .limit(limit)
        )

    @staticmethod
    def count(filter_query: Optional[Dict] = None) -> int:
        return RecommendationRule.get_collection().count_documents(filter_query or {})

    @staticmethod
    def update(rule_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(rule_id)
        except Exception:
            return None
        allowed = {
            "category", "minimumScore", "level", "careers", "courses",
            "roadmapId", "priority", "isActive",
        }
        update_doc = {k: v for k, v in data.items() if k in allowed}
        if not update_doc:
            return RecommendationRule.find_by_id(rule_id)
        update_doc["updatedAt"] = datetime.utcnow()
        RecommendationRule.get_collection().update_one({"_id": obj_id}, {"$set": update_doc})
        return RecommendationRule.get_collection().find_one({"_id": obj_id})

    @staticmethod
    def delete(rule_id: str) -> bool:
        try:
            obj_id = ObjectId(rule_id)
        except Exception:
            return False
        result = RecommendationRule.get_collection().delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "category": doc.get("category"),
            "minimumScore": doc.get("minimumScore"),
            "level": doc.get("level"),
            "careers": doc.get("careers", []),
            "courses": doc.get("courses", []),
            "roadmapId": doc.get("roadmapId"),
            "priority": doc.get("priority", 0),
            "isActive": doc.get("isActive", True),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        }
