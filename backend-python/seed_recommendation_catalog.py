"""
Seed recommendation catalog collections (careers, courses, learning_paths, rules, categories).

Run once in development or via admin bootstrap:
    python -m seed_recommendation_catalog
"""

from models.career import Career
from models.course import Course
from models.learning_path_catalog import LearningPathCatalog
from models.recommendation_rule import RecommendationRule
from models.category import Category
from database import init_db
from utils.market_context import salary_band_for_level


CATEGORIES = [
    {"name": "Coding", "slug": "coding", "icon": "💻", "sortOrder": 1,
     "description": "Programming fundamentals and software development"},
    {"name": "Web Development", "slug": "web-development", "icon": "🌐", "sortOrder": 2,
     "description": "Frontend, backend, and full-stack web technologies"},
    {"name": "Mobile Development", "slug": "mobile-development", "icon": "📱", "sortOrder": 3,
     "description": "iOS, Android, and cross-platform mobile apps"},
    {"name": "AI & Machine Learning", "slug": "ai-machine-learning", "icon": "🤖", "sortOrder": 4,
     "description": "Artificial intelligence, deep learning, and ML engineering"},
    {"name": "Data Science", "slug": "data-science", "icon": "📊", "sortOrder": 5,
     "description": "Analytics, statistics, and data-driven decision making"},
    {"name": "Cybersecurity", "slug": "cybersecurity", "icon": "🔐", "sortOrder": 6,
     "description": "Security engineering, ethical hacking, and threat analysis"},
    {"name": "Cloud Computing", "slug": "cloud-computing", "icon": "☁️", "sortOrder": 7,
     "description": "Cloud infrastructure, DevOps, and distributed systems"},
    {"name": "Game Development", "slug": "game-development", "icon": "🎮", "sortOrder": 8,
     "description": "Game design, engines, and interactive entertainment"},
]


def _seed_categories() -> None:
    for cat in CATEGORIES:
        if not Category.find_by_name(cat["name"]):
            Category.create(cat)


def _seed_ai_ml_expert() -> dict:
    """Example Expert AI/ML catalog matching system requirements."""
    existing = LearningPathCatalog.find_many(
        {"category": "AI & Machine Learning", "level": "Expert"}, limit=1
    )
    if existing:
        return {"roadmap": existing[0], "careers": [], "courses": []}

    roadmap = LearningPathCatalog.create({
        "category": "AI & Machine Learning",
        "level": "Expert",
        "title": "Expert AI/ML Engineering Path",
        "steps": [
            "Advanced Python",
            "Deep Learning",
            "Transformers",
            "LLMs",
            "RAG Systems",
            "MLOps",
            "Production Deployment",
        ],
        "estimatedDuration": "6-9 months",
    })

    careers = []
    for title, skills, salary, demand in [
        ("AI Engineer", ["Python", "Deep Learning", "LLMs", "MLOps"], "PKR 200,000 – 400,000 per month", 92),
        ("Machine Learning Engineer", ["ML", "TensorFlow", "Model Training", "Python"], "PKR 180,000 – 350,000 per month", 90),
        ("Research Engineer", ["Research", "PyTorch", "Transformers", "Math"], "PKR 220,000 – 450,000 per month", 85),
        ("MLOps Engineer", ["Docker", "Kubernetes", "CI/CD", "ML Pipelines"], "PKR 190,000 – 380,000 per month", 88),
    ]:
        careers.append(Career.create({
            "title": title,
            "category": "AI & Machine Learning",
            "level": "Expert",
            "description": f"Senior {title} role building production AI systems.",
            "requiredSkills": skills,
            "salaryRange": salary,
            "demandScore": demand,
        }))

    courses = []
    for title, provider, skills, url in [
        ("Advanced Deep Learning", "Coursera", ["Deep Learning", "CNNs", "RNNs"], "https://www.coursera.org"),
        ("LLM Engineering", "DeepLearning.AI", ["LLMs", "Transformers", "Fine-tuning"], "https://www.deeplearning.ai"),
        ("Production AI Systems", "Udacity", ["MLOps", "Deployment", "Monitoring"], "https://www.udacity.com"),
    ]:
        courses.append(Course.create({
            "title": title,
            "provider": provider,
            "category": "AI & Machine Learning",
            "level": "Expert",
            "duration": "8-12 weeks",
            "url": url,
            "skillsCovered": skills,
        }))

    RecommendationRule.create({
        "category": "AI & Machine Learning",
        "minimumScore": 76,
        "level": "Expert",
        "careers": [str(c["_id"]) for c in careers],
        "courses": [str(c["_id"]) for c in courses],
        "roadmapId": str(roadmap["_id"]),
        "priority": 100,
    })
    return {"roadmap": roadmap, "careers": careers, "courses": courses}


def _seed_domain_level(category: str, level: str, career_titles: list, course_titles: list, steps: list) -> None:
    existing = LearningPathCatalog.find_many({"category": category, "level": level}, limit=1)
    if existing:
        return

    roadmap = LearningPathCatalog.create({
        "category": category,
        "level": level,
        "title": f"{category} — {level} Path",
        "steps": steps,
        "estimatedDuration": {"Beginner": "3-4 months", "Intermediate": "4-6 months", "Expert": "6-9 months"}.get(level, "4-6 months"),
    })

    career_ids = []
    for title in career_titles:
        c = Career.create({
            "title": title,
            "category": category,
            "level": level,
            "description": f"{title} in {category}.",
            "requiredSkills": steps[:4],
            "salaryRange": salary_band_for_level(level),
            "demandScore": 70 + len(title) % 20,
        })
        career_ids.append(str(c["_id"]))

    course_ids = []
    for i, title in enumerate(course_titles):
        c = Course.create({
            "title": title,
            "provider": ["Coursera", "Udemy", "freeCodeCamp", "edX"][i % 4],
            "category": category,
            "level": level,
            "duration": f"{4 + i * 2} weeks",
            "url": "https://www.coursera.org",
            "skillsCovered": steps[i:i + 2] if i < len(steps) else steps[:2],
        })
        course_ids.append(str(c["_id"]))

    min_score = {"Beginner": 0, "Intermediate": 41, "Expert": 76}[level]
    RecommendationRule.create({
        "category": category,
        "minimumScore": min_score,
        "level": level,
        "careers": career_ids,
        "courses": course_ids,
        "roadmapId": str(roadmap["_id"]),
        "priority": min_score,
    })


DOMAIN_SEEDS = {
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
    "Mobile Development": {
        "Beginner": (["Junior Mobile Dev", "App Developer Intern"], ["Mobile UI Basics", "Flutter Intro"],
                     ["UI Components", "Navigation", "State", "APIs", "Publishing"]),
        "Intermediate": (["Mobile Engineer", "Cross-Platform Developer"], ["Advanced Flutter", "Native Modules"],
                        ["Architecture", "Offline Storage", "Push Notifications", "Testing", "CI/CD"]),
        "Expert": (["Senior Mobile Engineer", "Mobile Architect"], ["Performance Optimization", "Platform Design"],
                  ["Scalable Architecture", "Security", "Analytics", "Modularization", "Team Lead"]),
    },
    "Data Science": {
        "Beginner": (["Data Analyst", "Junior Data Scientist"], ["Statistics Basics", "Python for Data"],
                     ["Statistics", "Pandas", "Visualization", "SQL", "Excel"]),
        "Intermediate": (["Data Scientist", "ML Analyst"], ["Machine Learning Fundamentals", "Feature Engineering"],
                        ["Scikit-learn", "Feature Engineering", "Model Evaluation", "SQL Advanced", "Dashboards"]),
        "Expert": (["Senior Data Scientist", "ML Scientist"], ["Advanced ML", "Big Data"],
                  ["Deep Learning", "Spark", "A/B Testing", "MLOps", "Research"]),
    },
    "Cybersecurity": {
        "Beginner": (["Security Analyst Intern", "SOC Analyst"], ["Security Fundamentals", "Network Security"],
                     ["Networking", "Threats", "Cryptography Basics", "Linux", "SIEM"]),
        "Intermediate": (["Penetration Tester", "Security Engineer"], ["Ethical Hacking", "Web App Security"],
                        ["Pen Testing", "OWASP", "Forensics", "Incident Response", "Cloud Security"]),
        "Expert": (["Senior Security Architect", "Red Team Lead"], ["Advanced Exploitation", "Security Architecture"],
                  ["Red Team", "Zero Trust", "Threat Modeling", "Compliance", "Leadership"]),
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
}


def seed_recommendation_catalog(force: bool = False) -> dict:
    init_db()
    Career.ensure_indexes()
    Course.ensure_indexes()
    LearningPathCatalog.ensure_indexes()
    RecommendationRule.ensure_indexes()
    Category.ensure_indexes()

    if force:
        for coll in (Career, Course, LearningPathCatalog, RecommendationRule):
            coll.get_collection().delete_many({})

    _seed_categories()
    _seed_ai_ml_expert()

    for category, levels in DOMAIN_SEEDS.items():
        for level, (careers, courses, steps) in levels.items():
            _seed_domain_level(category, level, careers, courses, steps)

    for level, careers, courses, steps in [
        ("Beginner", ["Junior AI Developer"], ["Intro to AI", "Python for AI"],
         ["Python", "NumPy", "Pandas", "ML Basics", "Linear Algebra"]),
        ("Intermediate", ["ML Developer", "Data ML Engineer"], ["Machine Learning", "Neural Networks"],
         ["Supervised Learning", "Unsupervised Learning", "Neural Nets", "Model Tuning", "Deployment"]),
    ]:
        _seed_domain_level("AI & Machine Learning", level, careers, courses, steps)

    counts = {
        "categories": Category.get_collection().count_documents({}),
        "careers": Career.count({}),
        "courses": Course.count({}),
        "learning_paths": LearningPathCatalog.count({}),
        "rules": RecommendationRule.count({}),
    }
    print("Recommendation catalog seeded:", counts)
    return counts


if __name__ == "__main__":
    seed_recommendation_catalog()
