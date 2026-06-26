"""
AI-Driven Quiz Generation Service

This module provides the core quiz generation functionality, integrating with
OpenAI API to create personalized, adaptive quizzes based on user interests
and performance.
"""

from .generator import generate_quiz, retrieve_quiz, generate_adaptive_quiz
from .exceptions import (
    ValidationError,
    APIError,
    ParseError,
    QuestionValidationError,
    DatabaseError,
    NotFoundError
)
from .models import Question, Quiz

__all__ = [
    'generate_quiz',
    'retrieve_quiz',
    'generate_adaptive_quiz',
    'ValidationError',
    'APIError',
    'ParseError',
    'QuestionValidationError',
    'DatabaseError',
    'NotFoundError',
    'Question',
    'Quiz'
]
