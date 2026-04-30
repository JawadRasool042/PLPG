"""
============================================
Learning Path Adapter Service
============================================

This service creates and manages personalized learning paths based on
user interests, performance, knowledge gaps, and learning objectives.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from database import get_collection
from models.user_analytics import UserAnalytics
from services.quiz_adaptor import QuizAdaptor

logger = logging.getLogger(__name__)


class LearningPathAdapter:
    """Service for creating adaptive learning paths"""
    
    collection_name = 'learning_paths'
    
    @staticmethod
    def get_collection():
        """Get the learning paths collection"""
        return get_collection(LearningPathAdapter.collection_name)
    
    @staticmethod
    def generate_learning_path(user_id: str, primary_domain: str,
                              current_level: str = 'Beginner',
                              user_goals: List[str] = None) -> Dict[str, Any]:
        """
        Generate a personalized learning path
        
        Args:
            user_id: User ID
            primary_domain: Primary domain of interest
            current_level: User's current skill level
            user_goals: User's learning goals
            
        Returns:
            Personalized learning path document
        """
        
        # Get user analytics
        analytics = UserAnalytics.get_analytics(user_id)
        
        # Create learning path phases
        phases = LearningPathAdapter._create_learning_phases(
            primary_domain,
            current_level,
            analytics
        )
        
        # Create knowledge map
        knowledge_map = LearningPathAdapter._create_knowledge_map(
            primary_domain,
            current_level,
            analytics
        )
        
        # Identify knowledge gaps
        knowledge_gaps = LearningPathAdapter._identify_knowledge_gaps(
            knowledge_map,
            current_level
        )
        
        # Create personalized path
        learning_path = {
            'userId': user_id,
            'domain': primary_domain,
            'currentLevel': current_level,
            'targetLevel': LearningPathAdapter._determine_target_level(user_goals),
            'goals': user_goals or [],
            'phases': phases,
            'knowledgeMap': knowledge_map,
            'knowledgeGaps': knowledge_gaps,
            'milestones': LearningPathAdapter._create_milestones(primary_domain, current_level),
            'recommendations': LearningPathAdapter._generate_path_recommendations(
                analytics, primary_domain, current_level
            ),
            'estimatedDuration': LearningPathAdapter._estimate_duration(
                current_level,
                LearningPathAdapter._determine_target_level(user_goals),
                analytics
            ),
            'startDate': datetime.utcnow(),
            'targetCompletionDate': datetime.utcnow() + timedelta(days=180),  # 6 months default
            'status': 'active',
            'progress': 0,
            'lastUpdated': datetime.utcnow(),
            'createdAt': datetime.utcnow()
        }
        
        return learning_path
    
    @staticmethod
    def _create_learning_phases(domain: str, current_level: str,
                               analytics: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Create learning phases for the path"""
        
        phases = [
            {
                'id': 'phase_1',
                'name': 'Foundations',
                'level': 'Beginner',
                'duration': '2-4 weeks',
                'topics': LearningPathAdapter._get_foundation_topics(domain),
                'quizzes': 5,
                'projects': 1,
                'status': 'not_started' if current_level != 'Beginner' else 'in_progress',
                'progressPercentage': 0,
                'resources': LearningPathAdapter._get_phase_resources(domain, 'Beginner')
            },
            {
                'id': 'phase_2',
                'name': 'Core Concepts',
                'level': 'Intermediate',
                'duration': '4-8 weeks',
                'topics': LearningPathAdapter._get_intermediate_topics(domain),
                'quizzes': 8,
                'projects': 2,
                'status': 'not_started',
                'progressPercentage': 0,
                'resources': LearningPathAdapter._get_phase_resources(domain, 'Intermediate')
            },
            {
                'id': 'phase_3',
                'name': 'Advanced Topics',
                'level': 'Advanced',
                'duration': '8-12 weeks',
                'topics': LearningPathAdapter._get_advanced_topics(domain),
                'quizzes': 10,
                'projects': 3,
                'status': 'not_started',
                'progressPercentage': 0,
                'resources': LearningPathAdapter._get_phase_resources(domain, 'Advanced')
            },
            {
                'id': 'phase_4',
                'name': 'Specialization',
                'level': 'Expert',
                'duration': '12+ weeks',
                'topics': LearningPathAdapter._get_specialization_topics(domain),
                'quizzes': 0,
                'projects': 4,
                'status': 'not_started',
                'progressPercentage': 0,
                'resources': ['Real-world projects', 'Community contribution', 'Mentorship']
            }
        ]
        
        return phases
    
    @staticmethod
    def _create_knowledge_map(domain: str, current_level: str,
                             analytics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a knowledge map for tracking learning"""
        
        knowledge_areas = LearningPathAdapter._get_knowledge_areas(domain)
        
        knowledge_map = {}
        
        for area in knowledge_areas:
            # Check if concept already exists in analytics
            current_mastery = 0
            current_status = 'unknown'
            
            if analytics:
                concept_mastery = analytics.get('conceptMastery', {})
                if area in concept_mastery:
                    current_mastery = concept_mastery[area]
                    if current_mastery >= 80:
                        current_status = 'learned'
                    elif current_mastery >= 50:
                        current_status = 'partial'
            
            knowledge_map[area] = {
                'concept': area,
                'status': current_status,
                'masteryLevel': current_mastery,
                'recommendedOrder': LearningPathAdapter._get_concept_order(domain, area),
                'prerequisites': LearningPathAdapter._get_prerequisites(domain, area),
                'resources': [],
                'quizzes': 0,
                'difficulty': LearningPathAdapter._estimate_concept_difficulty(domain, area)
            }
        
        return knowledge_map
    
    @staticmethod
    def _identify_knowledge_gaps(knowledge_map: Dict[str, Any],
                                current_level: str) -> List[Dict[str, Any]]:
        """Identify knowledge gaps based on level"""
        
        gaps = []
        
        required_concepts = {
            'Beginner': ['basics', 'fundamentals', 'core'],
            'Intermediate': ['advanced', 'optimization', 'patterns'],
            'Advanced': ['specialization', 'edge_cases', 'research']
        }
        
        required = required_concepts.get(current_level, [])
        
        for concept, data in knowledge_map.items():
            # Check if concept is fundamental and not learned
            if data['status'] in ['unknown', 'partial'] and data['masteryLevel'] < 70:
                gaps.append({
                    'concept': concept,
                    'priority': 'high' if data['masteryLevel'] == 0 else 'medium',
                    'importance': 'critical' if concept in required else 'important',
                    'recommendedAction': f"Review {concept} to strengthen foundation",
                    'estimatedTime': '2-3 hours'
                })
        
        return sorted(gaps, key=lambda x: (x['priority'] == 'medium', -x['masteryLevel']))[:5]
    
    @staticmethod
    def _create_milestones(domain: str, current_level: str) -> List[Dict[str, Any]]:
        """Create learning milestones"""
        
        milestones = [
            {
                'id': 'milestone_1',
                'name': f'{domain} Fundamentals Mastered',
                'description': 'Complete all foundation-level quizzes with 80% accuracy',
                'criteria': ['5 beginner quizzes passed', '80%+ average score', 'Build 1 small project'],
                'estimatedDate': datetime.utcnow() + timedelta(weeks=4),
                'reward': '🏅 Foundation Badge'
            },
            {
                'id': 'milestone_2',
                'name': f'{domain} Intermediate Skills',
                'description': 'Master intermediate concepts and complete projects',
                'criteria': ['8 intermediate quizzes passed', '75%+ average score', 'Build 2 projects'],
                'estimatedDate': datetime.utcnow() + timedelta(weeks=12),
                'reward': '🌟 Intermediate Badge'
            },
            {
                'id': 'milestone_3',
                'name': f'{domain} Advanced Proficiency',
                'description': 'Demonstrate advanced skills in real-world scenarios',
                'criteria': ['10 advanced quizzes passed', '85%+ average score', 'Build portfolio project'],
                'estimatedDate': datetime.utcnow() + timedelta(weeks=24),
                'reward': '⭐ Advanced Badge'
            },
            {
                'id': 'milestone_4',
                'name': f'{domain} Expert Ready',
                'description': 'Job-ready level proficiency',
                'criteria': ['Mastered all topics', '90%+ average score', 'Showcase portfolio', 'Community contribution'],
                'estimatedDate': datetime.utcnow() + timedelta(weeks=36),
                'reward': '👑 Expert Badge'
            }
        ]
        
        return milestones
    
    @staticmethod
    def _generate_path_recommendations(analytics: Dict[str, Any],
                                      domain: str,
                                      current_level: str) -> List[str]:
        """Generate recommendations for the learning path"""
        
        recommendations = []
        
        if analytics:
            learning_velocity = analytics.get('learningVelocity', 0)
            if learning_velocity > 50:
                recommendations.append("Your learning velocity is excellent! Consider accelerating to advanced topics.")
            elif learning_velocity < -50:
                recommendations.append("Your recent performance has declined. Review fundamentals before proceeding.")
            
            total_minutes = analytics.get('totalLearningMinutes', 0)
            if total_minutes < 300:
                recommendations.append("Dedicate at least 1 hour per day to optimize your learning path.")
            elif total_minutes > 1000:
                recommendations.append("You're making excellent progress! Consider taking on larger projects.")
        
        recommendations.append(f"Focus on weak areas: Arrays, Algorithms, and Data Structures.")
        recommendations.append("Join study groups or communities to accelerate learning.")
        recommendations.append("Build a portfolio project to apply your knowledge.")
        
        return recommendations
    
    @staticmethod
    def _determine_target_level(goals: List[str] = None) -> str:
        """Determine target level based on goals"""
        
        if not goals:
            return 'Intermediate'
        
        goal_string = ' '.join(goals).lower()
        
        if any(keyword in goal_string for keyword in ['job', 'career', 'professional', 'hire']):
            return 'Advanced'
        elif any(keyword in goal_string for keyword in ['expert', 'master', 'specialist']):
            return 'Expert'
        else:
            return 'Intermediate'
    
    @staticmethod
    def _estimate_duration(current_level: str, target_level: str,
                          analytics: Dict[str, Any] = None) -> str:
        """Estimate time to reach target level"""
        
        level_progression = {
            ('Beginner', 'Intermediate'): '8-12 weeks',
            ('Beginner', 'Advanced'): '16-24 weeks',
            ('Beginner', 'Expert'): '6-12 months',
            ('Intermediate', 'Advanced'): '8-12 weeks',
            ('Intermediate', 'Expert'): '4-6 months',
            ('Advanced', 'Expert'): '2-4 months'
        }
        
        default = level_progression.get((current_level, target_level), '3-6 months')
        
        # Adjust based on learning velocity
        if analytics:
            velocity = analytics.get('learningVelocity', 0)
            if velocity > 50:
                # Faster learner, reduce estimate by 20%
                # This is simplified; real implementation would parse and adjust durations
                pass
            elif velocity < -50:
                # Slower learner, increase estimate by 20%
                pass
        
        return default
    
    # Helper methods for getting domain-specific content
    
    @staticmethod
    def _get_foundation_topics(domain: str) -> List[str]:
        """Get foundation topics for a domain"""
        
        topics_map = {
            'Coding': ['Variables and Data Types', 'Control Structures', 'Functions', 'Basic Algorithms'],
            'Web Development': ['HTML Basics', 'CSS Fundamentals', 'JavaScript Basics', 'DOM Manipulation'],
            'Data Science': ['Statistics Basics', 'Python Fundamentals', 'Data Analysis', 'Visualization'],
            'AI & Machine Learning': ['Linear Algebra', 'Statistics', 'Python', 'Numpy and Pandas'],
        }
        
        return topics_map.get(domain, ['Fundamentals', 'Core Concepts', 'Best Practices'])
    
    @staticmethod
    def _get_intermediate_topics(domain: str) -> List[str]:
        """Get intermediate topics"""
        
        topics_map = {
            'Coding': ['OOP', 'Data Structures', 'Design Patterns', 'Testing'],
            'Web Development': ['React/Vue', 'Backend Development', 'Databases', 'API Development'],
            'Data Science': ['Advanced Statistics', 'Machine Learning', 'Feature Engineering', 'Model Evaluation'],
            'AI & Machine Learning': ['Supervised Learning', 'Neural Networks', 'Deep Learning Basics', 'Model Training'],
        }
        
        return topics_map.get(domain, ['Advanced Topics', 'Optimization', 'Patterns'])
    
    @staticmethod
    def _get_advanced_topics(domain: str) -> List[str]:
        """Get advanced topics"""
        
        return [
            'System Design',
            'Performance Optimization',
            'Production Deployment',
            'Advanced Algorithms'
        ]
    
    @staticmethod
    def _get_specialization_topics(domain: str) -> List[str]:
        """Get specialization topics"""
        
        return [
            'Real-world Projects',
            'Open Source Contribution',
            'Technical Leadership',
            'Innovation and Research'
        ]
    
    @staticmethod
    def _get_knowledge_areas(domain: str) -> List[str]:
        """Get key knowledge areas for a domain"""
        
        areas_map = {
            'Coding': ['Variables', 'Data Structures', 'Algorithms', 'OOP', 'Design Patterns'],
            'Web Development': ['HTML', 'CSS', 'JavaScript', 'Frontend Frameworks', 'Backend', 'Databases'],
            'Data Science': ['Statistics', 'Python', 'Data Cleaning', 'Visualization', 'Machine Learning'],
            'AI & Machine Learning': ['Linear Algebra', 'Statistics', 'Python', 'Neural Networks', 'Deep Learning'],
        }
        
        return areas_map.get(domain, ['Fundamentals', 'Core Concepts', 'Advanced Concepts'])
    
    @staticmethod
    def _get_concept_order(domain: str, concept: str) -> int:
        """Get recommended order to learn a concept"""
        
        # Return order (1 = first, higher = later)
        foundation_concepts = ['Basics', 'Variables', 'Data Types', 'Functions']
        
        if any(fc in concept for fc in foundation_concepts):
            return 1
        else:
            return 2
    
    @staticmethod
    def _get_prerequisites(domain: str, concept: str) -> List[str]:
        """Get prerequisites for a concept"""
        
        prerequisites_map = {
            'OOP': ['Variables', 'Functions', 'Data Structures'],
            'Algorithms': ['Data Structures', 'Loops', 'Recursion'],
            'Databases': ['SQL Basics', 'Data Structures'],
            'React': ['JavaScript', 'HTML', 'CSS'],
        }
        
        return prerequisites_map.get(concept, [])
    
    @staticmethod
    def _estimate_concept_difficulty(domain: str, concept: str) -> str:
        """Estimate difficulty of a concept"""
        
        if any(word in concept for word in ['Basic', 'Introduction', 'Fundamentals']):
            return 'Easy'
        elif any(word in concept for word in ['Advanced', 'Optimization', 'Algorithm']):
            return 'Hard'
        else:
            return 'Medium'
    
    @staticmethod
    def _get_phase_resources(domain: str, level: str) -> List[str]:
        """Get resources for a learning phase"""
        
        return [
            f'{domain} {level} Course',
            'Interactive Tutorials',
            'Coding Challenges',
            'Documentation',
            'YouTube Videos',
            'Community Forums'
        ]
    
    @staticmethod
    def save_learning_path(learning_path: Dict[str, Any]) -> Dict[str, Any]:
        """Save learning path to database"""
        
        coll = LearningPathAdapter.get_collection()
        
        # Replace existing path if present
        result = coll.replace_one(
            {'userId': learning_path['userId'], 'domain': learning_path['domain']},
            learning_path,
            upsert=True
        )
        
        if result.upserted_id:
            learning_path['_id'] = result.upserted_id
        
        return learning_path
    
    @staticmethod
    def get_user_learning_path(user_id: str, domain: str) -> Optional[Dict[str, Any]]:
        """Get user's learning path for a domain"""
        
        coll = LearningPathAdapter.get_collection()
        return coll.find_one({
            'userId': user_id,
            'domain': domain,
            'status': 'active'
        })
    
    @staticmethod
    def update_path_progress(user_id: str, domain: str, 
                            phase_id: str, progress_percentage: float) -> bool:
        """Update progress in a learning path"""
        
        coll = LearningPathAdapter.get_collection()
        
        # Update phase progress
        result = coll.update_one(
            {
                'userId': user_id,
                'domain': domain,
                'phases.id': phase_id
            },
            {
                '$set': {
                    'phases.$.progressPercentage': min(100, progress_percentage),
                    'lastUpdated': datetime.utcnow()
                }
            }
        )
        
        # Recalculate overall progress
        if result.modified_count > 0:
            path = coll.find_one({'userId': user_id, 'domain': domain})
            if path:
                total_progress = sum(p.get('progressPercentage', 0) for p in path.get('phases', [])) / len(path.get('phases', [1]))
                coll.update_one(
                    {'userId': user_id, 'domain': domain},
                    {'$set': {'progress': round(total_progress, 2)}}
                )
        
        return result.modified_count > 0
