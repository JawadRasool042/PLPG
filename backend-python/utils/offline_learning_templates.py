"""Offline learning-path templates when OpenAI is unavailable (interest check + roadmap fallback)."""

from __future__ import annotations

from typing import Any, Dict, List

from utils.market_context import (
    align_careers_to_user_progress,
    market_metadata,
    normalize_careers_for_market,
    normalize_roadmap_for_market,
    salary_band_for_level,
)

# careers, course names, topics per stage
_DOMAIN_DATA: Dict[str, Dict[str, tuple]] = {
    "Coding": {
        "Beginner": (["Junior Developer", "Programming Intern"], ["Intro to Programming", "Python Basics"],
                     ["Variables & Types", "Control Flow", "Functions", "OOP Basics", "Git"]),
        "Intermediate": (["Software Developer", "Backend Developer"], ["Data Structures", "API Development"],
                          ["DSA", "REST APIs", "Databases", "Testing", "Design Patterns"]),
        "Expert": (["Senior Software Engineer", "Tech Lead"], ["System Design", "Advanced Algorithms"],
                  ["System Design", "Microservices", "Performance", "Architecture", "Leadership"]),
    },
    "Web Development": {
        "Beginner": (["Frontend Intern", "Junior Web Developer"], ["HTML/CSS Fundamentals", "JavaScript Basics"],
                     ["HTML", "CSS", "JavaScript", "Responsive Design", "Git"]),
        "Intermediate": (["Full Stack Developer", "React Developer"], ["React Mastery", "Node.js Backend"],
                        ["React", "Node.js", "REST", "MongoDB", "Auth"]),
        "Expert": (["Senior Full Stack Engineer", "Web Architect"], ["Advanced React Patterns", "Micro Frontends"],
                  ["Next.js", "GraphQL", "Performance", "SSR/SSG", "Cloud Deploy"]),
    },
    "Cybersecurity": {
        "Beginner": (["SOC Analyst", "Security Analyst Intern"], ["Security Fundamentals", "Network Security"],
                     ["Networking", "Threats", "Cryptography Basics", "Linux", "SIEM"]),
        "Intermediate": (["Penetration Tester", "Security Engineer"], ["Ethical Hacking", "Web App Security"],
                        ["Pen Testing", "OWASP", "Forensics", "Incident Response", "Cloud Security"]),
        "Expert": (["Senior Security Architect", "Red Team Lead"], ["Advanced Exploitation", "Security Architecture"],
                  ["Red Team", "Zero Trust", "Threat Modeling", "Compliance", "Leadership"]),
    },
    "Data Science": {
        "Beginner": (["Data Analyst", "Junior Data Scientist"], ["Statistics Basics", "Python for Data"],
                     ["Statistics", "Pandas", "Visualization", "SQL", "Excel"]),
        "Intermediate": (["Data Scientist", "ML Analyst"], ["Machine Learning Fundamentals", "Feature Engineering"],
                        ["Scikit-learn", "Feature Engineering", "Model Evaluation", "SQL Advanced", "Dashboards"]),
        "Expert": (["Senior Data Scientist", "ML Scientist"], ["Advanced ML", "Big Data"],
                  ["Deep Learning", "Spark", "A/B Testing", "MLOps", "Research"]),
    },
    "AI & Machine Learning": {
        "Beginner": (["ML Intern", "Junior AI Engineer"], ["Python for AI", "ML Basics"],
                     ["Python", "Statistics", "Linear Algebra", "Scikit-learn", "Data Prep"]),
        "Intermediate": (["Machine Learning Engineer", "AI Developer"], ["Deep Learning", "NLP Intro"],
                        ["TensorFlow/PyTorch", "CNNs", "NLP", "Model Evaluation", "Deployment"]),
        "Expert": (["Senior AI Engineer", "ML Architect"], ["LLMs & MLOps", "Production AI"],
                  ["Transformers", "LLMs", "RAG", "MLOps", "System Design"]),
    },
    "Mobile Development": {
        "Beginner": (["Junior Mobile Dev", "App Developer Intern"], ["Mobile UI Basics", "Flutter Intro"],
                     ["UI Components", "Navigation", "State", "APIs", "Publishing"]),
        "Intermediate": (["Mobile Engineer", "Cross-Platform Developer"], ["Advanced Flutter", "Native Modules"],
                        ["Architecture", "Offline Storage", "Push Notifications", "Testing", "CI/CD"]),
        "Expert": (["Senior Mobile Engineer", "Mobile Architect"], ["Performance Optimization", "Platform Design"],
                  ["Scalable Architecture", "Security", "Analytics", "Modularization", "Team Lead"]),
    },
    "Cloud Computing": {
        "Beginner": (["Cloud Support Associate", "Junior Cloud Engineer"], ["Cloud Fundamentals", "AWS Basics"],
                     ["Cloud Concepts", "AWS Core", "Networking", "Storage", "IAM"]),
        "Intermediate": (["Cloud Engineer", "DevOps Engineer"], ["AWS Solutions Architect", "Docker & Kubernetes"],
                        ["Docker", "Kubernetes", "Terraform", "CI/CD", "Monitoring"]),
        "Expert": (["Cloud Architect", "Principal DevOps Engineer"], ["Multi-Cloud Architecture", "SRE"],
                  ["Architecture", "Cost Optimization", "Security", "Disaster Recovery", "Leadership"]),
    },
    "Game Development": {
        "Beginner": (["Junior Game Developer", "Game Design Intern"], ["Game Dev Basics", "Unity Intro"],
                     ["Game Loops", "Unity", "C# Basics", "2D Physics", "Level Design"]),
        "Intermediate": (["Game Developer", "Gameplay Programmer"], ["Advanced Unity", "Multiplayer Basics"],
                        ["3D Graphics", "AI NPCs", "Animation", "Networking", "Optimization"]),
        "Expert": (["Senior Game Engineer", "Technical Director"], ["Engine Architecture", "AAA Production"],
                  ["Custom Engines", "Rendering", "Performance", "Pipeline", "Leadership"]),
    },
    "Physical Games / Sports": {
        "Beginner": (["Sports Trainee", "Assistant Coach"], ["Fitness Basics", "Fundamentals"],
                     ["Conditioning", "Rules", "Teamwork", "Nutrition Basics", "Safety"]),
        "Intermediate": (["Coach", "Athletic Trainer"], ["Training Plans", "Performance Analytics"],
                        ["Strategy", "Periodization", "Injury Prevention", "Leadership", "Analytics"]),
        "Expert": (["Head Coach", "Sports Scientist"], ["High Performance", "Program Design"],
                  ["Elite Training", "Biomechanics", "Team Management", "Scouting", "Sports Psychology"]),
    },
}

_LEVEL_MAP = {
    "Beginner": ("basic", "beginner", "4-6 weeks"),
    "Intermediate": ("intermediate", "intermediate", "6-8 weeks"),
    "Expert": ("advanced", "expert", "8-12 weeks"),
}


def _resolve_domain(domain: str) -> str:
    key = (domain or "").strip()
    if key in _DOMAIN_DATA:
        return key
    for name in _DOMAIN_DATA:
        if name.lower() == key.lower():
            return name
    return "Coding"


def _stage_block(topics: List[str], label: str, duration: str) -> Dict[str, Any]:
    projects = topics[:2] if topics else [f"{label} portfolio project"]
    return {
        "topics": topics,
        "all_topics": topics,
        "duration_label": duration,
        "stage_projects": projects,
        "pakistan_focus": f"Build employable {label.lower()} skills for Pakistan's IT and remote-work market.",
        "local_milestones": [
            "Complete a free DigiSkills or YouTube module",
            "Publish a project on GitHub",
            "Update Rozee.pk / LinkedIn profile",
        ],
        "market_skills": topics[:5],
    }


def build_offline_openai_bundle(
    domain: str,
    *,
    quiz_caliber: Dict[str, Any] | None = None,
    user: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Shape-compatible with ``generate_learning_path_via_openai`` output."""
    domain = _resolve_domain(domain)
    data = _DOMAIN_DATA.get(domain, _DOMAIN_DATA["Coding"])
    caliber = quiz_caliber or {}

    basic = _stage_block(data["Beginner"][2], "Beginner", "4-6 weeks")
    intermediate = _stage_block(data["Intermediate"][2], "Intermediate", "6-8 weeks")
    advanced = _stage_block(data["Expert"][2], "Advanced", "8-12 weeks")
    expert = _stage_block(data["Expert"][2], "Expert", "8-12 weeks")

    course_cards = []
    for level_key, (_, courses, _) in zip(["Beginner", "Intermediate", "Expert"], [
        data["Beginner"], data["Intermediate"], data["Expert"],
    ]):
        for i, name in enumerate(courses[:2]):
            course_cards.append({
                "name": name,
                "platform": ["DigiSkills.pk", "Coursera", "YouTube"][i % 3],
                "url_hint": "",
                "free": True,
                "difficulty": level_key.lower(),
                "language": "English",
                "price_pkr_hint": "Free",
                "pakistan_relevance": f"Accessible in Pakistan for {domain} learners.",
                "related_pakistani_jobs": [],
            })

    careers_detailed: List[Dict[str, Any]] = []
    level_keys = ["beginner", "intermediate", "advanced"]
    for level_idx, level_key in enumerate(level_keys):
        seed_key = ["Beginner", "Intermediate", "Expert"][level_idx]
        titles, _, skills = data[seed_key]
        salary = salary_band_for_level(seed_key)
        for j, title in enumerate(titles):
            careers_detailed.append({
                "title": title,
                "level": level_key,
                "industry": domain,
                "salary_range": salary,
                "growth_potential": "Steady demand in Pakistan IT and remote-work market",
                "required_skills": skills[:4],
                "resume_angle": f"Entry path toward {title} in {domain}.",
            })

    careers_detailed = normalize_careers_for_market(careers_detailed, domain=domain)
    careers_detailed, _, _ = align_careers_to_user_progress(careers_detailed, caliber)

    roadmap = normalize_roadmap_for_market(
        {
            "basic": basic,
            "beginner": basic,
            "intermediate": intermediate,
            "advanced": advanced,
            "expert": expert,
            "roadmap_summary_pakistan": (
                f"Offline {domain} roadmap for Pakistan learners — complete quizzes to unlock a personalized AI path."
            ),
            "resources": {
                "courses": [c["name"] for c in course_cards],
                "course_cards": course_cards,
            },
            "career_paths": [c["title"] for c in careers_detailed],
            "suggested_projects": (
                basic.get("stage_projects", [])
                + intermediate.get("stage_projects", [])[:2]
            )[:6],
        },
        domain=domain,
    )

    return {
        "source": "offline_template",
        **market_metadata(),
        "recommended_quiz_difficulty": str(
            caliber.get("recommended_quiz_difficulty") or "beginner"
        ),
        "caliber_summary": "Template roadmap (OpenAI unavailable). Take a quiz to refresh with AI personalization.",
        "roadmap": roadmap,
        "careers_detailed": careers_detailed,
        "pakistani_jobs": [],
        "resume_outline": {
            "headline": f"{domain} learner — Pakistan market path",
            "keywords": roadmap.get("basic", {}).get("topics", [])[:6],
            "bullets": [
                f"Building foundational {domain} skills for the Pakistan job market.",
                "Complete domain quizzes to unlock AI-personalized milestones.",
            ],
        },
        "secondary_insights": {},
    }


def enrich_interest_recommendation(
    primary_interest: str,
    user_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Offline careers + skill roadmap for interest checker results."""
    domain = _resolve_domain(primary_interest)
    data = _DOMAIN_DATA.get(domain, _DOMAIN_DATA["Coding"])

    career_paths: List[Dict[str, Any]] = []
    for level_idx, level_label in enumerate(["Beginner", "Intermediate", "Expert"]):
        titles, _, skills = data[level_label]
        salary = salary_band_for_level(level_label)
        level_key = ["beginner", "intermediate", "advanced"][level_idx]
        for title in titles:
            career_paths.append({
                "title": title,
                "level": level_key,
                "industry": domain,
                "salary_range": salary,
                "growth_potential": "Growing demand in Pakistan tech hubs",
                "required_skills": skills[:4],
                "entry_requirements": ", ".join(skills[:2]),
                "recommended": level_key == "beginner",
                "progress_status": "current" if level_key == "beginner" else "upcoming",
            })

    careers_detailed = normalize_careers_for_market(career_paths, domain=domain)
    aligned, _, _ = align_careers_to_user_progress(careers_detailed, {})

    skill_roadmap = []
    for level_label in ["Beginner", "Intermediate", "Expert"]:
        _, _, topics = data[level_label]
        skill_roadmap.append({
            "level": level_label,
            "duration": {"Beginner": "4-6 weeks", "Intermediate": "6-8 weeks", "Expert": "8-12 weeks"}[level_label],
            "topics": topics,
            "projects": topics[:2],
            "resources": [
                "DigiSkills.pk",
                "YouTube (Urdu/English)",
                "freeCodeCamp",
            ],
        })

    return {
        "career_paths": aligned,
        "skill_roadmap": skill_roadmap,
    }
