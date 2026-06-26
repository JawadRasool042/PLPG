"""
State builder.

Translates raw learner signals (interest prediction, quiz outcomes,
time spent, hints, etc.) into a discretised :class:`LearnerState`.

The builder is intentionally tolerant: every input has a sensible
default, so callers from the frontend or other backend services can
omit fields that aren't relevant to their step (e.g. the very first
question of a session has no `accuracy` yet).
"""

from __future__ import annotations

import bisect
import logging
from typing import Any, Dict, Iterable, Optional

from .config import CONFIG, RLConfig
from .schemas import LearnerState

logger = logging.getLogger(__name__)


def _bucket(value: float, edges: Iterable[float]) -> int:
    """Return the index of `value` within the sorted bucket `edges`.

    Edges are exclusive upper bounds, so `bins=(0.4, 0.6, 0.8)` produces
    4 buckets: [<=0.4], (0.4..0.6], (0.6..0.8], (>0.8].
    """
    if value is None:
        return 0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    return bisect.bisect_left(list(edges), v)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class StateBuilder:
    """Builds :class:`LearnerState` instances from heterogeneous inputs."""

    def __init__(self, config: Optional[RLConfig] = None) -> None:
        self.config = config or CONFIG

    # ------------------------------------------------------------------ #
    # High-level helpers
    # ------------------------------------------------------------------ #
    def build(self, payload: Dict[str, Any]) -> LearnerState:
        """
        Assemble a :class:`LearnerState` from a flexible payload.

        Recognised keys (all optional except ``domain``):
            domain (str)                  -> primary subject (required)
            profile (str)                 -> Builder/Analyst/...
            difficulty (str|int)          -> beginner/intermediate/advanced or bucket index
            accuracy (float, 0-1 or 0-100)-> recent quiz accuracy
            response_time (float, sec)    -> avg/last response time
            streak (int)                  -> current consecutive-correct streak
            wrong_answers (int)           -> wrong-answer count this session
            hints_used (int)              -> hints consumed this session
            engagement_score (float, 0-1) -> derived engagement metric
            dropout_risk (float, 0-1)     -> derived dropout-risk metric
            topic_performance (float, 0-1)-> rolling perf for current topic
        """
        if not isinstance(payload, dict):
            raise TypeError("StateBuilder.build expects a dict payload")

        domain = (payload.get("domain") or payload.get("primary_domain") or "").strip()
        if not domain:
            # Fallback to first known domain so the agent still has somewhere
            # to start; logged so callers can audit missing input.
            logger.debug("StateBuilder: missing domain, defaulting to '%s'", self.config.DEFAULT_DOMAINS[0])
            domain = self.config.DEFAULT_DOMAINS[0]

        profile = (payload.get("profile") or payload.get("user_profile") or "Explorer").strip() or "Explorer"

        difficulty = payload.get("difficulty") or payload.get("level")
        difficulty_bucket = (
            self.config.difficulty_bucket(difficulty) if isinstance(difficulty, str)
            else max(0, min(2, _safe_int(difficulty, 1)))
        )

        accuracy = self._normalise_unit(payload.get("accuracy"))
        response_time = _safe_float(payload.get("response_time") or payload.get("avg_response_time"), 0.0)
        streak = max(0, _safe_int(payload.get("streak"), 0))
        wrong_answers = max(0, _safe_int(payload.get("wrong_answers"), 0))
        hints_used = max(0, _safe_int(payload.get("hints_used"), 0))
        engagement = self._normalise_unit(payload.get("engagement_score"))
        dropout_risk = self._normalise_unit(payload.get("dropout_risk"))
        topic_perf = self._normalise_unit(payload.get("topic_performance"))

        buckets = self.config.buckets

        state = LearnerState(
            domain=domain,
            profile=profile,
            difficulty_bucket=difficulty_bucket,
            accuracy_bucket=_bucket(accuracy, buckets.accuracy_bins),
            response_time_bucket=_bucket(response_time, buckets.response_time_bins_sec),
            streak_bucket=_bucket(streak, buckets.streak_bins),
            wrong_bucket=_bucket(wrong_answers, buckets.wrong_bins),
            hint_bucket=_bucket(hints_used, buckets.hint_bins),
            engagement_bucket=_bucket(engagement, buckets.engagement_bins),
            dropout_risk_bucket=_bucket(dropout_risk, buckets.dropout_risk_bins),
            topic_perf_bucket=_bucket(topic_perf, buckets.topic_perf_bins),
            raw={
                "difficulty_label": self.config.difficulty_label(difficulty_bucket),
                "accuracy": accuracy,
                "response_time": response_time,
                "streak": streak,
                "wrong_answers": wrong_answers,
                "hints_used": hints_used,
                "engagement_score": engagement,
                "dropout_risk": dropout_risk,
                "topic_performance": topic_perf,
            },
        )
        return state

    # ------------------------------------------------------------------ #
    # Derived signal helpers (used by callers that have raw quiz data)
    # ------------------------------------------------------------------ #
    @staticmethod
    def derive_engagement(
        *,
        accuracy: float,
        completion_ratio: float,
        avg_response_time: float,
        expected_response_time: float = 25.0,
        streak: int = 0,
    ) -> float:
        """
        Heuristic engagement score in [0, 1].

        Combines accuracy, completion progress, response-time alignment
        and a small streak bonus. Designed to be cheap, deterministic and
        explainable in the UI.
        """
        accuracy = StateBuilder._clip_unit(accuracy)
        completion_ratio = StateBuilder._clip_unit(completion_ratio)
        rt_factor = 1.0
        if expected_response_time > 0 and avg_response_time > 0:
            ratio = avg_response_time / expected_response_time
            # Closer to 1.0 = ideal; very fast / very slow penalised.
            rt_factor = max(0.0, 1.0 - min(1.0, abs(ratio - 1.0)))
        streak_bonus = min(0.20, max(0, streak) * 0.04)
        score = (0.45 * accuracy) + (0.30 * completion_ratio) + (0.20 * rt_factor) + streak_bonus
        return StateBuilder._clip_unit(score)

    @staticmethod
    def derive_dropout_risk(
        *,
        wrong_streak: int,
        hints_used: int,
        avg_response_time: float,
        expected_response_time: float = 25.0,
        idle_seconds: float = 0.0,
    ) -> float:
        """
        Heuristic dropout-risk score in [0, 1].

        Higher values signal frustration/disengagement: long wrong-answer
        streaks, heavy hint usage, abnormally fast or slow response times,
        or long idle periods.
        """
        wrong_factor = min(1.0, max(0, wrong_streak) / 5.0)
        hint_factor = min(1.0, max(0, hints_used) / 6.0)
        rt_factor = 0.0
        if expected_response_time > 0 and avg_response_time > 0:
            ratio = avg_response_time / expected_response_time
            rt_factor = min(1.0, abs(ratio - 1.0))
        idle_factor = min(1.0, max(0.0, idle_seconds) / 180.0)
        risk = (0.45 * wrong_factor) + (0.20 * hint_factor) + (0.20 * rt_factor) + (0.15 * idle_factor)
        return StateBuilder._clip_unit(risk)

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalise_unit(value: Any) -> float:
        """Coerce 0..100 percentages and 0..1 ratios into 0..1."""
        v = _safe_float(value, 0.0)
        if v > 1.0:
            v = v / 100.0
        return StateBuilder._clip_unit(v)

    @staticmethod
    def _clip_unit(value: float) -> float:
        if value != value:  # NaN guard
            return 0.0
        return max(0.0, min(1.0, float(value)))
