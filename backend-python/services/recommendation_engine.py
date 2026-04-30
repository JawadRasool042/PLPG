"""
============================================
Recommendation Engine Service
============================================

This service manages personalized recommendations based on user interests
and learning analytics.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from database import get_collection
from services.interest_analyzer import InterestAnalyzer
from services.smart_interest_engine import SmartInterestEngine

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Service for managing personalized recommendations"""
    
    collection_name = 'recommendations'
    
    @staticmethod
    def get_collection():
        """Get the recommendations collection"""
        return get_collection(RecommendationEngine.collection_name)
    
    @staticmethod
    def generate_and_store_recommendation(user_id: str, interest_scores: Dict[str, float],
                                        user_analytics: Dict[str, Any] = None,
                                        user_info: Dict[str, Any] = None,
                                        force_regenerate: bool = False,
                                        multidim_responses: Dict[str, Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Generate and store recommendation for user
        
        Args:
            user_id: User ID
            interest_scores: Interest scores by domain
            user_analytics: User's learning analytics
            user_info: User profile information
            force_regenerate: Force regeneration even if recent recommendation exists
            
        Returns:
            Stored recommendation document
        """
        
        coll = RecommendationEngine.get_collection()
        
        # Check if recent recommendation exists
        if not force_regenerate:
            existing = coll.find_one({
                'userId': user_id,
                'expiresAt': {'$gt': datetime.utcnow()}
            })
            if existing:
                logger.info(f"Using existing recommendation for user {user_id}")
                return existing
        
        try:
            # Use SmartInterestEngine when multidimensional responses are available,
            # otherwise fall back to the existing InterestAnalyzer behavior.
            if multidim_responses:
                analysis = SmartInterestEngine.analyze_and_recommend(
                    user_id,
                    multidim_responses,
                    user_analytics,
                    user_info
                )

                primary_domain = None
                if analysis.get('adjustedScores'):
                    primary_domain = max(analysis['adjustedScores'].items(), key=lambda x: x[1])[0]

                    detailed_recs = analysis.get('detailedRecommendations', {}) or {}
                    # If SmartInterestEngine requested clarification (tie or suspicious), return that instruction
                    if analysis.get('action') == 'request_clarification':
                        return {
                            'userId': user_id,
                            'action': 'request_clarification',
                            'clarification': analysis.get('tieInfo') or analysis.get('suspicion') or {},
                            'question': (analysis.get('tieInfo', {}).get('clarification_question') if analysis.get('tieInfo') else None),
                            'generatedAt': analysis.get('generatedAt')
                        }

                    interest_analysis = {
                    'primary_interest': primary_domain,
                    'primary_score': analysis.get('adjustedScores', {}).get(primary_domain, 0) if primary_domain else 0,
                    'confidence': analysis.get('metrics', {}).get(primary_domain, {}).get('confidencePct', 0) if primary_domain else 0,
                    'secondary_interests': [],
                    'analysis': {
                        'explanation': analysis.get('reasons'),
                        'suspicion': analysis.get('suspicion'),
                    },
                    'all_scores': analysis.get('adjustedScores', {})
                }

            else:
                # Generate interest profile analysis (legacy)
                interest_analysis = InterestAnalyzer.analyze_interest_profile(
                    user_id, 
                    interest_scores,
                    user_analytics,
                    user_info
                )
                primary_domain = interest_analysis['primary_interest']
                detailed_recs = InterestAnalyzer.generate_detailed_recommendations(
                    primary_domain,
                    user_analytics,
                    user_info
                )
            
            # Create recommendation document
            recommendation_doc = {
                'userId': user_id,
                'primaryDomain': primary_domain,
                'confidence': interest_analysis['confidence'],
                'interestAnalysis': interest_analysis['analysis'],
                'secondaryInterests': interest_analysis['secondary_interests'],
                'allScores': interest_analysis['all_scores'],
                'detailedRecommendations': detailed_recs,
                'learningPath': RecommendationEngine._generate_learning_path(
                    primary_domain,
                    detailed_recs.get('learning_path', []),
                    user_analytics
                ),
                'nextMilestones': RecommendationEngine._generate_milestones(primary_domain),
                'generatedAt': datetime.utcnow(),
                'expiresAt': datetime.utcnow() + timedelta(days=30),
                'status': 'active'
            }
            
            # Store recommendation
            result = coll.update_one(
                {'userId': user_id, 'status': 'active'},
                {'$set': {'status': 'archived', 'archivedAt': datetime.utcnow()}},
                upsert=False
            )
            
            result = coll.insert_one(recommendation_doc)
            recommendation_doc['_id'] = result.inserted_id
            
            logger.info(f"Generated recommendation for user {user_id}: {primary_domain}")
            return recommendation_doc
        
        except Exception as e:
            logger.error(f"Error generating recommendation for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_active_recommendation(user_id: str) -> Optional[Dict[str, Any]]:
        """Get active recommendation for user"""
        coll = RecommendationEngine.get_collection()
        return coll.find_one({
            'userId': user_id,
            'status': 'active',
            'expiresAt': {'$gt': datetime.utcnow()}
        })
    
    @staticmethod
    def get_recommendation_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recommendation history for user"""
        coll = RecommendationEngine.get_collection()
        return list(coll.find({'userId': user_id})
                   .sort('generatedAt', -1)
                   .limit(limit))
    
    @staticmethod
    def _generate_learning_path(domain: str, learning_path_data: List[Dict],
                               user_analytics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate adaptive learning path"""
        
        # Determine user's current level based on analytics
        current_level = "Beginner"
        if user_analytics:
            avg_score = user_analytics.get('averageQuizScore', 0)
            if avg_score >= 70:
                current_level = "Intermediate"
            elif avg_score >= 85:
                current_level = "Advanced"
        
        # Build personalized learning path
        path = {
            'domain': domain,
            'currentLevel': current_level,
            'estimatedDuration': '6-12 months',
            'phases': [],
            'nextPhase': None,
            'progress': 0
        }
        
        # Add phases with personalized recommendations
        if learning_path_data:
            path['phases'] = learning_path_data
            
            # Find next phase based on current level
            for phase in learning_path_data:
                if phase.get('level') == current_level:
                    path['nextPhase'] = phase
                    break
            
            # If not found, set to first level not yet completed
            if not path['nextPhase'] and learning_path_data:
                path['nextPhase'] = learning_path_data[0]
        
        # Add specific goals
        path['goals'] = RecommendationEngine._generate_goals(domain, current_level)
        
        return path
    
    @staticmethod
    def _generate_goals(domain: str, level: str) -> List[Dict[str, Any]]:
        """Generate specific learning goals"""
        
        level_goals = {
            "Beginner": [
                "Understand core concepts and fundamentals",
                "Set up development environment",
                "Complete first small project",
                "Join community forums"
            ],
            "Intermediate": [
                "Build a medium-sized project",
                "Master key frameworks and tools",
                "Contribute to open source",
                "Learn best practices"
            ],
            "Advanced": [
                "Create professional-grade project",
                "Explore advanced topics",
                "Mentor others",
                "Consider specialization paths"
            ]
        }
        
        goals = level_goals.get(level, level_goals["Beginner"])
        
        return [
            {
                'id': f"goal_{i}",
                'description': goal,
                'status': 'not_started',
                'dueDate': datetime.utcnow() + timedelta(weeks=(i+1)*4),
                'priority': 'high' if i < 2 else 'medium'
            }
            for i, goal in enumerate(goals)
        ]
    
    @staticmethod
    def _generate_milestones(domain: str) -> List[Dict[str, Any]]:
        """Generate learning milestones"""
        
        return [
            {
                'name': 'Foundations Complete',
                'description': f'Master core {domain} fundamentals',
                'timeframe': '1-2 months',
                'indicators': ['Complete 5 beginner quizzes', 'Build first project', '70%+ accuracy']
            },
            {
                'name': 'Intermediate Skills',
                'description': f'Develop intermediate {domain} skills',
                'timeframe': '2-3 months',
                'indicators': ['Complete 10 intermediate quizzes', 'Build 2 projects', '80%+ accuracy']
            },
            {
                'name': 'Practical Competency',
                'description': f'Apply {domain} skills in real-world scenarios',
                'timeframe': '3-6 months',
                'indicators': ['Build portfolio project', 'Contribute to open source', '85%+ accuracy']
            },
            {
                'name': 'Professional Readiness',
                'description': f'Reach job-ready level in {domain}',
                'timeframe': '6-12 months',
                'indicators': ['Advanced project completion', 'Mentorship', '90%+ accuracy']
            }
        ]
    
    @staticmethod
    def get_personalized_summary(user_id: str) -> Dict[str, Any]:
        """
        Get personalized learning summary
        
        Returns:
            Summary including recommendations, progress, and next steps
        """
        
        recommendation = RecommendationEngine.get_active_recommendation(user_id)
        
        if not recommendation:
            return {
                'status': 'no_recommendation',
                'message': 'No active recommendation. Please complete interest assessment.'
            }
        
        return {
            'status': 'active',
            'primaryInterest': recommendation.get('primaryDomain'),
            'confidence': recommendation.get('confidence'),
            'analysis': recommendation.get('interestAnalysis', {}),
            'learningPath': recommendation.get('learningPath', {}),
            'nextMilestones': recommendation.get('nextMilestones', []),
            'topResources': recommendation.get('detailedRecommendations', {}).get('top_resources', [])[:5],
            'suggestedProjects': recommendation.get('detailedRecommendations', {}).get('project_ideas', [])[:3],
            'generatedAt': recommendation.get('generatedAt'),
            'expiresAt': recommendation.get('expiresAt')
        }
    
    @staticmethod
    def archive_old_recommendations(user_id: str, keep_count: int = 3) -> int:
        """Archive old recommendations, keeping only the most recent ones"""
        
        coll = RecommendationEngine.get_collection()
        
        # Find all recommendations for user, sorted by date
        recommendations = list(coll.find({'userId': user_id})
                               .sort('generatedAt', -1))
        
        archived_count = 0
        for rec in recommendations[keep_count:]:
            result = coll.update_one(
                {'_id': rec['_id']},
                {'$set': {'status': 'archived', 'archivedAt': datetime.utcnow()}}
            )
            archived_count += result.modified_count
        
        return archived_count
    
    @staticmethod
    def to_response(recommendation: Dict[str, Any], include_full: bool = False) -> Dict[str, Any]:
        """Convert recommendation document to API response"""
        
        if not recommendation:
            return None
        
        response = {
            'id': str(recommendation.get('_id')),
            'primaryDomain': recommendation.get('primaryDomain'),
            'confidence': recommendation.get('confidence'),
            'analysis': recommendation.get('interestAnalysis', {}),
            'secondaryInterests': recommendation.get('secondaryInterests', []),
            'learningPath': recommendation.get('learningPath', {}),
            'nextMilestones': recommendation.get('nextMilestones', [])[:3],
            'generatedAt': recommendation.get('generatedAt'),
            'expiresAt': recommendation.get('expiresAt')
        }
        
        if include_full:
            response['detailedRecommendations'] = recommendation.get('detailedRecommendations', {})
            response['allScores'] = recommendation.get('allScores', {})
        
        return response
