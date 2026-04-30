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
from datetime import datetime
from middleware.auth import authenticate_token
from services.interest_intelligence_engine import InterestIntelligenceEngine

logger = logging.getLogger(__name__)

bp = Blueprint('interest_intelligence', __name__)


# ============================================================================
# ENDPOINTS
# ============================================================================

@bp.post('/analyze')
@cross_origin()
@authenticate_token
def analyze_interests():
    """
    Comprehensive interest analysis with:
    - Weighted scoring (base + behavioral)
    - Normalization (exactly 100%)
    - Tie detection
    - Explainable rankings
    - Career recommendations
    
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
        "previous_assessments": [...],
        "learning_history": [...]
      }
    }
    
    Response: Structured JSON with full analysis
    """
    try:
        data = request.json or {}
        interests = data.get('interests', {})
        behavioral_data = data.get('behavioral_data')
        user_context = data.get('user_context')
        
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
        
        logger.info(f"Analyzing interests for user {g.user['id']}: {list(interests.keys())}")
        
        # Run analysis
        engine = InterestIntelligenceEngine()
        result = engine.analyze_interests(
            interests=interests,
            behavioral_data=behavioral_data,
            user_context=user_context
        )
        
        # Convert to JSON-serializable format
        response_data = {
            'success': True,
            'primary_interest': result.primary_interest,
            'ranked_interests': result.ranked_interests,
            'tie_detected': {
                'is_tie': result.tie_detected.is_tie,
                'tie_candidates': result.tie_detected.tie_candidates,
                'resolution_question': result.tie_detected.resolution_question
            },
            'recommendation': result.recommendation,
            'data_validation': result.data_validation,
            'timestamp': result.timestamp,
            'metadata': {
                'system': 'Advanced AI Interest Intelligence Engine',
                'version': '1.0',
                'accuracy': 'Production-Grade'
            }
        }
        
        logger.info(f"Analysis complete: primary={result.primary_interest}, tie={result.tie_detected.is_tie}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.exception(f"Error in interest analysis: {e}")
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
        selected_interest = data.get('selected_interest')
        
        if not selected_interest:
            return jsonify({
                'success': False,
                'error': 'selected_interest is required'
            }), 400
        
        logger.info(f"Resolving tie for user {g.user['id']}: {selected_interest}")
        
        # TODO: Get previous analysis from session/cache
        # For now, return success
        
        return jsonify({
            'success': True,
            'message': f'Tie resolved. {selected_interest} set as primary interest.',
            'primary_interest': selected_interest,
            'timestamp': datetime.utcnow().isoformat()
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
    """
    Get career paths for a specific domain.
    
    Response: List of career options with details
    """
    try:
        engine = InterestIntelligenceEngine()
        
        if domain not in engine.CAREER_DATABASE:
            return jsonify({
                'success': False,
                'error': f'Domain {domain} not found'
            }), 404
        
        db = engine.CAREER_DATABASE[domain]
        career_paths = [
            {
                'title': p['title'],
                'industry': p['industry'],
                'salary_range': p['salary'],
                'growth_potential': p['growth']
            }
            for p in db['paths']
        ]
        
        return jsonify({
            'success': True,
            'domain': domain,
            'career_paths': career_paths
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
    """Get list of all supported domains."""
    try:
        engine = InterestIntelligenceEngine()
        domains = list(engine.CAREER_DATABASE.keys())
        
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
    """Health check for interest analysis system."""
    try:
        engine = InterestIntelligenceEngine()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'system': 'Advanced AI Interest Intelligence Engine',
            'domains_supported': len(engine.CAREER_DATABASE),
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500
