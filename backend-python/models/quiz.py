"""
============================================
Quiz Model - MongoDB
============================================

This model handles quiz-related database operations including
quiz generation, storage, and retrieval.
"""

import secrets
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

from database import get_collection


class Quiz:
    """Quiz model class with static methods for database operations"""
    
    collection_name = 'quizzes'
    templates_collection_name = 'quiz_templates'
    
    # Available interest categories
    INTERESTS = [
        'AI/ML',
        'Web Development',
        'Cybersecurity',
        'Data Science',
        'Cloud Computing',
        'Mobile Development',
        'DevOps',
        'Blockchain',
        'IoT',
        'Game Development'
    ]

    INTEREST_TOPIC_MAP = {
        'AI/ML': 'Artificial Intelligence and Machine Learning',
        'AI & Machine Learning': 'Artificial Intelligence and Machine Learning',
        'Coding': 'Programming Fundamentals',
        'Web Development': 'Web Development',
        'Cybersecurity': 'Cybersecurity',
        'Data Science': 'Data Science',
        'Cloud Computing': 'Cloud Computing',
        'Mobile Development': 'Mobile Development',
        'Game Development': 'Game Development',
        'Physical Games / Sports': 'Sports Science and Strategy',
        'DevOps': 'DevOps and CI/CD',
        'Blockchain': 'Blockchain Development',
        'IoT': 'Internet of Things'
    }
    
    # Skill levels
    LEVELS = ['Beginner', 'Intermediate', 'Advanced']
    
    @staticmethod
    def get_collection():
        """Get the quizzes collection"""
        return get_collection(Quiz.collection_name)
    
    @staticmethod
    def get_templates_collection():
        """Get the quiz templates collection"""
        return get_collection(Quiz.templates_collection_name)
    
    @staticmethod
    def validate_interest(interest: str) -> bool:
        """Validate if interest is supported"""
        return isinstance(interest, str) and interest.strip() != ''

    @staticmethod
    def map_interest_to_topic(interest: str) -> str:
        """Map interest label to a more descriptive LLM topic."""
        return Quiz.INTEREST_TOPIC_MAP.get(interest, interest)
    
    @staticmethod
    def validate_level(level: str) -> bool:
        """Validate if level is supported"""
        return level in Quiz.LEVELS
    
    @staticmethod
    def generate_quiz(interest: str, level: str = 'Beginner', num_questions: int = 10, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a new quiz using LLM-driven questions.
        
        Args:
            interest: The subject area
            level: Difficulty level
            num_questions: Number of questions (default: 10)
            user_id: Optional user ID for audit/logging
            
        Returns:
            Generated quiz document
        """
        if not Quiz.validate_interest(interest):
            raise ValueError("Interest is required")
        
        if not Quiz.validate_level(level):
            raise ValueError(f"Invalid level: {level}")

        from services.llm_question_service import generate_and_verify_questions

        topic = Quiz.map_interest_to_topic(interest)
        concept_tag = interest.lower().replace(' ', '_').replace('/', '_')

        questions, gen_count, ver_count = generate_and_verify_questions(
            topic=topic,
            level=level,
            concept_tag=concept_tag,
            count=num_questions,
            user_id=user_id
        )

        if len(questions) < num_questions:
            raise ValueError(f"Not enough AI questions generated for {interest} - {level}. Please try again.")

        # Format questions for quiz
        formatted_questions = []
        for q in questions[:num_questions]:
            options = q.get('options', [])
            correct_index = q.get('correct_index', 0)
            answer_map = ['A', 'B', 'C', 'D']
            answer = answer_map[correct_index] if isinstance(correct_index, int) and 0 <= correct_index < 4 else 'A'

            formatted_questions.append({
                'q': q.get('question'),
                'options': options,
                'answer': answer,
                'explanation': q.get('explanation'),
                'concept_tag': q.get('concept_tag'),
                'difficulty': q.get('difficulty')
            })
        
        # Create quiz document
        quiz_doc = {
            'interest': interest,
            'level': level,
            'questions': formatted_questions,
            'totalQuestions': num_questions,
            'createdAt': datetime.utcnow(),
            'source': 'llm'
        }
        
        # Save to database
        quizzes_coll = Quiz.get_collection()
        result = quizzes_coll.insert_one(quiz_doc)
        quiz_doc['_id'] = result.inserted_id
        
        return quiz_doc
    
    @staticmethod
    def find_by_id(quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a quiz by ID
        
        Args:
            quiz_id: Quiz ID
            
        Returns:
            Quiz document or None
        """
        try:
            coll = Quiz.get_collection()
            quiz = coll.find_one({'_id': ObjectId(quiz_id)})
            return quiz
        except Exception:
            return None
    
    @staticmethod
    def find_by_interest(interest: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find quizzes by interest
        
        Args:
            interest: Subject area
            limit: Maximum number of quizzes to return
            
        Returns:
            List of quiz documents
        """
        coll = Quiz.get_collection()
        quizzes = list(coll.find({'interest': interest})
                          .sort('createdAt', -1)
                          .limit(limit))
        return quizzes
    
    @staticmethod
    def get_available_interests() -> List[str]:
        """
        Get list of interests that have quiz templates
        
        Returns:
            List of available interests
        """
        templates_coll = Quiz.get_templates_collection()
        interests = templates_coll.distinct('interest')
        return sorted(interests)
    
    @staticmethod
    def get_template_count(interest: str, level: str) -> int:
        """
        Get count of available templates for interest and level
        
        Args:
            interest: Subject area
            level: Difficulty level
            
        Returns:
            Number of templates
        """
        templates_coll = Quiz.get_templates_collection()
        count = templates_coll.count_documents({
            'interest': interest,
            'level': level
        })
        return count
    
    @staticmethod
    def to_response(quiz: Dict[str, Any], include_answers: bool = False) -> Dict[str, Any]:
        """
        Convert quiz document to API response format
        
        Args:
            quiz: Quiz document
            include_answers: Whether to include correct answers
            
        Returns:
            Formatted response
        """
        if not quiz:
            return None
        
        response = {
            'id': str(quiz['_id']),
            'interest': quiz.get('interest'),
            'level': quiz.get('level'),
            'totalQuestions': quiz.get('totalQuestions', 10),
            'createdAt': quiz.get('createdAt').isoformat() if quiz.get('createdAt') else None
        }
        
        # Format questions
        questions = []
        for idx, q in enumerate(quiz.get('questions', [])):
            question_data = {
                'index': idx,
                'q': q.get('q'),
                'options': q.get('options')
            }
            
            # Only include answers if requested (for results/review)
            if include_answers:
                question_data['answer'] = q.get('answer')
                question_data['explanation'] = q.get('explanation')
            
            questions.append(question_data)
        
        response['questions'] = questions
        
        return response

    @staticmethod
    def get_templates(
        interest: Optional[str] = None,
        level: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if interest:
            query["interest"] = interest
        if level:
            query["level"] = level
        return list(
            Quiz.get_templates_collection()
            .find(query)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )

    @staticmethod
    def count_templates(
        interest: Optional[str] = None,
        level: Optional[str] = None,
    ) -> int:
        query: Dict[str, Any] = {}
        if interest:
            query["interest"] = interest
        if level:
            query["level"] = level
        return Quiz.get_templates_collection().count_documents(query)

    @staticmethod
    def create_template(data: Dict[str, Any]) -> Dict[str, Any]:
        doc = {
            "interest": data.get("interest"),
            "level": data.get("level") or "Beginner",
            "questions": data.get("questions") or [],
            "totalQuestions": len(data.get("questions") or []),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        result = Quiz.get_templates_collection().insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    @staticmethod
    def update_template(template_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            obj_id = ObjectId(template_id)
        except Exception:
            return None
        allowed = {"interest", "level", "questions"}
        update_doc = {k: v for k, v in data.items() if k in allowed}
        if "questions" in update_doc:
            update_doc["totalQuestions"] = len(update_doc["questions"])
        if not update_doc:
            return Quiz.get_templates_collection().find_one({"_id": obj_id})
        update_doc["updatedAt"] = datetime.utcnow()
        Quiz.get_templates_collection().update_one({"_id": obj_id}, {"$set": update_doc})
        return Quiz.get_templates_collection().find_one({"_id": obj_id})

    @staticmethod
    def delete_template(template_id: str) -> bool:
        try:
            obj_id = ObjectId(template_id)
        except Exception:
            return False
        result = Quiz.get_templates_collection().delete_one({"_id": obj_id})
        return result.deleted_count > 0

    @staticmethod
    def template_to_response(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "interest": doc.get("interest"),
            "level": doc.get("level"),
            "totalQuestions": doc.get("totalQuestions", 0),
            "questions": doc.get("questions", []),
            "createdAt": doc.get("createdAt").isoformat() if doc.get("createdAt") else None,
            "updatedAt": doc.get("updatedAt").isoformat() if doc.get("updatedAt") else None,
        }
