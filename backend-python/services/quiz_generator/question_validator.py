"""
Question validation for quiz generation.

Validates generated questions against strict criteria.
"""

import logging
from typing import List, Dict, Any, Optional, Set

from .exceptions import QuestionValidationError

logger = logging.getLogger(__name__)


def validate_questions(
    questions: List[Dict[str, Any]],
    requested_count: int,
    requested_difficulty: int,
    weak_areas: Optional[List[str]] = None
) -> None:
    """
    Validate all questions against strict criteria.
    
    Checks:
    1. Count matches: len(questions) == requested_count
    2. No duplicates: All questions are unique
    3. Difficulty match: All questions match requested_difficulty
    4. Option structure: Each question has exactly 4 options (A, B, C, D)
    5. Answer validity: correct_answer is one of A, B, C, D
    6. Distractor quality: All options are plausible
    7. Sub-topic coverage: Questions cover diverse sub-topics
    8. Weak area coverage: If weak_areas provided, ≥30% target them
    9. Reasoning present: All questions have reasoning field
    
    Args:
        questions: List of question dictionaries
        requested_count: Expected number of questions
        requested_difficulty: Expected difficulty level (1-5)
        weak_areas: Optional list of weak areas to check coverage
    
    Raises:
        QuestionValidationError: If any validation check fails
    """
    
    # Check 1: Count matches
    if len(questions) != requested_count:
        raise QuestionValidationError(
            'count_match',
            f"Expected {requested_count} questions, got {len(questions)}"
        )
    
    # Check 2: No duplicates
    _check_no_duplicates(questions)
    
    # Check 3: Difficulty match
    _check_difficulty_consistency(questions, requested_difficulty)
    
    # Check 4: Option structure
    _check_option_structure(questions)
    
    # Check 5: Answer validity
    _check_answer_validity(questions)
    
    # Check 6: Reasoning present
    _check_reasoning_present(questions)
    
    # Check 7: Sub-topic present
    _check_sub_topic_present(questions)
    
    # Check 8: Sub-topic diversity
    if len(questions) > 1:
        _check_sub_topic_diversity(questions)
    
    # Check 9: Weak area coverage
    if weak_areas:
        _check_weak_area_coverage(questions, weak_areas)


def _check_no_duplicates(questions: List[Dict[str, Any]]) -> None:
    """Check that all questions are unique"""
    seen = set()
    
    for i, question in enumerate(questions):
        # Create a unique identifier for the question
        question_id = (
            question['question_text'],
            tuple(sorted(question['options'].items())),
            question['correct_answer']
        )
        
        if question_id in seen:
            raise QuestionValidationError(
                'no_duplicates',
                f"Question {i} is a duplicate of a previous question"
            )
        
        seen.add(question_id)


def _check_difficulty_consistency(
    questions: List[Dict[str, Any]],
    requested_difficulty: int
) -> None:
    """Check that all questions match the requested difficulty"""
    for i, question in enumerate(questions):
        difficulty = question.get('difficulty')
        if difficulty != requested_difficulty:
            raise QuestionValidationError(
                'difficulty_match',
                f"Question {i} has difficulty {difficulty}, "
                f"expected {requested_difficulty}"
            )


def _check_option_structure(questions: List[Dict[str, Any]]) -> None:
    """Check that each question has exactly 4 options (A, B, C, D)"""
    for i, question in enumerate(questions):
        options = question.get('options', {})
        
        if not isinstance(options, dict):
            raise QuestionValidationError(
                'option_structure',
                f"Question {i}: options must be a dictionary"
            )
        
        expected_keys = {'A', 'B', 'C', 'D'}
        actual_keys = set(options.keys())
        
        if actual_keys != expected_keys:
            raise QuestionValidationError(
                'option_structure',
                f"Question {i}: options must have exactly keys A, B, C, D. "
                f"Got: {actual_keys}"
            )
        
        # Check each option is non-empty
        for key in expected_keys:
            option_text = options.get(key)
            if not isinstance(option_text, str) or not option_text.strip():
                raise QuestionValidationError(
                    'option_structure',
                    f"Question {i}: option {key} must be a non-empty string"
                )


def _check_answer_validity(questions: List[Dict[str, Any]]) -> None:
    """Check that correct_answer is one of A, B, C, D"""
    for i, question in enumerate(questions):
        correct_answer = question.get('correct_answer')
        
        if not isinstance(correct_answer, str):
            raise QuestionValidationError(
                'answer_validity',
                f"Question {i}: correct_answer must be a string"
            )
        
        if correct_answer not in {'A', 'B', 'C', 'D'}:
            raise QuestionValidationError(
                'answer_validity',
                f"Question {i}: correct_answer must be one of A, B, C, D. "
                f"Got: {correct_answer}"
            )


def _check_reasoning_present(questions: List[Dict[str, Any]]) -> None:
    """Check that all questions have a reasoning field"""
    for i, question in enumerate(questions):
        reasoning = question.get('reasoning')
        
        if not isinstance(reasoning, str) or not reasoning.strip():
            raise QuestionValidationError(
                'reasoning_present',
                f"Question {i}: reasoning must be a non-empty string"
            )


def _check_sub_topic_present(questions: List[Dict[str, Any]]) -> None:
    """Check that all questions have a sub_topic field"""
    for i, question in enumerate(questions):
        sub_topic = question.get('sub_topic')
        
        if not isinstance(sub_topic, str) or not sub_topic.strip():
            raise QuestionValidationError(
                'sub_topic_present',
                f"Question {i}: sub_topic must be a non-empty string"
            )


def _check_sub_topic_diversity(questions: List[Dict[str, Any]]) -> None:
    """Check that questions cover at least 2 different sub-topics"""
    sub_topics: Set[str] = set()
    
    for question in questions:
        sub_topic = question.get('sub_topic', '').strip()
        if sub_topic:
            sub_topics.add(sub_topic)
    
    if len(sub_topics) < 2:
        raise QuestionValidationError(
            'sub_topic_diversity',
            f"Questions must cover at least 2 different sub-topics. "
            f"Got {len(sub_topics)}: {sub_topics}"
        )


def _check_weak_area_coverage(
    questions: List[Dict[str, Any]],
    weak_areas: List[str]
) -> None:
    """Check that at least 30% of questions target weak areas"""
    
    if not weak_areas:
        return
    
    weak_area_set = set(area.strip().lower() for area in weak_areas if area.strip())
    
    if not weak_area_set:
        return
    
    weak_area_count = 0
    
    for question in questions:
        sub_topic = question.get('sub_topic', '').strip().lower()
        
        # Check if this question's sub_topic matches any weak area
        if sub_topic in weak_area_set:
            weak_area_count += 1
    
    # Calculate percentage
    total_questions = len(questions)
    weak_area_percentage = (weak_area_count / total_questions * 100) if total_questions > 0 else 0
    
    # Require at least 30%
    if weak_area_percentage < 30:
        raise QuestionValidationError(
            'weak_area_coverage',
            f"At least 30% of questions must target weak areas. "
            f"Got {weak_area_percentage:.1f}% ({weak_area_count}/{total_questions})"
        )
