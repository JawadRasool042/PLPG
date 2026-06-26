"""
============================================
Recommendation Routes - API Endpoints
============================================

RESTful API endpoints for personalized recommendations
"""

import logging
from flask import Blueprint, request, jsonify, g

from middleware.auth import authenticate_token, get_current_user_id
from models.user import User
from models.user_analytics import UserAnalytics
from services.recommendation_engine import RecommendationEngine
from services.dynamic_recommendation_service import DynamicRecommendationService
from services.interest_intelligence_engine import InterestIntelligenceEngine

logger = logging.getLogger(__name__)

recommendations_bp = Blueprint('recommendations', __name__)


def _current_user_id_or_401():
    user_id = get_current_user_id()
    if not user_id:
        return None, (jsonify({'success': False, 'message': 'Unauthorized'}), 401)
    return user_id, None


@recommendations_bp.route('/generate', methods=['POST'])
@authenticate_token
def generate_recommendation():
    """
    Generate personalized recommendation for user
    
    POST /api/recommendations/generate
    Body: {
        "interest_scores": { "domain": score, ... },
        "force_regenerate": false (optional)
    }
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400
        
        interest_scores = data.get('interest_scores')
        multidim_responses = data.get('multidim_responses')
        force_regenerate = data.get('force_regenerate', False)
        
        if not interest_scores:
            return jsonify({
                'success': False,
                'message': 'interest_scores is required'
            }), 400
        
        # Get user analytics
        analytics = UserAnalytics.get_analytics(user_id)
        if not analytics:
            UserAnalytics.initialize_analytics(user_id)
            analytics = UserAnalytics.get_analytics(user_id)
        
        # Generate recommendation
        recommendation = RecommendationEngine.generate_and_store_recommendation(
            user_id,
            interest_scores,
            analytics,
            g.user,
            force_regenerate,
            multidim_responses=multidim_responses
        )
        
        # If engine requested clarification (tie or suspicious responses)
        if recommendation.get('action') == 'request_clarification':
            return jsonify({
                'success': False,
                'message': 'Clarification required',
                'clarification': recommendation.get('clarification'),
                'question': recommendation.get('question')
            }), 200

        # Record interest trend in analytics
        UserAnalytics.add_interest_trend(
            user_id,
            recommendation['primaryDomain'],
            [
                {
                    'domain': domain,
                    'score': score,
                    'percentile': round((score / 10) * 100, 1)
                }
                for domain, score in interest_scores.items()
            ]
        )
        
        return jsonify({
            'success': True,
            'message': 'Recommendation generated successfully',
            'recommendation': RecommendationEngine.to_response(recommendation, include_full=True)
        }), 201
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Invalid request: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"Error generating recommendation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate recommendation'
        }), 500


@recommendations_bp.route('/active', methods=['GET'])
@authenticate_token
def get_active_recommendation():
    """
    Get active recommendation for user
    
    GET /api/recommendations/active
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return jsonify({
                'success': False,
                'message': 'No active recommendation found. Please generate one.',
                'data': None
            }), 404
        
        return jsonify({
            'success': True,
            'recommendation': RecommendationEngine.to_response(recommendation, include_full=True)
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting active recommendation: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve recommendation'
        }), 500


@recommendations_bp.route('/summary', methods=['GET'])
@authenticate_token
def get_personalized_summary():
    """
    Get personalized learning summary
    
    GET /api/recommendations/summary
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        
        summary = RecommendationEngine.get_personalized_summary(user_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting personalized summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve summary'
        }), 500


@recommendations_bp.route('/history', methods=['GET'])
@authenticate_token
def get_recommendation_history():
    """
    Get recommendation history
    
    GET /api/recommendations/history?limit=5
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        limit = request.args.get('limit', 5, type=int)
        
        limit = max(1, min(limit, 20))  # Clamp between 1-20
        
        history = RecommendationEngine.get_recommendation_history(user_id, limit)
        
        return jsonify({
            'success': True,
            'count': len(history),
            'history': [RecommendationEngine.to_response(rec) for rec in history]
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting recommendation history: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve history'
        }), 500


@recommendations_bp.route('/learning-path', methods=['GET'])
@authenticate_token
def get_learning_path():
    """
    Get current learning path
    
    GET /api/recommendations/learning-path
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return jsonify({
                'success': False,
                'message': 'No active recommendation found',
                'data': None
            }), 404
        
        learning_path = recommendation.get('learningPath', {})
        
        return jsonify({
            'success': True,
            'learningPath': learning_path
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting learning path: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve learning path'
        }), 500


@recommendations_bp.route('/analytics', methods=['GET'])
@authenticate_token
def get_learning_analytics():
    """
    Get comprehensive learning analytics
    
    GET /api/recommendations/analytics
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        
        analytics = UserAnalytics.get_analytics(user_id)
        
        if not analytics:
            return jsonify({
                'success': False,
                'message': 'No analytics found',
                'data': None
            }), 404
        
        summary = UserAnalytics.get_learning_summary(user_id)
        
        return jsonify({
            'success': True,
            'analytics': summary
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve analytics'
        }), 500


@recommendations_bp.route('/interest-analysis', methods=['POST'])
@authenticate_token
def analyze_interests():
    """
    Analyze user interests with LLM
    
    POST /api/recommendations/interest-analysis
    Body: {
        "interest_scores": { "domain": score, ... }
    }
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        data = request.get_json()
        
        if not data or 'interest_scores' not in data:
            return jsonify({
                'success': False,
                'message': 'interest_scores is required'
            }), 400
        
        interest_scores = data['interest_scores']

        multidim_responses = data.get('multidim_responses')

        # Unified analysis using InterestIntelligenceEngine (legacy modules removed).
        scores = dict(interest_scores or {})
        if multidim_responses and isinstance(multidim_responses, dict):
            try:
                averaged = {}
                for domain, dims in multidim_responses.items():
                    if isinstance(dims, dict) and dims:
                        vals = []
                        for v in dims.values():
                            try:
                                vals.append(float(v))
                            except (TypeError, ValueError):
                                continue
                        if vals:
                            averaged[domain] = sum(vals) / len(vals)
                if averaged:
                    scores.update(averaged)
            except Exception:
                pass

        engine = InterestIntelligenceEngine()
        result = engine.analyze_interests(interests=scores, behavioral_data=None, user_context=g.user or {}, historical_data=None)
        
        return jsonify({
            'success': True,
            'analysis': {
                'primaryInterest': result.primary_interest,
                'rankedInterests': result.ranked_interests,
                'tieDetected': {
                    'isTie': result.tie_detected.is_tie,
                    'candidates': result.tie_detected.tie_candidates,
                    'tieConfidence': result.tie_detected.tie_confidence,
                    'question': result.tie_detected.resolution_question
                } if result.tie_detected else None,
                'anomaly': {
                    'isAnomalous': result.anomaly_detection.is_anomalous,
                    'type': result.anomaly_detection.anomaly_type,
                    'score': result.anomaly_detection.anomaly_score,
                    'confidence': result.anomaly_detection.confidence,
                    'recommendation': result.anomaly_detection.recommendation
                } if result.anomaly_detection else None,
                'recommendation': {
                    'careerPaths': result.recommendation.career_paths,
                    'skillRoadmap': result.recommendation.skill_roadmap,
                    'learningNextStep': result.recommendation.learning_next_step,
                    'justification': result.recommendation.justification,
                    'learningApproach': result.recommendation.learning_approach,
                } if result.recommendation else None,
                'qualityMetrics': result.quality_metrics,
                'dataValidation': result.data_validation,
                'timestamp': result.timestamp
            }
        }), 200
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Invalid request: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"Error analyzing interests: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to analyze interests. This could be due to API rate limits. Please try again later.'
        }), 500


@recommendations_bp.route('/next-milestones', methods=['GET'])
@authenticate_token
def get_next_milestones():
    """
    Get next learning milestones
    
    GET /api/recommendations/next-milestones
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return jsonify({
                'success': False,
                'message': 'No active recommendation found',
                'data': None
            }), 404
        
        milestones = recommendation.get('nextMilestones', [])[:3]
        
        return jsonify({
            'success': True,
            'milestones': milestones
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting milestones: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve milestones'
        }), 500


@recommendations_bp.route('/resources', methods=['GET'])
@authenticate_token
def get_recommended_resources():
    """
    Get recommended learning resources
    
    GET /api/recommendations/resources?limit=10
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        limit = request.args.get('limit', 10, type=int)
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return jsonify({
                'success': False,
                'message': 'No active recommendation found',
                'data': None
            }), 404
        
        resources = recommendation.get('detailedRecommendations', {}).get('top_resources', [])[:limit]
        
        return jsonify({
            'success': True,
            'count': len(resources),
            'resources': resources
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting resources: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve resources'
        }), 500


@recommendations_bp.route('/project-ideas', methods=['GET'])
@authenticate_token
def get_project_ideas():
    """
    Get suggested project ideas
    
    GET /api/recommendations/project-ideas?difficulty=Beginner
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        difficulty = request.args.get('difficulty', None)
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return jsonify({
                'success': False,
                'message': 'No active recommendation found',
                'data': None
            }), 404
        
        projects = recommendation.get('detailedRecommendations', {}).get('project_ideas', [])
        
        # Filter by difficulty if specified
        if difficulty:
            projects = [p for p in projects if p.get('difficulty') == difficulty]
        
        return jsonify({
            'success': True,
            'count': len(projects),
            'projects': projects
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting project ideas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve project ideas'
        }), 500


@recommendations_bp.route('', methods=['GET'])
@recommendations_bp.route('/', methods=['GET'])
@authenticate_token
def get_recommendations():
    """
    Get full personalized recommendations (careers, courses, roadmap, skill gap).

    GET /api/recommendations
    """
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized

        rec = DynamicRecommendationService.get_or_generate(user_id)
        return jsonify({
            'success': True,
            'data': DynamicRecommendationService.to_api_response(rec),
        }), 200
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve recommendations'}), 500


@recommendations_bp.route('/careers', methods=['GET'])
@authenticate_token
def get_recommended_careers():
    """GET /api/recommendations/careers"""
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        rec = DynamicRecommendationService.get_or_generate(user_id)
        return jsonify({
            'success': True,
            'skillLevel': rec.get('skillLevel'),
            'primaryDomain': rec.get('primaryDomain'),
            'careers': rec.get('careers', []),
        }), 200
    except Exception as e:
        logger.error(f"Error getting career recommendations: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve careers'}), 500


@recommendations_bp.route('/courses', methods=['GET'])
@authenticate_token
def get_recommended_courses():
    """GET /api/recommendations/courses"""
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        rec = DynamicRecommendationService.get_or_generate(user_id)
        return jsonify({
            'success': True,
            'skillLevel': rec.get('skillLevel'),
            'primaryDomain': rec.get('primaryDomain'),
            'courses': rec.get('courses', []),
        }), 200
    except Exception as e:
        logger.error(f"Error getting course recommendations: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve courses'}), 500


@recommendations_bp.route('/roadmap', methods=['GET'])
@authenticate_token
def get_recommended_roadmap():
    """GET /api/recommendations/roadmap"""
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        rec = DynamicRecommendationService.get_or_generate(user_id)
        return jsonify({
            'success': True,
            'skillLevel': rec.get('skillLevel'),
            'primaryDomain': rec.get('primaryDomain'),
            'roadmap': rec.get('roadmap'),
            'learningPath': rec.get('learningPath'),
        }), 200
    except Exception as e:
        logger.error(f"Error getting roadmap: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve roadmap'}), 500


@recommendations_bp.route('/skill-gap', methods=['GET'])
@authenticate_token
def get_skill_gap():
    """GET /api/recommendations/skill-gap"""
    try:
        user_id, unauthorized = _current_user_id_or_401()
        if unauthorized:
            return unauthorized
        rec = DynamicRecommendationService.get_or_generate(user_id)
        return jsonify({
            'success': True,
            'skillGapAnalysis': rec.get('skillGapAnalysis', {}),
            'strongestDomain': rec.get('strongestDomain'),
            'weakestDomain': rec.get('weakestDomain'),
            'overallScore': rec.get('overallScore'),
            'skillLevel': rec.get('skillLevel'),
        }), 200
    except Exception as e:
        logger.error(f"Error getting skill gap: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve skill gap analysis'}), 500
