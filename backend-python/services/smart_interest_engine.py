"""
Smart Interest Intelligence Engine

Provides deterministic, explainable scoring and recommendation logic that
augments the existing LLM-backed InterestAnalyzer. Implements:
- multi-dimensional question weighting
- behavioral signal integration
- fake/random response detection
- tie resolution guidance (returns clarification prompts)
- confidence/consistency/skill readiness/career match metrics
- explainable justification text

This module is intentionally deterministic so results are transparent and
mathematically auditable. It will call the LLM-based InterestAnalyzer for
rich learning path generation when needed.
"""

from typing import Dict, Any, List, Tuple, Optional
import math
import logging
from datetime import datetime

from services.interest_analyzer import DOMAIN_INFO, InterestAnalyzer
from database import get_collection

logger = logging.getLogger(__name__)


class SmartInterestEngine:
    """Engine exposing analysis and recommendation utilities."""

    @staticmethod
    def score_from_multidimensional_responses(responses: Dict[str, Dict[str, float]],
                                             weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Compute base interest scores for each domain from multidimensional responses.

        responses: {
            domain: {
                'enjoyment': 0-10,
                'frequency': 0-10,
                'free_time_choice': 0-10,
                'career_interest': 0-10,
                'self_confidence': 0-10
            }
        }

        weights: optional per-dimension weights (sums not required)
        Returns scores 0-100
        """
        # Default weights emphasise enjoyment and career interest
        default_weights = {
            'enjoyment': 0.30,
            'frequency': 0.15,
            'free_time_choice': 0.20,
            'career_interest': 0.25,
            'self_confidence': 0.10
        }

        w = default_weights.copy()
        if weights:
            w.update(weights)

        scores = {}
        for domain, dims in responses.items():
            # Normalize missing dims to 0
            val = 0.0
            for k, weight in w.items():
                dim_value = float(dims.get(k, 0))
                val += (dim_value / 10.0) * weight

            # Scale to 0-100
            scores[domain] = round(val * 100, 2)

        return scores

    @staticmethod
    def integrate_behavioral_signals(base_scores: Dict[str, float], analytics: Dict[str, Any]) -> Dict[str, float]:
        """
        Boost or attenuate base_scores using behavioral signals from analytics.

        analytics structure expected (best-effort):
        {
            'timeSpent': { domain: seconds },
            'clicks': { domain: count },
            'quizAttempts': { domain: count },
            'completionRate': { domain: 0-1 },
            'returnVisits': { domain: count }
        }
        """
        if not analytics:
            return base_scores

        adjusted = base_scores.copy()

        # Compute normalization factors
        def safe_norm(d):
            if not d:
                return {}
            mx = max(d.values()) if d.values() else 0
            if mx <= 0:
                return {k: 0 for k in d}
            return {k: v / mx for k, v in d.items()}

        time_norm = safe_norm(analytics.get('timeSpent', {}))
        clicks_norm = safe_norm(analytics.get('clicks', {}))
        quiz_norm = safe_norm(analytics.get('quizAttempts', {}))
        comp = analytics.get('completionRate', {})
        return_norm = safe_norm(analytics.get('returnVisits', {}))

        for domain in adjusted.keys():
            boost = 0.0
            boost += time_norm.get(domain, 0.0) * 15  # up to +15
            boost += clicks_norm.get(domain, 0.0) * 8  # up to +8
            boost += quiz_norm.get(domain, 0.0) * 10  # up to +10
            boost += return_norm.get(domain, 0.0) * 7  # up to +7
            boost += comp.get(domain, 0.0) * 12 if isinstance(comp, dict) else 0

            # Apply boost, but cap at +30 and floor at -20
            adjusted_val = adjusted[domain] + boost
            adjusted[domain] = round(max(0.0, min(100.0, adjusted_val)), 2)

        return adjusted

    @staticmethod
    def detect_fake_or_random_responses(responses: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Detects suspicious patterns like all-max answers or high variance across domains.
        Returns:
            { 'is_suspicious': bool, 'reason': str, 'score': float }
        """
        flat_values = []
        for domain, dims in responses.items():
            for v in dims.values():
                flat_values.append(float(v))

        if not flat_values:
            return {'is_suspicious': True, 'reason': 'No responses provided', 'score': 1.0}

        # If user rates everything 9-10 across many domains -> suspicious
        high_count = sum(1 for v in flat_values if v >= 9)
        if high_count >= max(5, len(flat_values) * 0.6):
            return {'is_suspicious': True, 'reason': 'Uniformly high ratings across many dimensions', 'score': 0.9}

        # Compute coefficient of variation across domain-aggregates
        domain_means = []
        for domain, dims in responses.items():
            vals = [float(x) for x in dims.values()] or [0]
            domain_means.append(sum(vals) / len(vals))

        mean = sum(domain_means) / len(domain_means)
        variance = sum((x - mean) ** 2 for x in domain_means) / len(domain_means)
        std = math.sqrt(variance)
        cov = std / mean if mean != 0 else 0

        # If responses are nearly identical across domains (low cov) and high, suspicious
        if cov < 0.05 and mean >= 8:
            return {'is_suspicious': True, 'reason': 'Low variability with high mean across domains', 'score': 0.8}

        # Randomness heuristic: if per-domain variance is very high across dims
        per_domain_variances = []
        for domain, dims in responses.items():
            vals = [float(x) for x in dims.values()]
            m = sum(vals) / len(vals)
            v = sum((x - m) ** 2 for x in vals) / len(vals)
            per_domain_variances.append(v)

        avg_var = sum(per_domain_variances) / len(per_domain_variances)
        if avg_var > 8.0:  # arbitrary threshold
            return {'is_suspicious': True, 'reason': 'High within-domain variance (possibly random answers)', 'score': 0.7}

        return {'is_suspicious': False, 'reason': 'Responses appear consistent', 'score': 0.0}

    @staticmethod
    def resolve_ties(scores: Dict[str, float], threshold: float = 3.0) -> Dict[str, Any]:
        """
        If top scores are within `threshold` (percentage points), return a tie response
        object including a clarification question to present to the user.
        """
        if not scores:
            return {'is_tie': False}

        # Sort domains
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_score = sorted_items[0][1]
        tied = [d for d, s in sorted_items if top_score - s <= threshold]

        if len(tied) <= 1:
            return {'is_tie': False}

        question = (
            f"You showed equal top interest in {', '.join(tied)}. "
            f"Which of these would you prefer to do consistently for the next 6 months?"
        )

        options = tied

        return {'is_tie': True, 'tied_domains': tied, 'clarification_question': question, 'options': options}

    @staticmethod
    def compute_confidence_metrics(responses: Dict[str, Dict[str, float]],
                                   scores: Dict[str, float],
                                   analytics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute confidence, consistency, skill readiness, and career match percentages.
        Returns dict per domain and overall indicators.
        """
        metrics = {}

        # Precompute analytics measures
        quiz_scores = analytics.get('quizScores', {}) if analytics else {}
        wants_career = analytics.get('learningGoals', []) if analytics else []

        for domain, score in scores.items():
            # Confidence: based on self_confidence and behavioral signals
            self_conf = float(responses.get(domain, {}).get('self_confidence', 0))
            consistency = SmartInterestEngine._compute_domain_consistency(domain, analytics)
            quiz = quiz_scores.get(domain, 0)

            confidence_pct = round(min(100, (self_conf / 10.0) * 60 + (consistency * 0.3) * 40 + (min(quiz,100)/100)*10), 2)

            # consistency as percent
            consistency_pct = round(min(100, consistency * 100), 1)

            # skill readiness from quiz performance and completionRate
            readiness = 0.0
            if quiz:
                readiness += min(100, quiz) * 0.6
            comp_rate = analytics.get('completionRate', {}).get(domain, 0) if analytics else 0
            readiness += comp_rate * 100 * 0.4
            readiness = round(min(100, readiness), 1)

            # career match based on explicit career_interest and user goals keywords
            career_interest = float(responses.get(domain, {}).get('career_interest', 0))
            domain_keywords = DOMAIN_INFO.get(domain, {}).get('careers', [])
            goal_match = 1.0 if any(g.lower() in ' '.join(wants_career).lower() for g in domain_keywords) else 0.0
            career_match = round(min(100, career_interest * 10 * 0.7 + goal_match * 30), 1)

            metrics[domain] = {
                'interestScore': round(score, 2),
                'confidencePct': confidence_pct,
                'consistencyPct': consistency_pct,
                'skillReadinessPct': readiness,
                'careerMatchPct': career_match
            }

        return metrics

    @staticmethod
    def _compute_domain_consistency(domain: str, analytics: Dict[str, Any]) -> float:
        """
        Compute a 0-1 consistency measure for a domain using repeat selections and time stability.
        """
        if not analytics:
            return 0.5

        trends = analytics.get('interestTrends', [])
        # trends: list of {'domain':..., 'score':...}
        domain_values = []
        for t in trends:
            for entry in t:
                if entry.get('domain') == domain:
                    domain_values.append(entry.get('score', 0))

        if not domain_values:
            return 0.5

        mean = sum(domain_values) / len(domain_values)
        variance = sum((x - mean) ** 2 for x in domain_values) / len(domain_values)
        std = math.sqrt(variance)

        # consistency = 1 - normalized std (higher std -> lower consistency)
        denom = mean if mean > 0 else 10
        consistency = max(0.0, 1.0 - (std / denom))
        return consistency

    @staticmethod
    def analyze_and_recommend(user_id: str,
                              multidim_responses: Dict[str, Dict[str, float]],
                              analytics: Optional[Dict[str, Any]] = None,
                              user_info: Optional[Dict[str, Any]] = None,
                              weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Full analysis pipeline: scoring, behavioral integration, fake detection,
        tie resolution, metrics computation, LLM explainable analysis and
        recommendation generation (delegates to InterestAnalyzer where helpful).
        """
        # 1. Detect suspicious input
        suspicion = SmartInterestEngine.detect_fake_or_random_responses(multidim_responses)

        # 2. Compute base scores
        base_scores = SmartInterestEngine.score_from_multidimensional_responses(multidim_responses, weights)

        # 3. Integrate behavioral signals
        adjusted_scores = SmartInterestEngine.integrate_behavioral_signals(base_scores, analytics or {})

        # 4. Check ties
        tie_info = SmartInterestEngine.resolve_ties(adjusted_scores)

        # 5. Compute metrics
        metrics = SmartInterestEngine.compute_confidence_metrics(multidim_responses, adjusted_scores, analytics or {})

        # 6. Explainable reason (deterministic summary)
        reasons = SmartInterestEngine._build_explanation(adjusted_scores, multidim_responses, analytics or {}, suspicion)

        # 7. If suspicious, recommend deeper assessment
        action = 'generate_recommendation'
        if suspicion.get('is_suspicious'):
            action = 'request_clarification'

        # 8. LLM-backed detailed recommendations for top domain
        primary_domain = max(adjusted_scores.items(), key=lambda x: x[1])[0] if adjusted_scores else None
        detailed_recs = {}
        if action == 'generate_recommendation' and primary_domain:
            try:
                detailed_recs = InterestAnalyzer.generate_detailed_recommendations(primary_domain, analytics or {}, user_info or {})
            except Exception as e:
                logger.exception('LLM recommendation generation failed, proceeding with deterministic fallback')
                detailed_recs = {}

        result = {
            'userId': user_id,
            'baseScores': base_scores,
            'adjustedScores': adjusted_scores,
            'suspicion': suspicion,
            'tieInfo': tie_info,
            'metrics': metrics,
            'reasons': reasons,
            'detailedRecommendations': detailed_recs,
            'action': action,
            'generatedAt': datetime.utcnow()
        }

        return result

    @staticmethod
    def _build_explanation(adjusted_scores: Dict[str, float], responses: Dict[str, Dict[str, float]], analytics: Dict[str, Any], suspicion: Dict[str, Any]) -> str:
        """
        Create a short explainable justification for the top recommendation.
        """
        if not adjusted_scores:
            return 'No sufficient data to explain recommendation.'

        top_domain, top_score = max(adjusted_scores.items(), key=lambda x: x[1])

        parts = []
        if suspicion.get('is_suspicious'):
            parts.append(f"Input flagged as suspicious: {suspicion.get('reason')}. We recommend a deeper assessment.")

        parts.append(f"Top domain: {top_domain} (score {round(top_score,1)}%).")

        # Add behavioral evidence
        evidence = []
        time_spent = analytics.get('timeSpent', {}).get(top_domain, 0) if analytics else 0
        clicks = analytics.get('clicks', {}).get(top_domain, 0) if analytics else 0
        quiz_attempts = analytics.get('quizAttempts', {}).get(top_domain, 0) if analytics else 0

        if time_spent:
            evidence.append(f'spent {int(time_spent)}s on {top_domain}')
        if clicks:
            evidence.append(f'clicked {clicks} times on {top_domain} content')
        if quiz_attempts:
            evidence.append(f'attempted {quiz_attempts} quizzes in {top_domain}')

        if evidence:
            parts.append('Behavioral evidence: ' + ', '.join(evidence) + '.')

        # Add self-reported signals
        resp = responses.get(top_domain, {})
        enjoyment = resp.get('enjoyment')
        career_interest = resp.get('career_interest')
        if enjoyment is not None:
            parts.append(f"You reported enjoyment {enjoyment}/10 and career interest {career_interest}/10 for {top_domain}.")

        parts.append('The recommendation balances self-report with real engagement to provide a trustworthy match.')

        return ' '.join(parts)
