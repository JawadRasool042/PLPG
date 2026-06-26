"""Career market region helpers (default: Pakistan)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional


def get_market_region() -> str:
    return (os.getenv("CAREER_MARKET_REGION") or "Pakistan").strip() or "Pakistan"


def salary_band_for_level(level: str) -> str:
    """Catalog seed bands for Pakistan IT market (monthly PKR)."""
    bands = {
        "Beginner": "PKR 50,000 – 90,000 per month",
        "Intermediate": "PKR 90,000 – 180,000 per month",
        "Expert": "PKR 180,000 – 400,000 per month",
    }
    return bands.get(level, bands["Intermediate"])


# Domain-specific Pakistan salary bands (monthly PKR).
DOMAIN_SALARY_BANDS: Dict[str, Dict[str, str]] = {
    "Cybersecurity": {
        "junior": "PKR 60,000 – 110,000 per month",
        "mid": "PKR 110,000 – 200,000 per month",
        "senior": "PKR 200,000 – 380,000 per month",
    },
    "Web Development": {
        "junior": "PKR 55,000 – 95,000 per month",
        "mid": "PKR 95,000 – 170,000 per month",
        "senior": "PKR 170,000 – 320,000 per month",
    },
    "Coding": {
        "junior": "PKR 50,000 – 90,000 per month",
        "mid": "PKR 90,000 – 160,000 per month",
        "senior": "PKR 160,000 – 300,000 per month",
    },
    "AI & Machine Learning": {
        "junior": "PKR 80,000 – 140,000 per month",
        "mid": "PKR 140,000 – 250,000 per month",
        "senior": "PKR 250,000 – 450,000 per month",
    },
    "Data Science": {
        "junior": "PKR 70,000 – 120,000 per month",
        "mid": "PKR 120,000 – 210,000 per month",
        "senior": "PKR 210,000 – 380,000 per month",
    },
    "Mobile Development": {
        "junior": "PKR 55,000 – 100,000 per month",
        "mid": "PKR 100,000 – 180,000 per month",
        "senior": "PKR 180,000 – 330,000 per month",
    },
    "Cloud Computing": {
        "junior": "PKR 65,000 – 115,000 per month",
        "mid": "PKR 115,000 – 200,000 per month",
        "senior": "PKR 200,000 – 360,000 per month",
    },
    "Game Development": {
        "junior": "PKR 45,000 – 85,000 per month",
        "mid": "PKR 85,000 – 150,000 per month",
        "senior": "PKR 150,000 – 280,000 per month",
    },
}

# Platforms and providers commonly used by learners in Pakistan.
PAKISTAN_COURSE_SOURCES: List[str] = [
    "DigiSkills.pk",
    "PITB (Punjab IT Board)",
    "NAVTTC",
    "HEC Virtual Academy",
    "PIAIC (Presidential Initiative for AI & Computing)",
    "Saylani Mass IT Training (SMIT)",
    "Coursera (financial aid available in Pakistan)",
    "Udemy (PKR pricing / frequent sales)",
    "YouTube (Urdu/English channels e.g. CodeWithHarry, Apna College Urdu, freeCodeCamp)",
    "Microsoft Learn",
    "Google Developers / Google Skills",
    "AWS Skill Builder",
    "freeCodeCamp",
    "Khan Academy",
    "NPTEL (free, widely used in Pakistan)",
    "Local university MOOCs (LUMS, NUST, FAST, COMSATS online resources)",
]


def get_market_prompt_rules(region: str | None = None) -> List[str]:
    market = (region or get_market_region()).strip()
    return [
        f"All careers and salary_range values MUST reflect the {market} job market only.",
        "Express salaries in Pakistani Rupees (PKR), not USD or other currencies.",
        'Format salary_range like "PKR 80,000 – 150,000 per month" or "PKR 960,000 – 1,800,000 per year".',
        f"Use job titles commonly posted in {market} (local IT firms, startups, banks, telcos, and remote roles for international clients).",
        f"Reference realistic hiring demand in {market} tech hubs (Karachi, Lahore, Islamabad, Rawalpindi, Faisalabad).",
        "growth_potential should describe demand trends in the Pakistan market (e.g. rising remote work, fintech, ecommerce).",
        "Never use USD ($) or US salary figures. salary_range must start with PKR.",
        "Include at least 4 careers_detailed entries with distinct seniority levels (intern/junior, mid, senior, lead).",
    ]


def get_job_recommendation_prompt_rules(region: str | None = None) -> List[str]:
    """Prompt rules for course-linked Pakistani job recommendations."""
    market = (region or get_market_region()).strip()
    return [
        f"For EVERY recommended course, include 2–3 related_pakistani_jobs tied to skills that course teaches.",
        f"Each job must be realistic for the {market} market — use titles seen on Rozee.pk, LinkedIn Pakistan, Mustakbil, and local company career pages.",
        "salary_pkr must be in PKR (monthly), e.g. PKR 65,000 – 110,000 per month. Never use USD.",
        "city must be a Pakistan tech hub (Karachi, Lahore, Islamabad, Rawalpindi, Faisalabad) or Remote (Pakistan).",
        "employer_type examples: Pakistani IT services (Systems Limited, NETSOL, TRG), local startup, bank/fintech, telco, ecommerce, or remote-for-foreign-client.",
        "why_recommended must explicitly connect the course name/skills to why the student qualifies for that job after completing it.",
        "Also populate top-level pakistani_jobs with 6–10 unique roles aggregated across all courses (deduplicate by title+city).",
        "Match job seniority to student quiz caliber: lower scores → intern/junior roles; higher scores → mid/senior roles.",
    ]


def get_course_recommendation_prompt_rules(region: str | None = None) -> List[str]:
    """Prompt rules for Pakistan-relevant course recommendations."""
    market = (region or get_market_region()).strip()
    sources = ", ".join(PAKISTAN_COURSE_SOURCES[:10])
    return [
        f"Recommend 6–10 courses tailored for students in {market} — not generic US-only bootcamps unless highly relevant.",
        f"At least half of courses MUST come from Pakistan-accessible sources such as: {sources}.",
        "Prioritize FREE or low-cost options (DigiSkills, YouTube Urdu/English, freeCodeCamp, Microsoft Learn) — many Pakistani students need affordable paths.",
        "For paid courses, set price_pkr_hint in PKR (e.g. PKR 1,500 – 3,500 or Free with Coursera financial aid). Never list USD-only prices.",
        "platform must name the actual provider (e.g. DigiSkills.pk, Udemy, Coursera, YouTube — CodeWithHarry).",
        "language must be English, Urdu, or Both — prefer Urdu or bilingual when the student is a beginner.",
        "pakistan_relevance: one sentence on why this course fits Pakistani learners (local job market, Urdu support, free access, remote-work skills).",
        "secondary_insights recommended_courses must also be Pakistan-accessible (name platform in the course string, e.g. 'React — DigiSkills.pk').",
    ]


def get_roadmap_prompt_rules(region: str | None = None) -> List[str]:
    """Prompt rules for Pakistan-tailored learning roadmaps."""
    market = (region or get_market_region()).strip()
    return [
        f"The roadmap MUST be designed for a student in {market} entering the local + remote job market.",
        "Each roadmap stage (basic, intermediate, advanced, expert) must include pakistan_focus: one sentence on how that stage helps land jobs in Pakistan.",
        "Each stage must include local_milestones: 2–4 actionable milestones (e.g. portfolio for Rozee.pk, Fiverr gig, GitHub for remote clients, PITB/DigiSkills certificate).",
        "Each stage must include market_skills: 3–6 skills explicitly demanded in Pakistan job posts for this domain and level.",
        "Topics must reflect Pakistan industry needs — ecommerce (Daraz), fintech (JazzCash, Easypaisa), IT services exports, telco, banking software, freelancing (Upwork/Fiverr from Pakistan).",
        "stage_projects must be portfolio pieces Pakistani employers or international remote clients would recognize (real-world apps, not toy examples).",
        "Basic projects: simple but deployable (landing page for local business, basic CRUD app). Intermediate: API + database project. Advanced: production-style features. Expert: capstone aligned with Pakistan hiring (e.g. fintech dashboard, ecommerce backend, system design).",
        "duration_label should be realistic for part-time learners in Pakistan (e.g. 4–8 weeks per stage at 5–10 hrs/week).",
        "Include roadmap_summary_pakistan: 2–3 sentences summarizing the full path toward employability in the Pakistan market.",
        "Do NOT use US-centric examples (Silicon Valley internships, FAANG prep) unless the student explicitly targets remote US roles.",
        "Prefer milestones achievable with free/low-cost tools available in Pakistan (GitHub, Vercel free tier, freeCodeCamp, DigiSkills).",
    ]


def normalize_roadmap_stage(
    stage: Dict[str, Any],
    *,
    level: str,
    domain: str = "",
) -> Dict[str, Any]:
    """Ensure each roadmap stage includes Pakistan market context."""
    item = dict(stage)
    item["market_region"] = get_market_region()
    level_label = level.capitalize()
    item.setdefault(
        "pakistan_focus",
        f"{level_label} skills in {domain or 'this domain'} aligned with hiring demand in Pakistan's IT and remote-work market.",
    )
    milestones = item.get("local_milestones") or item.get("milestones") or []
    if not isinstance(milestones, list):
        milestones = []
    if not milestones and get_market_region().lower() == "pakistan":
        defaults = {
            "basic": [
                "Complete one free module on DigiSkills or YouTube (Urdu/English)",
                "Publish a small project on GitHub",
                "Create a Rozee.pk / LinkedIn profile listing your stack",
            ],
            "beginner": [
                "Complete one free module on DigiSkills or YouTube (Urdu/English)",
                "Publish a small project on GitHub",
                "Create a Rozee.pk / LinkedIn profile listing your stack",
            ],
            "intermediate": [
                "Build a portfolio project solving a local business problem",
                "Apply to 5 junior roles or freelance gigs on Rozee.pk / Upwork",
                "Earn a certificate from Coursera (financial aid) or PITB program",
            ],
            "advanced": [
                "Deliver a production-style project deployable for Pakistani or remote clients",
                "Demonstrate architecture and debugging skills in portfolio reviews",
                "Prepare for mid-level technical interviews in Pakistan IT companies",
            ],
            "expert": [
                "Deliver a capstone project deployable for Pakistani or remote clients",
                "Target senior roles at IT firms (Karachi, Lahore, Islamabad) or high-value remote contracts",
                "Prepare for system design and leadership interviews common in Pakistan IT companies",
            ],
        }
        milestones = defaults.get(level.lower(), defaults["intermediate"])
    item["local_milestones"] = [str(m).strip() for m in milestones[:6] if str(m).strip()]

    market_skills = item.get("market_skills") or []
    if not isinstance(market_skills, list):
        market_skills = []
    item["market_skills"] = [str(s).strip() for s in market_skills[:8] if str(s).strip()]
    return item


def normalize_roadmap_for_market(
    roadmap: Dict[str, Any],
    *,
    domain: str = "",
) -> Dict[str, Any]:
    """Normalize full roadmap for Pakistan market metadata."""
    if get_market_region().lower() != "pakistan":
        return roadmap

    out = dict(roadmap)
    out["market_region"] = get_market_region()
    out.setdefault(
        "roadmap_summary_pakistan",
        f"Structured path from foundations to job-ready {domain or 'skills'} for Pakistan's local IT market and remote freelancing.",
    )
    for level in ("basic", "intermediate", "advanced", "expert"):
        block = out.get(level)
        if not isinstance(block, dict) and level == "basic":
            block = out.get("beginner")
        if isinstance(block, dict):
            out[level] = normalize_roadmap_stage(block, level=level, domain=domain)
    out.pop("beginner", None)
    return out


def normalize_job_salary(salary: Optional[str], *, title: str = "", domain: str = "", index: int = 0) -> str:
    """Ensure job salary fields use PKR bands."""
    return normalize_salary_range(salary, title=title, domain=domain, index=index)


def normalize_pakistani_jobs(
    jobs: List[Dict[str, Any]],
    *,
    domain: str = "",
) -> List[Dict[str, Any]]:
    """Normalize OpenAI job recommendations for Pakistan market."""
    if get_market_region().lower() != "pakistan":
        return jobs

    normalized: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for i, job in enumerate(jobs):
        if not isinstance(job, dict):
            continue
        title = str(job.get("title") or "").strip()
        if not title:
            continue
        city = str(job.get("city") or "Pakistan").strip()
        dedupe_key = f"{title.lower()}|{city.lower()}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        salary = job.get("salary_pkr") or job.get("salary_range") or job.get("salary")
        skills = job.get("skills_match") or job.get("required_skills") or []
        if not isinstance(skills, list):
            skills = []

        normalized.append(
            {
                "title": title,
                "matched_course": str(job.get("matched_course") or job.get("course") or "").strip(),
                "employer_type": str(job.get("employer_type") or job.get("company_type") or "Pakistani employer").strip(),
                "city": city,
                "salary_pkr": normalize_job_salary(str(salary) if salary else None, title=title, domain=domain, index=i),
                "employment_type": str(job.get("employment_type") or "full-time").strip(),
                "skills_match": [str(s) for s in skills[:6]],
                "why_recommended": str(job.get("why_recommended") or job.get("why") or "").strip(),
            }
        )
    return normalized


def market_metadata(region: str | None = None) -> Dict[str, str]:
    market = (region or get_market_region()).strip()
    return {
        "market_region": market,
        "salary_currency": "PKR",
        "salary_basis": "Pakistan local market estimates",
        "course_market": market,
    }


_USD_PATTERN = re.compile(r"[$]|usd|\bus\b", re.I)
_PKR_PATTERN = re.compile(r"pkr|rs\.?\s*\d|rupee", re.I)


def is_pkr_salary(text: Optional[str]) -> bool:
    if not text or not str(text).strip():
        return False
    raw = str(text).strip()
    if _PKR_PATTERN.search(raw):
        return True
    if _USD_PATTERN.search(raw):
        return False
    # Large annual numbers without currency are treated as foreign/US-style output.
    if re.search(r"\d{2,3},?\d{3}\s*[-–—]\s*\d{2,3},?\d{3}", raw) and re.search(r"per\s+year", raw, re.I):
        return False
    return False


def _infer_salary_tier(title: str, index: int) -> str:
    t = (title or "").lower()
    if any(x in t for x in ("intern", "trainee", "entry", "junior", "associate")):
        return "junior"
    if any(x in t for x in ("senior", "lead", "principal", "architect", "director", "head")):
        return "senior"
    if index <= 0:
        return "junior"
    if index >= 2:
        return "mid"
    return "mid"


def normalize_salary_range(
    salary: Optional[str],
    *,
    title: str = "",
    domain: str = "",
    index: int = 0,
) -> str:
    """Replace USD or missing salaries with Pakistan-market PKR bands."""
    if is_pkr_salary(salary):
        return str(salary).strip()

    tier = _infer_salary_tier(title, index)
    domain_bands = DOMAIN_SALARY_BANDS.get((domain or "").strip()) or {}
    if tier in domain_bands:
        return domain_bands[tier]

    tier_to_level = {
        "junior": "Beginner",
        "mid": "Intermediate",
        "senior": "Expert",
    }
    return salary_band_for_level(tier_to_level.get(tier, "Intermediate"))


def normalize_careers_for_market(
    careers: List[Dict[str, Any]],
    *,
    domain: str = "",
) -> List[Dict[str, Any]]:
    """Ensure every career card uses PKR salary ranges for the configured market."""
    if get_market_region().lower() != "pakistan":
        return careers

    normalized: List[Dict[str, Any]] = []
    for i, career in enumerate(careers):
        if not isinstance(career, dict):
            continue
        item = dict(career)
        title = str(item.get("title") or "")
        item["salary_range"] = normalize_salary_range(
            item.get("salary_range") or item.get("salaryRange"),
            title=title,
            domain=domain,
            index=i,
        )
        normalized.append(item)
    return normalized


def normalize_course_card(
    course: Dict[str, Any],
    *,
    domain: str = "",
    index: int = 0,
) -> Dict[str, Any]:
    """Ensure course cards include Pakistan market metadata."""
    item = dict(course)
    item["market_region"] = get_market_region()
    item.setdefault("language", "English")
    item.setdefault(
        "pakistan_relevance",
        f"Supports {domain or 'your'} skills valued in the Pakistan job market.",
    )
    if get_market_region().lower() == "pakistan":
        price = str(item.get("price_pkr_hint") or item.get("price") or "").strip()
        if not price:
            item["price_pkr_hint"] = "Free" if item.get("free", True) else "Check platform for PKR pricing"
        elif _USD_PATTERN.search(price) and not _PKR_PATTERN.search(price):
            item["price_pkr_hint"] = "See platform for PKR price (Udemy/Coursera sales)"
        else:
            item["price_pkr_hint"] = price
    platform = str(item.get("platform") or "").strip()
    if not platform or platform.lower() == "openai recommendation":
        item["platform"] = "Pakistan-accessible learning resource"
    return item


def normalize_courses_for_market(
    courses: List[Dict[str, Any]],
    *,
    domain: str = "",
) -> List[Dict[str, Any]]:
    """Normalize course recommendations for the configured market."""
    if get_market_region().lower() != "pakistan":
        return courses
    return [
        normalize_course_card(c, domain=domain, index=i)
        for i, c in enumerate(courses)
        if isinstance(c, dict)
    ]


CAREER_LEVEL_ORDER: Dict[str, int] = {"beginner": 0, "intermediate": 1, "advanced": 2}


def get_career_progress_prompt_rules() -> List[str]:
    """Prompt rules tying career levels to student quiz progress."""
    return [
        "Every careers_detailed entry MUST include level: beginner, intermediate, or advanced.",
        "Provide at least 2 career roles per level (6+ total) with PKR salary_range appropriate to that seniority.",
        "beginner = intern, trainee, junior, fresher, entry-level roles.",
        "intermediate = mid-level developer/engineer, 1–3 years experience roles.",
        "advanced = senior, lead, architect, principal, team lead roles.",
        "Match emphasis to quiz_caliber: low scores / beginner difficulty → more beginner roles; high scores → include advanced roles.",
        "Mark the career closest to the student's current progress with progress_note explaining why it fits their quiz performance.",
    ]


def resolve_user_career_level(quiz_caliber: Optional[Dict[str, Any]]) -> str:
    """Map quiz performance to beginner / intermediate / advanced."""
    caliber = quiz_caliber or {}
    explicit = str(caliber.get("recommended_quiz_difficulty") or "").strip().lower()
    if explicit in CAREER_LEVEL_ORDER:
        return explicit

    try:
        mastery = float(caliber.get("mastery_level") or 0)
    except (TypeError, ValueError):
        mastery = 0.0
    if mastery >= 0.72:
        return "advanced"
    if mastery >= 0.45:
        return "intermediate"
    return "beginner"


def infer_career_level(title: str, index: int = 0) -> str:
    """Infer career level from job title when API omits level."""
    t = (title or "").lower()
    if any(x in t for x in ("intern", "trainee", "entry", "junior", "associate", "fresher", "graduate")):
        return "beginner"
    if any(x in t for x in ("senior", "lead", "principal", "architect", "director", "head", "manager")):
        return "advanced"
    if index % 3 == 0:
        return "beginner"
    if index % 3 == 2:
        return "advanced"
    return "intermediate"


def build_careers_by_level(careers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {
        "beginner": [],
        "intermediate": [],
        "advanced": [],
    }
    for career in careers:
        level = str(career.get("level") or "intermediate").lower()
        if level not in grouped:
            level = infer_career_level(str(career.get("title") or ""))
        grouped[level].append(career)
    return grouped


def align_careers_to_user_progress(
    careers: List[Dict[str, Any]],
    quiz_caliber: Optional[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], str, Dict[str, List[Dict[str, Any]]]]:
    """
    Tag each career with level + progress_status relative to the user's quiz progress.
    Returns (aligned_careers, user_level, careers_by_level).
    """
    user_level = resolve_user_career_level(quiz_caliber)
    user_rank = CAREER_LEVEL_ORDER[user_level]

    aligned: List[Dict[str, Any]] = []
    for i, career in enumerate(careers):
        if not isinstance(career, dict):
            continue
        item = dict(career)
        level = str(item.get("level") or item.get("career_level") or "").strip().lower()
        if level not in CAREER_LEVEL_ORDER:
            level = infer_career_level(str(item.get("title") or ""), i)
        item["level"] = level

        career_rank = CAREER_LEVEL_ORDER[level]
        if career_rank < user_rank:
            item["progress_status"] = "achieved"
        elif career_rank == user_rank:
            item["progress_status"] = "current"
        else:
            item["progress_status"] = "upcoming"
        item["recommended"] = career_rank == user_rank
        aligned.append(item)

    aligned.sort(key=lambda c: (CAREER_LEVEL_ORDER.get(str(c.get("level")), 1), not c.get("recommended")))
    by_level = build_careers_by_level(aligned)
    return aligned, user_level, by_level
