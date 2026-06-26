"""
============================================
Quiz Attempt Model - MongoDB
============================================

This model handles quiz attempt operations including
submission, scoring, and retrieval.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from bson import ObjectId

from database import get_collection


class QuizAttempt:
    """Quiz attempt model class"""
    
    collection_name = 'quiz_attempts'

    @staticmethod
    def completion_timestamp_iso(attempt: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Single value for API `completedAt`: real finish time when present, else last DB touch,
        else quiz start, else Mongo ObjectId creation time. Avoids null → client epoch (1969) bugs.
        """
        if not attempt:
            return None

        def _coerce_iso(val: Any) -> Optional[str]:
            if val is None:
                return None
            if isinstance(val, datetime):
                if val.tzinfo is None:
                    return val.isoformat() + 'Z'
                return val.isoformat()
            if isinstance(val, str) and val.strip():
                return val.strip()
            if isinstance(val, (int, float)):
                if val == 0:
                    return None
                ts = float(val)
                if ts > 1e12:
                    ts /= 1000.0
                try:
                    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                except (OSError, ValueError, OverflowError):
                    return None
            return None

        for key in ('completedAt', 'updatedAt', 'startedAt', 'createdAt'):
            iso = _coerce_iso(attempt.get(key))
            if iso:
                return iso

        try:
            oid = attempt.get('_id')
            if oid is None:
                return None
            if isinstance(oid, ObjectId):
                gt = oid.generation_time
                return (gt.isoformat() + 'Z') if gt.tzinfo is None else gt.isoformat()
            if isinstance(oid, str) and oid:
                gt = ObjectId(oid).generation_time
                return (gt.isoformat() + 'Z') if gt.tzinfo is None else gt.isoformat()
        except Exception:
            pass
        return None

    @staticmethod
    def _normalize_choice(value: Any) -> str:
        """Normalize submitted answers like 'A)', 'A. text', or 'Option A' to 'A'."""
        raw = str(value or '').strip().upper()
        if not raw:
            return ''
        if raw.startswith('OPTION '):
            parts = raw.split()
            if len(parts) >= 2 and parts[1][:1] in {'A', 'B', 'C', 'D'}:
                return parts[1][:1]
        first = raw[:1]
        if first in {'A', 'B', 'C', 'D'}:
            return first
        return raw
    
    @staticmethod
    def get_collection():
        """Get the quiz attempts collection"""
        return get_collection(QuizAttempt.collection_name)
    
    @staticmethod
    def create(user_id: str, quiz_id: str, answers: Dict[str, str], 
               quiz_data: Dict[str, Any], time_spent: int = 0,
               estimated_difficulty: str = 'Beginner') -> Dict[str, Any]:
        """
        Create a new quiz attempt with scoring
        
        Args:
            user_id: User ID
            quiz_id: Quiz ID
            answers: User's answers {question_index: selected_answer}
            quiz_data: The quiz document with correct answers
            time_spent: Time spent on quiz in seconds
            estimated_difficulty: Estimated difficulty for adaptive learning
            
        Returns:
            Created attempt document with score
        """
        # Calculate score
        score_data = QuizAttempt.calculate_score(answers, quiz_data)
        
        # Create attempt document with enhanced fields
        attempt_doc = {
            'userId': user_id,
            'quizId': quiz_id,
            'interest': quiz_data.get('interest'),
            'level': quiz_data.get('level'),
            'answers': answers,
            'score': score_data['score'],
            'correctCount': score_data['correctCount'],
            'totalQuestions': score_data['totalQuestions'],
            'results': score_data['results'],
            
            # Enhanced fields for adaptive learning
            'estimatedDifficulty': estimated_difficulty,
            'actualDifficulty': quiz_data.get('level', 'Beginner'),
            'isAdaptiveDifficulty': True,
            'timeSpent': time_spent,  # in seconds
            'timePerQuestion': round(time_spent / score_data['totalQuestions'], 1) if score_data['totalQuestions'] > 0 else 0,
            
            # Explanation tracking
            'userExplanations': {},  # { question_index: explanation_text }
            'explanationProvided': False,
            
            # Confidence tracking
            'confidenceScores': {},  # { question_index: confidence_level (1-5) }
            
            # Concepts learning
            'concepts': [],  # [{ concept, correct, difficulty }]
            'wrongAnswersAnalyzed': False,
            
            # Timestamps
            'startedAt': datetime.utcnow(),
            'completedAt': datetime.utcnow(),
            'analyzedAt': None
        }
        
        # Save to database
        coll = QuizAttempt.get_collection()
        result = coll.insert_one(attempt_doc)
        attempt_doc['_id'] = result.inserted_id
        
        return attempt_doc
    
    @staticmethod
    def calculate_score(answers: Dict[str, str], quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate the score for a quiz attempt
        
        Args:
            answers: User's answers {question_index: selected_answer}
            quiz_data: Quiz document with correct answers
            
        Returns:
            Score data with results breakdown
        """
        questions = quiz_data.get('questions', [])
        total_questions = len(questions)
        correct_count = 0
        results = []
        
        for idx, question in enumerate(questions):
            user_answer_raw = answers.get(str(idx), '')
            correct_answer_raw = question.get('answer', '')
            user_answer = QuizAttempt._normalize_choice(user_answer_raw)
            correct_answer = QuizAttempt._normalize_choice(correct_answer_raw)
            is_correct = user_answer == correct_answer
            
            if is_correct:
                correct_count += 1
            
            results.append({
                'questionIndex': idx,
                'question': question.get('q'),
                'options': question.get('options'),
                'userAnswer': user_answer,
                'correctAnswer': correct_answer,
                'isCorrect': is_correct,
                'explanation': question.get('explanation')
            })
        
        score = round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
        
        return {
            'score': score,
            'correctCount': correct_count,
            'totalQuestions': total_questions,
            'results': results
        }
    
    @staticmethod
    def find_by_id(attempt_id: str) -> Optional[Dict[str, Any]]:
        """Find an attempt by ID"""
        try:
            coll = QuizAttempt.get_collection()
            attempt = coll.find_one({'_id': ObjectId(attempt_id)})
            return attempt
        except Exception:
            return None
    
    @staticmethod
    def find_by_user(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find quiz attempts by user
        
        Args:
            user_id: User ID
            limit: Maximum number of attempts to return
            
        Returns:
            List of attempt documents
        """
        coll = QuizAttempt.get_collection()
        attempts = list(coll.find({'userId': user_id})
                           .sort('completedAt', -1)
                           .limit(limit))
        return attempts
    
    @staticmethod
    def find_by_quiz(quiz_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find attempts for a specific quiz"""
        coll = QuizAttempt.get_collection()
        attempts = list(coll.find({'quizId': quiz_id})
                           .sort('completedAt', -1)
                           .limit(limit))
        return attempts
    
    @staticmethod
    def get_user_stats(user_id: str) -> Dict[str, Any]:
        """
        Get aggregate statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Statistics dictionary
        """
        coll = QuizAttempt.get_collection()
        
        # Get all attempts
        attempts = list(coll.find({'userId': user_id}))
        
        if not attempts:
            return {
                'totalAttempts': 0,
                'averageScore': 0,
                'bestScore': 0,
                'totalCorrect': 0,
                'totalQuestions': 0
            }
        
        total_score = sum(a.get('score', 0) for a in attempts)
        total_correct = sum(a.get('correctCount', 0) for a in attempts)
        total_questions = sum(a.get('totalQuestions', 0) for a in attempts)
        best_score = max(a.get('score', 0) for a in attempts)
        
        return {
            'totalAttempts': len(attempts),
            'averageScore': round(total_score / len(attempts), 2),
            'bestScore': best_score,
            'totalCorrect': total_correct,
            'totalQuestions': total_questions
        }
    
    @staticmethod
    def to_response(attempt: Dict[str, Any], include_results: bool = True) -> Dict[str, Any]:
        """
        Convert attempt document to API response
        
        Args:
            attempt: Attempt document
            include_results: Whether to include detailed results
            
        Returns:
            Formatted response
        """
        if not attempt:
            return None
        
        response = {
            'id': str(attempt['_id']),
            'quizId': attempt.get('quizId'),
            'interest': attempt.get('interest'),
            'level': attempt.get('level'),
            'score': attempt.get('score'),
            'correctCount': attempt.get('correctCount'),
            'totalQuestions': attempt.get('totalQuestions'),
            'completedAt': QuizAttempt.completion_timestamp_iso(attempt),
            'timeSpent': attempt.get('timeSpent', 0),
            'timePerQuestion': attempt.get('timePerQuestion', 0),
            'estimatedDifficulty': attempt.get('estimatedDifficulty', 'Beginner'),
            'explanationProvided': attempt.get('explanationProvided', False)
        }
        
        if include_results:
            response['results'] = attempt.get('results', [])
            response['userExplanations'] = attempt.get('userExplanations', {})
        
        return response
    
    @staticmethod
    def add_user_explanation(attempt_id: str, question_index: int, explanation: str) -> bool:
        """
        Add user's explanation for why they chose an answer
        
        Args:
            attempt_id: Attempt ID
            question_index: Index of the question
            explanation: User's explanation
            
        Returns:
            True if successful
        """
        coll = QuizAttempt.get_collection()
        
        result = coll.update_one(
            {'_id': ObjectId(attempt_id)},
            {
                '$set': {
                    f'userExplanations.{question_index}': explanation,
                    'explanationProvided': True
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def add_confidence_score(attempt_id: str, question_index: int, confidence: int) -> bool:
        """
        Record user's confidence for an answer (1-5 scale)
        
        Args:
            attempt_id: Attempt ID
            question_index: Index of the question
            confidence: Confidence level (1-5)
            
        Returns:
            True if successful
        """
        confidence = max(1, min(5, confidence))  # Clamp 1-5
        
        coll = QuizAttempt.get_collection()
        
        result = coll.update_one(
            {'_id': ObjectId(attempt_id)},
            {
                '$set': {
                    f'confidenceScores.{question_index}': confidence
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def analyze_wrong_answers(attempt_id: str, analysis_data: List[Dict[str, Any]]) -> bool:
        """
        Store analysis of wrong answers with LLM-generated explanations
        
        Args:
            attempt_id: Attempt ID
            analysis_data: [{ questionIndex, question, concept, userExplanation, 
                             correctAnswer, correctExplanation }]
            
        Returns:
            True if successful
        """
        coll = QuizAttempt.get_collection()
        
        wrong_answers = []
        concepts = []
        
        for analysis in analysis_data:
            wrong_answers.append({
                'questionIndex': analysis.get('questionIndex'),
                'question': analysis.get('question'),
                'concept': analysis.get('concept'),
                'userExplanation': analysis.get('userExplanation'),
                'correctAnswer': analysis.get('correctAnswer'),
                'correctExplanation': analysis.get('correctExplanation'),
                'analyzedAt': datetime.utcnow()
            })
            
            if analysis.get('concept'):
                concepts.append({
                    'concept': analysis.get('concept'),
                    'correct': False,
                    'difficulty': analysis.get('difficulty', 'Beginner')
                })
        
        result = coll.update_one(
            {'_id': ObjectId(attempt_id)},
            {
                '$set': {
                    'wrongAnswers': wrong_answers,
                    'concepts': concepts,
                    'wrongAnswersAnalyzed': True,
                    'analyzedAt': datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def update_concepts(attempt_id: str, concepts: List[Dict[str, Any]]) -> bool:
        """
        Update concept tracking for attempt
        
        Args:
            attempt_id: Attempt ID
            concepts: [{ concept, correct, difficulty }]
            
        Returns:
            True if successful
        """
        coll = QuizAttempt.get_collection()
        
        result = coll.update_one(
            {'_id': ObjectId(attempt_id)},
            {
                '$set': {
                    'concepts': concepts
                }
            }
        )
        
        return result.modified_count > 0
