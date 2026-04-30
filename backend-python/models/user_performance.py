"""
============================================
User Performance Model - MongoDB
============================================

This model tracks user performance analytics across quizzes
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

from database import get_collection


class UserPerformance:
    """User performance tracking model"""
    
    collection_name = 'user_performance'
    
    @staticmethod
    def get_collection():
        """Get the user performance collection"""
        return get_collection(UserPerformance.collection_name)
    
    @staticmethod
    def update_performance(user_id: str, attempt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user performance after a quiz attempt
        
        Args:
            user_id: User ID
            attempt_data: Quiz attempt data
            
        Returns:
            Updated performance document
        """
        coll = UserPerformance.get_collection()
        interest = attempt_data.get('interest')
        score = attempt_data.get('score', 0)
        correct_count = attempt_data.get('correctCount', 0)
        total_questions = attempt_data.get('totalQuestions', 0)
        
        # Find existing performance doc
        perf_doc = coll.find_one({'userId': user_id})
        
        if not perf_doc:
            # Create new performance document
            perf_doc = {
                'userId': user_id,
                'overallStats': {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0,
                    'totalCorrect': 0,
                    'totalQuestions': 0
                },
                'byInterest': {},
                'recentScores': [],
                'updatedAt': datetime.utcnow()
            }
        
        # Update overall stats
        overall = perf_doc['overallStats']
        total_quizzes = overall['totalQuizzes'] + 1
        total_score = (overall['averageScore'] * overall['totalQuizzes']) + score
        
        overall['totalQuizzes'] = total_quizzes
        overall['averageScore'] = round(total_score / total_quizzes, 2)
        overall['bestScore'] = max(overall['bestScore'], score)
        overall['totalCorrect'] = overall['totalCorrect'] + correct_count
        overall['totalQuestions'] = overall['totalQuestions'] + total_questions
        
        # Update interest-specific stats
        if interest not in perf_doc['byInterest']:
            perf_doc['byInterest'][interest] = {
                'totalQuizzes': 0,
                'averageScore': 0,
                'bestScore': 0,
                'lastAttempted': None
            }
        
        interest_stats = perf_doc['byInterest'][interest]
        interest_total_quizzes = interest_stats['totalQuizzes'] + 1
        interest_total_score = (interest_stats['averageScore'] * interest_stats['totalQuizzes']) + score
        
        interest_stats['totalQuizzes'] = interest_total_quizzes
        interest_stats['averageScore'] = round(interest_total_score / interest_total_quizzes, 2)
        interest_stats['bestScore'] = max(interest_stats['bestScore'], score)
        interest_stats['lastAttempted'] = datetime.utcnow()
        
        # Update recent scores (keep last 10)
        perf_doc['recentScores'].append({
            'interest': interest,
            'score': score,
            'date': datetime.utcnow()
        })
        perf_doc['recentScores'] = perf_doc['recentScores'][-10:]
        
        # Analyze strengths and weaknesses
        perf_doc['analysis'] = UserPerformance._analyze_performance(perf_doc)
        
        perf_doc['updatedAt'] = datetime.utcnow()
        
        # Save or update
        if '_id' in perf_doc:
            coll.update_one(
                {'_id': perf_doc['_id']},
                {'$set': perf_doc}
            )
        else:
            result = coll.insert_one(perf_doc)
            perf_doc['_id'] = result.inserted_id
        
        return perf_doc
    
    @staticmethod
    def _analyze_performance(perf_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze performance to identify strengths and weaknesses
        
        Args:
            perf_doc: Performance document
            
        Returns:
            Analysis with strengths and weaknesses
        """
        by_interest = perf_doc.get('byInterest', {})
        
        if not by_interest:
            return {
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
        
        # Sort interests by average score
        interests_sorted = sorted(
            by_interest.items(),
            key=lambda x: x[1]['averageScore'],
            reverse=True
        )
        
        # Top 3 are strengths, bottom 3 are weaknesses
        strengths = [
            {
                'interest': interest,
                'score': stats['averageScore'],
                'quizzes': stats['totalQuizzes']
            }
            for interest, stats in interests_sorted[:3]
            if stats['averageScore'] >= 70
        ]
        
        weaknesses = [
            {
                'interest': interest,
                'score': stats['averageScore'],
                'quizzes': stats['totalQuizzes']
            }
            for interest, stats in interests_sorted[-3:]
            if stats['averageScore'] < 70
        ]
        
        # Generate recommendations
        recommendations = []
        for weakness in weaknesses:
            recommendations.append(
                f"Practice more {weakness['interest']} quizzes to improve your score"
            )
        
        if perf_doc['overallStats']['averageScore'] >= 85:
            recommendations.append("Excellent performance! Consider trying Advanced level quizzes")
        elif perf_doc['overallStats']['averageScore'] < 60:
            recommendations.append("Focus on fundamental concepts and try Beginner level quizzes")
        
        return {
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations
        }
    
    @staticmethod
    def get_performance(user_id: str, interest: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user performance data
        
        Args:
            user_id: User ID
            interest: Optional interest filter
            
        Returns:
            Performance data
        """
        coll = UserPerformance.get_collection()
        perf_doc = coll.find_one({'userId': user_id})
        
        if not perf_doc:
            return {
                'overallStats': {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0
                },
                'byInterest': {},
                'analysis': {
                    'strengths': [],
                    'weaknesses': [],
                    'recommendations': []
                }
            }
        
        if interest:
            # Return interest-specific data
            interest_stats = perf_doc.get('byInterest', {}).get(interest, {
                'totalQuizzes': 0,
                'averageScore': 0,
                'bestScore': 0
            })
            return {
                'interest': interest,
                'stats': interest_stats
            }
        
        return perf_doc
    
    @staticmethod
    def to_response(perf_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert performance document to API response"""
        if not perf_doc:
            return {
                'overallStats': {
                    'totalQuizzes': 0,
                    'averageScore': 0,
                    'bestScore': 0,
                    'totalCorrect': 0,
                    'totalQuestions': 0
                },
                'byInterest': {},
                'recentScores': [],
                'analysis': {
                    'strengths': [],
                    'weaknesses': [],
                    'recommendations': []
                },
                'updatedAt': None
            }
        
        # Safely format recent scores
        recent_scores = []
        for score in perf_doc.get('recentScores', []):
            try:
                recent_scores.append({
                    'interest': score.get('interest'),
                    'score': score.get('score'),
                    'date': score.get('date').isoformat() if score.get('date') else None
                })
            except Exception:
                continue
        
        return {
            'overallStats': perf_doc.get('overallStats', {
                'totalQuizzes': 0,
                'averageScore': 0,
                'bestScore': 0,
                'totalCorrect': 0,
                'totalQuestions': 0
            }),
            'byInterest': perf_doc.get('byInterest', {}),
            'recentScores': recent_scores,
            'analysis': perf_doc.get('analysis', {
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }),
            'updatedAt': perf_doc.get('updatedAt').isoformat() if perf_doc.get('updatedAt') else None
        }
