"""OpenAI-powered personalized roadmap, courses, and careers (no static catalogs)."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from utils.openai_request import chat_completions, DEFAULT_FALLBACK_MODELS

from utils.market_context import (
    align_careers_to_user_progress,
    get_career_progress_prompt_rules,
    get_course_recommendation_prompt_rules,
    get_job_recommendation_prompt_rules,
    get_market_prompt_rules,
    get_market_region,
    get_roadmap_prompt_rules,
    market_metadata,
    normalize_careers_for_market,
    normalize_courses_for_market,
    normalize_pakistani_jobs,
    normalize_roadmap_for_market,
)

logger = logging.getLogger(__name__)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_PATH_FALLBACK_MODELS = DEFAULT_FALLBACK_MODELS
OPENAI_TIMEOUT = float(os.getenv("OPENAI_PATH_TIMEOUT", "25"))
OPENAI_CONNECT_TIMEOUT = float(os.getenv("OPENAI_PATH_CONNECT_TIMEOUT", "15"))
OPENAI_RETRIES = max(0, int(os.getenv("OPENAI_PATH_RETRIES", "2")))


class OpenAIPathGeneratorError(Exception):
    pass


def _openai_timeout() -> Union[float, Tuple[float, float]]:
    return (OPENAI_CONNECT_TIMEOUT, OPENAI_TIMEOUT)


def _post_openai_chat(*, headers: Dict[str, str], json_body: Dict[str, Any]) -> requests.Response:
    """POST to OpenAI with connect/read timeouts and retries on transient failures."""
    last_err: Optional[Exception] = None
    attempts = OPENAI_RETRIES + 1
    for attempt in range(attempts):
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=json_body,
                timeout=_openai_timeout(),
            )
            response.raise_for_status()
            return response
        except (Timeout, RequestsConnectionError) as exc:
            last_err = exc
            logger.warning(
                "OpenAI learning-path request failed (attempt %s/%s): %s",
                attempt + 1,
                attempts,
                exc,
            )
            if attempt < attempts - 1:
                time.sleep(min(8, 2 ** attempt))
                continue
        except RequestException as exc:
            raise OpenAIPathGeneratorError(str(exc)) from exc
    raise OpenAIPathGeneratorError(str(last_err or "OpenAI request failed"))


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise OpenAIPathGeneratorError("Empty OpenAI response")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise OpenAIPathGeneratorError("Could not parse JSON from OpenAI response")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise OpenAIPathGeneratorError("Could not parse JSON from OpenAI response") from exc
    if not isinstance(parsed, dict):
        raise OpenAIPathGeneratorError("OpenAI response root must be an object")
    return parsed


def _normalize_stage(stage: Any, fallback_label: str) -> Dict[str, Any]:
    block = stage if isinstance(stage, dict) else {}
    topics = block.get("topics") or block.get("all_topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip() for t in topics if str(t).strip()]
    projects = block.get("stage_projects") or block.get("projects") or []
    if not isinstance(projects, list):
        projects = []
    projects = [str(p).strip() for p in projects if str(p).strip()]
    duration_label = str(block.get("duration_label") or block.get("duration") or "4-6 weeks").strip()
    milestones = block.get("local_milestones") or block.get("milestones") or []
    if not isinstance(milestones, list):
        milestones = []
    milestones = [str(m).strip() for m in milestones if str(m).strip()]
    market_skills = block.get("market_skills") or []
    if not isinstance(market_skills, list):
        market_skills = []
    market_skills = [str(s).strip() for s in market_skills if str(s).strip()]
    return {
        "topics": topics[:12],
        "all_topics": topics[:20],
        "duration_label": duration_label,
        "stage_projects": projects[:6],
        "pakistan_focus": str(block.get("pakistan_focus") or "").strip(),
        "local_milestones": milestones[:6],
        "market_skills": market_skills[:8],
    }


def generate_learning_path_via_openai(
    *,
    domain: str,
    user: Dict[str, Any],
    quiz_caliber: Dict[str, Any],
    interest_signals: Optional[Dict[str, Any]] = None,
    secondary_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate roadmap, courses, careers, and resume outline using OpenAI.
    Content is personalized from assessment + quiz performance (student caliber).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIPathGeneratorError("OPENAI_API_KEY is not configured")

    caliber = quiz_caliber or {}
    signals = interest_signals or {}
    secondary = secondary_domains or []
    market_region = get_market_region()

    prompt = {
        "task": "Generate a personalized learning path for a student.",
        "domain": domain,
        "market_region": market_region,
        "student_profile": {
            "known": user.get("known", ""),
            "want": user.get("want", ""),
            "goals": user.get("goals", user.get("learning_goals", "")),
            "learning_style": user.get("learning_style", user.get("learningStyle", "mixed")),
            "weekly_hours": user.get("weekly_availability_hours", 5),
            "assessment_tags": user.get("assessment_tags", user.get("assessmentTags", [])),
        },
        "quiz_caliber": {
            "attempt_count": caliber.get("attempt_count", 0),
            "average_score": caliber.get("average_score", 0),
            "best_score": caliber.get("best_score", 0),
            "recent_scores": caliber.get("recent_scores", []),
            "recommended_quiz_difficulty": caliber.get("recommended_quiz_difficulty", "beginner"),
            "mastery_level": caliber.get("mastery_level", 0),
        },
        "interest_signals": signals,
        "secondary_domains": secondary,
        "output_schema": {
            "recommended_quiz_difficulty": "beginner|intermediate|advanced",
            "caliber_summary": "string",
            "roadmap_summary_pakistan": "string — full path summary for Pakistan job market",
            "roadmap": {
                "basic": {
                    "topics": [],
                    "duration_label": "string",
                    "stage_projects": [],
                    "pakistan_focus": "string",
                    "local_milestones": ["string"],
                    "market_skills": ["string"],
                },
                "intermediate": {
                    "topics": [],
                    "duration_label": "string",
                    "stage_projects": [],
                    "pakistan_focus": "string",
                    "local_milestones": ["string"],
                    "market_skills": ["string"],
                },
                "advanced": {
                    "topics": [],
                    "duration_label": "string",
                    "stage_projects": [],
                    "pakistan_focus": "string",
                    "local_milestones": ["string"],
                    "market_skills": ["string"],
                },
                "expert": {
                    "topics": [],
                    "duration_label": "string",
                    "stage_projects": [],
                    "pakistan_focus": "string",
                    "local_milestones": ["string"],
                    "market_skills": ["string"],
                },
            },
            "resources": {
                "courses": [
                    {
                        "name": "string",
                        "platform": "string (e.g. DigiSkills.pk, Coursera, Udemy, YouTube)",
                        "url_hint": "string",
                        "free": True,
                        "difficulty": "beginner|intermediate|advanced",
                        "language": "English|Urdu|Both",
                        "price_pkr_hint": "Free or PKR amount (e.g. PKR 2,500)",
                        "pakistan_relevance": "string — why this course suits Pakistani learners",
                        "related_pakistani_jobs": [
                            {
                                "title": "string (Pakistan job title)",
                                "employer_type": "string (e.g. local IT firm, fintech startup, remote-for-foreign)",
                                "city": "Karachi|Lahore|Islamabad|Remote (Pakistan)",
                                "salary_pkr": "PKR X – Y per month",
                                "employment_type": "full-time|contract|remote|hybrid",
                                "skills_match": ["string"],
                                "why_recommended": "string linking this course to the job",
                            }
                        ],
                    }
                ]
            },
            "pakistani_jobs": [
                {
                    "title": "string",
                    "matched_course": "string (course name from resources.courses)",
                    "employer_type": "string",
                    "city": "string",
                    "salary_pkr": "PKR X – Y per month",
                    "employment_type": "full-time|contract|remote|hybrid",
                    "skills_match": ["string"],
                    "why_recommended": "string",
                }
            ],
            "careers_detailed": [
                {
                    "title": "string",
                    "level": "beginner|intermediate|advanced",
                    "industry": "string",
                    "salary_range": "string (PKR, Pakistan market)",
                    "growth_potential": "string",
                    "required_skills": ["string"],
                    "resume_angle": "string",
                    "progress_note": "string (optional — why this fits student quiz level)",
                }
            ],
            "resume_outline": {
                "headline": "string",
                "keywords": ["string"],
                "bullets": ["string"],
            },
            "secondary_insights": {
                "<secondary_domain>": {
                    "recommended_courses": ["string"],
                    "skill_focus": ["string"],
                }
            },
        },
        "rules": [
            "Do not use generic placeholder catalogs; tailor every item to this student.",
            "Match roadmap depth to quiz caliber (lower scores = more foundational topics).",
            "Courses must be real, searchable resources accessible from Pakistan (local platforms, free MOOCs, Urdu/English YouTube).",
            "Careers must align with domain + student goals.",
            "Only include secondary_insights for domains listed in secondary_domains — never add extra domains.",
            "Do not recommend generic intro courses (e.g. CS50, broad programming foundations) unless the student explicitly rated or tagged that domain.",
            "Every course must relate to the student's interest assessment: known skills, want-to-learn, goals, and assessment_tags.",
            "Return ONLY valid JSON matching output_schema.",
            "Keep the JSON compact: at most 6 courses, 1 related_pakistani_jobs entry per course, at most 6 pakistani_jobs total, 4 topics per roadmap stage.",
            *get_market_prompt_rules(market_region),
            *get_roadmap_prompt_rules(market_region),
            *get_course_recommendation_prompt_rules(market_region),
            *get_job_recommendation_prompt_rules(market_region),
            *get_career_progress_prompt_rules(),
        ],
    }

    system_content = (
        "You are an expert learning-path designer for students in Pakistan. Return ONLY valid JSON. "
        "Personalize roadmap, courses, careers, and job recommendations from student quiz performance. "
        f"All career salary_range and job salary_pkr values MUST reflect the {market_region} job market in PKR only. "
        "The roadmap must target Pakistan employability: local IT firms, freelancing, fintech/ecommerce, and remote roles. "
        "Each roadmap stage needs pakistan_focus, local_milestones, and market_skills for the Pakistan job market. "
        "Recommend courses from Pakistan-accessible platforms (DigiSkills, PITB, Coursera, Udemy, Urdu/English YouTube) with PKR pricing hints. "
        "Keep responses concise so generation finishes quickly."
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": json.dumps(prompt)},
    ]

    last_err: Optional[Exception] = None
    attempts = OPENAI_RETRIES + 1
    content = ""
    for attempt in range(attempts):
        try:
            _, content = chat_completions(
                messages=messages,
                api_key=api_key,
                model=OPENAI_MODEL,
                max_tokens=3200,
                temperature=0.55,
                response_format={"type": "json_object"},
                timeout=_openai_timeout(),
                fallback_models=OPENAI_PATH_FALLBACK_MODELS,
            )
            break
        except RuntimeError as exc:
            last_err = exc
            logger.warning(
                "OpenAI learning-path request failed (attempt %s/%s): %s",
                attempt + 1,
                attempts,
                exc,
            )
            if attempt < attempts - 1:
                time.sleep(min(8, 2 ** attempt))
                continue
            raise OpenAIPathGeneratorError(str(exc)) from exc
    else:
        raise OpenAIPathGeneratorError(str(last_err or "OpenAI request failed"))

    data = _extract_json(content)

    roadmap_raw = data.get("roadmap") if isinstance(data.get("roadmap"), dict) else {}
    basic = _normalize_stage(roadmap_raw.get("basic") or roadmap_raw.get("beginner"), "Basic")
    intermediate = _normalize_stage(roadmap_raw.get("intermediate"), "Intermediate")
    advanced = _normalize_stage(roadmap_raw.get("advanced"), "Advanced")
    expert = _normalize_stage(roadmap_raw.get("expert"), "Expert")
    if not expert.get("topics") and advanced.get("topics"):
        adv_all = list(advanced.get("all_topics") or advanced.get("topics") or [])
        if len(adv_all) > 4:
            split_at = max(2, len(adv_all) // 2)
            expert = _normalize_stage({"topics": adv_all[split_at:], "stage_projects": advanced.get("stage_projects", [])[1:]}, "Expert")
            advanced = _normalize_stage({**advanced, "topics": adv_all[:split_at]}, "Advanced")
    roadmap_summary_pakistan = str(data.get("roadmap_summary_pakistan") or "").strip()

    courses_raw = []
    resources = data.get("resources") if isinstance(data.get("resources"), dict) else {}
    if isinstance(resources.get("courses"), list):
        courses_raw = resources.get("courses")

    courses: List[str] = []
    course_cards: List[Dict[str, Any]] = []
    aggregated_jobs: List[Dict[str, Any]] = []

    def _parse_course_jobs(raw_jobs: Any, course_name: str) -> List[Dict[str, Any]]:
        if not isinstance(raw_jobs, list):
            return []
        parsed: List[Dict[str, Any]] = []
        for j in raw_jobs:
            if not isinstance(j, dict):
                continue
            title = str(j.get("title") or "").strip()
            if not title:
                continue
            skills = j.get("skills_match") or j.get("required_skills") or []
            if not isinstance(skills, list):
                skills = []
            salary = j.get("salary_pkr") or j.get("salary_range") or j.get("salary")
            parsed.append(
                {
                    "title": title,
                    "matched_course": course_name,
                    "employer_type": str(j.get("employer_type") or j.get("company_type") or "").strip(),
                    "city": str(j.get("city") or "Pakistan").strip(),
                    "salary_pkr": str(salary).strip() if salary else "",
                    "employment_type": str(j.get("employment_type") or "full-time").strip(),
                    "skills_match": [str(s) for s in skills[:6]],
                    "why_recommended": str(j.get("why_recommended") or j.get("why") or "").strip(),
                }
            )
        return parsed

    for item in courses_raw:
        if isinstance(item, str):
            name = item.strip()
            if name:
                courses.append(name)
                course_cards.append({
                    "name": name,
                    "platform": "Pakistan-accessible learning resource",
                    "free": True,
                    "related_pakistani_jobs": [],
                })
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            course_jobs = _parse_course_jobs(item.get("related_pakistani_jobs"), name)
            courses.append(name)
            course_cards.append(
                {
                    "name": name,
                    "platform": str(item.get("platform") or "OpenAI recommendation"),
                    "url_hint": str(item.get("url_hint") or ""),
                    "free": bool(item.get("free", True)),
                    "difficulty": str(item.get("difficulty") or ""),
                    "language": str(item.get("language") or "English"),
                    "price_pkr_hint": str(item.get("price_pkr_hint") or item.get("price") or ""),
                    "pakistan_relevance": str(item.get("pakistan_relevance") or ""),
                    "related_pakistani_jobs": course_jobs,
                }
            )
            aggregated_jobs.extend(course_jobs)

    course_cards = normalize_courses_for_market(course_cards, domain=domain)

    top_level_jobs = _parse_course_jobs(data.get("pakistani_jobs"), "")
    for job in top_level_jobs:
        if not job.get("matched_course"):
            job["matched_course"] = str(
                next((c["name"] for c in course_cards if c.get("name")), "")
            )
    aggregated_jobs.extend(top_level_jobs)
    pakistani_jobs = normalize_pakistani_jobs(aggregated_jobs, domain=domain)

    # Attach normalized jobs back to each course card
    jobs_by_course: Dict[str, List[Dict[str, Any]]] = {}
    for job in pakistani_jobs:
        key = str(job.get("matched_course") or "").strip().lower()
        if key:
            jobs_by_course.setdefault(key, []).append(job)
    for card in course_cards:
        key = str(card.get("name") or "").strip().lower()
        card["related_pakistani_jobs"] = jobs_by_course.get(key, card.get("related_pakistani_jobs") or [])

    careers_detailed: List[Dict[str, Any]] = []
    for c in data.get("careers_detailed") or []:
        if not isinstance(c, dict):
            continue
        title = str(c.get("title") or "").strip()
        if not title:
            continue
        skills = c.get("required_skills") or []
        if not isinstance(skills, list):
            skills = []
        careers_detailed.append(
            {
                "title": title,
                "level": str(c.get("level") or c.get("career_level") or "").strip().lower(),
                "industry": c.get("industry"),
                "salary_range": c.get("salary_range"),
                "growth_potential": c.get("growth_potential"),
                "required_skills": [str(s) for s in skills[:8]],
                "resume_angle": str(c.get("resume_angle") or ""),
                "progress_note": str(c.get("progress_note") or ""),
            }
        )

    careers_detailed = normalize_careers_for_market(careers_detailed, domain=domain)
    careers_detailed, user_career_level, careers_by_level = align_careers_to_user_progress(
        careers_detailed, caliber
    )

    resume = data.get("resume_outline") if isinstance(data.get("resume_outline"), dict) else {}
    secondary_insights_raw = data.get("secondary_insights") if isinstance(data.get("secondary_insights"), dict) else {}

    # Keep only secondary domains the student actually rated in the interest checker.
    allowed_secondary = {str(d).strip().lower() for d in (secondary or []) if str(d).strip()}
    secondary_insights: Dict[str, Any] = {}
    if allowed_secondary:
        for key, value in secondary_insights_raw.items():
            if str(key).strip().lower() not in allowed_secondary:
                continue
            if not isinstance(value, dict):
                continue
            courses_list = value.get("recommended_courses") or []
            if not isinstance(courses_list, list):
                courses_list = []
            cleaned_courses = [str(c).strip() for c in courses_list if str(c).strip()]
            if not cleaned_courses:
                continue
            secondary_insights[str(key).strip()] = {
                **value,
                "recommended_courses": cleaned_courses[:6],
            }

    return {
        "source": "openai",
        **market_metadata(market_region),
        "recommended_quiz_difficulty": str(
            data.get("recommended_quiz_difficulty")
            or caliber.get("recommended_quiz_difficulty")
            or "beginner"
        ),
        "caliber_summary": str(data.get("caliber_summary") or ""),
        "roadmap": normalize_roadmap_for_market(
            {
                "basic": basic,
                "intermediate": intermediate,
                "advanced": advanced,
                "expert": expert,
                "roadmap_summary_pakistan": roadmap_summary_pakistan,
                "resources": {"courses": courses, "course_cards": course_cards},
                "career_paths": [c.get("title") for c in careers_detailed],
                "suggested_projects": (
                    basic.get("stage_projects", [])
                    + intermediate.get("stage_projects", [])[:2]
                    + advanced.get("stage_projects", [])[:1]
                    + expert.get("stage_projects", [])[:1]
                )[:8],
            },
            domain=domain,
        ),
        "careers_detailed": careers_detailed,
        "careers_by_level": careers_by_level,
        "user_career_level": user_career_level,
        "pakistani_jobs": pakistani_jobs,
        "resume_outline": {
            "headline": str(resume.get("headline") or f"{domain} learning path personalized from quiz performance"),
            "keywords": [str(k) for k in (resume.get("keywords") or [])[:12]],
            "bullets": [str(b) for b in (resume.get("bullets") or [])[:14]],
        },
        "secondary_insights": secondary_insights,
    }
