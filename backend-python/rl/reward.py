"""
Reward function.

The reward function turns observed learner behaviour into the scalar
training signal consumed by Q-learning. Weights are configurable via
:mod:`rl.config` so educators / product can re-tune without code
changes.

The function returns both the scalar reward and a structured
breakdown so the API can show "why the reward was X" to admins and
power-users.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import CONFIG, RLConfig
from .schemas import Action, StepFeedback

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RewardBreakdown:
    """Structured explanation of how a reward was computed."""

    total: float
    components: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "total": round(float(self.total), 4),
            "components": {k: round(float(v), 4) for k, v in self.components.items()},
            "notes": list(self.notes),
        }


class RewardFunction:
    """Configurable reward computation for the RL agent."""

    def __init__(self, config: Optional[RLConfig] = None) -> None:
        self.config = config or CONFIG

    def compute(self, action: Action, feedback: StepFeedback) -> RewardBreakdown:
        """Compute reward for a single (action, feedback) pair."""
        rc = self.config.reward
        components: Dict[str, float] = {}
        notes: List[str] = []

        # ------------------------------------------------------------------
        # Per-question outcome
        # ------------------------------------------------------------------
        if feedback.is_correct is True:
            components["correct"] = rc.correct
            if (
                feedback.response_time_sec is not None
                and feedback.response_time_sec > 0
                and feedback.expected_time_sec
                and feedback.response_time_sec <= feedback.expected_time_sec * 0.6
            ):
                components["fast_correct_bonus"] = rc.fast_correct_bonus
                notes.append("answered correctly and faster than expected")
            elif (
                feedback.response_time_sec is not None
                and feedback.expected_time_sec
                and feedback.response_time_sec >= feedback.expected_time_sec * 1.8
            ):
                components["slow_correct_penalty"] = rc.slow_correct_penalty
                notes.append("correct but unusually slow")
            if feedback.streak_length > 1:
                # Cap streak bonus so it can't overwhelm other signals.
                bonus = min(5, feedback.streak_length - 1) * rc.streak_bonus_per_step
                components["streak_bonus"] = bonus
                notes.append(f"streak of {feedback.streak_length} correct answers")
        elif feedback.is_correct is False:
            components["wrong"] = rc.wrong
            if feedback.repeated_mistake:
                components["repeated_mistake"] = rc.repeated_mistake_extra
                notes.append("repeated mistake on the same concept")

        # ------------------------------------------------------------------
        # Action-level shaping
        # ------------------------------------------------------------------
        if feedback.used_hint or action == Action.GIVE_HINT:
            components["hint_penalty"] = rc.hint_penalty
            notes.append("a hint was provided / used")

        # ------------------------------------------------------------------
        # Episode-level signals (these are normally added on terminal step)
        # ------------------------------------------------------------------
        if feedback.quiz_completed:
            components["quiz_completed"] = rc.quiz_completed
            notes.append("quiz completed")
        if feedback.quiz_dropped:
            components["quiz_dropped"] = rc.quiz_dropped
            notes.append("quiz abandoned")
        if feedback.score_delta is not None:
            if feedback.score_delta >= 5.0:
                components["improved_score"] = rc.improved_score
                notes.append(f"score improved by {feedback.score_delta:.1f} pts")
            elif feedback.score_delta <= -5.0:
                components["declined_score"] = rc.declined_score
                notes.append(f"score dropped by {abs(feedback.score_delta):.1f} pts")
        if feedback.returned_next_session:
            components["return_next_session"] = rc.return_next_session
            notes.append("user returned in a follow-up session")

        # ------------------------------------------------------------------
        # Action-specific micro-shaping
        # ------------------------------------------------------------------
        # Discourage gratuitous topic switching when the learner is doing well.
        if (
            action == Action.CHANGE_TOPIC
            and feedback.is_correct is True
            and feedback.streak_length >= 2
        ):
            components["change_topic_when_strong"] = -2.0
            notes.append("changed topic while learner was on a hot streak")

        # Encourage decreasing difficulty after repeated failures.
        if action == Action.DECREASE_DIFFICULTY and feedback.is_correct is False and feedback.repeated_mistake:
            components["decrease_after_struggle"] = 1.5
            notes.append("appropriately reduced difficulty after struggle")

        # Reward holding steady when the learner is in the productive zone.
        if (
            action == Action.KEEP_DIFFICULTY
            and feedback.is_correct is True
            and 1 <= feedback.streak_length <= 2
        ):
            components["hold_in_zone"] = 0.5

        total = sum(components.values())
        # Clip so a single transition cannot dominate Q-values.
        total = max(rc.reward_clip_low, min(rc.reward_clip_high, total))

        return RewardBreakdown(total=total, components=components, notes=notes)

    def explain(self, action: Action, feedback: StepFeedback) -> str:
        """Human-readable summary used for the `reason` field."""
        breakdown = self.compute(action, feedback)
        if not breakdown.notes:
            return f"Selected '{action.value}' based on current learner state."
        primary = breakdown.notes[0]
        return f"{action.value.replace('_', ' ').capitalize()} – {primary}."
