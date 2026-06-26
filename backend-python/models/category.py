"""Category registry — extensible domain list for recommendations."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from database import get_collection


class Category:
    collection_name = "categories"

    @staticmethod
    def get_collection():
        return get_collection(Category.collection_name)

    @staticmethod
    def ensure_indexes() -> None:
        col = Category.get_collection()
        col.create_index([("slug", 1)], unique=True)
        col.create_index([("isActive", 1)])

    @staticmethod
    def create(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "name": (data.get("name") or "").strip(),
            "slug": (data.get("slug") or "").strip().lower().replace(" ", "-"),
            "description": (data.get("description") or "").strip(),
            "icon": data.get("icon") or "📘",
            "sortOrder": int(data.get("sortOrder") or 0),
            "isActive": data.get("isActive", True),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = Category.get_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def find_by_name(name: str) -> Optional[Dict[str, Any]]:
        return Category.get_collection().find_one({"name": name, "isActive": True})

    @staticmethod
    def find_many(active_only: bool = True) -> List[Dict[str, Any]]:
        query = {"isActive": True} if active_only else {}
        return list(
            Category.get_collection().find(query).sort("sortOrder", 1)
        )

    @staticmethod
    def to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name"),
            "slug": doc.get("slug"),
            "description": doc.get("description"),
            "icon": doc.get("icon"),
            "sortOrder": doc.get("sortOrder", 0),
            "isActive": doc.get("isActive", True),
        }
