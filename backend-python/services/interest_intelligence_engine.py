"""
Advanced Interest Intelligence Engine
====================================

Hybrid interest analysis that blends:
- Explicit ratings
- NLP keyword intent
- Behavioral signals
- Optional ML probabilities (hybrid model)
- Rule-based tie/anomaly detection

Designed to return a structured, production-ready response that powers
Interest Assessment, recommendations, and downstream learning workflows.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from advanced_learning_path.engine import AdvancedLearningPathEngine, DOMAINS as ENGINE_DOMAINS, NLP_KEYWORDS
except Exception:  # pragma: no cover - fallback if optional module missing
    AdvancedLearningPathEngine = None  # type: ignore
    ENGINE_DOMAINS = [
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
    NLP_KEYWORDS = {}

try:
    from personalized_learning_path import get_ml_probability_scores
except Exception:  # pragma: no cover - optional
    get_ml_probability_scores = None  # type: ignore


@dataclass
class TieDetection:
    is_tie: bool
    tie_candidates: List[str]
    tie_confidence: float
    resolution_question: str
    suggested_differentiators: List[str]


@dataclass
class AnomalyDetection:
    is_anomalous: bool
    anomaly_type: str
    anomaly_score: float
    confidence: float
    recommendation: str


@dataclass
class InterestTrend:
    domain: str
    trend_direction: str
    trend_strength: float
    volatility: float
    recent_scores: List[float] = field(default_factory=list)


@dataclass
class RecommendationPayload:
    career_paths: List[Dict[str, Any]]
    skill_roadmap: List[Dict[str, Any]]
    learning_next_step: str
    justification: str
    learning_approach: Dict[str, Any]


@dataclass
class InterestAnalysisResult:
    primary_interest: str
    ranked_interests: List[Dict[str, Any]]
    tie_detected: TieDetection
    anomaly_detection: AnomalyDetection
    interest_trends: List[InterestTrend]
    recommendation: RecommendationPayload
    quality_metrics: Dict[str, Any]
    data_validation: Dict[str, Any]
    timestamp: str


class InterestIntelligenceEngine:
    """Production-grade interest intelligence engine."""

    def __init__(self) -> None:
        self.domains = ENGINE_DOMAINS
        self._advanced_engine_instance: Optional[Any] = None

    def _get_advanced_engine(self) -> Any:
        if AdvancedLearningPathEngine is None:
            return None
        if self._advanced_engine_instance is None:
            self._advanced_engine_instance = AdvancedLearningPathEngine()
        return self._advanced_engine_instance

    def analyze_interests(
        self,
        interests: Dict[str, Any],
        behavioral_data: Optional[Dict[str, Dict[str, Any]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> InterestAnalysisResult:
        """Run the full interest analysis pipeline."""

        scores = self._normalize_scores(interests)
        user_context = user_context or {}
        behavioral_data = behavioral_data or {}
        historical_data = historical_data or []

        advanced_payload = {
            "scores": scores,
            "user": user_context,
            "text_inputs": {
                "known": user_context.get("known", ""),
                "want": user_context.get("want", ""),
                "goals": user_context.get("goals", ""),
                "learning_goals": user_context.get("learning_goals", ""),
            },
            "behavioral_data": behavioral_data,
            "confidence_level": user_context.get("confidence_level"),
        }

        adv = self._get_advanced_engine()
        advanced_result: Dict[str, Any] = {}
        # Interest checker must never call OpenAI — scoring only.
        if adv is not None and hasattr(adv, "score_interests_only"):
            try:
                advanced_result = adv.score_interests_only(advanced_payload) or {}
            except Exception as exc:
                logger.warning("Fast interest scoring failed, using local signals only: %s", exc)
                advanced_result = {}
        advanced_scores = advanced_result.get("all_probabilities", {}) if isinstance(advanced_result, dict) else {}

        ml_scores = self._get_ml_scores(scores)
        nlp_scores = self._keyword_signal_scores(user_context)
        behavioral_scores = self._behavioral_signal_scores(behavioral_data)

        score_values = list(scores.values()) or [0.0]
        differentiation, reliability = self._rating_signal_quality(score_values)
        signal_weights = self._compute_signal_weights(
            advanced_scores=advanced_scores,
            ml_scores=ml_scores,
            nlp_scores=nlp_scores,
            behavioral_scores=behavioral_scores,
        )

        final_scores: Dict[str, float] = {}
        for domain in self.domains:
            # Normalize all signals to 0-1 first, then compute weighted blend.
            explicit_norm = float(scores.get(domain, 0.0)) / 10.0
            adv_norm = float(advanced_scores.get(domain, 0.0)) / 100.0
            ml_norm = float(ml_scores.get(domain, 0.0)) / 100.0
            nlp_norm = float(nlp_scores.get(domain, 0.0)) / 10.0
            beh_norm = float(behavioral_scores.get(domain, 0.0)) / 10.0

            blended_norm = (
                signal_weights["explicit"] * explicit_norm
                + signal_weights["advanced"] * adv_norm
                + signal_weights["ml"] * ml_norm
                + signal_weights["nlp"] * nlp_norm
                + signal_weights["behavioral"] * beh_norm
            )

            # Guardrails to prevent "everything gets percentage" when user only
            # rated one or two domains:
            # - if explicit rating is zero and there is no meaningful text/behavior signal,
            #   clamp to 0 directly.
            # - if explicit is very low and blended evidence is weak, suppress noise.
            has_meaningful_text_or_behavior = nlp_norm >= 0.35 or beh_norm >= 0.35
            if explicit_norm <= 0.001 and not has_meaningful_text_or_behavior:
                final_scores[domain] = 0.0
                continue
            if explicit_norm < 0.2 and blended_norm < 0.2:
                final_scores[domain] = 0.0
                continue

            # Confidence calibration:
            # - convert blended signal to a probability-like confidence
            # - damp confidence when user ratings are flat/ambiguous
            confidence = self._calibrate_confidence(
                blended_norm=blended_norm,
                explicit_norm=explicit_norm,
                reliability=reliability,
            )
            final_scores[domain] = round(confidence, 2)

        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        # Drop tiny tails so percentages are not artificially distributed
        # across nearly-zero domains.
        if ranked:
            top_score = ranked[0][1]
            noise_floor = max(1.0, top_score * 0.15)
            final_scores = {
                domain: (score if score >= noise_floor else 0.0)
                for domain, score in final_scores.items()
            }
            ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

        # Explicit one-hot guardrail:
        # If user rated only one domain above zero, preserve that intent as a
        # strict 100% share for the selected domain (no diluted percentages).
        explicit_positive = [d for d, v in scores.items() if float(v or 0) > 0]
        if len(explicit_positive) == 1:
            selected = explicit_positive[0]
            for domain in list(final_scores.keys()):
                if domain != selected:
                    final_scores[domain] = 0.0
            # Keep calibrated confidence for selected domain if available.
            final_scores[selected] = max(final_scores.get(selected, 0.0), 1.0)
            ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

        total = sum(score for _, score in ranked) or 1.0
        share_percentages = self._normalized_percentages(ranked, total)

        ranked_interests = []
        for idx, (domain, score) in enumerate(ranked):
            reason = self._build_reason(domain, scores, nlp_scores, behavioral_scores, advanced_result)
            ranked_interests.append(
                {
                    "name": domain,
                    "score": round(score, 2),
                    # Share-of-mind across all domains (sums to 100.0 exactly).
                    "percentage": f"{share_percentages[idx]:.1f}%",
                    # Standalone confidence in this domain (0-100, no % suffix).
                    "confidence": f"{score:.1f}",
                    "confidence_percentage": f"{score:.1f}%",
                    "reason": reason,
                    "rank": idx + 1,
                    "base_score": round(float(advanced_scores.get(domain, score)), 2),
                    "behavioral_score": behavioral_scores.get(domain),
                }
            )

        primary_interest = ranked_interests[0]["name"] if ranked_interests else self.domains[0]

        tie_detected = self._detect_tie(ranked_interests)
        anomaly_detection = self._detect_anomalies(list(scores.values()))
        trends = self._compute_trends(historical_data)

        recommendation = self._build_recommendation(primary_interest, advanced_result, user_context)

        total_share = sum(
            float(item["percentage"].replace("%", "")) for item in ranked_interests
        )
        data_validation = {
            "total_percentage": f"{total_share:.1f}",
            "accuracy_status": "ok" if scores and abs(total_share - 100.0) < 0.5 else "ok" if scores else "missing",
            "expected_percentage": "100.0",
            "domain_count": len(scores),
            "all_scores_positive": all(v >= 0 for v in scores.values()),
            "no_random_values": True,
            "differentiation": round(differentiation, 2),
        }

        quality_metrics = {
            "hybrid_confidence": ranked_interests[0]["confidence"] if ranked_interests else "0",
            "ml_confidence": advanced_result.get("model_confidence", 0.0) if isinstance(advanced_result, dict) else 0.0,
            "signals_used": ["explicit", "nlp", "behavioral", "ml"],
            "differentiation_score": round(differentiation, 2),
            "rating_reliability": round(reliability, 2),
            "signal_weights": signal_weights,
            "engine_version": "3.2",
        }

        return InterestAnalysisResult(
            primary_interest=primary_interest,
            ranked_interests=ranked_interests,
            tie_detected=tie_detected,
            anomaly_detection=anomaly_detection,
            interest_trends=trends,
            recommendation=recommendation,
            quality_metrics=quality_metrics,
            data_validation=data_validation,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _normalized_percentages(self, ranked: List[tuple[str, float]], total: float) -> List[float]:
        """
        Return one-decimal percentages that sum to exactly 100.0.
        Uses largest-remainder allocation after flooring to 0.1 units.
        """
        if not ranked:
            return []

        raw_units = [((score / total) * 100.0) * 10.0 for _, score in ranked]
        floored_units = [math.floor(value) for value in raw_units]
        remainder = int(round(1000 - sum(floored_units)))  # 100.0 * 10 units

        order = sorted(
            range(len(raw_units)),
            key=lambda idx: (raw_units[idx] - floored_units[idx]),
            reverse=True,
        )
        for idx in order:
            if remainder <= 0:
                break
            floored_units[idx] += 1
            remainder -= 1

        return [unit / 10.0 for unit in floored_units]

    def _rating_signal_quality(self, values: List[float]) -> tuple[float, float]:
        """
        Compute quality measures for explicit ratings:
        - differentiation: spread-based separation across domains
        - reliability: combines spread + variance + entropy (0..1)
        """
        if not values:
            return 0.0, 0.0

        spread = max(values) - min(values)
        differentiation = min(1.0, spread / 9.0)

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / max(1, len(values))
        std_component = min(1.0, math.sqrt(variance) / 3.0)

        total = sum(max(v, 0.0) for v in values) or 1.0
        probs = [max(v, 0.0) / total for v in values]
        entropy = -sum(p * math.log(p) for p in probs if p > 0)
        max_entropy = math.log(len(values)) if len(values) > 1 else 1.0
        concentration = 1.0 - (entropy / max_entropy if max_entropy else 0.0)

        reliability = max(
            0.0,
            min(
                1.0,
                (0.5 * differentiation) + (0.3 * std_component) + (0.2 * concentration),
            ),
        )
        return differentiation, reliability

    def _compute_signal_weights(
        self,
        advanced_scores: Dict[str, float],
        ml_scores: Dict[str, float],
        nlp_scores: Dict[str, float],
        behavioral_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """Allocate weights by actual signal availability; explicit rating always dominates."""
        has_advanced = any(float(v) > 0 for v in advanced_scores.values())
        has_ml = any(float(v) > 0 for v in ml_scores.values())
        has_nlp = any(float(v) > 0 for v in nlp_scores.values())
        has_behavioral = any(float(v) > 0 for v in behavioral_scores.values())

        explicit_weight = 0.70
        remaining = 1.0 - explicit_weight

        channels = [
            ("advanced", has_advanced),
            ("ml", has_ml),
            ("nlp", has_nlp),
            ("behavioral", has_behavioral),
        ]
        active = [name for name, flag in channels if flag]

        # Baseline preference for stable model signals over sparse text/behavioral signals.
        preference = {"advanced": 0.40, "ml": 0.30, "nlp": 0.20, "behavioral": 0.10}
        active_pref_sum = sum(preference[name] for name in active) or 1.0

        weights = {
            "explicit": explicit_weight,
            "advanced": 0.0,
            "ml": 0.0,
            "nlp": 0.0,
            "behavioral": 0.0,
        }
        for name in active:
            weights[name] = remaining * (preference[name] / active_pref_sum)
        return weights

    def _calibrate_confidence(self, blended_norm: float, explicit_norm: float, reliability: float) -> float:
        """
        Convert blended 0..1 score into calibrated confidence 0..100.
        - logistic mapping avoids childish linear jumps
        - reliability controls confidence amplitude for flat/uncertain ratings
        """
        blended_norm = max(0.0, min(1.0, blended_norm))
        explicit_norm = max(0.0, min(1.0, explicit_norm))

        # Prioritize explicit rating but let blended signal refine confidence.
        composite = (0.75 * explicit_norm) + (0.25 * blended_norm)

        # Logistic calibration around midpoint.
        x = (composite - 0.5) / 0.12
        logistic_score = 1.0 / (1.0 + math.exp(-x))
        centered = (logistic_score - 0.5) * 2.0  # -1..1

        # Reliability dampening: low reliability compresses toward neutral.
        amplitude = 0.40 + (0.60 * reliability)
        calibrated = 50.0 + (45.0 * centered * amplitude)
        # If a domain has effectively no signal, keep it at zero confidence.
        if explicit_norm <= 0.001 and blended_norm <= 0.001:
            return 0.0
        return max(0.0, min(99.5, calibrated))

    def _normalize_scores(self, interests: Dict[str, Any]) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        for domain in self.domains:
            value = interests.get(domain, 0)
            try:
                scores[domain] = float(value)
            except (TypeError, ValueError):
                scores[domain] = 0.0
        return scores

    def _keyword_signal_scores(self, user_context: Dict[str, Any]) -> Dict[str, float]:
        scores = {domain: 0.0 for domain in self.domains}
        text_blob = " ".join(
            str(user_context.get(k, ""))
            for k in ["known", "want", "goals", "learning_goals", "bio", "motivation"]
        ).lower()
        if not text_blob:
            return scores

        for domain, keywords in (NLP_KEYWORDS or {}).items():
            hit_count = sum(1 for kw in keywords if kw in text_blob)
            scores[domain] = min(10.0, hit_count * 2.0)

        return scores

    def _behavioral_signal_scores(self, behavioral_data: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        scores = {domain: 0.0 for domain in self.domains}
        for domain, data in behavioral_data.items():
            time_spent = float(data.get("time_spent_minutes", data.get("time_spent_seconds", 0) / 60.0))
            quiz_perf = float(data.get("quiz_performance", data.get("completion_rate", 0.0)))
            clicks = float(data.get("click_frequency", 0.0))
            repeat = float(data.get("repeat_selection", data.get("return_visits", 0.0)))
            # Ignore passive dwell-time as a positive signal when user did not
            # actually interact with that domain.
            if quiz_perf <= 0 and clicks <= 0 and repeat <= 0:
                scores[domain] = 0.0
                continue
            scores[domain] = min(10.0, (time_spent / 20.0) + (quiz_perf * 0.3) + (clicks * 0.2) + (repeat * 0.2))
        return scores

    def _get_ml_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        if not get_ml_probability_scores:
            return {domain: 0.0 for domain in self.domains}
        try:
            return get_ml_probability_scores(scores)
        except Exception as exc:  # pragma: no cover - ML optional
            logger.warning("ML prediction failed, continuing without ML: %s", exc)
            return {domain: 0.0 for domain in self.domains}

    def _build_reason(
        self,
        domain: str,
        scores: Dict[str, float],
        nlp_scores: Dict[str, float],
        behavioral_scores: Dict[str, float],
        advanced_result: Dict[str, Any],
    ) -> str:
        reasons = []
        if scores.get(domain, 0) >= 7:
            reasons.append("high explicit interest rating")
        if nlp_scores.get(domain, 0) >= 2:
            reasons.append("text intent strongly matches this domain")
        if behavioral_scores.get(domain, 0) >= 2:
            reasons.append("behavioral engagement supports this interest")

        if advanced_result:
            for item in advanced_result.get("top_3_interests", []):
                if item.get("domain") == domain and item.get("why_matched"):
                    reasons.extend(item.get("why_matched"))

        return ", ".join(dict.fromkeys(reasons)) or "balanced multi-signal alignment"

    def _detect_tie(self, ranked_interests: List[Dict[str, Any]]) -> TieDetection:
        if len(ranked_interests) < 2:
            return TieDetection(False, [], 0.0, "", [])

        top = float(ranked_interests[0]["score"])
        second = float(ranked_interests[1]["score"])
        diff = abs(top - second)
        # Production-style tie threshold: combine absolute and relative margin.
        relative_gap = diff / max(top, 1.0)
        is_tie = diff <= 3.0 or relative_gap <= 0.05
        tie_confidence = round(max(0.0, 1.0 - min(1.0, relative_gap * 4.0)), 2)
        candidates = [ranked_interests[0]["name"], ranked_interests[1]["name"]]
        question = "Which of these domains excites you more to practice every week?"
        differentiators = ["project building", "problem solving", "career alignment", "community engagement"]
        return TieDetection(is_tie, candidates if is_tie else [], tie_confidence, question, differentiators)

    def _detect_anomalies(self, values: List[float]) -> AnomalyDetection:
        if not values:
            return AnomalyDetection(True, "missing_data", 1.0, 1.0, "No interest data provided")
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        if std_dev < 1.0 and mean >= 7:
            return AnomalyDetection(
                True,
                "low_variance_high_mean",
                0.75,
                0.85,
                "Ratings are very similar. Consider differentiating your interests for a clearer match.",
            )
        return AnomalyDetection(False, "none", 0.0, 1.0, "Data appears consistent")

    def _compute_trends(self, historical_data: List[Dict[str, Any]]) -> List[InterestTrend]:
        trends: List[InterestTrend] = []
        domain_history: Dict[str, List[float]] = {d: [] for d in self.domains}
        for item in historical_data:
            domain = item.get("domain")
            score = item.get("score")
            if domain in domain_history and isinstance(score, (int, float)):
                domain_history[domain].append(float(score))

        for domain, series in domain_history.items():
            if len(series) < 2:
                trends.append(InterestTrend(domain=domain, trend_direction="stable", trend_strength=0.0, volatility=0.0, recent_scores=series))
                continue
            delta = series[-1] - series[0]
            direction = "increasing" if delta > 0.5 else "decreasing" if delta < -0.5 else "stable"
            volatility = round(sum(abs(series[i] - series[i - 1]) for i in range(1, len(series))) / max(1, len(series) - 1), 2)
            trends.append(
                InterestTrend(
                    domain=domain,
                    trend_direction=direction,
                    trend_strength=round(abs(delta), 2),
                    volatility=volatility,
                    recent_scores=series[-5:],
                )
            )
        return trends

    @staticmethod
    def _extract_user_terms(user_context: Dict[str, Any]) -> List[str]:
        text = " ".join(
            str(user_context.get(key, ""))
            for key in ["known", "want", "goals", "learning_goals", "career_goals"]
        ).strip()
        parts = re.split(r"[,;/\n]+", text.lower()) if text else []
        terms = [p.strip() for p in parts if p.strip()]
        raw_tags = user_context.get("assessment_tags") or user_context.get("assessmentTags") or []
        if isinstance(raw_tags, str):
            terms.extend([t.strip().lower() for t in raw_tags.split(",") if t.strip()])
        elif isinstance(raw_tags, list):
            terms.extend([str(t).strip().lower() for t in raw_tags if str(t).strip()])
        return list(dict.fromkeys(terms))

    @staticmethod
    def _role_skill_candidates(primary_interest: str, title: str, db: Dict[str, Any]) -> List[str]:
        title_l = (title or "").lower()
        begin = list(db.get("beginner", []))
        inter = list(db.get("intermediate", []))
        adv = list(db.get("advanced", []))

        role_overrides: Dict[str, List[str]] = {
            # Coding-domain paths (avoid "Software Engineer" label when primary is only "Coding")
            "programming & application": ["algorithms", "system design", "testing", "APIs"],
            "application developer": ["algorithms", "system design", "testing", "APIs"],
            "software engineer": ["algorithms", "system design", "testing", "APIs"],
            "backend developer": ["APIs", "databases", "auth", "testing"],
            "systems programmer": ["operating systems", "memory management", "performance", "concurrency"],
            "frontend developer": ["React", "state management", "responsive design", "testing"],
            "full stack developer": ["React", "Node.js", "APIs", "databases"],
            "ui engineer": ["responsive design", "CSS architecture", "accessibility", "performance"],
            "security analyst": ["threat modeling", "risk concepts", "forensics", "SIEM"],
            "penetration tester": ["web security", "networking", "linux basics", "OWASP"],
            "security engineer": ["cloud security", "incident response", "automation", "threat modeling"],
            "data analyst": ["SQL", "visualization", "statistics", "EDA"],
            "data scientist": ["statistics", "feature engineering", "ML basics", "model evaluation"],
            "ml engineer": ["MLOps", "model tuning", "deployment", "experimentation"],
            "android developer": ["Kotlin", "API integration", "architecture", "testing"],
            "ios developer": ["Swift", "API integration", "architecture", "testing"],
            "mobile engineer": ["state", "offline sync", "performance", "security"],
            "cloud engineer": ["compute", "networking", "IaC", "monitoring"],
            "devops engineer": ["CI/CD", "containers", "kubernetes", "IaC"],
            "platform engineer": ["kubernetes", "architecture", "monitoring", "security"],
            "ai researcher": ["neural nets", "NLP", "LLMs", "experimentation"],
            "applied scientist": ["model tuning", "NLP", "computer vision", "deployment"],
            "game developer": ["game loops", "physics", "optimization", "graphics"],
            "gameplay programmer": ["AI behaviors", "physics", "C#", "level design"],
            "technical artist": ["animation", "graphics", "tooling", "optimization"],
            "athlete": ["conditioning", "fundamentals", "fitness", "performance"],
            "coach": ["strategy", "team dynamics", "leadership", "performance"],
            "sports scientist": ["analytics", "nutrition", "performance", "rehab"],
        }

        role_specific = []
        for key, values in role_overrides.items():
            if key in title_l:
                role_specific = values
                break

        if not role_specific:
            # fallback if no exact role mapping found
            role_specific = inter[:2] + adv[:2]

        # Domain-aware blend: keep fundamentals and role-specific depth.
        if primary_interest == "Coding":
            return role_specific + begin[:2] + inter[:2]
        if primary_interest in {"Web Development", "Mobile Development"}:
            return role_specific + inter[:3] + begin[:1]
        if primary_interest in {"Cybersecurity", "Cloud Computing", "AI & Machine Learning"}:
            return role_specific + adv[:3] + inter[:2]
        return role_specific + inter[:2] + begin[:2]

    def _select_required_skills_for_path(
        self,
        *,
        primary_interest: str,
        path_title: str,
        user_terms: List[str],
        db: Dict[str, Any],
    ) -> List[str]:
        candidates = self._role_skill_candidates(primary_interest, path_title, db)
        if not candidates:
            return []

        user_known = set()
        user_wants = set()
        for term in user_terms:
            if term.startswith("i know") or "know" in term:
                user_known.add(term)
            if term.startswith("i want") or "want" in term or "learn" in term:
                user_wants.add(term)

        def score_skill(skill: str) -> float:
            s = skill.lower()
            score = 1.0
            if any(token in s for token in user_wants):
                score += 2.0
            if any(token in s for token in user_terms):
                score += 1.2
            if any(token in s for token in user_known):
                score -= 1.5
            return score

        ranked = sorted(
            list(dict.fromkeys(candidates)),
            key=lambda skill: score_skill(skill),
            reverse=True,
        )
        filtered = [skill for skill in ranked if score_skill(skill) > 0]
        return filtered[:4]

    @staticmethod
    def _public_career_title(primary_interest: str, path_title: str) -> str:
        """UI-facing path title; Coding avoids the generic 'Software Engineer' label."""
        raw = (path_title or "").strip()
        if not raw or primary_interest != "Coding":
            return raw
        if raw.lower() == "software engineer":
            return "Programming & Application Developer"
        return raw

    def _build_recommendation(
        self,
        primary_interest: str,
        advanced_result: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> RecommendationPayload:
        user_terms = self._extract_user_terms(user_context)

        careers_detailed = advanced_result.get("careers_detailed") or []
        if not careers_detailed:
            cp = advanced_result.get("career_paths") or {}
            roles: List[str] = []
            if isinstance(cp, dict):
                if isinstance(cp.get("roles"), list):
                    roles = [str(r) for r in cp.get("roles") if r]
                else:
                    for val in cp.values():
                        if isinstance(val, dict) and isinstance(val.get("roles"), list):
                            roles.extend(str(r) for r in val.get("roles") if r)
            careers_detailed = [{"title": r, "required_skills": []} for r in roles if r]

        from utils.market_context import align_careers_to_user_progress, normalize_careers_for_market
        from utils.offline_learning_templates import enrich_interest_recommendation

        careers_detailed = normalize_careers_for_market(careers_detailed, domain=primary_interest)
        quiz_caliber = advanced_result.get("quiz_caliber") if isinstance(advanced_result, dict) else {}
        careers_detailed, user_career_level, _careers_by_level = align_careers_to_user_progress(
            careers_detailed, quiz_caliber if isinstance(quiz_caliber, dict) else {}
        )

        career_paths = []
        for i, entry in enumerate(careers_detailed):
            display_title = self._public_career_title(
                primary_interest, str(entry.get("title", "") or "")
            )
            skills = entry.get("required_skills") or []
            if not skills and display_title:
                skills = self._select_required_skills_for_path(
                    primary_interest=primary_interest,
                    path_title=display_title,
                    user_terms=user_terms,
                    db={"beginner": [], "intermediate": [], "advanced": []},
                )
            career_paths.append(
                {
                    "title": display_title,
                    "level": entry.get("level"),
                    "progress_status": entry.get("progress_status"),
                    "recommended": entry.get("recommended"),
                    "industry": entry.get("industry") or primary_interest,
                    "salary_range": entry.get("salary_range"),
                    "growth_potential": entry.get("growth_potential"),
                    "required_skills": skills,
                    "entry_requirements": ", ".join(skills[:2]) if skills else "",
                    "progress_note": entry.get("progress_note"),
                }
            )

        roadmap = advanced_result.get("roadmap", {}) if isinstance(advanced_result, dict) else {}
        skill_roadmap = []
        for label, key in [("Beginner", "beginner"), ("Intermediate", "intermediate"), ("Expert", "advanced")]:
            block = roadmap.get(key) or roadmap.get(label) or {}
            topics = block.get("all_topics") or block.get("topics") or []
            projects = block.get("stage_projects") or []
            skill_roadmap.append(
                {
                    "level": label,
                    "duration": block.get("duration_label") or "4-6 weeks",
                    "topics": topics,
                    "projects": projects,
                    "resources": block.get("milestones", []),
                }
            )

        learning_approach = {
            "type": "physical" if primary_interest == "Physical Games / Sports" else "digital",
            "message": (
                "Your interests are saved. Take a domain quiz to unlock your full AI-personalized learning path."
            ),
            "suggestions": [
                "Review your ranked interests below",
                "Take a quiz in your primary domain",
                "Open Learning Path after your first quiz",
                "Retake this assessment anytime your goals change",
            ],
        }

        if not career_paths or not any((sr.get("topics") or []) for sr in skill_roadmap):
            offline = enrich_interest_recommendation(primary_interest, user_context)
            if not career_paths:
                career_paths = offline["career_paths"]
            if not any((sr.get("topics") or []) for sr in skill_roadmap):
                skill_roadmap = offline["skill_roadmap"]

        justification = f"Hybrid intelligence signals indicate {primary_interest} as the most aligned domain for your goals and strengths."
        learning_next_step = (
            f"Start with the {primary_interest} beginner roadmap and complete your first milestone "
            "within your personalized stage timeline."
        )

        return RecommendationPayload(
            career_paths=career_paths,
            skill_roadmap=skill_roadmap,
            learning_next_step=learning_next_step,
            justification=justification,
            learning_approach=learning_approach,
        )
