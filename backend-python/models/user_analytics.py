"""
============================================
User Analytics Model - MongoDB
============================================

This model tracks comprehensive user learning analytics including:
- Knowledge map (concepts learned/unknown)
- Strong and weak areas
- Concept mastery levels
- Interest trends over time
- Quiz performance metrics
- Learning velocity and streaks
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId

from database import get_collection


class UserAnalytics:
    """User analytics tracking model"""
    
    collection_name = 'user_analytics'
    
    @staticmethod
    def get_collection():
        """Get the user analytics collection"""
        return get_collection(UserAnalytics.collection_name)
    
    @staticmethod
    def initialize_analytics(user_id: str) -> Dict[str, Any]:
        """
        Initialize analytics for a new user
        
        Args:
            user_id: User ID
            
        Returns:
            Created analytics document
        """
        coll = UserAnalytics.get_collection()
        
        analytics_doc = {
            'userId': user_id,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
            
            # Knowledge tracking
            'knowledgeMap': {},  # { concept: { status, level, firstSeen, lastTested } }
            'conceptMastery': {},  # { concept: score }
            
            # Area tracking
            'strongAreas': [],
            'weakAreas': [],
            
            # Trend tracking
            'interestTrends': [],  # [{ date, primaryInterest, allInterests }]
            'quizPerformance': {},  # { domain: [{ date, score, difficulty, correct, total }] }
            
            # Metrics
            'totalQuizzesAttempted': 0,
            'totalCorrect': 0,
            'overallAccuracy': 0.0,
            'averageQuizScore': 0.0,
            'learningVelocity': 0.0,
            
            # Time tracking
            'totalLearningMinutes': 0,
            'lastActiveDate': datetime.utcnow(),
            'streakDays': 0,
            'longestStreak': 0,
            'streakStartDate': None,
            
            # Learning from mistakes
            'wrongAnswersAnalysis': [],  # [{ question, userExplanation, correctExplanation, domain, date, conceptsRelated }]
        }
        
        result = coll.insert_one(analytics_doc)
        analytics_doc['_id'] = result.inserted_id
        
        return analytics_doc
    
    @staticmethod
    def get_analytics(user_id: str) -> Optional[Dict[str, Any]]:
        """Get analytics for a user"""
        coll = UserAnalytics.get_collection()
        return coll.find_one({'userId': user_id})
    
    @staticmethod
    def update_knowledge_map(user_id: str, concept: str, status: str, 
                            level: int, metadata: Dict = None) -> bool:
        """
        Update knowledge map for a concept
        
        Args:
            user_id: User ID
            concept: Concept name
            status: 'learned', 'partial', or 'unknown'
            level: Mastery level (0-100)
            metadata: Additional metadata (domain, category, etc.)
            
        Returns:
            True if successful
        """
        coll = UserAnalytics.get_collection()
        
        knowledge_key = f'knowledgeMap.{concept}'
        
        update_doc = {
            f'{knowledge_key}.status': status,
            f'{knowledge_key}.level': max(0, min(100, level)),
            f'{knowledge_key}.lastTested': datetime.utcnow(),
        }
        
        if metadata:
            update_doc[f'{knowledge_key}.metadata'] = metadata
        
        # Set firstSeen if this is the first time
        analytics = coll.find_one({'userId': user_id})
        if not analytics or concept not in analytics.get('knowledgeMap', {}):
            update_doc[f'{knowledge_key}.firstSeen'] = datetime.utcnow()
        
        update_doc['updatedAt'] = datetime.utcnow()
        
        result = coll.update_one(
            {'userId': user_id},
            {'$set': update_doc},
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def update_concept_mastery(user_id: str, concept: str, score: float) -> bool:
        """
        Update concept mastery score
        
        Args:
            user_id: User ID
            concept: Concept name
            score: Mastery score (0-100)
            
        Returns:
            True if successful
        """
        coll = UserAnalytics.get_collection()
        
        score = max(0, min(100, score))  # Clamp between 0-100
        
        result = coll.update_one(
            {'userId': user_id},
            {
                '$set': {
                    f'conceptMastery.{concept}': score,
                    'updatedAt': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def add_quiz_performance(user_id: str, domain: str, score: float, 
                            difficulty: str, correct: int, total: int) -> bool:
        """
        Add a quiz performance record
        
        Args:
            user_id: User ID
            domain: Subject domain
            score: Quiz score (0-100)
            difficulty: 'Beginner', 'Intermediate', 'Advanced'
            correct: Number of correct answers
            total: Total questions
            
        Returns:
            True if successful
        """
        coll = UserAnalytics.get_collection()
        
        performance_record = {
            'date': datetime.utcnow(),
            'score': max(0, min(100, score)),
            'difficulty': difficulty,
            'correct': correct,
            'total': total,
            'accuracy': (correct / total * 100) if total > 0 else 0
        }
        
        # Push new performance record
        coll.update_one(
            {'userId': user_id},
            {
                '$push': {
                    f'quizPerformance.{domain}': performance_record
                },
                '$inc': {
                    'totalQuizzesAttempted': 1,
                    'totalCorrect': correct,
                    'totalLearningMinutes': 10  # Assume 10 min per quiz
                },
                '$set': {
                    'lastActiveDate': datetime.utcnow(),
                    'updatedAt': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        # Recalculate metrics
        UserAnalytics._recalculate_metrics(user_id)
        
        return True
    
    @staticmethod
    def add_wrong_answer_analysis(user_id: str, question: str, user_explanation: str,
                                 correct_explanation: str, domain: str, 
                                 concepts: List[str] = None) -> bool:
        """
        Track a wrong answer for learning purposes
        
        Args:
            user_id: User ID
            question: The question text
            user_explanation: Why user chose that answer
            correct_explanation: Correct explanation
            domain: Subject domain
            concepts: Related concepts
            
        Returns:
            True if successful
        """
        coll = UserAnalytics.get_collection()
        
        analysis_record = {
            'date': datetime.utcnow(),
            'question': question,
            'userExplanation': user_explanation,
            'correctExplanation': correct_explanation,
            'domain': domain,
            'conceptsRelated': concepts or [],
            'learningFeedback': None,  # Will be updated when we review this
        }
        
        result = coll.update_one(
            {'userId': user_id},
            {
                '$push': {
                    'wrongAnswersAnalysis': {
                        '$each': [analysis_record],
                        '$slice': -100  # Keep last 100 wrong answers
                    }
                },
                '$set': {
                    'updatedAt': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def add_interest_trend(user_id: str, primary_interest: str, 
                          all_interests: List[Dict[str, Any]]) -> bool:
        """
        Record an interest assessment
        
        Args:
            user_id: User ID
            primary_interest: Primary interest domain
            all_interests: List of all interests with scores
                          [{ domain: string, score: float, percentile: float }]
            
        Returns:
            True if successful
        """
        coll = UserAnalytics.get_collection()
        
        trend_record = {
            'date': datetime.utcnow(),
            'primaryInterest': primary_interest,
            'allInterests': all_interests
        }
        
        result = coll.update_one(
            {'userId': user_id},
            {
                '$push': {
                    'interestTrends': {
                        '$each': [trend_record],
                        '$slice': -52  # Keep one year of weekly data
                    }
                },
                '$set': {
                    'updatedAt': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def update_learning_streak(user_id: str) -> Tuple[int, int]:
        """
        Update learning streak based on activity
        
        Returns:
            Tuple of (currentStreak, longestStreak)
        """
        coll = UserAnalytics.get_collection()
        analytics = coll.find_one({'userId': user_id})
        
        if not analytics:
            return 0, 0
        
        last_active = analytics.get('lastActiveDate')
        if not last_active:
            last_active = datetime.utcnow()
        
        today = datetime.utcnow().date()
        last_active_date = last_active.date() if isinstance(last_active, datetime) else last_active
        
        current_streak = analytics.get('streakDays', 0)
        longest_streak = analytics.get('longestStreak', 0)
        
        # Check if activity is today
        if last_active_date == today:
            return current_streak, longest_streak
        
        # Check if activity is yesterday (continue streak)
        if last_active_date == (today - timedelta(days=1)):
            current_streak += 1
        else:
            # Streak broken
            current_streak = 1
        
        # Update longest streak
        longest_streak = max(longest_streak, current_streak)
        
        coll.update_one(
            {'userId': user_id},
            {
                '$set': {
                    'streakDays': current_streak,
                    'longestStreak': longest_streak,
                    'streakStartDate': datetime.utcnow(),
                    'lastActiveDate': datetime.utcnow(),
                    'updatedAt': datetime.utcnow()
                }
            }
        )
        
        return current_streak, longest_streak
    
    @staticmethod
    def _recalculate_metrics(user_id: str) -> None:
        """Recalculate derived metrics"""
        coll = UserAnalytics.get_collection()
        analytics = coll.find_one({'userId': user_id})
        
        if not analytics:
            return
        
        # Calculate overall accuracy
        total_quizzes = analytics.get('totalQuizzesAttempted', 0)
        total_correct = analytics.get('totalCorrect', 0)
        overall_accuracy = (total_correct / (total_quizzes * 10)) * 100 if total_quizzes > 0 else 0
        overall_accuracy = max(0, min(100, overall_accuracy))  # Clamp 0-100
        
        # Calculate average score from quizzes
        all_scores = []
        for domain, performances in analytics.get('quizPerformance', {}).items():
            if isinstance(performances, list):
                all_scores.extend([p.get('score', 0) for p in performances])
        
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Calculate learning velocity (change in score over recent quizzes)
        learning_velocity = UserAnalytics._calculate_learning_velocity(all_scores)
        
        # Update strong and weak areas
        strong_areas, weak_areas = UserAnalytics._categorize_areas(analytics)
        
        coll.update_one(
            {'userId': user_id},
            {
                '$set': {
                    'overallAccuracy': round(overall_accuracy, 2),
                    'averageQuizScore': round(average_score, 2),
                    'learningVelocity': round(learning_velocity, 2),
                    'strongAreas': strong_areas,
                    'weakAreas': weak_areas,
                    'updatedAt': datetime.utcnow()
                }
            }
        )
    
    @staticmethod
    def _calculate_learning_velocity(scores: List[float]) -> float:
        """
        Calculate learning velocity (improvement rate)
        Returns value between -100 and +100
        """
        if len(scores) < 2:
            return 0.0
        
        # Compare recent scores to older scores
        recent_scores = scores[-5:]  # Last 5 quizzes
        older_scores = scores[-10:-5] if len(scores) >= 10 else scores[:max(1, len(scores)-5)]
        
        avg_recent = sum(recent_scores) / len(recent_scores)
        avg_older = sum(older_scores) / len(older_scores) if older_scores else avg_recent
        
        # Velocity as percentage improvement
        velocity = ((avg_recent - avg_older) / 100) * 100 if avg_older > 0 else 0
        
        return max(-100, min(100, velocity))  # Clamp -100 to +100
    
    @staticmethod
    def _categorize_areas(analytics: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """
        Categorize strong and weak areas
        
        Returns:
            Tuple of (strongAreas, weakAreas)
        """
        domain_stats = {}
        
        for domain, performances in analytics.get('quizPerformance', {}).items():
            if isinstance(performances, list) and performances:
                scores = [p.get('score', 0) for p in performances]
                avg_score = sum(scores) / len(scores)
                domain_stats[domain] = {
                    'domain': domain,
                    'avgScore': round(avg_score, 2),
                    'topicCount': len(performances),
                    'recentScore': performances[-1].get('score', 0) if performances else 0
                }
        
        # Sort by average score
        sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1]['avgScore'], reverse=True)
        
        # Top 3 are strong areas, bottom 3 are weak areas
        strong_areas = [item[1] for item in sorted_domains[:3]]
        weak_areas = [item[1] for item in sorted_domains[-3:]]
        
        return strong_areas, weak_areas
    
    @staticmethod
    def get_learning_summary(user_id: str) -> Dict[str, Any]:
        """Get comprehensive learning summary for user"""
        coll = UserAnalytics.get_collection()
        analytics = coll.find_one({'userId': user_id})
        
        if not analytics:
            return None
        
        return {
            'overall': {
                'totalQuizzesAttempted': analytics.get('totalQuizzesAttempted', 0),
                'overallAccuracy': analytics.get('overallAccuracy', 0),
                'averageQuizScore': analytics.get('averageQuizScore', 0),
                'learningVelocity': analytics.get('learningVelocity', 0),
            },
            'time': {
                'totalLearningMinutes': analytics.get('totalLearningMinutes', 0),
                'lastActiveDate': analytics.get('lastActiveDate'),
                'streakDays': analytics.get('streakDays', 0),
                'longestStreak': analytics.get('longestStreak', 0),
            },
            'areas': {
                'strongAreas': analytics.get('strongAreas', []),
                'weakAreas': analytics.get('weakAreas', []),
            },
            'concepts': {
                'totalConceptsMastered': len([c for c in analytics.get('conceptMastery', {}).values() if c >= 80]),
                'topConcepts': sorted(
                    [(k, v) for k, v in analytics.get('conceptMastery', {}).items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            },
            'interests': {
                'primaryInterest': analytics.get('interestTrends', [{}])[-1].get('primaryInterest') if analytics.get('interestTrends') else None,
                'recentTrends': analytics.get('interestTrends', [])[-5:] if analytics.get('interestTrends') else []
            }
        }
