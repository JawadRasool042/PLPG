"""
============================================
Advanced Interest Intelligence Routes
============================================

RESTful API for the Advanced AI Interest Intelligence System.

Endpoints:
- POST /api/interest/analyze - Full analysis pipeline
- POST /api/interest/resolve-tie - Tie resolution
- GET /api/interest/careers/{domain} - Career paths
"""

from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
import logging
from datetime import datetime, timedelta
from middleware.auth import authenticate_token
from services.interest_intelligence_engine import InterestIntelligenceEngine
from models.user import User
from database import get_collection

logger = logging.getLogger(__name__)

bp = Blueprint('interest_intelligence', __name__)


# ---------------------------------------------------------------------------
# Persistence helpers (Requirements C3 + C5)
# ---------------------------------------------------------------------------

PENDING_TIE_TTL_MINUTES = 30
_PENDING_TIE_INDEX_READY = False


def _ensure_pending_tie_index() -> None:
    """Create a TTL index on the pending-tie cache (idempotent)."""
    global _PENDING_TIE_INDEX_READY
    if _PENDING_TIE_INDEX_READY:
        return
    try:
        col = get_collection('interest_pending_resolution')
        col.create_index('createdAt', expireAfterSeconds=PENDING_TIE_TTL_MINUTES * 60)
        col.create_index('userId', unique=True)
        _PENDING_TIE_INDEX_READY = True
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not ensure pending-tie indexes: %s", exc)


def _build_assessment_payload(
    result,
    primary_override: str | None = None,
    domain_scores: dict | None = None,
    user_context: dict | None = None,
) -> dict:
    """Convert an analysis result + optional override into the User.interestAssessment shape."""
    primary = primary_override or result.primary_interest

    ranked = result.ranked_interests or []
    all_interests: list[dict] = []
    primary_confidence = 0.0
    for entry in ranked:
        try:
            confidence_raw = entry.get('confidence', 0)
            if isinstance(confidence_raw, str):
                confidence_raw = float(confidence_raw.replace('%', '').strip() or 0)
            confidence = float(confidence_raw) / 100 if float(confidence_raw) > 1 else float(confidence_raw)
        except (TypeError, ValueError):
            confidence = 0.0
        domain = entry.get('name') or entry.get('domain') or ''
        all_interests.append({'domain': domain, 'confidence': round(max(0.0, min(1.0, confidence)), 4)})
        if domain == primary:
            primary_confidence = confidence

    if primary and not any(i['domain'] == primary for i in all_interests):
        all_interests.insert(0, {'domain': primary, 'confidence': primary_confidence})

    now = datetime.utcnow()
    payload: dict = {
        'completed': True,
        'primaryInterest': primary,
        'confidence': round(max(0.0, min(1.0, primary_confidence)), 4),
        'allInterests': all_interests,
        'domainScores': domain_scores or {},
        'tieResolved': bool(primary_override),
        'completedAt': now,
        'lastUpdated': now,
    }

    if user_context and isinstance(user_context, dict):
        known = user_context.get('known')
        want = user_context.get('want')
        goals = user_context.get('goals') or user_context.get('learning_goals')
        if known or want or goals:
            payload['assessmentContext'] = {
                'known': str(known or ''),
                'want': str(want or ''),
                'goals': str(goals or ''),
            }
        tags = user_context.get('assessment_tags')
        if isinstance(tags, list):
            cleaned_tags = [str(t).strip() for t in tags if str(t).strip()]
            if cleaned_tags:
                payload['assessmentTags'] = cleaned_tags

    return payload


def _persist_assessment(user_id: str, payload: dict, primary: str) -> None:
    """Update User.interestAssessment + focusDomains in Mongo."""
    try:
        ok = User.update(user_id, {
            'interestAssessment': payload,
            'focusDomains': [primary] if primary else [],
        })
        if not ok:
            logger.error("interestAssessment update matched no user document for user %s", user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist interestAssessment for user %s: %s", user_id, exc)


def _cache_pending_tie(user_id: str, result_dict: dict) -> None:
    """Persist the most recent analysis so /resolve-tie can pin a primary later."""
    try:
        _ensure_pending_tie_index()
        col = get_collection('interest_pending_resolution')
        col.replace_one(
            {'userId': user_id},
            {
                'userId': user_id,
                'analysis': result_dict,
                'createdAt': datetime.utcnow(),
            },
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to cache pending tie for %s: %s", user_id, exc)


def _load_pending_tie(user_id: str) -> dict | None:
    try:
        col = get_collection('interest_pending_resolution')
        doc = col.find_one({'userId': user_id})
        if not doc:
            return None
        created_at = doc.get('createdAt')
        if isinstance(created_at, datetime):
            if datetime.utcnow() - created_at > timedelta(minutes=PENDING_TIE_TTL_MINUTES):
                return None
        return doc.get('analysis')
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not load pending tie for %s: %s", user_id, exc)
        return None


def _clear_pending_tie(user_id: str) -> None:
    try:
        get_collection('interest_pending_resolution').delete_one({'userId': user_id})
    except Exception:  # noqa: BLE001
        pass


# ============================================================================
# ENDPOINTS
# ============================================================================

@bp.post('/analyze')
@cross_origin()
@authenticate_token
def analyze_interests():
    """
    Comprehensive advanced interest analysis with:
    - Multi-dimensional weighted scoring (base + behavioral + contextual)
    - Anomaly detection
    - Trend analysis
    - Tie detection with confidence
    - Skill gap identification
    - Success rate prediction
    
    Request JSON:
    {
      "interests": {
        "Coding": 8,
        "Web Development": 7,
        ...
      },
      "behavioral_data": {
        "Coding": {
          "time_spent_minutes": 45,
          "quiz_performance": 8.5,
          "click_frequency": 7,
          "repeat_selection": 9
        },
        ...
      },
      "user_context": {
        "career_goals": ["Software Engineer"],
        "current_skills": ["Python", "JavaScript"],
        "learning_goals": ["Build web apps"]
      },
      "historical_data": [
        {"domain": "Coding", "score": 7.5, "date": "2024-01-01"},
        ...
      ]
    }
    
    Response: Structured JSON with full advanced analysis
    """
    try:
        data = request.json or {}
        interests = data.get('interests', {})
        behavioral_data = data.get('behavioral_data')
        user_context = data.get('user_context')
        historical_data = data.get('historical_data')
        
        # Validate interests
        if not interests or not isinstance(interests, dict):
            return jsonify({
                'success': False,
                'error': 'interests must be a non-empty dict with domain: rating pairs'
            }), 400
        
        # Validate ratings are 0-10
        for domain, rating in interests.items():
            try:
                rating_float = float(rating)
                if not 0 <= rating_float <= 10:
                    return jsonify({
                        'success': False,
                        'error': f'Rating for {domain} must be between 0 and 10, got {rating_float}'
                    }), 400
            except (TypeError, ValueError):
                return jsonify({
                    'success': False,
                    'error': f'Invalid rating for {domain}: {rating}'
                }), 400

        # Hard-stop all-zero submissions so the system does not fabricate a ranking.
        if not any(float(v) > 0 for v in interests.values()):
            return jsonify({
                'success': False,
                'error': 'Please rate at least one domain above 0 to generate a meaningful ranking.'
            }), 400
        
        logger.info(f"Advanced analysis for user {g.user['id']}: {list(interests.keys())}")
        
        # Run advanced analysis
        engine = InterestIntelligenceEngine()
        result = engine.analyze_interests(
            interests=interests,
            behavioral_data=behavioral_data,
            user_context=user_context,
            historical_data=historical_data
        )
        
        # Convert to JSON-serializable format
        response_data = {
            'success': True,
            'primary_interest': result.primary_interest,
            'ranked_interests': result.ranked_interests,
            'tie_detected': {
                'is_tie': result.tie_detected.is_tie,
                'tie_candidates': result.tie_detected.tie_candidates,
                'tie_confidence': round(result.tie_detected.tie_confidence, 2),
                'resolution_question': result.tie_detected.resolution_question,
                'suggested_differentiators': result.tie_detected.suggested_differentiators
            },
            'anomaly_detection': {
                'is_anomalous': result.anomaly_detection.is_anomalous,
                'anomaly_type': result.anomaly_detection.anomaly_type,
                'anomaly_score': round(result.anomaly_detection.anomaly_score, 2),
                'confidence': round(result.anomaly_detection.confidence, 2),
                'recommendation': result.anomaly_detection.recommendation
            },
            'interest_trends': [
                {
                    'domain': t.domain,
                    'trend_direction': t.trend_direction,
                    'trend_strength': round(t.trend_strength, 2),
                    'volatility': round(t.volatility, 2),
                    'recent_scores': t.recent_scores
                }
                for t in result.interest_trends
            ],
            'recommendation': result.recommendation,
            'quality_metrics': result.quality_metrics,
            'data_validation': result.data_validation,
            'timestamp': result.timestamp,
            'metadata': {
                'system': 'Advanced AI Interest Intelligence Engine v2.0',
                'version': '2.0',
                'accuracy': 'Production-Grade',
                'features': [
                    'Multi-dimensional scoring',
                    'Anomaly detection',
                    'Trend analysis',
                    'Skill gap identification',
                    'Success prediction'
                ]
            }
        }
        
        logger.info(
            "Advanced analysis complete: primary=%s, anomaly=%s, tie=%s",
            result.primary_interest,
            result.anomaly_detection.is_anomalous,
            result.tie_detected.is_tie,
        )

        user_id = g.user.get('id') if hasattr(g, 'user') else None
        is_tie = bool(result.tie_detected.is_tie)

        if user_id:
            if is_tie:
                # Stash the analysis so /resolve-tie can use it later.
                _cache_pending_tie(
                    user_id,
                    {
                        **response_data,
                        'domain_scores': interests,
                        'user_context': user_context if isinstance(user_context, dict) else {},
                    },
                )
            else:
                payload = _build_assessment_payload(
                    result,
                    domain_scores=interests,
                    user_context=user_context if isinstance(user_context, dict) else None,
                )
                _persist_assessment(user_id, payload, result.primary_interest)
                _clear_pending_tie(user_id)
                response_data['persisted'] = True

        return jsonify(response_data), 200

    except Exception as e:
        logger.exception(f"Error in advanced interest analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/resolve-tie')
@cross_origin()
@authenticate_token
def resolve_tie():
    """
    Resolve a detected tie by user selection.
    
    Request JSON:
    {
      "selected_interest": "Web Development"
    }
    
    Response: Confirmation with updated primary interest
    """
    try:
        data = request.json or {}
        selected_interest = (data.get('selected_interest') or '').strip()

        if not selected_interest:
            return jsonify({
                'success': False,
                'error': 'selected_interest is required'
            }), 400

        user_id = g.user['id']
        logger.info("Resolving tie for user %s: %s", user_id, selected_interest)

        cached = _load_pending_tie(user_id)
        if not cached:
            # Fallback: allow the client to send the latest tie analysis snapshot.
            # This avoids false negatives when cache TTL/indexing clears pending ties early.
            snapshot = data.get('analysis_snapshot')
            if isinstance(snapshot, dict) and snapshot.get('ranked_interests'):
                cached = snapshot
                logger.info(
                    "Using client-provided analysis snapshot for tie resolution (user=%s)",
                    user_id,
                )
            else:
                return jsonify({
                    'success': False,
                    'error': (
                        'No pending interest analysis found. Please retake the assessment '
                        'before resolving a tie.'
                    ),
                    'code': 'NO_PENDING_TIE_ANALYSIS',
                }), 404

        # Verify the selected interest was actually one of the tie candidates.
        tie_info = cached.get('tie_detected') or {}
        candidates = tie_info.get('tie_candidates') or []
        if candidates and selected_interest not in candidates:
            return jsonify({
                'success': False,
                'error': (
                    f"'{selected_interest}' was not among the tie candidates "
                    f"({', '.join(candidates)})."
                ),
            }), 400

        # Re-shape the cached analysis with the resolved primary.
        ranked = list(cached.get('ranked_interests') or [])
        all_interests: list[dict] = []
        for entry in ranked:
            try:
                confidence_raw = entry.get('confidence', 0)
                if isinstance(confidence_raw, str):
                    confidence_raw = float(confidence_raw.replace('%', '').strip() or 0)
                confidence = float(confidence_raw) / 100 if float(confidence_raw) > 1 else float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.0
            domain = entry.get('name') or entry.get('domain') or ''
            all_interests.append({
                'domain': domain,
                'confidence': round(max(0.0, min(1.0, confidence)), 4),
            })

        chosen_confidence = next(
            (i['confidence'] for i in all_interests if i['domain'] == selected_interest),
            0.0,
        )
        if not any(i['domain'] == selected_interest for i in all_interests):
            all_interests.insert(0, {'domain': selected_interest, 'confidence': chosen_confidence})

        now = datetime.utcnow()
        domain_scores = cached.get('domain_scores') or cached.get('interests') or {}
        user_context = cached.get('user_context') if isinstance(cached.get('user_context'), dict) else None
        payload = {
            'completed': True,
            'primaryInterest': selected_interest,
            'confidence': chosen_confidence,
            'allInterests': all_interests,
            'domainScores': domain_scores if isinstance(domain_scores, dict) else {},
            'tieResolved': True,
            'completedAt': now,
            'lastUpdated': now,
        }
        if user_context:
            known = user_context.get('known')
            want = user_context.get('want')
            goals = user_context.get('goals') or user_context.get('learning_goals')
            if known or want or goals:
                payload['assessmentContext'] = {
                    'known': str(known or ''),
                    'want': str(want or ''),
                    'goals': str(goals or ''),
                }
            tags = user_context.get('assessment_tags')
            if isinstance(tags, list):
                cleaned = [str(t).strip() for t in tags if str(t).strip()]
                if cleaned:
                    payload['assessmentTags'] = cleaned

        _persist_assessment(user_id, payload, selected_interest)
        _clear_pending_tie(user_id)

        return jsonify({
            'success': True,
            'message': f'Tie resolved. {selected_interest} set as primary interest.',
            'primary_interest': selected_interest,
            'confidence': chosen_confidence,
            'all_interests': all_interests,
            'timestamp': now.isoformat(),
        }), 200

    except Exception as e:
        logger.exception(f"Error resolving tie: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.get('/careers/<domain>')
@cross_origin()
def get_career_paths(domain):
    """Get AI-generated career paths for a domain."""
    try:
        from advanced_learning_path.engine import AdvancedLearningPathEngine

        path_result = AdvancedLearningPathEngine().generate_roadmap(domain, {"user": {}})
        careers_detailed = path_result.get("careers_detailed") or []
        if not careers_detailed:
            return jsonify({
                'success': False,
                'error': f'No careers generated for domain {domain}. Ensure OPENAI_API_KEY is set.'
            }), 404

        career_paths = [
            {
                'title': c.get('title'),
                'industry': c.get('industry'),
                'salary_range': c.get('salary_range'),
                'growth_potential': c.get('growth_potential'),
                'required_skills': c.get('required_skills', []),
            }
            for c in careers_detailed
        ]

        return jsonify({
            'success': True,
            'domain': domain,
            'career_paths': career_paths,
            'pakistani_jobs': path_result.get('pakistani_jobs') or [],
            'source': 'openai',
            'market_region': path_result.get('market_region'),
            'salary_currency': path_result.get('salary_currency'),
        }), 200

    except Exception as e:
        logger.exception(f"Error fetching careers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.get('/domains')
@cross_origin()
def get_all_domains():
    """Get list of all supported domains from the database catalog."""
    try:
        from models.category import Category

        categories = Category.find_many(active_only=True)
        domains = [c.get('name') for c in categories if c.get('name')]

        return jsonify({
            'success': True,
            'domains': domains,
            'count': len(domains)
        }), 200

    except Exception as e:
        logger.exception(f"Error fetching domains: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.get('/health')
@cross_origin()
def health_check():
    """Health check for advanced interest analysis system."""
    try:
        engine = InterestIntelligenceEngine()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'system': 'Advanced AI Interest Intelligence Engine v2.0',
            'version': '2.0',
            'domains_supported': len(engine.domains),
            'features': [
                'Multi-dimensional scoring',
                'Anomaly detection',
                'Trend analysis',
                'Skill gap identification',
                'Success prediction',
                'Tie resolution with confidence'
            ],
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@bp.post('/skill-gaps')
@cross_origin()
@authenticate_token
def get_skill_gaps():
    """
    Get skill gaps for a specific domain.
    
    Request JSON:
    {
      "domain": "Web Development",
      "current_skills": ["HTML", "CSS"],
      "target_level": "Intermediate"
    }
    """
    try:
        data = request.json or {}
        domain = data.get('domain')
        current_skills = data.get('current_skills', [])
        target_level = data.get('target_level', 'Intermediate')
        
        if not domain:
            return jsonify({
                'success': False,
                'error': 'domain is required'
            }), 400

        from advanced_learning_path.engine import AdvancedLearningPathEngine

        path_result = AdvancedLearningPathEngine().generate_roadmap(
            domain,
            {
                'user': {},
                'quiz_caliber': {'recommended_quiz_difficulty': target_level.lower()},
            },
        )
        roadmap = path_result.get('roadmap') or {}
        block = roadmap.get(target_level.lower()) or roadmap.get('basic') or roadmap.get('beginner') or {}
        required_skills = block.get('topics') or block.get('all_topics') or []
        
        # Identify gaps
        current_skills_lower = [s.lower() for s in current_skills]
        gaps = []
        
        for skill in required_skills:
            has_skill = any(skill.lower() in cs for cs in current_skills_lower)
            if not has_skill:
                gaps.append({
                    'skill': skill,
                    'priority': 'high' if skill in required_skills[:2] else 'medium',
                    'estimated_hours': 20 if skill in required_skills[:2] else 10
                })
        
        return jsonify({
            'success': True,
            'domain': domain,
            'target_level': target_level,
            'current_skills': current_skills,
            'required_skills': required_skills,
            'skill_gaps': gaps,
            'total_gap_hours': sum(g['estimated_hours'] for g in gaps),
            'completion_percentage': round((len(current_skills) / len(required_skills)) * 100, 1) if required_skills else 0
        }), 200
        
    except Exception as e:
        logger.exception(f"Error getting skill gaps: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.post('/learning-path')
@cross_origin()
@authenticate_token
def get_personalized_learning_path():
    """
    Get personalized learning path based on interests and current level.
    
    Request JSON:
    {
      "domain": "Web Development",
      "current_level": "Beginner",
      "available_hours_per_week": 10,
      "learning_style": "project-based"
    }
    """
    try:
        data = request.json or {}
        domain = data.get('domain')
        current_level = data.get('current_level', 'Beginner')
        available_hours = data.get('available_hours_per_week', 10)
        learning_style = data.get('learning_style', 'mixed')
        
        if not domain:
            return jsonify({
                'success': False,
                'error': 'domain is required'
            }), 400

        from advanced_learning_path.engine import AdvancedLearningPathEngine

        path_result = AdvancedLearningPathEngine().generate_roadmap(
            domain,
            {
                'user': {
                    'learning_style': learning_style,
                    'weekly_availability_hours': available_hours,
                },
            },
        )
        roadmap = path_result.get('roadmap') or {}
        level_map = {
            'Basic': 'basic',
            'Beginner': 'basic',
            'Intermediate': 'intermediate',
            'Advanced': 'advanced',
            'Expert': 'expert',
        }
        level_key = level_map.get(current_level, 'basic')
        block = roadmap.get(level_key) or roadmap.get('basic') or roadmap.get('beginner') or {}
        topics = block.get('topics') or block.get('all_topics') or []
        duration_label = block.get('duration_label') or '4-6 weeks'
        
        # Calculate pace
        weeks = 4 if current_level in ('Beginner', 'Basic') else 6 if current_level == 'Intermediate' else 8 if current_level == 'Advanced' else 10
        total_hours = weeks * 40  # Assume 40 hours per week standard
        pace_multiplier = 40 / available_hours if available_hours > 0 else 1
        adjusted_weeks = int(weeks * pace_multiplier)
        
        path = {
            'domain': domain,
            'current_level': current_level,
            'learning_style': learning_style,
            'available_hours_per_week': available_hours,
            'estimated_duration_weeks': adjusted_weeks,
            'duration_label': duration_label,
            'total_hours_required': total_hours,
            'topics': topics,
            'careers_detailed': path_result.get('careers_detailed') or [],
            'pakistani_jobs': path_result.get('pakistani_jobs') or [],
            'market_region': path_result.get('market_region'),
            'salary_currency': path_result.get('salary_currency'),
            'source': 'openai',
            'weekly_schedule': {
                'hours_per_week': available_hours,
                'sessions_per_week': max(2, int(available_hours / 3)),
                'session_duration_minutes': 90
            },
            'milestones': [
                {
                    'week': adjusted_weeks // 3,
                    'goal': f'Complete first {len(topics) // 3} topics',
                    'deliverable': 'Small project'
                },
                {
                    'week': (adjusted_weeks * 2) // 3,
                    'goal': f'Master intermediate concepts',
                    'deliverable': 'Medium project'
                },
                {
                    'week': adjusted_weeks,
                    'goal': 'Achieve proficiency',
                    'deliverable': 'Capstone project'
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'learning_path': path
        }), 200
        
    except Exception as e:
        logger.exception(f"Error generating learning path: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
