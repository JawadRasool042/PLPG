"""
============================================
Quiz Adaptor Service - Reinforcement Learning
============================================

This service implements reinforcement learning for adaptive quizzes.
It adjusts difficulty based on user performance and tracks learning progress.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from bson import ObjectId

from database import get_collection
from models.user_analytics import UserAnalytics

logger = logging.getLogger(__name__)


class QuizAdaptor:
    """Service for adaptive quiz generation using reinforcement learning"""
    
    # Performance thresholds for difficulty adjustment
    PERFORMANCE_THRESHOLDS = {
        'excellent': 90,  # >= 90% correct
        'good': 75,       # 75-89%
        'fair': 60,       # 60-74%
        'poor': 0         # < 60%
    }
    
    # Difficulty progression rules
    DIFFICULTY_PROGRESSION = {
        'Beginner': {
            'excellent': 'Beginner',      # Stay and test more
            'good': 'Intermediate',        # Progress
            'fair': 'Beginner',            # Reinforcement
            'poor': 'Beginner'             # Strong reinforcement
        },
        'Intermediate': {
            'excellent': 'Advanced',
            'good': 'Advanced',
            'fair': 'Intermediate',
            'poor': 'Beginner'
        },
        'Advanced': {
            'excellent': 'Advanced',
            'good': 'Advanced',
            'fair': 'Intermediate',
            'poor': 'Intermediate'
        }
    }
    
    @staticmethod
    def get_recommended_difficulty(user_id: str, interest: str, 
                                  last_performance: float = None) -> str:
        """
        Determine recommended difficulty for next quiz using RL
        
        Args:
            user_id: User ID
            interest: Domain/interest
            last_performance: Override with specific performance score (0-100)
            
        Returns:
            Recommended difficulty level
        """
        
        if last_performance is not None:
            # Use provided performance score
            performance_level = QuizAdaptor._classify_performance(last_performance)
        else:
            # Get last performance from analytics
            analytics = UserAnalytics.get_analytics(user_id)
            if not analytics:
                return 'Beginner'
            
            # Get recent performance for this interest
            quiz_perf = analytics.get('quizPerformance', {})
            domain_performances = quiz_perf.get(interest, [])
            
            if not domain_performances:
                return 'Beginner'
            
            # Analyze recent performances (last 3 quizzes)
            recent_scores = [p.get('accuracy', 0) for p in domain_performances[-3:]]
            avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 50
            
            performance_level = QuizAdaptor._classify_performance(avg_recent)
        
        # Get current level
        analytics = UserAnalytics.get_analytics(user_id)
        if analytics:
            quiz_perf = analytics.get('quizPerformance', {})
            domain_performances = quiz_perf.get(interest, [])
            if domain_performances:
                current_level = domain_performances[-1].get('difficulty', 'Beginner')
            else:
                current_level = 'Beginner'
        else:
            current_level = 'Beginner'
        
        # Apply progression rule
        progression_rules = QuizAdaptor.DIFFICULTY_PROGRESSION.get(current_level, {})
        recommended = progression_rules.get(performance_level, 'Beginner')
        
        return recommended
    
    @staticmethod
    def _classify_performance(accuracy: float) -> str:
        """Classify performance level"""
        if accuracy >= QuizAdaptor.PERFORMANCE_THRESHOLDS['excellent']:
            return 'excellent'
        elif accuracy >= QuizAdaptor.PERFORMANCE_THRESHOLDS['good']:
            return 'good'
        elif accuracy >= QuizAdaptor.PERFORMANCE_THRESHOLDS['fair']:
            return 'fair'
        else:
            return 'poor'
    
    @staticmethod
    def analyze_quiz_attempt(user_id: str, quiz_attempt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze quiz attempt and extract learning insights
        
        Args:
            user_id: User ID
            quiz_attempt: Quiz attempt data
            
        Returns:
            Analysis with learning insights and recommendations
        """
        
        domain = quiz_attempt.get('interest', 'Unknown')
        correct_count = quiz_attempt.get('correctCount', 0)
        total_questions = quiz_attempt.get('totalQuestions', 10)
        accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
        time_spent = quiz_attempt.get('timeSpent', 0)  # in seconds
        difficulty = quiz_attempt.get('difficulty', 'Beginner')
        
        analysis = {
            'accuracy': round(accuracy, 2),
            'performance_level': QuizAdaptor._classify_performance(accuracy),
            'correctCount': correct_count,
            'totalQuestions': total_questions,
            'timePerQuestion': round(time_spent / total_questions, 1) if total_questions > 0 else 0,
            'recommendations': QuizAdaptor._generate_learning_recommendations(
                accuracy, domain, difficulty
            ),
            'nextSteps': QuizAdaptor._generate_next_steps(
                user_id, accuracy, domain, difficulty
            ),
            'conceptsToFocus': QuizAdaptor._identify_weak_concepts(
                quiz_attempt
            ),
            'strongConcepts': QuizAdaptor._identify_strong_concepts(
                quiz_attempt
            )
        }
        
        return analysis
    
    @staticmethod
    def _generate_learning_recommendations(accuracy: float, domain: str, 
                                          difficulty: str) -> List[str]:
        """Generate specific learning recommendations"""
        
        recommendations = []
        
        if accuracy >= 90:
            recommendations.append(f"Excellent work! You're mastering {domain}.")
            recommendations.append("Consider moving to a more challenging level.")
            recommendations.append("Try applying your knowledge in a real project.")
        
        elif accuracy >= 75:
            recommendations.append(f"Good progress in {domain}!")
            recommendations.append("Review challenging concepts to strengthen your foundation.")
            recommendations.append("Practice with more complex problems.")
        
        elif accuracy >= 60:
            recommendations.append(f"You're making progress in {domain}.")
            recommendations.append("Focus on the concepts you found difficult.")
            recommendations.append("Review fundamental concepts and try similar problems.")
        
        else:
            recommendations.append(f"Let's strengthen your {domain} foundation.")
            recommendations.append("Go back to beginner-level concepts.")
            recommendations.append("Take time to understand core principles before moving forward.")
        
        return recommendations
    
    @staticmethod
    def _generate_next_steps(user_id: str, accuracy: float, domain: str, 
                            difficulty: str) -> Dict[str, Any]:
        """Generate next learning steps"""
        
        next_difficulty = QuizAdaptor.get_recommended_difficulty(
            user_id, domain, accuracy
        )
        
        steps = {
            'recommendedDifficulty': next_difficulty,
            'suggestedAction': '',
            'timeToNextQuiz': '1 day',
            'focusAreas': [],
            'suggestedResources': []
        }
        
        if accuracy >= 85:
            steps['suggestedAction'] = f"Take a {next_difficulty} quiz to advance your skills"
            steps['timeToNextQuiz'] = '2-3 days'
        elif accuracy >= 60:
            steps['suggestedAction'] = f"Review weak areas, then try another {next_difficulty} quiz"
            steps['timeToNextQuiz'] = '1 day'
        else:
            steps['suggestedAction'] = f"Review {domain} fundamentals before trying another quiz"
            steps['timeToNextQuiz'] = '2-3 days'
        
        return steps
    
    @staticmethod
    def _identify_weak_concepts(quiz_attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify concepts where user struggled"""
        
        weak_concepts = []
        
        # Extract wrong answers
        wrong_answers = quiz_attempt.get('wrongAnswers', [])
        for idx, answer in enumerate(wrong_answers):
            concept = answer.get('concept')
            question = answer.get('question')
            
            if concept:
                weak_concepts.append({
                    'concept': concept,
                    'question': question,
                    'importance': 'high' if idx < 3 else 'medium',
                    'actionItem': f"Review {concept} in detail"
                })
        
        return weak_concepts[:5]  # Top 5 weak concepts
    
    @staticmethod
    def _identify_strong_concepts(quiz_attempt: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify concepts where user performed well"""
        
        strong_concepts = []
        
        # Extract correct answers if provided
        correct_answers = quiz_attempt.get('correctAnswers', [])
        for idx, answer in enumerate(correct_answers):
            concept = answer.get('concept')
            
            if concept and idx < 5:  # Top 5 concepts
                strong_concepts.append({
                    'concept': concept,
                    'mastery': 'high' if idx < 2 else 'medium'
                })
        
        return strong_concepts
    
    @staticmethod
    def track_concept_mastery(user_id: str, concepts: List[Dict[str, Any]]) -> None:
        """
        Track mastery level for concepts
        
        Args:
            user_id: User ID
            concepts: [{ concept: string, correct: bool, difficulty: string }]
        """
        
        for concept_data in concepts:
            concept = concept_data.get('concept')
            correct = concept_data.get('correct', False)
            difficulty = concept_data.get('difficulty', 'Beginner')
            
            if not concept:
                continue
            
            # Calculate mastery score increment
            if correct:
                mastery_increment = 5 if difficulty == 'Beginner' else (10 if difficulty == 'Intermediate' else 15)
            else:
                mastery_increment = -10 if difficulty == 'Beginner' else (-5 if difficulty == 'Intermediate' else -3)
            
            # Get current mastery
            analytics = UserAnalytics.get_analytics(user_id)
            current_mastery = 0
            if analytics:
                current_mastery = analytics.get('conceptMastery', {}).get(concept, 0)
            
            # Update mastery (clamped 0-100)
            new_mastery = max(0, min(100, current_mastery + mastery_increment))
            
            # Update concept mastery
            UserAnalytics.update_concept_mastery(user_id, concept, new_mastery)
            
            # Update knowledge map
            if new_mastery >= 80:
                status = 'learned'
            elif new_mastery >= 50:
                status = 'partial'
            else:
                status = 'unknown'
            
            UserAnalytics.update_knowledge_map(user_id, concept, status, new_mastery)
    
    @staticmethod
    def get_performance_metrics(user_id: str, interest: str, 
                               time_window_days: int = 30) -> Dict[str, Any]:
        """
        Get performance metrics for reinforcement learning
        
        Args:
            user_id: User ID
            interest: Domain/interest
            time_window_days: Look back period
            
        Returns:
            Performance metrics
        """
        
        analytics = UserAnalytics.get_analytics(user_id)
        if not analytics:
            return QuizAdaptor._empty_metrics()
        
        quiz_perf = analytics.get('quizPerformance', {})
        domain_performances = quiz_perf.get(interest, [])
        
        if not domain_performances:
            return QuizAdaptor._empty_metrics()
        
        # Filter by time window
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        recent_perfs = [
            p for p in domain_performances 
            if p.get('date', datetime.utcnow()) > cutoff_date
        ]
        
        if not recent_perfs:
            return QuizAdaptor._empty_metrics()
        
        # Calculate metrics
        scores = [p.get('score', 0) for p in recent_perfs]
        accuracies = [p.get('accuracy', 0) for p in recent_perfs]
        
        metrics = {
            'totalAttempts': len(recent_perfs),
            'averageScore': round(sum(scores) / len(scores), 2) if scores else 0,
            'averageAccuracy': round(sum(accuracies) / len(accuracies), 2) if accuracies else 0,
            'bestScore': max(scores) if scores else 0,
            'worstScore': min(scores) if scores else 0,
            'trend': QuizAdaptor._calculate_trend(scores),
            'consistency': QuizAdaptor._calculate_consistency(scores),
            'byDifficulty': QuizAdaptor._breakdown_by_difficulty(recent_perfs),
            'improvementRate': QuizAdaptor._calculate_improvement_rate(scores)
        }
        
        return metrics
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            'totalAttempts': 0,
            'averageScore': 0,
            'averageAccuracy': 0,
            'bestScore': 0,
            'worstScore': 0,
            'trend': 'neutral',
            'consistency': 0,
            'byDifficulty': {},
            'improvementRate': 0
        }
    
    @staticmethod
    def _calculate_trend(scores: List[float]) -> str:
        """Calculate performance trend"""
        if len(scores) < 2:
            return 'neutral'
        
        recent_avg = sum(scores[-3:]) / len(scores[-3:])
        older_avg = sum(scores[:-3]) / (len(scores)-3) if len(scores) > 3 else scores[0]
        
        improvement = recent_avg - older_avg
        
        if improvement > 10:
            return 'improving'
        elif improvement < -10:
            return 'declining'
        else:
            return 'stable'
    
    @staticmethod
    def _calculate_consistency(scores: List[float]) -> float:
        """Calculate score consistency (inverse of variance)"""
        if len(scores) < 2:
            return 100.0
        
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Convert std dev to consistency (0-100, higher is more consistent)
        consistency = max(0, 100 - std_dev)
        
        return round(consistency, 2)
    
    @staticmethod
    def _breakdown_by_difficulty(performances: List[Dict]) -> Dict[str, Any]:
        """Break down performance by difficulty level"""
        
        breakdown = {
            'Beginner': {'attempts': 0, 'avgScore': 0},
            'Intermediate': {'attempts': 0, 'avgScore': 0},
            'Advanced': {'attempts': 0, 'avgScore': 0}
        }
        
        for diff in breakdown:
            perfs = [p for p in performances if p.get('difficulty') == diff]
            if perfs:
                breakdown[diff]['attempts'] = len(perfs)
                breakdown[diff]['avgScore'] = round(
                    sum(p.get('score', 0) for p in perfs) / len(perfs), 2
                )
        
        return breakdown
    
    @staticmethod
    def _calculate_improvement_rate(scores: List[float]) -> float:
        """Calculate improvement rate as percentage change"""
        if len(scores) < 2:
            return 0.0
        
        first_score = scores[0]
        last_score = scores[-1]
        
        if first_score == 0:
            return 0.0
        
        improvement_rate = ((last_score - first_score) / first_score) * 100
        
        return round(improvement_rate, 2)
