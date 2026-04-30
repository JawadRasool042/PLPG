# services/llm_question_service.py
# Production-ready LLM question generation + verification + persistence
# Drop into backend-python/services/

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from jsonschema import validate, ValidationError
import google.generativeai as genai
import requests
import time

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION & SCHEMAS
# ============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE_URL = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek" if DEEPSEEK_API_KEY else "gemini")
PROMPT_VERSION = "questions_v2"
VERIFICATION_ENABLED = True
CACHE_DURATION_HOURS = 24
TEMPERATURE_GENERATION = 0.7
TEMPERATURE_VERIFY = 0.0

# JSON Schema for Question validation
QUESTION_SCHEMA = {
    "type": "object",
    "required": ["question", "options", "correct_index", "explanation", "concept_tag", "difficulty"],
    "properties": {
        "question": {"type": "string", "minLength": 20, "maxLength": 500},
        "options": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {"type": "string", "minLength": 3, "maxLength": 300}
        },
        "correct_index": {"type": "integer", "minimum": 0, "maximum": 3},
        "explanation": {"type": "string", "minLength": 50, "maxLength": 1000},
        "concept_tag": {"type": "string", "minLength": 2},
        "difficulty": {"type": "integer", "minimum": 0, "maximum": 4},
        "estimated_time": {"type": "integer", "minimum": 10, "maximum": 300},
        "source": {"type": "string", "enum": ["llm", "human"]},
        "prompt_version": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    }
}

# Verification Schema
VERIFICATION_SCHEMA = {
    "type": "object",
    "required": ["is_valid", "issues", "confidence"],
    "properties": {
        "is_valid": {"type": "boolean"},
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "severity": {"enum": ["critical", "high", "medium", "low"]},
                    "description": {"type": "string"}
                }
            }
        },
        "corrected_question": {"type": ["object", "null"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation": {"type": "string"}
    }
}

# ============================================================================
# GEMINI PROMPTS (Production-ready)
# ============================================================================

SYSTEM_PROMPT_GENERATE = """You are an expert assessment writer. Your job is to create high-quality multiple-choice questions.

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON. No markdown, no explanation, no preamble.
2. Each question must have exactly 4 options.
3. Distractors must be plausible but clearly distinct from the correct answer.
4. Never repeat the question text in options.
5. Difficulty is an integer 0-4: 0=Remember, 1=Understand, 2=Apply, 3=Analyze, 4=Evaluate
6. Estimated time should be realistic (e.g., 30-60 seconds typical).

JSON Structure (for each question):
{
  "question": "clear, unambiguous question",
  "options": ["option A", "option B", "option C", "option D"],
  "correct_index": 0,
  "explanation": "Why option A is correct and why B, C, D are common misconceptions",
  "concept_tag": "technical concept being tested",
  "difficulty": 1,
  "estimated_time": 45,
  "source": "llm",
  "prompt_version": "questions_v2",
  "confidence": 0.95
}

OUTPUT: Valid JSON array of questions only. Example:
[{"question":"...","options":[...],...},{"question":"...","options":[...],...}]"""

SYSTEM_PROMPT_VERIFY = """You are a question validator. Your job is to audit multiple-choice questions for correctness, clarity, and quality.

VALIDATION CHECKS:
1. Is the correct_index valid (0-3)?
2. Is the correct answer actually correct? Verify against standard references.
3. Are options clearly distinct (no ambiguity)?
4. Is the explanation accurate and helpful?
5. Are distractors plausible but wrong?
6. Is the difficulty rating appropriate?

Return ONLY valid JSON:
{
  "is_valid": true|false,
  "issues": [
    {
      "type": "factual|clarity|distractor|difficulty|ambiguity",
      "severity": "critical|high|medium|low",
      "description": "specific issue"
    }
  ],
  "corrected_question": {...or null if no fix needed...},
  "confidence": 0.0-1.0,
  "explanation": "brief summary"
}

If is_valid=true, issues should be empty. If is_valid=false, propose corrections if possible."""


# ============================================================================
# ADDITIONAL PROMPTS: EXPLANATIONS & MICRO-LESSONS
# ============================================================================

SYSTEM_PROMPT_EXPLAIN = """
You are an expert educator. Given a single multiple-choice question (JSON), produce a concise, clear answer explanation (1-3 sentences) and a per-option explanation explaining why each option is correct or incorrect.

REQUIREMENTS:
1. Output ONLY valid JSON (no markdown or prose outside JSON).
2. Respond with object:
{
    "answer_explanation": "...",
    "option_explanations": [ {"option_index": 0, "explanation": "..."}, ... ]
}
3. Keep answer_explanation short (<= 3 sentences). Option explanations should be 1-2 sentences each.
4. Use deterministic style (temperature 0.0 recommended by caller).
"""

SYSTEM_PROMPT_MICROLESSON = """
You are an expert instructor. Given a concept tag and a target mastery level (0-100), generate a compact micro-lesson containing:
1) lesson_text: a clear explanation (3-6 short paragraphs)
2) examples: 3 short illustrative examples
3) practice_questions: 2-4 short practice MCQs (JSON with question, options)

Output ONLY valid JSON:
{
    "lesson_text": "...",
    "examples": ["...", "..."],
    "practice_questions": [ {"question":"...","options":["...","...","...","..."],"correct_index":1}, ... ]
}
Keep outputs concise and pedagogically focused.
"""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_question_json(q: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate question JSON against schema.
    Returns (is_valid, error_message)
    """
    try:
        validate(instance=q, schema=QUESTION_SCHEMA)
        return True, None
    except ValidationError as e:
        return False, str(e)


def extract_json_from_response(text: str) -> Optional[List[Dict]]:
    """
    Extract JSON from LLM response.
    Handles markdown code fences and cleanup.
    """
    if not text:
        return None

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove markdown code fences
    text = text.replace("```json", "").replace("```", "")
    text = text.strip()

    # Try again
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from LLM: {e}")
        return None


def call_gemini_api(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> Optional[str]:
    """
    Call Gemini API safely with error handling.
    """
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not set")
            return None

        genai.configure(api_key=GEMINI_API_KEY)
        client = genai.GenerativeModel('gemini-2.0-flash')
        
        full_prompt = f"{system_prompt}\n\nUser request:\n{prompt}"
        
        response = client.generate_content(
            full_prompt,
            generation_config={
                'max_output_tokens': max_tokens,
                'temperature': temperature
            }
        )
        
        return response.text if response else None
        
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return None


def call_deepseek_api(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> Optional[str]:
    """
    Call DeepSeek API (OpenAI-compatible) with error handling.
    """
    try:
        if not DEEPSEEK_API_KEY:
            logger.error("DEEPSEEK_API_KEY not set")
            return None

        url = f"{DEEPSEEK_API_BASE_URL.rstrip('/')}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()

        return data.get("choices", [{}])[0].get("message", {}).get("content")

    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return None


def call_llm_api(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> Optional[str]:
    """
    Route LLM call to configured provider.
    """
    provider = (LLM_PROVIDER or "gemini").lower()

    if provider == "deepseek":
        return call_deepseek_api(prompt, system_prompt, max_tokens, temperature)

    return call_gemini_api(prompt, system_prompt, max_tokens, temperature)


def generate_explanation(question_doc: Dict, user_id: Optional[str] = None) -> Dict:
    """
    Generate answer explanation and per-option explanations for a question_doc.
    Returns a dict with keys: explanations (dict) or error/raw_response when parsing fails.
    """
    try:
        user_prompt = json.dumps(question_doc, ensure_ascii=False)
        raw = call_llm_api(user_prompt, system_prompt=SYSTEM_PROMPT_EXPLAIN, max_tokens=800, temperature=TEMPERATURE_VERIFY)

        if raw is None:
            return {'error': 'LLM_ERROR', 'message': 'No response from LLM'}

        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try cleaning fences
            cleaned = raw.replace('```json', '').replace('```', '').strip()
            try:
                parsed = json.loads(cleaned)
            except Exception:
                return {'error': 'INVALID_JSON', 'raw_response': raw}

        # Basic validation shape
        if not isinstance(parsed, dict) or 'answer_explanation' not in parsed:
            return {'error': 'INVALID_FORMAT', 'raw_response': raw}

        return {'explanations': parsed}

    except Exception as e:
        logger.exception(f"Error generating explanation: {e}")
        return {'error': 'INTERNAL_ERROR', 'message': str(e)}


def generate_micro_lesson(concept: str, mastery: int = 20, user_id: Optional[str] = None) -> Dict:
    """
    Generate a short micro-lesson for a concept.
    Returns: { lesson: {lesson_text, examples, practice_questions} } or error
    """
    try:
        prompt = f"Concept: {concept}\nTarget mastery: {mastery}\nProvide lesson_text, examples, practice_questions as JSON."
        raw = call_llm_api(prompt, system_prompt=SYSTEM_PROMPT_MICROLESSON, max_tokens=1200, temperature=TEMPERATURE_GENERATION)

        if raw is None:
            return {'error': 'LLM_ERROR', 'message': 'No response from LLM'}

        parsed = None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            cleaned = raw.replace('```json', '').replace('```', '').strip()
            try:
                parsed = json.loads(cleaned)
            except Exception:
                return {'error': 'INVALID_JSON', 'raw_response': raw}

        if not isinstance(parsed, dict) or 'lesson_text' not in parsed:
            return {'error': 'INVALID_FORMAT', 'raw_response': raw}

        return {'lesson': parsed}

    except Exception as e:
        logger.exception(f"Error generating micro-lesson: {e}")
        return {'error': 'INTERNAL_ERROR', 'message': str(e)}


def check_cache(topic: str, level: str, concept_tag: str) -> Optional[List[Dict]]:
    """
    Check if we have cached questions for this topic/level/concept.
    """
    try:
        # Import db from your models (adjust import path)
        from models import get_db
        db = get_db()
        
        cutoff = datetime.utcnow() - timedelta(hours=CACHE_DURATION_HOURS)
        
        cached = list(db['questions'].find({
            'topic': topic,
            'level': level,
            'concept_tag': concept_tag,
            'source': 'llm',
            'created_at': {'$gte': cutoff},
            'status': 'approved'
        }).limit(10))
        
        return cached if cached else None
        
    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
        return None


def persist_questions(questions: List[Dict], topic: str, level: str, user_id: Optional[str] = None):
    """
    Persist validated questions to MongoDB.
    """
    try:
        from models import get_db
        db = get_db()
        
        now = datetime.utcnow()
        
        for q in questions:
            doc = {
                **q,
                'topic': topic,
                'level': level,
                'source': 'llm',
                'prompt_version': PROMPT_VERSION,
                'created_at': now,
                'created_by': user_id,
                'status': 'approved',  # Starts approved; can be downgraded
                'quality_score': None,
                'attempt_count': 0,
                'correct_count': 0,
                'flagged': False,
                'reviewer_notes': None
            }
            
            result = db['questions'].insert_one(doc)
            logger.info(f"Persisted question {result.inserted_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error persisting questions: {e}")
        return False


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def generate_and_verify_questions(
    topic: str,
    level: str,
    concept_tag: str,
    count: int = 5,
    user_id: Optional[str] = None
) -> Tuple[List[Dict], int, int]:
    """
    Main workflow: Generate questions → Verify → Persist
    
    Returns: (questions_list, generated_count, verified_count)
    """
    
    logger.info(f"Generating {count} questions: topic={topic}, level={level}, concept={concept_tag}")
    
    # 1. Check cache first
    cached = check_cache(topic, level, concept_tag)
    if cached and len(cached) >= count:
        logger.info(f"Returning {len(cached)} cached questions")
        return cached[:count], 0, 0
    
    # 2. Generate questions via LLM
    user_prompt = (
        f"Generate {count} multiple-choice questions about '{topic}' "
        f"for level '{level}'. "
        f"Tag each with concept: '{concept_tag}'. "
        f"Ensure difficulty is 0-4 and estimated_time is realistic."
    )
    
    raw_response = call_llm_api(
        prompt=user_prompt,
        system_prompt=SYSTEM_PROMPT_GENERATE,
        max_tokens=3000,
        temperature=TEMPERATURE_GENERATION
    )
    
    if not raw_response:
        logger.error("LLM generation failed")
        return [], 0, 0
    
    # 3. Parse response
    generated_questions = extract_json_from_response(raw_response)
    if not generated_questions or not isinstance(generated_questions, list):
        logger.error(f"Invalid response format: {raw_response[:200]}")
        return [], 0, 0
    
    logger.info(f"Parsed {len(generated_questions)} questions from LLM")
    
    # 4. Validate structure
    valid_questions = []
    for q in generated_questions:
        is_valid, error = validate_question_json(q)
        if is_valid:
            valid_questions.append(q)
        else:
            logger.warning(f"Question failed schema validation: {error}")
    
    if not valid_questions:
        logger.error("No questions passed schema validation")
        return [], len(generated_questions), 0
    
    # 5. Verify each question (optional but recommended)
    verified_questions = []
    
    if VERIFICATION_ENABLED:
        for q in valid_questions:
            verified = verify_question_correctness(q)
            if verified:
                verified_questions.append(verified)
            else:
                logger.warning(f"Question failed verification: {q.get('question', '')[:50]}")
    else:
        verified_questions = valid_questions
    
    logger.info(f"Verified {len(verified_questions)} / {len(valid_questions)} questions")
    
    # 6. Persist to DB
    if verified_questions:
        persist_questions(verified_questions, topic, level, user_id)
    
    return verified_questions, len(generated_questions), len(verified_questions)


def verify_question_correctness(question: Dict) -> Optional[Dict]:
    """
    Run LLM verification on a single question.
    Returns corrected question if valid, None if invalid/unfixable.
    """
    
    verify_prompt = f"Validate this question:\n{json.dumps(question, indent=2)}"
    
    raw_response = call_llm_api(
        prompt=verify_prompt,
        system_prompt=SYSTEM_PROMPT_VERIFY,
        max_tokens=1000,
        temperature=TEMPERATURE_VERIFY
    )
    
    if not raw_response:
        logger.warning("Verification LLM call failed")
        return None
    
    # Parse verification response
    verify_result = extract_json_from_response(raw_response)
    if not verify_result:
        logger.warning("Invalid verification response")
        return None
    
    # Add verification metadata to question
    question['verification'] = verify_result
    question['verified_at'] = datetime.utcnow()
    question['confidence'] = verify_result.get('confidence', 0.5)
    
    # If valid, return question (potentially corrected)
    if verify_result.get('is_valid'):
        return question
    
    # If not valid but corrected_question provided, use that
    if verify_result.get('corrected_question'):
        corrected = verify_result['corrected_question']
        corrected['verification'] = verify_result
        return corrected
    
    # Otherwise, question is invalid and unfixable
    logger.warning(f"Question invalid and no correction: {verify_result.get('issues')}")
    return None


def generate_interest_weights(free_text: str) -> Optional[Dict]:
    """
    Extract and normalize interests from free-text user input.
    Returns dict like: { "AI_ML": 0.8, "Data_Science": 0.6, ... }
    """
    
    system_prompt = """You are an interest classifier. Output ONLY valid JSON.
Return:
{
  "interests": {"AI_ML": 0.8, "Data_Science": 0.6, ...},
  "top_topics": ["AI_ML", "Data_Science"],
  "confidence": 0.93,
  "explanation": "brief reason for classification"
}
Supported topics: AI_ML, Data_Science, Web_Dev, Cybersecurity, Mobile, Cloud, GameDev, Databases.
Each weight is 0..1. Set unused topics to 0 or omit them."""
    
    user_prompt = f'User interest: "{free_text}"\nClassify and weight interests.'
    
    raw_response = call_llm_api(
        prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=500,
        temperature=0.3
    )
    
    if not raw_response:
        return None
    
    result = extract_json_from_response(raw_response)
    return result


# ============================================================================
# QUALITY MONITORING
# ============================================================================

def compute_question_quality(question_id: str) -> Optional[float]:
    """
    After N quiz attempts on this question, compute quality score.
    Returns quality_score 0..1, or None if insufficient data.
    """
    try:
        from models import get_db
        db = get_db()
        
        # Require at least 10 attempts before scoring
        q = db['questions'].find_one({'_id': question_id})
        if not q:
            return None
        
        attempts = q.get('attempt_count', 0)
        if attempts < 10:
            return None
        
        correct_count = q.get('correct_count', 0)
        correct_rate = correct_count / attempts if attempts > 0 else 0
        
        # Quality: correct_rate should be 0.4-0.8 (too easy=1.0, too hard=0.0)
        # Ideal around 0.6 for discrimination
        if correct_rate < 0.3 or correct_rate > 0.9:
            quality_score = 0.4
        else:
            quality_score = 0.8 if 0.4 <= correct_rate <= 0.8 else 0.5
        
        # Update in DB
        db['questions'].update_one(
            {'_id': question_id},
            {'$set': {'quality_score': quality_score}}
        )
        
        # Flag if low quality
        if quality_score < 0.5:
            logger.warning(f"Question {question_id} flagged for review (quality={quality_score})")
            db['questions'].update_one(
                {'_id': question_id},
                {'$set': {'flagged': True, 'flag_reason': 'low_quality'}}
            )
        
        return quality_score
        
    except Exception as e:
        logger.error(f"Error computing quality: {e}")
        return None


def get_flagged_questions() -> List[Dict]:
    """
    Get all questions flagged for human review.
    """
    try:
        from models import get_db
        db = get_db()
        
        flagged = list(db['questions'].find(
            {'flagged': True, 'reviewer': None}
        ).sort('created_at', -1))
        
        return flagged
        
    except Exception as e:
        logger.error(f"Error fetching flagged questions: {e}")
        return []


# ============================================================================
# USAGE EXAMPLES (for testing)
# ============================================================================

if __name__ == "__main__":
    # Test 1: Generate questions
    print("Test 1: Generating questions...")
    questions, gen_count, ver_count = generate_and_verify_questions(
        topic="Python Async/Await",
        level="Intermediate",
        concept_tag="async_programming",
        count=3
    )
    print(f"Generated: {gen_count}, Verified: {ver_count}, Final: {len(questions)}")
    for q in questions:
        print(f"- {q.get('question', '')[:60]}...")
    
    # Test 2: Extract interests
    print("\nTest 2: Extracting interests...")
    interests = generate_interest_weights(
        "I love building web apps with React, bit interested in data science"
    )
    print(f"Interests: {interests}")
