#!/usr/bin/env python
"""
LOCAL TEST SCRIPT - No API Key Required
Test the prompt implementation, JSON validation, and schema compliance
"""

import sys
import json
sys.path.insert(0, 'backend-python')

from services.llm_question_service import (
    validate_question_json,
    extract_json_from_response,
    SYSTEM_PROMPT_GENERATE,
    SYSTEM_PROMPT_VERIFY,
    QUESTION_SCHEMA,
    VERIFICATION_SCHEMA
)

print("=" * 70)
print("LLM PROMPTS IMPLEMENTATION TEST")
print("=" * 70)
print()

# ============================================================================
# TEST 1: Verify Prompts Are Loaded
# ============================================================================
print("TEST 1: Prompt Loading")
print("-" * 70)

try:
    assert SYSTEM_PROMPT_GENERATE is not None, "Generation prompt is None"
    assert SYSTEM_PROMPT_VERIFY is not None, "Verification prompt is None"
    
    print(f"✓ Generation prompt loaded ({len(SYSTEM_PROMPT_GENERATE)} chars)")
    print(f"✓ Verification prompt loaded ({len(SYSTEM_PROMPT_VERIFY)} chars)")
    print()
    
except AssertionError as e:
    print(f"✗ FAILED: {e}")
    sys.exit(1)

# ============================================================================
# TEST 2: Validate Question Schema
# ============================================================================
print("TEST 2: Question Schema Validation")
print("-" * 70)

# Valid question
valid_question = {
    "question": "What is the capital of France?",
    "options": ["Paris", "London", "Berlin", "Madrid"],
    "correct_index": 0,
    "explanation": "Paris is the capital of France and the most populous city in the country. It serves as the political, cultural, and economic center. London is UK capital, Berlin is Germany capital, and Madrid is Spain capital.",
    "concept_tag": "geography_capitals",
    "difficulty": 0,
    "estimated_time": 30,
    "source": "llm",
    "prompt_version": "questions_v2",
    "confidence": 0.95
}

is_valid, error = validate_question_json(valid_question)
if is_valid:
    print("✓ Valid question passed schema validation")
else:
    print(f"✗ Valid question failed: {error}")
    sys.exit(1)

# Invalid question (missing required field)
invalid_question = {
    "question": "What is the capital of France?",
    "options": ["Paris", "London", "Berlin"],  # Only 3 options, need 4
    "correct_index": 0,
    "explanation": "Paris is the capital of France.",
}

is_valid, error = validate_question_json(invalid_question)
if not is_valid:
    print("✓ Invalid question correctly rejected")
else:
    print("✗ Invalid question was accepted (should have been rejected)")
    sys.exit(1)

print()

# ============================================================================
# TEST 3: JSON Extraction from LLM Response
# ============================================================================
print("TEST 3: JSON Extraction (Handles Markdown)")
print("-" * 70)

# Simulate LLM response with markdown code fence
llm_response_with_fence = """```json
[
  {
    "question": "What is 2+2?",
    "options": ["3", "4", "5", "6"],
    "correct_index": 1,
    "explanation": "When you add two and two together, the result is four. This is a fundamental arithmetic operation taught in elementary mathematics. Three, five, and six are incorrect results of different mathematical operations.",
    "concept_tag": "math_addition",
    "difficulty": 0,
    "estimated_time": 15,
    "source": "llm",
    "prompt_version": "questions_v2",
    "confidence": 0.99
  }
]
```"""

parsed = extract_json_from_response(llm_response_with_fence)
if parsed and len(parsed) == 1:
    print("✓ JSON extracted successfully from markdown fence")
    print(f"  Question: {parsed[0]['question']}")
else:
    print("✗ Failed to extract JSON")
    sys.exit(1)

# Direct JSON (no markdown)
direct_json = json.dumps([{
    "question": "What is the direct JSON test about?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "This is a test question to verify that direct JSON parsing works correctly without markdown code fences. It ensures the JSON extraction function handles both raw JSON and markdown-wrapped JSON properly.",
    "concept_tag": "test",
    "difficulty": 0,
    "estimated_time": 30,
    "source": "llm",
    "prompt_version": "questions_v2",
    "confidence": 0.9
}])

parsed = extract_json_from_response(direct_json)
if parsed and len(parsed) == 1:
    print("✓ Direct JSON parsed successfully")
else:
    print("✗ Failed to parse direct JSON")
    sys.exit(1)

print()

# ============================================================================
# TEST 4: Prompt Content Verification
# ============================================================================
print("TEST 4: Prompt Content Verification")
print("-" * 70)

# Check generation prompt contains key requirements
gen_checks = [
    ("Output ONLY valid JSON" in SYSTEM_PROMPT_GENERATE, "JSON-only requirement"),
    ("4 options" in SYSTEM_PROMPT_GENERATE, "Exactly 4 options requirement"),
    ("Difficulty is an integer 0-4" in SYSTEM_PROMPT_GENERATE, "Difficulty scale"),
]

gen_passed = 0
for check, desc in gen_checks:
    if check:
        print(f"  ✓ {desc}")
        gen_passed += 1
    else:
        print(f"  ✗ Missing: {desc}")

# Check verification prompt
ver_checks = [
    ("is_valid" in SYSTEM_PROMPT_VERIFY, "Validity check"),
    ("correctness" in SYSTEM_PROMPT_VERIFY.lower(), "Correctness check"),
    ("distractors" in SYSTEM_PROMPT_VERIFY.lower(), "Distractor quality check"),
]

ver_passed = 0
for check, desc in ver_checks:
    if check:
        print(f"  ✓ {desc}")
        ver_passed += 1
    else:
        print(f"  ✗ Missing: {desc}")

if gen_passed == len(gen_checks) and ver_passed == len(ver_checks):
    print()
    print("✓ All prompt content checks passed")
else:
    print()
    print("✗ Some prompt checks failed")
    sys.exit(1)

print()

# ============================================================================
# TEST 5: Schema Compliance
# ============================================================================
print("TEST 5: Schema JSON Structure")
print("-" * 70)

try:
    # Verify question schema has expected structure
    assert "properties" in QUESTION_SCHEMA, "Question schema missing properties"
    assert "question" in QUESTION_SCHEMA["properties"], "Missing question field"
    assert "options" in QUESTION_SCHEMA["properties"], "Missing options field"
    assert "correct_index" in QUESTION_SCHEMA["properties"], "Missing correct_index"
    
    print("✓ Question schema has all required fields")
    
    # Verify verification schema
    assert "properties" in VERIFICATION_SCHEMA, "Verification schema missing properties"
    assert "is_valid" in VERIFICATION_SCHEMA["properties"], "Missing is_valid field"
    assert "issues" in VERIFICATION_SCHEMA["properties"], "Missing issues field"
    
    print("✓ Verification schema has all required fields")
    
except AssertionError as e:
    print(f"✗ Schema check failed: {e}")
    sys.exit(1)

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 70)
print("✅ ALL TESTS PASSED")
print("=" * 70)
print()
print("Status:")
print("  ✓ Prompts loaded and ready")
print("  ✓ JSON schema validation working")
print("  ✓ Markdown parsing working")
print("  ✓ All prompt requirements present")
print("  ✓ Schema structure verified")
print()
print("Next steps:")
print("  1. Set GEMINI_API_KEY environment variable")
print("  2. Run: python backend-python/app.py")
print("  3. Test endpoint: POST http://localhost:5000/api/llm/questions/generate")
print()
print("Ready for production use! 🚀")
