"""Career catalog model — database-driven career recommendations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class Career:
    collection_name = "careers"

    VALID_LEVELS = ("Beginner", "Intermediate", "Expert")

    @staticmethod
    def get_collection():
        return get_collection(Career.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = Career.get_collection()
        col.create_index([("category", 1), ("level", 1)])
        col.create_index([("title", 1)])
        col.create_index([("isActive", 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "title": (data.get("title") or "").strip(),
            "category": (data.get("category") or "").strip(),
            "level": data.get("level") or "Intermediate",
            "description": (data.get("description") or "").strip(),
            "requiredSkills": data.get("requiredSkills") or [],
            "salaryRange": (data.get("salaryRange") or data.get("salary_range") or "").strip(),
            "demandScore": float(data.get("demandScore") or data.get("demand_score") or 50),
            "isActive": data.get("isActive", True),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = Career.get_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find_by_id(career_id: str) -> Optional[Dict[str, Any]]:
        try:
            return Career.get_collection().find_one({"_id": ObjectId(career_id)})
        except Exception:
            return None

    @staticmethod
    def find_many(
        filter_query: Optional[Dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return list(
            Career.get_collection()
            .find(filter_query or {})
            .sort("demandScore", -1)
            .skip(skip)
            .limit(limit)
        )

    @staticmethod
    def count(filter_query: Optional[Dict] = None) -> int:
        return Career.get_collection().count_documents(filter_query or {})

    @staticmethod
    def update(career_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(career_id)
        except Exception:
            return None
        allowed = {
            "title", "category", "level", "description",
            "requiredSkills", "salaryRange", "demandScore", "isActive",
        }
        update_doc = {k: v for k, v in data.items() if k in allowed}
        if not update_doc:
            return Career.find_by_id(career_id)
        update_doc["updatedAt"] = datetime.utcnow()
        Career.get_collection().update_one({"_id": obj_id}, {"$set": update_doc})
        return Career.get_collection().find_one({"_id": obj_id})

    @staticmethod
    def delete(career_id: str) -> bool:
        try:
            obj_id = ObjectId(career_id)
        except Exception:
            return False
        result = Career.get_collection().delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]], match_pct: Optional[float] = None) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        resp = {
            "id": str(doc["_id"]),
            "title": doc.get("title"),
            "category": doc.get("category"),
            "level": doc.get("level"),
            "description": doc.get("description"),
            "requiredSkills": doc.get("requiredSkills", []),
            "salaryRange": doc.get("salaryRange"),
            "demandScore": doc.get("demandScore"),
            "isActive": doc.get("isActive", True),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        }
        if match_pct is not None:
            resp["matchPercentage"] = round(match_pct, 1)
        return resp
