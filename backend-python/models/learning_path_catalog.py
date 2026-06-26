"""Learning path catalog model — database-driven roadmap templates."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class LearningPathCatalog:
    collection_name = "learning_paths"

    VALID_LEVELS = ("Beginner", "Intermediate", "Expert")

    @staticmethod
    def get_collection():
        return get_collection(LearningPathCatalog.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = LearningPathCatalog.get_collection()
        col.create_index([("category", 1), ("level", 1)])
        col.create_index([("isActive", 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "category": (data.get("category") or "").strip(),
            "level": data.get("level") or "Beginner",
            "title": (data.get("title") or "").strip(),
            "steps": data.get("steps") or [],
            "estimatedDuration": (data.get("estimatedDuration") or data.get("estimated_duration") or "").strip(),
            "isActive": data.get("isActive", True),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = LearningPathCatalog.get_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find_by_id(path_id: str) -> Optional[Dict[str, Any]]:
        try:
            return LearningPathCatalog.get_collection().find_one({"_id": ObjectId(path_id)})
        except Exception:
            return None

    @staticmethod
    def find_many(
        filter_query: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return list(
            LearningPathCatalog.get_collection()
            .find(filter_query or {})
            .sort("category", 1)
            .skip(skip)
            .limit(limit)
        )

    @staticmethod
    def count(filter_query: Optional[Dict] = None) -> int:
        return LearningPathCatalog.get_collection().count_documents(filter_query or {})

    @staticmethod
    def update(path_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(path_id)
        except Exception:
            return None
        allowed = {"category", "level", "title", "steps", "estimatedDuration", "isActive"}
        update_doc = {k: v for k, v in data.items() if k in allowed}
        if not update_doc:
            return LearningPathCatalog.find_by_id(path_id)
        update_doc["updatedAt"] = datetime.utcnow()
        LearningPathCatalog.get_collection().update_one({"_id": obj_id}, {"$set": update_doc})
        return LearningPathCatalog.get_collection().find_one({"_id": obj_id})

    @staticmethod
    def delete(path_id: str) -> bool:
        try:
            obj_id = ObjectId(path_id)
        except Exception:
            return False
        result = LearningPathCatalog.get_collection().delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "category": doc.get("category"),
            "level": doc.get("level"),
            "title": doc.get("title"),
            "steps": doc.get("steps", []),
            "estimatedDuration": doc.get("estimatedDuration"),
            "isActive": doc.get("isActive", True),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        }
