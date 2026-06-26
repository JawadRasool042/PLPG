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
from utils.market_context import align_careers_to_user_progress, market_metadata, normalize_careers_for_market

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

# Normalize API / UI labels to DOMAINS keys (avoids silent fallback to Coding roadmap).
DOMAIN_ALIASES: Dict[str, str] = {
    "coding": "Coding",
    "web development": "Web Development",
    "web dev": "Web Development",
    "game development": "Game Development",
    "game dev": "Game Development",
    "cybersecurity": "Cybersecurity",
    "cyber security": "Cybersecurity",
    "data science": "Data Science",
    "mobile development": "Mobile Development",
    "mobile dev": "Mobile Development",
    "cloud computing": "Cloud Computing",
    "cloud": "Cloud Computing",
    "ai & machine learning": "AI & Machine Learning",
    "ai/ml": "AI & Machine Learning",
    "machine learning": "AI & Machine Learning",
    "artificial intelligence": "AI & Machine Learning",
    "physical games / sports": "Physical Games / Sports",
    "physical games": "Physical Games / Sports",
    "physical sports": "Physical Games / Sports",
    "sports": "Physical Games / Sports",
    "fitness": "Physical Games / Sports",
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

    def __init__(self, repository: Optional[LearningPathRepository] = None):
        self.repository = repository or LearningPathRepository()
        self._model_bundle = None
        self._model_labels: List[str] = []

    def _canonical_domain(self, domain: Optional[str]) -> str:
        """Map free-text or alias labels to a DOMAINS key so roadmaps never default to Coding by accident."""
        if not domain:
            return "Coding"
        raw = str(domain).strip()
        if raw in DOMAINS:
            return raw
        key = raw.lower()
        if key in DOMAIN_ALIASES:
            return DOMAIN_ALIASES[key]
        for d in DOMAINS:
            if d.lower() == key:
                return d
        return raw

    @staticmethod
    def _duration_weeks_label(days: int) -> str:
        """Human-readable week range for roadmap cards (UI 'Duration: X-Y weeks')."""
        try:
            d = int(days)
        except (TypeError, ValueError):
            d = 0
        if d <= 0:
            return "4-6 weeks"
        w = d / 7.0
        lo = max(2, int(round(w * 0.78)))
        hi = max(lo + 1, int(round(w * 1.22)))
        hi = min(hi, lo + 10)
        return f"{lo}-{hi} weeks"

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
        primary_domain = top_domains[0]["domain"] if top_domains else self._canonical_domain(DOMAINS[0])

        path_result = self.generate_roadmap(primary_domain, payload)
        roadmap = path_result.get("roadmap") or {}
        careers_detailed = path_result.get("careers_detailed") or []
        career_paths = {primary_domain: path_result.get("career_paths") or {"roles": [c.get("title") for c in careers_detailed if c.get("title")]}}
        courses = ((roadmap.get("resources") or {}).get("courses") or [])
        projects_list = roadmap.get("suggested_projects") or []
        if top_domains:
            top_domains[0]["best_courses"] = courses[:8]
            top_domains[0]["best_projects"] = projects_list[:6]
            top_domains[0]["career_paths"] = career_paths.get(primary_domain, {})
            basic_topics = (roadmap.get("basic") or roadmap.get("beginner") or {}).get("topics") or []
            if basic_topics:
                top_domains[0]["fastest_path"] = f"Start with {', '.join(basic_topics[:3])}."

        skills_gap = self._build_skills_gap(top_domains, signals)
        projects = [
            {"domain": primary_domain, "project": project, "difficulty": "progressive"}
            for project in projects_list[:9]
        ]
        certifications: List[str] = []
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
                "careers_detailed": careers_detailed,
                "source": "openai+ml",
            },
        )

        if user_id:
            self.repository.save_assessment(user_id, payload, signals, result.to_dict())
            self.repository.save_prediction(user_id, top_domains[0]["domain"], result.to_dict(), result.confidence_scores, top_domains)
            self.repository.save_roadmap(user_id, primary_domain, roadmap, career_paths)
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

    def score_interests_only(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast interest scoring from explicit ratings + signals only.
        Skips OpenAI roadmap/career generation (use generate_roadmap for that).
        """
        explicit = self._normalize_explicit_scores(
            payload.get("scores") or payload.get("interest_scores") or {}
        )
        profile_inputs = payload.get("user", {}) or {}
        signals = self._collect_signals(explicit, profile_inputs, payload)
        combined = self._score_domains(signals)
        ranked = sorted(combined.items(), key=lambda item: item[1], reverse=True)
        profile = self._classify_profile(ranked, signals)
        top_domains = self._build_top_domain_payload(ranked, signals, profile_inputs)
        top = top_domains[0] if top_domains else {
            "domain": self._canonical_domain(DOMAINS[0]),
            "confidence": 0.0,
            "model_confidence": 0.0,
        }
        return {
            "user_profile": profile["profile"],
            "top_domains": top_domains,
            "primary_interest": top["domain"],
            "predicted_interest": top["domain"],
            "confidence": round(float(top.get("confidence", 0.0)), 4),
            "model_confidence": round(float(top.get("model_confidence", 0.0)), 4),
            "all_probabilities": {domain: round(score, 2) for domain, score in combined.items()},
            "top_3_interests": top_domains[:3],
            "top_2_interests": top_domains[:2],
            "signals": signals,
            "metadata": {
                "version": "3.0",
                "generated_at": datetime.utcnow().isoformat(),
                "source": "fast-scoring",
                "careers_detailed": [],
            },
        }

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
            "careers_detailed": result.metadata.get("careers_detailed") or [],
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

    def _extract_resume_terms(self, user: Dict[str, Any]) -> List[str]:
        text = " ".join(
            str(user.get(key, "") or "")
            for key in ["known", "want", "goals", "learning_goals", "career_goals", "bio"]
        ).strip()
        parts = re.split(r"[,;/\n]+", text.lower()) if text else []
        base = list(dict.fromkeys([p.strip() for p in parts if p.strip()]))
        extra = user.get("assessment_tags") or user.get("assessmentTags") or []
        if isinstance(extra, str):
            extra = [x.strip().lower() for x in extra.split(",") if x.strip()]
        elif isinstance(extra, list):
            extra = [str(x).strip().lower() for x in extra if str(x).strip()]
        merged = base + extra
        return list(dict.fromkeys([t for t in merged if t]))

    def _resume_outline_bundle(
        self,
        domain: str,
        roadmap: Dict[str, Any],
        user: Dict[str, Any],
        signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        terms = self._extract_resume_terms(user)
        gaps = self._estimate_skill_gap(domain, signals)
        adaptive = roadmap.get("adaptive_state") or {}
        next_step = roadmap.get("next_step") or {}
        bullets: List[str] = []

        style = str(user.get("learning_style") or user.get("learningStyle") or "").strip()
        if style:
            bullets.append(f"Learning cadence: {style} — match this tone in your summary.")

        known = str(user.get("known") or "").strip()
        want = str(user.get("want") or "").strip()
        goals = str(user.get("goals") or user.get("learning_goals") or "").strip()
        if known:
            bullets.append(f"Strengths / background to feature: {known[:220]}{'…' if len(known) > 220 else ''}")
        if want:
            bullets.append(f"Target growth areas: {want[:220]}{'…' if len(want) > 220 else ''}")
        if goals:
            bullets.append(f"Goals line for summary: {goals[:220]}{'…' if len(goals) > 220 else ''}")

        stage = adaptive.get("current_stage")
        explicit_map = signals.get("explicit") or {}
        try:
            slider_primary = float(explicit_map.get(domain, 0) or 0)
        except (TypeError, ValueError):
            slider_primary = 0.0
        if slider_primary > 0:
            bullets.append(
                f"Self-rated focus in {domain}: ~{round(max(0.0, min(100.0, (slider_primary / 10.0) * 100.0)))}% "
                f"(from your assessment sliders)."
            )
        if stage:
            mastery = adaptive.get("mastery_level")
            eng = adaptive.get("engagement_score")
            bullets.append(
                f"{domain} roadmap stage: {stage} (mastery ~{round(float(mastery or 0) * 100)}%, "
                f"engagement ~{round(float(eng or 0) * 100)}%)."
            )

        if gaps:
            bullets.append("Skill-gap keywords to weave into experience bullets: " + ", ".join(gaps[:6]))

        ns_title = next_step.get("title")
        ns_why = next_step.get("why")
        if ns_title:
            line = f"Next proof point to complete: {ns_title}"
            if ns_why:
                line += f" — {ns_why}"
            bullets.append(line[:400])

        topics: List[str] = []
        for key in ("basic", "intermediate", "advanced", "expert"):
            block = roadmap.get(key)
            if not isinstance(block, dict) and key == "basic":
                block = roadmap.get("beginner")
            if isinstance(block, dict):
                topics.extend(block.get("topics") or [])
        if topics:
            unique_topics = list(dict.fromkeys(topics))
            bullets.append("Portfolio themes to demonstrate: " + ", ".join(unique_topics[:8]))

        certs = roadmap.get("certifications") or []
        if isinstance(certs, list) and certs:
            bullets.append("Certifications to list when ready: " + ", ".join(str(c) for c in certs[:5]))

        headline = f"{domain} learner — personalized from your profile, quiz signals, and roadmap."
        return {"headline": headline, "keywords": terms[:12], "bullets": bullets[:14]}

    def _enrich_payload_with_quiz_caliber(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        caliber = payload.get("quiz_caliber") or {}
        if not isinstance(caliber, dict):
            caliber = {}
        merged = dict(payload)
        mastery = caliber.get("mastery_level")
        if mastery is not None:
            merged["mastery_level"] = mastery
            merged["quiz_accuracy"] = mastery
        attempts = int(caliber.get("attempt_count") or 0)
        if merged.get("engagement_score") is None and attempts > 0:
            merged["engagement_score"] = min(1.0, attempts / 5.0)
        return merged

    def _build_roadmap_from_openai(
        self,
        domain: str,
        signals: Dict[str, Any],
        payload: Dict[str, Any],
        openai_bundle: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge OpenAI-generated topics with ML adaptive pacing (no static catalogs)."""
        openai_roadmap = openai_bundle.get("roadmap") or {}
        basic_block = openai_roadmap.get("basic") or openai_roadmap.get("beginner") or {}
        intermediate_block = openai_roadmap.get("intermediate") or {}
        advanced_block = openai_roadmap.get("advanced") or {}
        expert_block = openai_roadmap.get("expert") or {}

        basic = list(basic_block.get("all_topics") or basic_block.get("topics") or [])
        intermediate = list(intermediate_block.get("all_topics") or intermediate_block.get("topics") or [])
        advanced = list(advanced_block.get("all_topics") or advanced_block.get("topics") or [])
        expert = list(expert_block.get("all_topics") or expert_block.get("topics") or [])
        if not basic and not intermediate and not advanced and not expert:
            raise ValueError("OpenAI roadmap returned no topics")

        weekly_hours = float(
            (payload.get("user") or {}).get("weekly_availability_hours")
            or payload.get("weekly_availability_hours")
            or 6
        )
        weekly_hours = max(1.0, min(40.0, weekly_hours))

        projects = list(openai_roadmap.get("suggested_projects") or [])
        resources_block = openai_roadmap.get("resources") or {}
        courses = list(resources_block.get("courses") or [])
        course_cards = list(resources_block.get("course_cards") or [])
        career_roles = list(openai_roadmap.get("career_paths") or [])

        adaptive_metrics = self._adaptive_metrics(domain, signals, payload)
        current_stage = self._determine_stage(adaptive_metrics)
        strategy = self._next_step_strategy(adaptive_metrics, current_stage)
        stage_topics = self._adaptive_topic_sequence(basic, intermediate, advanced, expert, current_stage, strategy)

        allow_expert_now = adaptive_metrics["mastery_level"] >= 0.85 and adaptive_metrics["engagement_score"] >= 0.72
        if not allow_expert_now:
            stage_topics["expert"] = stage_topics["expert"][:1]

        sessions_per_week = max(2, int(round(weekly_hours / 2.5)))
        session_minutes = int(round((weekly_hours * 60) / sessions_per_week))
        if strategy.get("path_modifier") == "short":
            sessions_per_week = max(2, sessions_per_week - 1)
            session_minutes = max(30, min(90, session_minutes))

        weekly_plan = {
            "hours_per_week": weekly_hours,
            "sessions_per_week": sessions_per_week,
            "minutes_per_session": max(30, min(120, session_minutes)),
            "cadence": "project-first" if (signals.get("learning_style") or {}).get(domain, 0) > 0.5 else "mixed",
        }

        stage_complexity = {"basic": 1.0, "intermediate": 1.3, "advanced": 1.7, "expert": 2.2}
        mastery = float(adaptive_metrics.get("mastery_level", 0.5))
        progression = float(adaptive_metrics.get("progression_completeness", 0.0))
        engagement = float(adaptive_metrics.get("engagement_score", 0.5))
        pace_modifier = max(0.65, min(1.25, 1.0 - (0.18 * progression) - (0.12 * max(0.0, engagement - 0.5))))
        mastery_modifier = max(0.75, min(1.35, 1.15 - (0.4 * mastery)))

        def _stage_duration_days(stage_key: str, topics: List[str]) -> int:
            topic_count = max(1, len(topics))
            complexity = stage_complexity.get(stage_key, 1.0)
            estimated_hours = topic_count * 5.5 * complexity * pace_modifier * mastery_modifier
            days = int(round((estimated_hours / max(weekly_hours, 1.0)) * 7))
            bounds = {"basic": (14, 90), "intermediate": (21, 150), "advanced": (28, 240), "expert": (35, 365)}
            lo, hi = bounds.get(stage_key, (14, 365))
            return max(lo, min(hi, days))

        basic_days = _stage_duration_days("basic", stage_topics["basic"])
        intermediate_days = _stage_duration_days("intermediate", stage_topics["intermediate"])
        advanced_days = _stage_duration_days("advanced", stage_topics["advanced"])
        expert_days = _stage_duration_days("expert", stage_topics["expert"])

        basic_label = str(basic_block.get("duration_label") or self._duration_weeks_label(basic_days))
        intermediate_label = str(intermediate_block.get("duration_label") or self._duration_weeks_label(intermediate_days))
        advanced_label = str(advanced_block.get("duration_label") or self._duration_weeks_label(advanced_days))
        expert_label = str(expert_block.get("duration_label") or self._duration_weeks_label(expert_days))

        if strategy.get("recommendation_type") == "project":
            next_step = {"type": "project", "title": projects[0] if projects else "Applied capstone", "why": strategy["reason"], "stage": current_stage}
        elif strategy.get("recommendation_type") == "course":
            next_step = {"type": "course", "title": courses[0] if courses else "Core concept refresher", "why": strategy["reason"], "stage": current_stage}
        else:
            next_step = {
                "type": "course_then_project",
                "title": f"{courses[0]} -> {projects[0]}" if courses and projects else "Guided practice path",
                "why": strategy["reason"],
                "stage": current_stage,
            }

        explainability = {
            "factors": adaptive_metrics,
            "decision_policy": {
                "current_stage": current_stage,
                "expert_gate_open": allow_expert_now,
                "strategy": strategy,
            },
            "reason_summary": [
                f"Roadmap generated by OpenAI and adapted to quiz caliber for {domain}.",
                f"Mastery={round(adaptive_metrics['mastery_level'] * 100)}%, engagement={round(adaptive_metrics['engagement_score'] * 100)}%",
                f"Recommended quiz difficulty: {openai_bundle.get('recommended_quiz_difficulty', 'beginner')}",
            ],
        }

        return {
            "basic": {
                "topics": stage_topics["basic"],
                "all_topics": basic,
                "duration_days": basic_days,
                "duration_label": basic_label,
                "stage_projects": list(basic_block.get("stage_projects") or [])[:6],
                "milestones": [
                    "Complete foundational topics from your quiz-caliber profile",
                    "Pass baseline concept checks at recommended difficulty",
                    f"Build {sessions_per_week} sessions/week habit",
                ],
            },
            "intermediate": {
                "topics": stage_topics["intermediate"],
                "all_topics": intermediate,
                "duration_days": intermediate_days,
                "duration_label": intermediate_label,
                "stage_projects": list(intermediate_block.get("stage_projects") or [])[:6],
                "milestones": [
                    "Complete guided project cycle",
                    "Improve debugging and review depth",
                    "Demonstrate repeatable implementation quality",
                ],
            },
            "advanced": {
                "topics": stage_topics["advanced"],
                "all_topics": advanced,
                "duration_days": advanced_days,
                "duration_label": advanced_label,
                "stage_projects": list(advanced_block.get("stage_projects") or [])[:6],
                "milestones": [
                    f"Deliver production-style {domain} features",
                    "Apply performance + architecture trade-offs",
                    "Prepare portfolio pieces for mid-level roles",
                ],
            },
            "expert": {
                "topics": stage_topics["expert"],
                "all_topics": expert,
                "duration_days": expert_days,
                "duration_label": expert_label,
                "stage_projects": list(expert_block.get("stage_projects") or [])[:6],
                "milestones": [
                    f"Deliver {domain} capstone",
                    "Lead system design and optimization decisions",
                    "Prepare portfolio and interview narrative for senior roles",
                ],
            },
            "weekly_study_plan": weekly_plan,
            "suggested_projects": projects,
            "resources": {
                "courses": courses,
                "course_cards": course_cards,
            },
            "career_paths": career_roles,
            "skill_gaps": self._estimate_skill_gap(domain, signals),
            "adaptive_state": {
                "interest_strength": adaptive_metrics["interest_strength"],
                "mastery_level": adaptive_metrics["mastery_level"],
                "progression_completeness": adaptive_metrics["progression_completeness"],
                "engagement_score": adaptive_metrics["engagement_score"],
                "dropout_risk": adaptive_metrics["dropout_risk"],
                "current_stage": current_stage,
            },
            "next_step": next_step,
            "explainability": explainability,
            "source": "openai+ml",
        }

    def _fetch_openai_learning_bundle(
        self,
        domain: str,
        signals: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        from .openai_path_generator import OpenAIPathGeneratorError, generate_learning_path_via_openai

        domain = self._canonical_domain(domain)
        payload = self._enrich_payload_with_quiz_caliber(payload)
        user = payload.get("user") or {}
        secondary_raw = payload.get("secondary_domains") or []
        if isinstance(secondary_raw, str):
            secondary_raw = [secondary_raw]
        secondary_domains = [str(s).strip() for s in secondary_raw if str(s).strip()]
        try:
            return generate_learning_path_via_openai(
                domain=domain,
                user=user,
                quiz_caliber=payload.get("quiz_caliber") or {},
                interest_signals=signals,
                secondary_domains=secondary_domains,
            )
        except OpenAIPathGeneratorError as exc:
            logger.error("OpenAI learning path generation failed: %s", exc)
            raise

    def generate_roadmap(self, domain: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        domain = self._canonical_domain(domain)
        payload = self._enrich_payload_with_quiz_caliber(payload)
        user_id = str(payload.get("user_id") or payload.get("userId") or "").strip()
        force_regenerate = bool(payload.get("force_regenerate") or payload.get("forceRegenerate"))

        if user_id and not force_regenerate:
            from services.learning_path_cache import (
                compute_invalidation_key,
                get_cached_learning_path,
                get_stale_learning_path,
                save_learning_path,
            )

            invalidation_key = compute_invalidation_key(user_id)
            cached = get_cached_learning_path(user_id, domain, invalidation_key=invalidation_key)
            if cached:
                cached.setdefault("domain", domain)
                cached.setdefault("metadata", {})
                if isinstance(cached["metadata"], dict):
                    cached["metadata"]["source"] = "cache"
                return cached
        else:
            from services.learning_path_cache import (
                compute_invalidation_key,
                get_stale_learning_path,
                save_learning_path,
            )
            invalidation_key = compute_invalidation_key(user_id) if user_id else ""

        signals = self._collect_signals(
            self._normalize_explicit_scores(payload.get("scores") or {}),
            payload.get("user", {}),
            payload,
        )

        try:
            openai_bundle = self._fetch_openai_learning_bundle(domain, signals, payload)
        except Exception as exc:
            logger.exception("OpenAI learning path generation failed: %s", exc)
            if user_id:
                stale = get_stale_learning_path(user_id, domain)
                if stale:
                    meta = dict(stale.get("metadata") or {}) if isinstance(stale.get("metadata"), dict) else {}
                    meta.update({
                        "source": "stale_cache",
                        "refresh_error": str(exc)[:500],
                    })
                    stale["metadata"] = meta
                    stale["stale"] = True
                    return stale
            from utils.offline_learning_templates import build_offline_openai_bundle

            openai_bundle = build_offline_openai_bundle(
                domain,
                quiz_caliber=payload.get("quiz_caliber") or {},
                user=payload.get("user") or {},
            )
            logger.warning("Falling back to offline learning path template for domain=%s", domain)

        try:
            roadmap = self._build_roadmap_from_openai(domain, signals, payload, openai_bundle)
        except Exception as exc:
            logger.warning("Roadmap build failed (%s); using offline template for domain=%s", exc, domain)
            from utils.offline_learning_templates import build_offline_openai_bundle

            openai_bundle = build_offline_openai_bundle(
                domain,
                quiz_caliber=payload.get("quiz_caliber") or {},
                user=payload.get("user") or {},
            )
            roadmap = self._build_roadmap_from_openai(domain, signals, payload, openai_bundle)
        careers_detailed = normalize_careers_for_market(
            openai_bundle.get("careers_detailed") or [],
            domain=domain,
        )
        quiz_caliber = payload.get("quiz_caliber") or {}
        careers_detailed, user_career_level, careers_by_level = align_careers_to_user_progress(
            careers_detailed, quiz_caliber
        )
        resume_outline = openai_bundle.get("resume_outline") or {}
        secondary_insights = openai_bundle.get("secondary_insights") or {}
        career = {
            "roles": [c.get("title") for c in careers_detailed if c.get("title")],
            "user_level": user_career_level,
            "by_level": {
                level: [c.get("title") for c in items if c.get("title")]
                for level, items in careers_by_level.items()
            },
        }

        result = {
            "domain": domain,
            "roadmap": roadmap,
            "career_paths": career,
            "careers_detailed": careers_detailed,
            "careers_by_level": careers_by_level,
            "user_career_level": user_career_level,
            "pakistani_jobs": openai_bundle.get("pakistani_jobs") or [],
            "resume_outline": resume_outline,
            "secondary_insights": secondary_insights,
            "skills_gap": self._estimate_skill_gap(domain, signals),
            "quiz_caliber": payload.get("quiz_caliber") or {},
            "recommended_quiz_difficulty": openai_bundle.get("recommended_quiz_difficulty"),
            "caliber_summary": openai_bundle.get("caliber_summary"),
            "market_region": openai_bundle.get("market_region"),
            "salary_currency": openai_bundle.get("salary_currency"),
            "cached": False,
            "metadata": {
                "source": openai_bundle.get("source") or "openai+ml",
                "generator": (
                    "offline_learning_templates"
                    if openai_bundle.get("source") == "offline_template"
                    else "openai_path_generator"
                ),
                **market_metadata(),
            },
        }

        if user_id:
            save_learning_path(user_id, domain, result, invalidation_key=invalidation_key)

        return result

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
        d_key = self._canonical_domain(domain)
        why = self._explain_domain_match(d_key, signals)
        skills_gap = self._estimate_skill_gap(d_key, signals)
        conf_lookup = confidence_lookup if isinstance(confidence_lookup, dict) else {}
        conf_val = float(conf_lookup.get(d_key, conf_lookup.get(domain, 0.0)))
        return LearningInsight(
            domain=d_key,
            match_score=conf_val,
            match_percent=conf_val,
            why_matched=why,
            skills_gap=skills_gap,
            fastest_path=f"Open Learning Path to load a live {d_key} roadmap from the API.",
            best_courses=[],
            best_projects=[],
            best_certifications=[],
            community_resources=[],
            career_paths={"roles": []},
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

    def _clamp01(self, value: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def _adaptive_metrics(self, domain: str, signals: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, float]:
        explicit_raw = (signals.get("explicit") or {}).get(domain, 5.0)
        interest_strength = self._clamp01(float(payload.get("interest_strength", explicit_raw / 10.0)))

        mastery = payload.get("mastery_level")
        if mastery is None:
            mastery = payload.get("quiz_accuracy")
        if mastery is None:
            topic_perf = (signals.get("behavioral") or {}).get(domain, 0.0) / 10.0
            mastery = topic_perf
        mastery_level = self._clamp01(mastery)

        progression = payload.get("learning_progression_completeness")
        if progression is None:
            progression = payload.get("progression_completeness")
        if progression is None:
            completed = float(payload.get("completed_topics", 0) or 0)
            total = float(payload.get("total_topics", 0) or 0)
            progression = (completed / total) if total > 0 else 0.0
        progression_completeness = self._clamp01(progression)

        engagement = payload.get("engagement_score")
        if engagement is None:
            engagement = (signals.get("behavioral") or {}).get(domain, 0.0) / 10.0
        engagement_score = self._clamp01(engagement)

        dropout = payload.get("dropout_risk")
        if dropout is None:
            dropout = max(0.0, 1.0 - engagement_score)
        dropout_risk = self._clamp01(dropout)

        return {
            "interest_strength": round(interest_strength, 4),
            "mastery_level": round(mastery_level, 4),
            "progression_completeness": round(progression_completeness, 4),
            "engagement_score": round(engagement_score, 4),
            "dropout_risk": round(dropout_risk, 4),
        }

    def _determine_stage(self, metrics: Dict[str, float]) -> str:
        mastery = metrics["mastery_level"]
        progression = metrics["progression_completeness"]
        engagement = metrics["engagement_score"]
        dropout = metrics["dropout_risk"]

        if mastery >= 0.88 and progression >= 0.78 and engagement >= 0.7 and dropout <= 0.3:
            return "expert"
        if mastery >= 0.72 and progression >= 0.55 and engagement >= 0.6 and dropout <= 0.35:
            return "advanced"
        if mastery >= 0.48 and progression >= 0.28 and dropout <= 0.5:
            return "intermediate"
        return "basic"

    def _next_step_strategy(self, metrics: Dict[str, float], stage: str) -> Dict[str, Any]:
        mastery = metrics["mastery_level"]
        engagement = metrics["engagement_score"]
        dropout = metrics["dropout_risk"]

        if dropout >= 0.6 or engagement <= 0.35:
            return {
                "mode": "simplified",
                "path_modifier": "short",
                "recommendation_type": "course",
                "reason": "Engagement dropped or dropout risk increased; reducing complexity and shortening next path.",
            }
        if mastery >= 0.78 and engagement >= 0.68:
            return {
                "mode": "challenge",
                "path_modifier": "project_first",
                "recommendation_type": "project",
                "reason": "Mastery and engagement are high; recommending project-based next step.",
            }
        if stage == "basic":
            return {
                "mode": "foundation",
                "path_modifier": "guided",
                "recommendation_type": "course",
                "reason": "Prerequisites are still building; guided foundational learning is prioritized.",
            }
        return {
            "mode": "balanced",
            "path_modifier": "mixed",
            "recommendation_type": "course_then_project",
            "reason": "Progression is healthy; continue with mixed course + practice cadence.",
        }

    def _adaptive_topic_sequence(
        self,
        basic: List[str],
        intermediate: List[str],
        advanced: List[str],
        expert: List[str],
        stage: str,
        strategy: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        if stage == "basic":
            b, i, a, e = basic[:3], intermediate[:1], advanced[:1], expert[:0]
        elif stage == "intermediate":
            b, i, a, e = basic[:2], intermediate[:3], advanced[:1], expert[:1]
        elif stage == "advanced":
            b, i, a, e = basic[:1], intermediate[:2], advanced[:3], expert[:1]
        else:
            b, i, a, e = basic[:1], intermediate[:1], advanced[:2], expert[:3]

        if strategy.get("path_modifier") == "short":
            b, i, a, e = b[:2], i[:2], a[:1], e[:1]

        return {
            "basic": b or basic[:2],
            "intermediate": i or intermediate[:2],
            "advanced": a or advanced[:2],
            "expert": e or expert[:2],
        }

    def _secondary_domain_snapshots(
        self, primary: str, secondary: List[str], signals: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Secondary domain packs come from OpenAI via generate_roadmap — no static catalogs."""
        return {}

    def build_roadmap(self, domain: str, signals: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible entry that always uses the dynamic OpenAI + ML pipeline."""
        payload = self._enrich_payload_with_quiz_caliber(payload)
        openai_bundle = self._fetch_openai_learning_bundle(domain, signals, payload)
        return self._build_roadmap_from_openai(domain, signals, payload, openai_bundle)

    def build_career_intelligence(self, top_domains: List[Dict[str, Any]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for item in top_domains:
            career = item.get("career_paths")
            if career:
                out[item["domain"]] = career
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
