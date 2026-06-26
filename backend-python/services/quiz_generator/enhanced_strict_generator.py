"""
============================================
Enhanced Strict Quiz Generator
============================================

Wraps the strict generator with:
1. Smart caching system (avoids repeated API calls)
2. Fallback generator (if OpenAI fails)
3. Response time logging (performance monitoring)

This is what makes your FYP production-grade.
"""

import logging
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from .strict_quiz_generator import StrictQuizGenerator

logger = logging.getLogger(__name__)


class CachedStrictQuizGenerator:
    """
    Enhanced quiz generator with caching, fallback, and timing.
    
    Caching Strategy:
    - Cache key: hash(topic + difficulty + count + weak_areas)
    - TTL: 24 hours
    - Storage: In-memory (can be upgraded to Redis)
    
    Fallback Strategy:
    - If OpenAI fails: use BasicFallbackGenerator
    - Returns valid quizzes with rule compliance
    
    Performance Tracking:
    - Logs all response times
    - Tracks cache hit/miss rates
    - Monitors provider API errors
    """
    
    def __init__(self, enable_cache: bool = True, cache_ttl_hours: int = 24):
        """Initialize with caching enabled."""
        # StrictQuizGenerator may require OPENAI_API_KEY; initialize lazily
        try:
            self.strict_generator = StrictQuizGenerator()
        except Exception as e:
            logger.warning(f"StrictQuizGenerator init failed: {e} - AI provider unavailable, fallback only")
            self.strict_generator = None
        self.enable_cache = enable_cache
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache = {}  # Format: {key: (quiz_data, timestamp)}
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'fallback_uses': 0,
            'provider_errors': 0,
            'avg_response_time': 0,
            'response_times': []
        }
        logger.info("CachedStrictQuizGenerator initialized with caching enabled")
    
    def _generate_cache_key(self, topic: str, difficulty: str, count: int, 
                           weak_areas: Optional[List[str]]) -> str:
        """Generate cache key from parameters."""
        weak_areas_str = ','.join(sorted(weak_areas)) if weak_areas else ''
        key_data = f"{topic}|{difficulty}|{count}|{weak_areas_str}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_cached_quiz(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve quiz from cache if valid."""
        if not self.enable_cache or cache_key not in self.cache:
            return None
        
        quiz_data, timestamp = self.cache[cache_key]
        
        # Check if cache expired
        if datetime.now() - timestamp > self.cache_ttl:
            del self.cache[cache_key]
            logger.info(f"Cache expired for key {cache_key[:8]}...")
            return None
        
        self.stats['cache_hits'] += 1
        logger.info(f"Cache hit! Key: {cache_key[:8]}... (age: {(datetime.now() - timestamp).seconds}s)")
        return quiz_data
    
    def _cache_quiz(self, cache_key: str, quiz_data: Dict[str, Any]) -> None:
        """Store quiz in cache."""
        if not self.enable_cache:
            return
        
        self.cache[cache_key] = (quiz_data, datetime.now())
        logger.info(f"Cached quiz with key: {cache_key[:8]}...")
    
    def _generate_with_provider(self, topic: str, difficulty: str, count: int,
                             weak_areas: Optional[List[str]]) -> Tuple[Dict[str, Any], float]:
        """
        Generate quiz using provider API with timing.
        
        Returns: (quiz_data, response_time_seconds)
        """
        start_time = time.time()
        
        if not self.strict_generator:
            response_time = time.time() - start_time
            self.stats['provider_errors'] += 1
            raise RuntimeError("Provider client not initialized")

        try:
            logger.info(f"🔄 Calling provider API for: {topic} ({difficulty}, {count} Q's)")
            quiz_data = self.strict_generator.generate(
                topic=topic,
                difficulty=difficulty,
                question_count=count,
                weak_areas=weak_areas
            )
            response_time = time.time() - start_time
            logger.info(f"✅ Provider API success in {response_time:.2f}s")
            return quiz_data, response_time

        except Exception as e:
            response_time = time.time() - start_time
            self.stats['provider_errors'] += 1
            logger.error(f"❌ Provider API error after {response_time:.2f}s: {str(e)}")
            raise
    
    def _generate_fallback_quiz(self, topic: str, difficulty: str, count: int,
                               weak_areas: Optional[List[str]]) -> Tuple[Dict[str, Any], float]:
        """
        Generate basic quiz without AI (fallback).
        
        Returns: (quiz_data, response_time_seconds)
        """
        start_time = time.time()
        logger.info(f"🔄 Using fallback generator for: {topic} ({difficulty}, {count} Q's)")
        
        fallback_gen = BasicFallbackGenerator()
        quiz_data = fallback_gen.generate(topic, difficulty, count, weak_areas)
        response_time = time.time() - start_time
        
        self.stats['fallback_uses'] += 1
        logger.warning(f"⚠️  Fallback generator used (response: {response_time:.2f}s)")
        return quiz_data, response_time
    
    def generate(self, topic: str, difficulty: str, question_count: int,
                weak_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate quiz with caching, fallback, and timing.
        
        Workflow:
        1. Check cache (if enabled)
        2. Try provider API
        3. If provider fails, use fallback
        4. Log all metrics
        
        Args:
            topic: Quiz topic
            difficulty: "easier", "beginner", "intermediate", "advanced", "expert"
            question_count: Number of questions
            weak_areas: Optional areas to emphasize
        
        Returns:
            {"quiz": [...], "metadata": {...}}
        """
        self.stats['total_requests'] += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key(topic, difficulty, question_count, weak_areas)
        
        # Check cache first
        cached_quiz = self._get_cached_quiz(cache_key)
        if cached_quiz:
            return {
                "quiz": cached_quiz,
                "metadata": {
                    "source": "cache",
                    "cached_at": "yes"
                }
            }
        
        self.stats['cache_misses'] += 1
        
        # Try provider API
        try:
            quiz_data, provider_time = self._generate_with_provider(
                topic, difficulty, question_count, weak_areas
            )
            self._cache_quiz(cache_key, quiz_data)
            response_time = provider_time
            source = "openai"
            
        except Exception as e:
            logger.warning(f"Provider failed, using fallback: {str(e)}")
            # Use fallback
            quiz_data, fallback_time = self._generate_fallback_quiz(
                topic, difficulty, question_count, weak_areas
            )
            response_time = fallback_time
            source = "fallback"
        
        # Update stats
        self.stats['response_times'].append(response_time)
        if len(self.stats['response_times']) > 100:
            self.stats['response_times'].pop(0)
        self.stats['avg_response_time'] = sum(self.stats['response_times']) / len(self.stats['response_times'])
        
        logger.info(
            f"✅ Quiz generated | Source: {source} | Time: {response_time:.2f}s | "
            f"Avg: {self.stats['avg_response_time']:.2f}s | "
            f"Cache hit rate: {self.stats['cache_hits']}/{self.stats['total_requests']}"
        )
        
        return {
            "quiz": quiz_data,
            "metadata": {
                "source": source,
                "response_time_seconds": round(response_time, 2),
                "topic": topic,
                "difficulty": difficulty,
                "question_count": question_count,
                "weak_areas_targeted": len(weak_areas) if weak_areas else 0,
                "generated_at": datetime.now().isoformat(),
                "cache_stats": {
                    "total_hits": self.stats['cache_hits'],
                    "total_requests": self.stats['total_requests'],
                    "hit_rate": round(self.stats['cache_hits'] / max(1, self.stats['total_requests']), 2),
                    "avg_response_time": round(self.stats['avg_response_time'], 2)
                }
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_requests": self.stats['total_requests'],
            "cache_hits": self.stats['cache_hits'],
            "cache_misses": self.stats['cache_misses'],
            "cache_hit_rate": round(self.stats['cache_hits'] / max(1, self.stats['total_requests']), 3),
            "fallback_uses": self.stats['fallback_uses'],
            "provider_errors": self.stats['provider_errors'],
            "avg_response_time_seconds": round(self.stats['avg_response_time'], 2),
            "cached_quizzes": len(self.cache)
        }
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        logger.info("Cache cleared")


class BasicFallbackGenerator:
    """
    Fallback quiz generator when the provider is unavailable.
    
    Generates valid quizzes without AI using:
    - Pre-built question banks by topic
    - Difficulty level mapping
    - Rule compliance
    
    This ensures the system NEVER fails completely.
    """
    
    # Pre-built fallback questions by topic
    FALLBACK_QUESTIONS = {
        "python": [
            {
                "question": "What is the correct syntax for a for loop in Python?",
                "sub_topic": "Control Flow",
                "options": {
                    "A": "for i in range(10): print(i)",
                    "B": "for i = 0; i < 10; i++ do print(i)",
                    "C": "for i in 0 to 10: print(i)",
                    "D": "for i -> range(10): print(i)"
                },
                "correct_answer": "A",
                "difficulty": "beginner"
            },
            {
                "question": "What does list.append() do?",
                "sub_topic": "Data Structures",
                "options": {
                    "A": "Returns the first element",
                    "B": "Adds an element to the end of the list",
                    "C": "Removes the last element",
                    "D": "Sorts the list"
                },
                "correct_answer": "B",
                "difficulty": "beginner"
            },
            {
                "question": "What is a decorator in Python?",
                "sub_topic": "Functions",
                "options": {
                    "A": "A type of variable",
                    "B": "A function that modifies another function or class",
                    "C": "A loop construct",
                    "D": "A comment marker"
                },
                "correct_answer": "B",
                "difficulty": "advanced"
            }
        ],
        "javascript": [
            {
                "question": "Which keyword creates a constant variable in JavaScript?",
                "sub_topic": "Variables",
                "options": {
                    "A": "const",
                    "B": "static",
                    "C": "final",
                    "D": "immutable"
                },
                "correct_answer": "A",
                "difficulty": "beginner"
            },
            {
                "question": "What does Promise.all() do?",
                "sub_topic": "Async Programming",
                "options": {
                    "A": "Waits for all promises to resolve",
                    "B": "Executes promises sequentially",
                    "C": "Cancels all promises",
                    "D": "Returns the first promise"
                },
                "correct_answer": "A",
                "difficulty": "advanced"
            }
        ],
        "react": [
            {
                "question": "What Hook allows you to manage state in a functional component?",
                "sub_topic": "Hooks",
                "options": {
                    "A": "useClass",
                    "B": "useState",
                    "C": "useState",
                    "D": "useMemo"
                },
                "correct_answer": "B",
                "difficulty": "beginner"
            },
            {
                "question": "When does useEffect run by default?",
                "sub_topic": "Side Effects",
                "options": {
                    "A": "Only on mount",
                    "B": "After every render",
                    "C": "Only on unmount",
                    "D": "Never"
                },
                "correct_answer": "B",
                "difficulty": "intermediate"
            }
        ]
    }
    
    def generate(self, topic: str, difficulty: str, count: int,
                weak_areas: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate fallback quiz from question bank.
        
        Returns list of questions that follow all rules.
        """
        topic_lower = topic.lower()
        
        # Find matching questions
        questions = []
        for key, qs in self.FALLBACK_QUESTIONS.items():
            if key in topic_lower:
                questions.extend(qs)
        
        # If no matching questions, use generic bank
        if not questions:
            questions = [q for qs in self.FALLBACK_QUESTIONS.values() for q in qs]
        
        # Filter by difficulty if needed
        if difficulty:
            matching = [q for q in questions if q.get('difficulty') == difficulty]
            if matching:
                questions = matching
        
        # Return requested count (repeat if necessary)
        result = []
        for i in range(count):
            q = questions[i % len(questions)].copy()
            q['id'] = i + 1
            q['reasoning'] = f"This is a {difficulty or 'standard'} level question about {q.get('sub_topic', 'the topic')}."
            result.append(q)
        
        logger.info(f"Fallback: Generated {count} questions for {topic} ({difficulty})")
        return result


# Create a singleton instance for the app
_cached_generator = None

def get_cached_generator() -> CachedStrictQuizGenerator:
    """Get or create the singleton instance."""
    global _cached_generator
    if _cached_generator is None:
        _cached_generator = CachedStrictQuizGenerator(enable_cache=True)
    return _cached_generator
