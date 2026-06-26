"""Course catalog model — database-driven course recommendations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class Course:
    collection_name = "courses"

    VALID_LEVELS = ("Beginner", "Intermediate", "Expert")

    @staticmethod
    def get_collection():
        return get_collection(Course.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = Course.get_collection()
        col.create_index([("category", 1), ("level", 1)])
        col.create_index([("title", 1)])
        col.create_index([("isActive", 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "title": (data.get("title") or "").strip(),
            "provider": (data.get("provider") or "").strip(),
            "category": (data.get("category") or "").strip(),
            "level": data.get("level") or "Beginner",
            "duration": (data.get("duration") or "").strip(),
            "url": (data.get("url") or "").strip(),
            "skillsCovered": data.get("skillsCovered") or data.get("skills_covered") or [],
            "isActive": data.get("isActive", True),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = Course.get_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find_by_id(course_id: str) -> Optional[Dict[str, Any]]:
        try:
            return Course.get_collection().find_one({"_id": ObjectId(course_id)})
        except Exception:
            return None

    @staticmethod
    def find_many(
        filter_query: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return list(
            Course.get_collection()
            .find(filter_query or {})
            .sort("title", 1)
            .skip(skip)
            .limit(limit)
        )

    @staticmethod
    def count(filter_query: Optional[Dict] = None) -> int:
        return Course.get_collection().count_documents(filter_query or {})

    @staticmethod
    def update(course_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(course_id)
        except Exception:
            return None
        allowed = {
            "title", "provider", "category", "level", "duration",
            "url", "skillsCovered", "isActive",
        }
        update_doc = {k: v for k, v in data.items() if k in allowed}
        if not update_doc:
            return Course.find_by_id(course_id)
        update_doc["updatedAt"] = datetime.utcnow()
        Course.get_collection().update_one({"_id": obj_id}, {"$set": update_doc})
        return Course.get_collection().find_one({"_id": obj_id})

    @staticmethod
    def delete(course_id: str) -> bool:
        try:
            obj_id = ObjectId(course_id)
        except Exception:
            return False
        result = Course.get_collection().delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]], match_pct: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        resp = {
            "id": str(doc["_id"]),
            "title": doc.get("title"),
            "provider": doc.get("provider"),
            "category": doc.get("category"),
            "level": doc.get("level"),
            "duration": doc.get("duration"),
            "url": doc.get("url"),
            "skillsCovered": doc.get("skillsCovered", []),
            "isActive": doc.get("isActive", True),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        }
        if match_pct is not None:
            resp["matchPercentage"] = round(match_pct, 1)
        return resp
