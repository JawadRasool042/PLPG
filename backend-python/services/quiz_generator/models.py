"""
Data models for quiz generation.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Question:
    """Represents a single quiz question"""
    
    question_text: str
    options: Dict[str, str]  # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_answer: str  # "A", "B", "C", or "D"
    reasoning: str
    sub_topic: str
    difficulty: int  # 1-5
    targets_weak_area: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        """Create from dictionary"""
        return cls(
            question_text=data['question_text'],
            options=data['options'],
            correct_answer=data['correct_answer'],
            reasoning=data['reasoning'],
            sub_topic=data['sub_topic'],
            difficulty=data['difficulty'],
            targets_weak_area=data.get('targets_weak_area', False)
        )


@dataclass
class Quiz:
    """Represents a complete quiz"""
    
    quiz_id: str
    topic: str
    difficulty_level: int  # 1-5
    question_count: int
    weak_areas: List[str]
    questions: List[Question]
    generation_timestamp: datetime
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'quiz_id': self.quiz_id,
            'topic': self.topic,
            'difficulty_level': self.difficulty_level,
            'question_count': self.question_count,
            'weak_areas': self.weak_areas,
            'questions': [q.to_dict() for q in self.questions],
            'generation_timestamp': self.generation_timestamp,
            'user_id': self.user_id,
            'metadata': self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Quiz':
        """Create from dictionary"""
        questions = [
            Question.from_dict(q) for q in data.get('questions', [])
        ]
        return cls(
            quiz_id=data['quiz_id'],
            topic=data['topic'],
            difficulty_level=data['difficulty_level'],
            question_count=data['question_count'],
            weak_areas=data.get('weak_areas', []),
            questions=questions,
            generation_timestamp=data['generation_timestamp'],
            user_id=data.get('user_id'),
            metadata=data.get('metadata', {})
        )
