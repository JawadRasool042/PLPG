"""
Custom exception classes for quiz generation service.
"""


class QuizGenerationError(Exception):
    """Base exception for quiz generation errors"""
    pass


class ValidationError(QuizGenerationError):
    """Raised when parameter validation fails"""
    
    def __init__(self, field: str, reason: str):
        self.field = field
        self.reason = reason
        super().__init__(f"Validation error in '{field}': {reason}")


class APIError(QuizGenerationError):
    """Raised when provider API call fails"""
    
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class ParseError(QuizGenerationError):
    """Raised when response parsing fails"""
    
    def __init__(self, message: str, raw_response: str = None):
        self.raw_response = raw_response
        super().__init__(message)


class QuestionValidationError(QuizGenerationError):
    """Raised when question validation fails"""
    
    def __init__(self, check_name: str, message: str):
        self.check_name = check_name
        super().__init__(f"Question validation failed ({check_name}): {message}")


class DatabaseError(QuizGenerationError):
    """Raised when database operation fails"""
    
    def __init__(self, operation: str, message: str):
        self.operation = operation
        super().__init__(f"Database error ({operation}): {message}")


class NotFoundError(QuizGenerationError):
    """Raised when quiz is not found in database"""
    
    def __init__(self, quiz_id: str):
        self.quiz_id = quiz_id
        super().__init__(f"Quiz not found: {quiz_id}")
