"""
Parameter validation for quiz generation.
"""

from typing import List, Optional
from .exceptions import ValidationError


def validate_parameters(
    topic: str,
    difficulty_level: int,
    question_count: int,
    weak_areas: Optional[List[str]] = None
) -> None:
    """
    Validate all input parameters for quiz generation.
    
    Args:
        topic: Main topic for quiz questions
        difficulty_level: 1-5 scale
        question_count: Number of questions to generate
        weak_areas: Optional list of concepts to emphasize
    
    Raises:
        ValidationError: If any parameter is invalid
    """
    
    # Validate topic
    if not isinstance(topic, str):
        raise ValidationError('topic', 'must be a string')
    
    if not topic or not topic.strip():
        raise ValidationError('topic', 'cannot be empty')
    
    if len(topic) > 200:
        raise ValidationError('topic', 'cannot exceed 200 characters')
    
    # Validate difficulty_level
    if not isinstance(difficulty_level, int):
        raise ValidationError('difficulty_level', 'must be an integer')
    
    if difficulty_level < 1 or difficulty_level > 5:
        raise ValidationError('difficulty_level', 'must be between 1 and 5 inclusive')
    
    # Validate question_count
    if not isinstance(question_count, int):
        raise ValidationError('question_count', 'must be an integer')
    
    if question_count <= 0:
        raise ValidationError('question_count', 'must be greater than 0')
    
    if question_count > 100:
        raise ValidationError('question_count', 'cannot exceed 100')
    
    # Validate weak_areas if provided
    if weak_areas is not None:
        if not isinstance(weak_areas, list):
            raise ValidationError('weak_areas', 'must be a list')
        
        for area in weak_areas:
            if not isinstance(area, str):
                raise ValidationError('weak_areas', 'all items must be strings')
            
            if not area or not area.strip():
                raise ValidationError('weak_areas', 'items cannot be empty')
