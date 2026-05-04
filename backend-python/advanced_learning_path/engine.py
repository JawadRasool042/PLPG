"""Advanced personalized learning path and interest intelligence engine."""

from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .charts import generate_domain_comparison, generate_growth_graph, generate_radar_chart, generate_skill_heatmap
from .schemas import LearningInsight, LearningProfile, RoadmapItem
from .storage import LearningPathRepository

logger = logging.getLogger(__name__)


DOMAINS = [
    "Coding",
    "Web Development",
    "Game Development",
    "Cybersecurity",
    "Data Science",
    "Mobile Development",
    "Cloud Computing",
    "AI & Machine Learning",
    "Physical Games / Sports",
]

PROFILE_LABELS = {
    "Builder": {"Coding", "Web Development", "Cloud Computing", "Mobile Development"},
    "Analyst": {"Data Science", "Cybersecurity", "Cloud Computing"},
    "Researcher": {"AI & Machine Learning", "Data Science", "Cybersecurity"},
    "Creator": {"Web Development", "Game Development", "Mobile Development"},
    "Athlete": {"Physical Games / Sports"},
    "Hacker": {"Cybersecurity", "Coding"},
    "Explorer": set(DOMAINS),
    "Beginner": set(DOMAINS),
    "Advanced Learner": {"Coding", "Data Science", "Cybersecurity", "AI & Machine Learning", "Cloud Computing"},
}

NLP_KEYWORDS = {
    "Coding": {"code", "coding", "program", "software", "algorithm", "debug", "logic", "build app", "develop"},
    "Web Development": {"website", "web", "frontend", "backend", "html", "css", "javascript", "react"},
    "Game Development": {"game", "unity", "unreal", "graphics", "3d", "animation"},
    "Cybersecurity": {"secure", "security", "hack", "penetration", "privacy", "threat", "defense"},
    "Data Science": {"data", "analysis", "analytics", "statistics", "machine learning", "ml", "predict"},
    "Mobile Development": {"mobile", "app", "android", "ios", "swift", "kotlin", "flutter"},
    "Cloud Computing": {"cloud", "aws", "azure", "gcp", "devops", "docker", "kubernetes"},
    "AI & Machine Learning": {"ai", "artificial intelligence", "machine learning", "neural", "model", "llm"},
    "Physical Games / Sports": {"sport", "fitness", "athlete", "coach", "workout", "leadership", "team"},
}


@dataclass(slots=True)
class SignalSummary:
    explicit: Dict[str, float]
    behavioral: Dict[str, float]
    nlp: Dict[str, float]
    skills: Dict[str, float]
    goals: Dict[str, float]
    learning_style: Dict[str, float]
    time_availability: Dict[str, float]
    personality: Dict[str, float]
    confidence: Dict[str, float]
    motivation: Dict[str, float]


@dataclass(slots=True)
class AdvancedResult:
    user_profile: str
    top_domains: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    roadmap: Dict[str, Any]
    career_paths: Dict[str, Any]
    skills_gap: Dict[str, Any]
    projects: List[Dict[str, Any]]
    certifications: List[str]
    gamification: Dict[str, Any]
    visual_analytics: Dict[str, str]
    raw_signals: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdvancedLearningPathEngine:
    """Hybrid intelligence engine combining weighted scoring, rules, and ML."""

    CAREER_DATA = {
        "Coding": {
            "roles": ["Software Engineer", "Backend Developer", "Systems Programmer"],
            "freelancing": ["API development", "automation scripts", "bug fixing"],
            "remote": ["Backend Engineer", "Platform Engineer", "Software Developer"],
            "startup": ["MVP builder", "Technical co-founder", "Product engineer"],
            "tools": ["Python", "Git", "Docker", "Linux", "Testing"],
            "salary_range": "$70k-$180k",
            "market_demand": 9.5,
            "future_growth": 9.4,
            "certifications": ["AWS Certified Developer", "Microsoft Azure Developer", "Oracle Java"],
        },
        "Web Development": {
            "roles": ["Frontend Developer", "Full Stack Developer", "Web Architect"],
            "freelancing": ["Landing pages", "e-commerce sites", "web apps"],
            "remote": ["Frontend Engineer", "UI Engineer", "Web Developer"],
            "startup": ["Rapid website delivery", "SaaS MVPs", "growth engineering"],
            "tools": ["HTML/CSS", "JavaScript", "React", "Node.js", "Figma"],
            "salary_range": "$60k-$160k",
            "market_demand": 9.2,
            "future_growth": 9.0,
            "certifications": ["Meta Front-End Developer", "Google UX Design", "freeCodeCamp"],
        },
        "Game Development": {
            "roles": ["Game Developer", "Gameplay Programmer", "Technical Artist"],
            "freelancing": ["Prototype development", "game systems", "tooling"],
            "remote": ["Unity Developer", "Unreal Developer", "Gameplay Engineer"],
            "startup": ["Indie studio founder", "mobile games", "VR/AR experiences"],
            "tools": ["Unity", "Unreal Engine", "Blender", "C#", "C++"],
            "salary_range": "$50k-$150k",
            "market_demand": 7.5,
            "future_growth": 7.9,
            "certifications": ["Unity Certified Developer", "Unreal Authorized Instructor"],
        },
        "Cybersecurity": {
            "roles": ["Security Analyst", "Penetration Tester", "Security Engineer"],
            "freelancing": ["Vulnerability assessment", "security audits", "hardening"],
            "remote": ["Security Operations", "SOC Analyst", "Cloud Security"],
            "startup": ["Security tools", "privacy products", "compliance services"],
            "tools": ["Wireshark", "Nmap", "Burp Suite", "Linux", "SIEM"],
            "salary_range": "$80k-$200k",
            "market_demand": 9.7,
            "future_growth": 9.6,
            "certifications": ["CompTIA Security+", "CEH", "OSCP", "CISSP"],
        },
        "Data Science": {
            "roles": ["Data Scientist", "ML Engineer", "Data Analyst"],
            "freelancing": ["dashboards", "forecasting", "automation analytics"],
            "remote": ["Analytics Engineer", "Data Scientist", "ML Engineer"],
            "startup": ["AI insights", "prediction products", "recommendation systems"],
            "tools": ["Python", "Pandas", "NumPy", "SQL", "Power BI"],
            "salary_range": "$75k-$190k",
            "market_demand": 9.4,
            "future_growth": 9.5,
            "certifications": ["Google Data Analytics", "IBM Data Science", "Microsoft Data Analyst"],
        },
        "Mobile Development": {
            "roles": ["iOS Developer", "Android Developer", "Mobile Engineer"],
            "freelancing": ["mobile apps", "cross-platform apps", "app modernization"],
            "remote": ["Mobile Engineer", "Flutter Developer", "Android/iOS Developer"],
            "startup": ["consumer apps", "mobile-first SaaS", "subscription apps"],
            "tools": ["Swift", "Kotlin", "Flutter", "React Native", "Firebase"],
            "salary_range": "$65k-$175k",
            "market_demand": 8.8,
            "future_growth": 8.9,
            "certifications": ["Google Associate Android Developer", "Apple Swift"],
        },
        "Cloud Computing": {
            "roles": ["Cloud Engineer", "DevOps Engineer", "SRE"],
            "freelancing": ["infrastructure automation", "deployment pipelines", "cloud migrations"],
            "remote": ["Platform Engineer", "DevOps", "Cloud Architect"],
            "startup": ["infra tooling", "FinOps", "scalable SaaS"],
            "tools": ["AWS", "Azure", "GCP", "Docker", "Kubernetes"],
            "salary_range": "$85k-$210k",
            "market_demand": 9.6,
            "future_growth": 9.6,
            "certifications": ["AWS Solutions Architect", "Azure Admin", "CKA"],
        },
        "AI & Machine Learning": {
            "roles": ["ML Engineer", "AI Researcher", "Applied Scientist"],
            "freelancing": ["LLM apps", "automation", "predictive models"],
            "remote": ["ML Engineer", "AI Engineer", "Applied Scientist"],
            "startup": ["AI copilots", "recommendation systems", "data products"],
            "tools": ["Python", "PyTorch", "TensorFlow", "scikit-learn", "LangChain"],
            "salary_range": "$90k-$240k",
            "market_demand": 10.0,
            "future_growth": 10.0,
            "certifications": ["DeepLearning.AI", "Google ML Engineer", "TensorFlow Developer"],
        },
        "Physical Games / Sports": {
            "roles": ["Athlete", "Coach", "Sports Scientist"],
            "freelancing": ["training plans", "coaching", "fitness consulting"],
            "remote": ["sports analytics", "online coaching", "fitness content"],
            "startup": ["fitness communities", "sports performance", "health products"],
            "tools": ["sports analytics", "wearables", "video analysis", "nutrition tracking"],
            "salary_range": "$35k-$120k+",
            "market_demand": 7.2,
            "future_growth": 7.8,
            "certifications": ["NASM", "ACE", "Sports coaching certification"],
        },
    }

    DOMAIN_ROADMAPS = {
        "Coding": {
            "Beginner": ["Python syntax", "control flow", "functions", "debugging basics"],
            "Intermediate": ["OOP", "data structures", "testing", "APIs"],
            "Advanced": ["system design", "performance", "architecture", "scalability"],
        },
        "Web Development": {
            "Beginner": ["HTML", "CSS", "JavaScript", "responsive design"],
            "Intermediate": ["React", "APIs", "auth", "state management"],
            "Advanced": ["architecture", "testing", "performance", "deployment"],
        },
        "Data Science": {
            "Beginner": ["statistics", "Python", "EDA", "visualization"],
            "Intermediate": ["SQL", "feature engineering", "ML basics", "model evaluation"],
            "Advanced": ["deep learning", "MLOps", "big data", "experimentation"],
        },
        "AI & Machine Learning": {
            "Beginner": ["Python", "math fundamentals", "ML concepts", "datasets"],
            "Intermediate": ["supervised learning", "neural networks", "NLP", "CV"],
            "Advanced": ["LLMs", "RAG", "optimization", "deployment"],
        },
    }

    def __init__(self, repository: Optional[LearningPathRepository] = None):
        self.repository = repository or LearningPathRepository()
        self._model_bundle = None
        self._model_labels: List[str] = []

    # -------------------------------
    # public API
    # -------------------------------
    def analyze_user(self, payload: Dict[str, Any]) -> AdvancedResult:
        user_id = payload.get("user_id")
        explicit = self._normalize_explicit_scores(payload.get("scores") or payload.get("interest_scores") or {})
        profile_inputs = payload.get("user", {})
        if profile_inputs and user_id:
            self.repository.upsert_user(user_id, profile_inputs)

        signals = self._collect_signals(explicit, profile_inputs, payload)
        combined = self._score_domains(signals)
        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)

        profile = self._classify_profile(ranked, signals)
        top_domains = self._build_top_domain_payload(ranked, signals, profile_inputs)
        roadmap = self.build_roadmap(top_domains[0]["domain"], signals, payload)
        career_paths = self.build_career_intelligence(top_domains)
        skills_gap = self._build_skills_gap(top_domains, signals)
        projects = self._build_projects(top_domains)
        certifications = self._build_certifications(top_domains)
        gamification = self._build_gamification(signals, top_domains)
        visuals = self._build_visual_analytics(top_domains, profile_inputs)

        result = AdvancedResult(
            user_profile=profile["profile"],
            top_domains=top_domains,
            confidence_scores={domain: round(score, 2) for domain, score in combined.items()},
            roadmap=roadmap,
            career_paths=career_paths,
            skills_gap=skills_gap,
            projects=projects,
            certifications=certifications,
            gamification=gamification,
            visual_analytics=visuals,
            raw_signals=signals,
            metadata={
                "version": "3.0",
                "generated_at": datetime.utcnow().isoformat(),
                "model": self._model_bundle["name"] if self._model_bundle else "weighted-hybrid",
            },
        )

        if user_id:
            self.repository.save_assessment(user_id, payload, signals, result.to_dict())
            self.repository.save_prediction(user_id, top_domains[0]["domain"], result.to_dict(), result.confidence_scores, top_domains)
            self.repository.save_roadmap(user_id, top_domains[0]["domain"], roadmap, career_paths)
            self.repository.save_progress(
                user_id,
                top_domains[0]["domain"],
                gamification["xp"],
                gamification["level"],
                gamification["streak_days"],
                gamification["weekly_progress_score"],
                gamification["achievements"],
            )

        return result

    def predict_interest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.analyze_user(payload)
        top = result.top_domains[0]
        return {
            "user_profile": result.user_profile,
            "top_domains": result.top_domains,
            "primary_interest": top["domain"],
            "predicted_interest": top["domain"],
            "confidence": round(top["confidence"], 4),
            "model_confidence": round(top["model_confidence"], 4),
            "all_probabilities": result.confidence_scores,
            "top_3_interests": result.top_domains[:3],
            "top_2_interests": result.top_domains[:2],
            "roadmap": result.roadmap,
            "career_paths": result.career_paths,
            "skills_gap": result.skills_gap,
            "projects": result.projects,
            "certifications": result.certifications,
            "gamification": result.gamification,
            "visual_analytics": result.visual_analytics,
            "signals": result.raw_signals,
            "metadata": result.metadata,
        }

    def get_recommendations(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.analyze_user(payload)
        insights = [self._insight_for_domain(item["domain"], result.raw_signals, result.confidence_scores) for item in result.top_domains[:3]]
        return {
            "user_profile": result.user_profile,
            "top_domains": [item["domain"] for item in result.top_domains[:3]],
            "confidence_scores": result.confidence_scores,
            "recommendations": [insight.to_dict() for insight in insights],
            "roadmap": result.roadmap,
            "career_paths": result.career_paths,
            "skills_gap": result.skills_gap,
            "projects": result.projects,
            "certifications": result.certifications,
            "gamification": result.gamification,
        }

    def generate_roadmap(self, domain: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        signals = self._collect_signals(self._normalize_explicit_scores(payload.get("scores") or {}), payload.get("user", {}), payload)
        roadmap = self.build_roadmap(domain, signals, payload)
        career = self._career_payload(domain)
        return {
            "domain": domain,
            "roadmap": roadmap,
            "career_paths": career,
            "skills_gap": self._roadmap_skill_gap(domain, signals),
        }

    def get_user_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.analyze_user(payload)
        return {
            "user_profile": result.user_profile,
            "top_domains": result.top_domains,
            "confidence_scores": result.confidence_scores,
            "gamification": result.gamification,
            "metadata": result.metadata,
        }

    def save_progress(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
        domain = payload.get("domain") or payload.get("primary_interest")
        if not domain:
            raise ValueError("domain is required")
        xp = int(payload.get("xp", 0))
        level = int(payload.get("level", 1))
        streak = int(payload.get("streak_days", 0))
        weekly = float(payload.get("weekly_progress_score", 0))
        achievements = payload.get("achievements", [])
        self.repository.save_progress(user_id, domain, xp, level, streak, weekly, achievements)
        return {"success": True, "user_id": user_id, "domain": domain}

    # -------------------------------
    # signal collection and scoring
    # -------------------------------
    def _normalize_explicit_scores(self, scores: Dict[str, Any]) -> Dict[str, float]:
        normalized = {}
        for domain in DOMAINS:
            try:
                normalized[domain] = float(scores.get(domain, 5.0))
            except (TypeError, ValueError):
                normalized[domain] = 5.0
        return normalized

    def _collect_signals(self, explicit: Dict[str, float], user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        text_blob = " ".join(
            str(user.get(key, "")) for key in ["known", "want", "goals", "learning_goals", "bio"]
        ).lower()
        text_blob += " " + " ".join(str(v) for v in payload.get("text_inputs", {}).values()).lower()

        nlp = self._nlp_signal_scores(text_blob)
        behavioral = self._behavioral_signal_scores(payload.get("behavioral_data", {}))
        skills = self._skills_signal_scores(user)
        goals = self._goal_signal_scores(user)
        learning_style = self._learning_style_scores(user)
        time_availability = self._time_scores(user)
        personality = self._personality_scores(payload.get("personality", user.get("personality")))
        confidence = self._confidence_scores(payload.get("confidence_level"), user)
        motivation = self._motivation_scores(payload)

        return asdict(
            SignalSummary(
                explicit=explicit,
                behavioral=behavioral,
                nlp=nlp,
                skills=skills,
                goals=goals,
                learning_style=learning_style,
                time_availability=time_availability,
                personality=personality,
                confidence=confidence,
                motivation=motivation,
            )
        )

    def _nlp_signal_scores(self, text: str) -> Dict[str, float]:
        scores = {domain: 0.0 for domain in DOMAINS}
        if not text:
            return scores
        for domain, keywords in NLP_KEYWORDS.items():
            hit_count = 0
            for keyword in keywords:
                if keyword in text:
                    hit_count += 1
            scores[domain] += min(10.0, hit_count * 2.2)

        # simple phrase patterns
        if re.search(r"build\s+website|create\s+website|design\s+website", text):
            scores["Web Development"] += 3.5
            scores["Coding"] += 1.0
        if re.search(r"solve\s+problems|problem\s+solving|logic", text):
            scores["Coding"] += 3.0
        if re.search(r"secure\s+systems|protect\s+systems|cyber", text):
            scores["Cybersecurity"] += 4.0
        if re.search(r"data\s+analysis|analyze\s+data|predict", text):
            scores["Data Science"] += 4.0
        if re.search(r"machine\s+learning|ai|artificial\s+intelligence", text):
            scores["AI & Machine Learning"] += 4.5
        return scores

    def _behavioral_signal_scores(self, behavioral_data: Dict[str, Any]) -> Dict[str, float]:
        scores = {domain: 0.0 for domain in DOMAINS}
        for domain in DOMAINS:
            data = behavioral_data.get(domain, {}) if isinstance(behavioral_data, dict) else {}
            time_spent = float(data.get("time_spent_minutes", data.get("time_spent_seconds", 0) / 60 if data.get("time_spent_seconds") else 0))
            quiz_perf = float(data.get("quiz_performance", data.get("completion_rate", 0)))
            click_frequency = float(data.get("click_frequency", 0))
            repeat = float(data.get("repeat_selection", data.get("return_visits", 0)))
            scores[domain] = min(10.0, (time_spent / 15.0) + (quiz_perf * 0.35) + (click_frequency * 0.15) + (repeat * 0.2))
        return scores

    def _skills_signal_scores(self, user: Dict[str, Any]) -> Dict[str, float]:
        current_skills = " ".join(user.get("current_skills", []) or []).lower()
        return self._nlp_signal_scores(current_skills)

    def _goal_signal_scores(self, user: Dict[str, Any]) -> Dict[str, float]:
        goal_text = " ".join(user.get("learning_goals", []) or user.get("goals", []) or []).lower()
        return self._nlp_signal_scores(goal_text)

    def _learning_style_scores(self, user: Dict[str, Any]) -> Dict[str, float]:
        style = str(user.get("learning_style", user.get("learningStyle", user.get("contentFormat", "")))).lower()
        scores = {domain: 0.0 for domain in DOMAINS}
        if "project" in style:
            scores["Web Development"] += 1.2
            scores["Coding"] += 1.0
            scores["AI & Machine Learning"] += 1.0
        if "visual" in style:
            scores["Game Development"] += 1.0
            scores["Web Development"] += 0.7
        if "self" in style or "paced" in style:
            scores["Data Science"] += 0.8
            scores["Cloud Computing"] += 0.8
        if "hands-on" in style or "practical" in style:
            scores["Cybersecurity"] += 1.0
        return scores

    def _time_scores(self, user: Dict[str, Any]) -> Dict[str, float]:
        hours = float(user.get("weekly_availability_hours", user.get("time_availability", 5) or 5))
        scores = {domain: 0.0 for domain in DOMAINS}
        if hours >= 10:
            scores["Data Science"] += 0.8
            scores["AI & Machine Learning"] += 1.0
            scores["Cloud Computing"] += 0.7
        elif hours <= 4:
            scores["Web Development"] += 0.6
            scores["Mobile Development"] += 0.6
        return scores

    def _personality_scores(self, personality: Any) -> Dict[str, float]:
        scores = {domain: 0.0 for domain in DOMAINS}
        p = str(personality or "").lower()
        if any(x in p for x in ["analytical", "logical"]):
            scores["Data Science"] += 1.0
            scores["Cybersecurity"] += 0.7
        if any(x in p for x in ["creative", "design", "maker"]):
            scores["Web Development"] += 1.0
            scores["Game Development"] += 1.0
        if any(x in p for x in ["leader", "entrepreneur", "business"]):
            scores["Cloud Computing"] += 0.7
            scores["AI & Machine Learning"] += 0.8
        if any(x in p for x in ["athletic", "competitive", "coach"]):
            scores["Physical Games / Sports"] += 1.5
        return scores

    def _confidence_scores(self, confidence_level: Any, user: Dict[str, Any]) -> Dict[str, float]:
        value = confidence_level if confidence_level is not None else user.get("confidence_level", 0.7)
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.7
        return {domain: confidence for domain in DOMAINS}

    def _motivation_scores(self, payload: Dict[str, Any]) -> Dict[str, float]:
        motivational = str(payload.get("motivation", payload.get("motive", ""))).lower()
        scores = {domain: 0.0 for domain in DOMAINS}
        if any(x in motivational for x in ["job", "career", "remote", "freelance"]):
            scores["Coding"] += 0.7
            scores["Web Development"] += 0.7
            scores["Cloud Computing"] += 0.7
        if any(x in motivational for x in ["research", "learn", "understand"]):
            scores["Data Science"] += 0.8
            scores["AI & Machine Learning"] += 1.0
        if any(x in motivational for x in ["build", "create", "ship"]):
            scores["Game Development"] += 0.6
            scores["Mobile Development"] += 0.6
            scores["Web Development"] += 0.6
        return scores

    def _score_domains(self, signals: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        weights = {
            "explicit": 0.30,
            "behavioral": 0.18,
            "nlp": 0.18,
            "skills": 0.10,
            "goals": 0.10,
            "learning_style": 0.05,
            "time_availability": 0.03,
            "personality": 0.03,
            "confidence": 0.02,
            "motivation": 0.01,
        }

        scores: Dict[str, float] = {domain: 0.0 for domain in DOMAINS}
        for domain in DOMAINS:
            for signal_name, signal_scores in signals.items():
                scores[domain] += signal_scores.get(domain, 0.0) * weights[signal_name]

        # normalize to 0-100 using a ceiling based on possible max contributions
        max_possible = 10.0 * sum(weights.values())
        return {domain: round(min(100.0, (value / max_possible) * 100.0), 2) for domain, value in scores.items()}

    # -------------------------------
    # profiles, recommendations, roadmap
    # -------------------------------
    def _classify_profile(self, ranked: List[Tuple[str, float]], signals: Dict[str, Any]) -> Dict[str, Any]:
        top_domain = ranked[0][0]
        top_score = ranked[0][1]
        label_scores: Dict[str, float] = {}
        for label, domains in PROFILE_LABELS.items():
            label_scores[label] = sum(1 for d in domains if d == top_domain or d in [x[0] for x in ranked[:3]])
        if top_score < 35:
            profile = "Beginner"
        else:
            profile = max(label_scores.items(), key=lambda x: x[1])[0]
        # Guardrail: ensure profile is in the product spec list.
        allowed = {"Beginner", "Explorer", "Builder", "Analyst", "Creator", "Researcher", "Hacker", "Athlete", "Advanced Learner"}
        if profile not in allowed:
            profile = "Explorer"
        return {"profile": profile, "confidence": round(min(1.0, 0.45 + top_score / 150), 2), "label_scores": label_scores}

    def _build_top_domain_payload(self, ranked: List[Tuple[str, float]], signals: Dict[str, Any], user: Dict[str, Any]) -> List[Dict[str, Any]]:
        top = []
        for domain, score in ranked[:3]:
            insight = self._insight_for_domain(domain, signals, dict(ranked))
            top.append({
                "domain": domain,
                "score": round(score, 2),
                "percent": round(score, 1),
                "confidence": round(min(0.99, 0.45 + score / 120), 4),
                "model_confidence": round(min(0.99, 0.55 + score / 130), 4),
                "why_matched": insight.why_matched,
                "skills_gap": insight.skills_gap,
                "fastest_path": insight.fastest_path,
                "best_courses": insight.best_courses,
                "best_projects": insight.best_projects,
                "best_certifications": insight.best_certifications,
                "community_resources": insight.community_resources,
                "career_paths": insight.career_paths,
            })
        return top

    def _insight_for_domain(self, domain: str, signals: Dict[str, Any], confidence_lookup: Dict[str, Any]) -> LearningInsight:
        career = self._career_payload(domain)
        why = self._explain_domain_match(domain, signals)
        skills_gap = self._estimate_skill_gap(domain, signals)
        roadmap = self.DOMAIN_ROADMAPS.get(domain, {})
        fastest_path = f"Start with {', '.join(roadmap.get('Beginner', ['foundations'])[:3])}."
        return LearningInsight(
            domain=domain,
            match_score=float(confidence_lookup.get(domain, 0.0) if isinstance(confidence_lookup, dict) else 0.0),
            match_percent=float(confidence_lookup.get(domain, 0.0) if isinstance(confidence_lookup, dict) else 0.0),
            why_matched=why,
            skills_gap=skills_gap,
            fastest_path=fastest_path,
            best_courses=self._best_courses(domain),
            best_projects=self._best_projects(domain),
            best_certifications=career["certifications"],
            community_resources=self._community_resources(domain),
            career_paths=career,
        )

    def _explain_domain_match(self, domain: str, signals: Dict[str, Any]) -> List[str]:
        reasons = []
        if signals["explicit"].get(domain, 0) >= 7:
            reasons.append("high explicit interest rating")
        if signals["nlp"].get(domain, 0) >= 2:
            reasons.append("text inputs strongly match this domain")
        if signals["skills"].get(domain, 0) >= 1:
            reasons.append("existing skills align well")
        if signals["goals"].get(domain, 0) >= 1:
            reasons.append("goals indicate this direction")
        if signals["behavioral"].get(domain, 0) >= 1:
            reasons.append("behavioral engagement supports it")
        return reasons or ["balanced multi-signal alignment"]

    def _estimate_skill_gap(self, domain: str, signals: Dict[str, Any]) -> List[str]:
        base = {
            "Coding": ["data structures", "debugging", "testing"],
            "Web Development": ["responsive design", "APIs", "state management"],
            "Game Development": ["game loops", "3D math", "optimization"],
            "Cybersecurity": ["networking", "linux", "threat modeling"],
            "Data Science": ["statistics", "SQL", "feature engineering"],
            "Mobile Development": ["state management", "platform SDKs", "deployment"],
            "Cloud Computing": ["IaC", "kubernetes", "observability"],
            "AI & Machine Learning": ["math foundations", "model deployment", "LLM tooling"],
            "Physical Games / Sports": ["conditioning", "training plans", "leadership"],
        }
        return base.get(domain, ["foundations", "practice", "projects"])

    def _build_skills_gap(self, top_domains: List[Dict[str, Any]], signals: Dict[str, Any]) -> Dict[str, Any]:
        return {
            item["domain"]: {
                "gaps": self._estimate_skill_gap(item["domain"], signals),
                "priority": "high" if item["score"] > 70 else "medium",
                "fastest_path": item["fastest_path"],
            }
            for item in top_domains
        }

    def _build_projects(self, top_domains: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        projects = []
        for item in top_domains:
            for project in self._best_projects(item["domain"]):
                projects.append({"domain": item["domain"], "project": project, "difficulty": "progressive"})
        return projects[:9]

    def _build_certifications(self, top_domains: List[Dict[str, Any]]) -> List[str]:
        certs = []
        for item in top_domains:
            certs.extend(self.CAREER_DATA[item["domain"]]["certifications"])
        seen = []
        for cert in certs:
            if cert not in seen:
                seen.append(cert)
        return seen[:10]

    def _build_gamification(self, signals: Dict[str, Any], top_domains: List[Dict[str, Any]]) -> Dict[str, Any]:
        score = top_domains[0]["score"] if top_domains else 0.0
        xp = int(round(score * 12))
        level = max(1, int(math.sqrt(max(0, xp) / 75)) + 1)
        streak = 7 if score > 70 else 3 if score > 45 else 1
        weekly = min(100.0, score * 0.9)
        badges = []
        if score >= 85:
            badges.append("Pathfinder Gold")
        if score >= 70:
            badges.append("Momentum Builder")
        if score >= 55:
            badges.append("Consistency Streak")
        return {
            "level": level,
            "xp": xp,
            "achievements": badges,
            "weekly_progress_score": round(weekly, 2),
            "streak_days": streak,
        }

    def _build_visual_analytics(self, top_domains: List[Dict[str, Any]], user: Dict[str, Any]) -> Dict[str, str]:
        base_dir = os.getenv("LEARNING_PATH_OUTPUT_DIR") or os.path.join(os.path.dirname(self.repository.db_path), "visuals")
        output_dir = base_dir
        user_name = user.get("name") or user.get("full_name") or user.get("email") or "student"
        scores = {item["domain"]: item["score"] for item in top_domains}
        history = [{"domain": item["domain"], "score": item["score"]} for item in top_domains]
        heatmap_labels = list(scores.keys()) or ["Domain"]
        matrix = [[abs(scores.get(a, 0) - scores.get(b, 0)) for b in heatmap_labels] for a in heatmap_labels]
        heatmap_matrix = np.array(matrix if matrix else [[0]])
        paths = {
            "radar": generate_radar_chart(scores or {"Domain": 0.0}, user_name, output_dir),
            "growth": generate_growth_graph(history, user_name, output_dir),
            "heatmap": generate_skill_heatmap(heatmap_matrix.tolist(), heatmap_labels, user_name, output_dir),
            "comparison": generate_domain_comparison(scores or {"Domain": 0.0}, user_name, output_dir),
        }
        return paths

    def _career_payload(self, domain: str) -> Dict[str, Any]:
        data = self.CAREER_DATA.get(domain, self.CAREER_DATA["Coding"])
        return {
            "roles": data["roles"],
            "freelancing": data["freelancing"],
            "remote_jobs": data["remote"],
            "startup_opportunities": data["startup"],
            "required_tools": data["tools"],
            "salary_range": data["salary_range"],
            "market_demand": data["market_demand"],
            "future_growth_score": data["future_growth"],
            "certifications": data["certifications"],
        }

    def _best_courses(self, domain: str) -> List[str]:
        return {
            "Coding": ["CS50", "Python for Everybody", "Automate the Boring Stuff"],
            "Web Development": ["The Odin Project", "MDN Web Docs", "Frontend Masters"],
            "Game Development": ["Unity Learn", "Unreal Engine Courses", "GameDev.tv"],
            "Cybersecurity": ["TryHackMe", "PortSwigger Academy", "HTB Academy"],
            "Data Science": ["Kaggle Learn", "Google Data Analytics", "fast.ai"],
            "Mobile Development": ["Flutter Docs", "Android Developer", "Stanford iOS"],
            "Cloud Computing": ["AWS Skill Builder", "Kubernetes.io", "DevOps Roadmap"],
            "AI & Machine Learning": ["DeepLearning.AI", "fast.ai", "Hugging Face Course"],
            "Physical Games / Sports": ["Sports coaching basics", "Athletic performance", "Strength programming"],
        }.get(domain, ["Structured online course", "project-based learning"])

    def _best_projects(self, domain: str) -> List[str]:
        return {
            "Coding": ["CLI task manager", "automation bot", "REST API service"],
            "Web Development": ["portfolio site", "dashboard", "e-commerce storefront"],
            "Game Development": ["2D platformer", "puzzle game", "game AI prototype"],
            "Cybersecurity": ["home lab", "vulnerability scanner", "security playbook"],
            "Data Science": ["EDA dashboard", "forecast model", "recommendation notebook"],
            "Mobile Development": ["habit tracker", "weather app", "expense app"],
            "Cloud Computing": ["CI/CD pipeline", "serverless app", "k8s deployment"],
            "AI & Machine Learning": ["chatbot", "image classifier", "LLM app"],
            "Physical Games / Sports": ["training plan app", "performance tracker", "coach dashboard"],
        }.get(domain, ["small project", "portfolio project"])

    def _community_resources(self, domain: str) -> List[str]:
        return {
            "Coding": ["GitHub", "Stack Overflow", "freeCodeCamp"],
            "Web Development": ["DEV Community", "MDN", "Frontend Mentor"],
            "Game Development": ["r/gamedev", "Unity Discord", "Unreal forums"],
            "Cybersecurity": ["OWASP", "TryHackMe Discord", "Hack The Box"],
            "Data Science": ["Kaggle", "DataTalks.Club", "Towards Data Science"],
            "Mobile Development": ["Flutter Community", "Android Developers", "Apple Dev Forums"],
            "Cloud Computing": ["AWS Community", "Kubernetes Slack", "DevOps Subreddit"],
            "AI & Machine Learning": ["Hugging Face", "MLOps Community", "Papers with Code"],
            "Physical Games / Sports": ["local clubs", "sports federation", "coach communities"],
        }.get(domain, ["Discord communities", "LinkedIn groups", "YouTube creators"])

    def build_roadmap(self, domain: str, signals: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        base = self.DOMAIN_ROADMAPS.get(domain, self.DOMAIN_ROADMAPS["Coding"])
        weekly_hours = float(
            (payload.get("user") or {}).get("weekly_availability_hours")
            or payload.get("weekly_availability_hours")
            or 6
        )
        weekly_hours = max(1.0, min(40.0, weekly_hours))

        # Build tiered roadmaps
        beginner = base.get("Beginner", ["foundations", "practice", "first project"])
        intermediate = base.get("Intermediate", ["core concepts", "projects", "review"])
        advanced = base.get("Advanced", ["architecture", "optimization", "deployment"])

        # Suggested projects & resources are already curated in helper methods
        projects = self._best_projects(domain)
        resources = {
            "courses": self._best_courses(domain),
            "community": self._community_resources(domain),
        }
        career = self._career_payload(domain)
        skill_gaps = self._estimate_skill_gap(domain, signals)

        # Simple pacing model
        sessions_per_week = max(2, int(round(weekly_hours / 2.5)))
        session_minutes = int(round((weekly_hours * 60) / sessions_per_week))
        weekly_plan = {
            "hours_per_week": weekly_hours,
            "sessions_per_week": sessions_per_week,
            "minutes_per_session": max(30, min(120, session_minutes)),
            "cadence": "project-first" if (signals.get("learning_style") or {}).get(domain, 0) > 0.5 else "mixed",
        }

        # Build timeboxed plans
        plan_30 = [{"week": w + 1, "focus": beginner[min(w, len(beginner) - 1)], "deliverable": projects[min(w, len(projects) - 1)]} for w in range(4)]
        plan_90 = [{"week": w + 1, "focus": intermediate[min(w // 2, len(intermediate) - 1)], "deliverable": projects[min(w // 3, len(projects) - 1)]} for w in range(12)]
        plan_365 = [
            {"month": 1, "focus": "Foundations + first portfolio piece"},
            {"month": 2, "focus": "Core concepts + repeat practice loops"},
            {"month": 3, "focus": "Intermediate projects + testing habits"},
            {"month": 4, "focus": "Deployment + performance + collaboration"},
            {"month": 5, "focus": "Advanced topics + specialization"},
            {"month": 6, "focus": "Capstone build + interview prep"},
            {"month": 9, "focus": "Real-world delivery + open-source / freelancing"},
            {"month": 12, "focus": "Career-ready mastery + certifications"},
        ]

        return {
            "beginner": {"topics": beginner, "duration_days": 30, "milestones": ["first project shipped", "baseline quiz passed", "habit formed"]},
            "intermediate": {"topics": intermediate, "duration_days": 90, "milestones": ["3 projects", "debugging fluency", "job-ready patterns"]},
            "advanced": {"topics": advanced, "duration_days": 365, "milestones": ["capstone", "performance + architecture", "portfolio + interview readiness"]},
            "plans": {
                "30_day": plan_30,
                "90_day": plan_90,
                "1_year": plan_365,
            },
            "weekly_study_plan": weekly_plan,
            "suggested_projects": projects,
            "certifications": career.get("certifications", []),
            "resources": resources,
            "career_paths": career.get("roles", []),
            "skill_gaps": skill_gaps,
        }

    def build_career_intelligence(self, top_domains: List[Dict[str, Any]]) -> Dict[str, Any]:
        out = {}
        for item in top_domains:
            out[item["domain"]] = self._career_payload(item["domain"])
        return out


def build_response_payload(result: AdvancedResult) -> Dict[str, Any]:
    top_domain = result.top_domains[0]["domain"] if result.top_domains else None
    return {
        "user_profile": result.user_profile,
        "top_domains": result.top_domains,
        "confidence_scores": result.confidence_scores,
        "roadmap": result.roadmap,
        "career_paths": result.career_paths,
        "skills_gap": result.skills_gap,
        "projects": result.projects,
        "certifications": result.certifications,
        "gamification": result.gamification,
        "visual_analytics": result.visual_analytics,
        "primary_interest": top_domain,
        "metadata": result.metadata,
    }
