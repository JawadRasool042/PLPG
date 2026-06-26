"""
Admin catalog management — CRUD for careers, courses, roadmaps, rules, categories, quiz templates.
"""

import logging
from flask import Blueprint, request, jsonify, g

from middleware.admin_auth import authenticate_admin, authorize
from models.audit_log import AuditLog
from models.career import Career
from models.course import Course
from models.learning_path_catalog import LearningPathCatalog
from models.recommendation_rule import RecommendationRule
from models.category import Category
from models.quiz import Quiz

logger = logging.getLogger(__name__)

admin_catalog_bp = Blueprint("admin_catalog", __name__)


def _paginate(default_limit=20):
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(int(request.args.get("limit", default_limit)), 100))
    except (TypeError, ValueError):
        page, limit = 1, default_limit
    skip = (page - 1) * limit
    return page, limit, skip


def _audit(action: str, resource: str, resource_id: str = None, changes: dict = None):
    try:
        AuditLog.create({
            "admin": g.admin.get("_id") if g.admin else None,
            "adminEmail": g.admin.get("email") if g.admin else None,
            "action": action,
            "resource": resource,
            "resourceId": resource_id,
            "changes": changes or {},
            "ipAddress": request.remote_addr,
        })
    except Exception as exc:
        logger.warning("Audit log failed: %s", exc)


# ── Categories ──────────────────────────────────────────────────────────────

@admin_catalog_bp.route("/categories", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_categories():
    items = [Category.to_response(c) for c in Category.find_many(active_only=False)]
    return jsonify({"success": True, "data": items}), 200


@admin_catalog_bp.route("/categories", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_category():
    data = request.get_json() or {}
    doc = Category.create(data)
    _audit("create", "category", str(doc["_id"]), data)
    return jsonify({"success": True, "data": Category.to_response(doc)}), 201


# ── Careers ─────────────────────────────────────────────────────────────────

@admin_catalog_bp.route("/careers", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_careers():
    page, limit, skip = _paginate()
    query = {}
    if request.args.get("category"):
        query["category"] = request.args.get("category")
    if request.args.get("level"):
        query["level"] = request.args.get("level")
    total = Career.count(query)
    items = [Career.to_response(c) for c in Career.find_many(query, skip=skip, limit=limit)]
    return jsonify({
        "success": True,
        "data": items,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }), 200


@admin_catalog_bp.route("/careers", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_career():
    data = request.get_json() or {}
    if not data.get("title") or not data.get("category"):
        return jsonify({"success": False, "message": "title and category are required"}), 400
    doc = Career.create(data)
    _audit("create", "career", str(doc["_id"]), data)
    return jsonify({"success": True, "data": Career.to_response(doc)}), 201


@admin_catalog_bp.route("/careers/<career_id>", methods=["PUT"])
@authenticate_admin
@authorize("content_update")
def update_career(career_id):
    data = request.get_json() or {}
    doc = Career.update(career_id, data)
    if not doc:
        return jsonify({"success": False, "message": "Career not found"}), 404
    _audit("update", "career", career_id, data)
    return jsonify({"success": True, "data": Career.to_response(doc)}), 200


@admin_catalog_bp.route("/careers/<career_id>", methods=["DELETE"])
@authenticate_admin
@authorize("content_delete")
def delete_career(career_id):
    if not Career.delete(career_id):
        return jsonify({"success": False, "message": "Career not found"}), 404
    _audit("delete", "career", career_id)
    return jsonify({"success": True, "message": "Career deleted"}), 200


# ── Courses ─────────────────────────────────────────────────────────────────

@admin_catalog_bp.route("/courses", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_courses():
    page, limit, skip = _paginate()
    query = {}
    if request.args.get("category"):
        query["category"] = request.args.get("category")
    if request.args.get("level"):
        query["level"] = request.args.get("level")
    total = Course.count(query)
    items = [Course.to_response(c) for c in Course.find_many(query, skip=skip, limit=limit)]
    return jsonify({
        "success": True,
        "data": items,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }), 200


@admin_catalog_bp.route("/courses", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_course():
    data = request.get_json() or {}
    if not data.get("title") or not data.get("category"):
        return jsonify({"success": False, "message": "title and category are required"}), 400
    doc = Course.create(data)
    _audit("create", "course", str(doc["_id"]), data)
    return jsonify({"success": True, "data": Course.to_response(doc)}), 201


@admin_catalog_bp.route("/courses/<course_id>", methods=["PUT"])
@authenticate_admin
@authorize("content_update")
def update_course(course_id):
    data = request.get_json() or {}
    doc = Course.update(course_id, data)
    if not doc:
        return jsonify({"success": False, "message": "Course not found"}), 404
    _audit("update", "course", course_id, data)
    return jsonify({"success": True, "data": Course.to_response(doc)}), 200


@admin_catalog_bp.route("/courses/<course_id>", methods=["DELETE"])
@authenticate_admin
@authorize("content_delete")
def delete_course(course_id):
    if not Course.delete(course_id):
        return jsonify({"success": False, "message": "Course not found"}), 404
    _audit("delete", "course", course_id)
    return jsonify({"success": True, "message": "Course deleted"}), 200


# ── Learning Paths (Roadmaps) ───────────────────────────────────────────────

@admin_catalog_bp.route("/roadmaps", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_roadmaps():
    page, limit, skip = _paginate()
    query = {}
    if request.args.get("category"):
        query["category"] = request.args.get("category")
    total = LearningPathCatalog.count(query)
    items = [LearningPathCatalog.to_response(p) for p in LearningPathCatalog.find_many(query, skip=skip, limit=limit)]
    return jsonify({
        "success": True,
        "data": items,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }), 200


@admin_catalog_bp.route("/roadmaps", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_roadmap():
    data = request.get_json() or {}
    if not data.get("category") or not data.get("steps"):
        return jsonify({"success": False, "message": "category and steps are required"}), 400
    doc = LearningPathCatalog.create(data)
    _audit("create", "roadmap", str(doc["_id"]), data)
    return jsonify({"success": True, "data": LearningPathCatalog.to_response(doc)}), 201


@admin_catalog_bp.route("/roadmaps/<path_id>", methods=["PUT"])
@authenticate_admin
@authorize("content_update")
def update_roadmap(path_id):
    data = request.get_json() or {}
    doc = LearningPathCatalog.update(path_id, data)
    if not doc:
        return jsonify({"success": False, "message": "Roadmap not found"}), 404
    _audit("update", "roadmap", path_id, data)
    return jsonify({"success": True, "data": LearningPathCatalog.to_response(doc)}), 200


@admin_catalog_bp.route("/roadmaps/<path_id>", methods=["DELETE"])
@authenticate_admin
@authorize("content_delete")
def delete_roadmap(path_id):
    if not LearningPathCatalog.delete(path_id):
        return jsonify({"success": False, "message": "Roadmap not found"}), 404
    _audit("delete", "roadmap", path_id)
    return jsonify({"success": True, "message": "Roadmap deleted"}), 200


# ── Recommendation Rules ────────────────────────────────────────────────────

@admin_catalog_bp.route("/recommendation-rules", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_rules():
    page, limit, skip = _paginate()
    query = {}
    if request.args.get("category"):
        query["category"] = request.args.get("category")
    total = RecommendationRule.count(query)
    items = [RecommendationRule.to_response(r) for r in RecommendationRule.find_many(query, skip=skip, limit=limit)]
    return jsonify({
        "success": True,
        "data": items,
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    }), 200


@admin_catalog_bp.route("/recommendation-rules", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_rule():
    data = request.get_json() or {}
    if not data.get("category") or data.get("level") is None:
        return jsonify({"success": False, "message": "category and level are required"}), 400
    doc = RecommendationRule.create(data)
    _audit("create", "recommendation_rule", str(doc["_id"]), data)
    return jsonify({"success": True, "data": RecommendationRule.to_response(doc)}), 201


@admin_catalog_bp.route("/recommendation-rules/<rule_id>", methods=["PUT"])
@authenticate_admin
@authorize("content_update")
def update_rule(rule_id):
    data = request.get_json() or {}
    doc = RecommendationRule.update(rule_id, data)
    if not doc:
        return jsonify({"success": False, "message": "Rule not found"}), 404
    _audit("update", "recommendation_rule", rule_id, data)
    return jsonify({"success": True, "data": RecommendationRule.to_response(doc)}), 200


@admin_catalog_bp.route("/recommendation-rules/<rule_id>", methods=["DELETE"])
@authenticate_admin
@authorize("content_delete")
def delete_rule(rule_id):
    if not RecommendationRule.delete(rule_id):
        return jsonify({"success": False, "message": "Rule not found"}), 404
    _audit("delete", "recommendation_rule", rule_id)
    return jsonify({"success": True, "message": "Rule deleted"}), 200


# ── Quiz Question Bank ──────────────────────────────────────────────────────

@admin_catalog_bp.route("/quiz-bank", methods=["GET"])
@authenticate_admin
@authorize("content_read")
def list_quiz_bank():
    page, limit, skip = _paginate(50)
    interest = request.args.get("interest")
    level = request.args.get("level")
    templates = Quiz.get_templates(interest=interest, level=level, skip=skip, limit=limit)
    total = Quiz.count_templates(interest=interest, level=level)
    return jsonify({
        "success": True,
        "data": [Quiz.template_to_response(t) for t in templates],
        "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit or 1},
    }), 200


@admin_catalog_bp.route("/quiz-bank", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def create_quiz_template():
    data = request.get_json() or {}
    if not data.get("interest") or not data.get("questions"):
        return jsonify({"success": False, "message": "interest and questions are required"}), 400
    doc = Quiz.create_template(data)
    _audit("create", "quiz_template", str(doc.get("_id")), {"interest": data.get("interest")})
    return jsonify({"success": True, "data": Quiz.template_to_response(doc)}), 201


@admin_catalog_bp.route("/quiz-bank/<template_id>", methods=["PUT"])
@authenticate_admin
@authorize("content_update")
def update_quiz_template(template_id):
    data = request.get_json() or {}
    doc = Quiz.update_template(template_id, data)
    if not doc:
        return jsonify({"success": False, "message": "Template not found"}), 404
    _audit("update", "quiz_template", template_id, data)
    return jsonify({"success": True, "data": Quiz.template_to_response(doc)}), 200


@admin_catalog_bp.route("/quiz-bank/<template_id>", methods=["DELETE"])
@authenticate_admin
@authorize("content_delete")
def delete_quiz_template(template_id):
    if not Quiz.delete_template(template_id):
        return jsonify({"success": False, "message": "Template not found"}), 404
    _audit("delete", "quiz_template", template_id)
    return jsonify({"success": True, "message": "Template deleted"}), 200


@admin_catalog_bp.route("/catalog/seed", methods=["POST"])
@authenticate_admin
@authorize("content_create")
def seed_catalog():
    from seed_recommendation_catalog import seed_recommendation_catalog
    force = (request.get_json() or {}).get("force", False)
    counts = seed_recommendation_catalog(force=force)
    _audit("seed", "recommendation_catalog", changes=counts)
    return jsonify({"success": True, "message": "Catalog seeded", "counts": counts}), 200
