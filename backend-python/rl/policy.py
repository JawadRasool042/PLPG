"""
Policy layer.

Wraps the underlying RL algorithm (currently :class:`QLearningAgent`)
behind a stable interface used by the API and service layers. This is
the place to add:

* action masking (don't suggest INCREASE_DIFFICULTY at advanced)
* contextual fallback (cold-start contextual bandit)
* explanations / human-readable reasons

Because the policy is stateless w.r.t. the underlying agent, swapping
in a Deep Q-Network later is a one-line change inside :class:`Policy`.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Tuple

from .config import CONFIG, RLConfig
from .q_learning import QLearningAgent
from .reward import RewardFunction
from .schemas import Action, Decision, LearnerState, StepFeedback

logger = logging.getLogger(__name__)


class Policy:
    """Action-selection policy used by the :class:`RLService`."""

    def __init__(
        self,
        agent: QLearningAgent,
        reward_fn: Optional[RewardFunction] = None,
        config: Optional[RLConfig] = None,
    ) -> None:
        self.agent = agent
        self.reward_fn = reward_fn or RewardFunction(config)
        self.config = config or CONFIG

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def decide(
        self,
        state: LearnerState,
        feedback: Optional[StepFeedback] = None,
        *,
        force_explore: bool = False,
        cold_start: bool = False,
    ) -> Decision:
        """Choose the next action and return a fully-populated Decision."""
        valid_actions = self._valid_actions(state)

        # Contextual cold-start: if we have very few transitions, bias
        # toward conservative defaults rather than random exploration.
        if cold_start and feedback is None:
            chosen, exploration, q_value = self._cold_start_action(state)
        else:
            chosen, exploration, q_value = self.agent.select_action(
                state, valid_actions=valid_actions, force_explore=force_explore
            )

        breakdown = self.reward_fn.compute(chosen, feedback or StepFeedback())
        next_difficulty = self._project_next_difficulty(state, chosen)
        reason = self._reason(state, chosen, feedback, breakdown.notes)

        return Decision(
            state=state,
            action=chosen,
            reason=reason,
            expected_reward=q_value,
            next_difficulty=next_difficulty,
            exploration=exploration,
            policy_version=self.agent.version,
            metadata={
                "valid_actions": [a.value for a in valid_actions],
                "epsilon": round(self.agent.epsilon, 4),
                "reward_components": breakdown.components,
                "reward_notes": breakdown.notes,
            },
        )

    # ------------------------------------------------------------------ #
    # Action constraints / cold start
    # ------------------------------------------------------------------ #
    def _valid_actions(self, state: LearnerState) -> List[Action]:
        """Return the list of actions allowed in the current state."""
        actions = list(Action)

        # Difficulty rails
        if state.difficulty_bucket >= len(self.config.DIFFICULTY_LEVELS) - 1:
            actions = [a for a in actions if a != Action.INCREASE_DIFFICULTY]
        if state.difficulty_bucket <= 0:
            actions = [a for a in actions if a != Action.DECREASE_DIFFICULTY]

        # Don't extend a quiz indefinitely if dropout risk is high.
        if state.dropout_risk_bucket >= 2:
            actions = [a for a in actions if a != Action.EXTEND_QUIZ]

        # Avoid suggesting more hints if already heavily used.
        if state.hint_bucket >= 2:
            actions = [a for a in actions if a != Action.GIVE_HINT]

        # Always keep at least one fallback action available.
        if not actions:
            actions = [Action.KEEP_DIFFICULTY]
        return actions

    def _cold_start_action(self, state: LearnerState) -> Tuple[Action, bool, float]:
        """
        Heuristic action used until we have enough data for the Q-table.

        Falls back to a conservative, explainable rule set so the
        first few sessions feel sensible even before training kicks in.
        """
        # Struggling -> ease the path
        if state.dropout_risk_bucket >= 2 or state.wrong_bucket >= 2:
            if state.difficulty_bucket > 0:
                return Action.DECREASE_DIFFICULTY, False, 0.0
            return Action.GIVE_HINT, False, 0.0

        # Strong streak with low difficulty -> push up
        if state.streak_bucket >= 2 and state.accuracy_bucket >= 2 and state.difficulty_bucket < 2:
            return Action.INCREASE_DIFFICULTY, False, 0.0

        # High engagement & strong topic perf -> recommend project
        if state.engagement_bucket >= 2 and state.topic_perf_bucket >= 2:
            return Action.RECOMMEND_PROJECT, False, 0.0

        # Default: hold the line
        return Action.KEEP_DIFFICULTY, False, 0.0

    # ------------------------------------------------------------------ #
    # Effect projection
    # ------------------------------------------------------------------ #
    def _project_next_difficulty(self, state: LearnerState, action: Action) -> str:
        bucket = state.difficulty_bucket
        if action == Action.INCREASE_DIFFICULTY:
            bucket = min(len(self.config.DIFFICULTY_LEVELS) - 1, bucket + 1)
        elif action == Action.DECREASE_DIFFICULTY:
            bucket = max(0, bucket - 1)
        return self.config.difficulty_label(bucket)

    def _reason(
        self,
        state: LearnerState,
        action: Action,
        feedback: Optional[StepFeedback],
        reward_notes: Iterable[str],
    ) -> str:
        """Explain the decision in user-facing language."""
        bits: List[str] = []
        acc = state.raw.get("accuracy", 0.0)
        streak = state.raw.get("streak", 0)
        wrongs = state.raw.get("wrong_answers", 0)
        engagement = state.raw.get("engagement_score", 0.0)
        difficulty_label = state.raw.get("difficulty_label", "")

        if action == Action.INCREASE_DIFFICULTY:
            bits.append(
                f"Strong recent accuracy ({acc * 100:.0f}%) and a streak of {int(streak)} – "
                f"raising difficulty from {difficulty_label}."
            )
        elif action == Action.DECREASE_DIFFICULTY:
            dr = float(state.raw.get("dropout_risk") or 0.0)
            if int(wrongs) > 0:
                bits.append(
                    f"Multiple recent misses ({int(wrongs)}) – "
                    f"easing difficulty from {difficulty_label} to keep momentum."
                )
            elif dr >= 0.55:
                bits.append(
                    f"Disengagement risk is elevated (~{dr * 100:.0f}%) – "
                    f"easing difficulty from {difficulty_label} so practice stays achievable."
                )
            elif engagement < 0.45:
                bits.append(
                    f"Activity in this area is still ramping up (engagement ~{engagement * 100:.0f}%) – "
                    f"starting a notch easier than {difficulty_label}."
                )
            else:
                bits.append(
                    f"Conservative pacing for now – easing from {difficulty_label} while your signals stabilize."
                )
        elif action == Action.KEEP_DIFFICULTY:
            bits.append(f"Accuracy at {acc * 100:.0f}% sits in the productive zone – holding difficulty steady.")
        elif action == Action.CHANGE_TOPIC:
            bits.append("Recent performance plateaued on this topic – switching to keep engagement up.")
        elif action == Action.GIVE_HINT:
            bits.append("Learner is stuck on the current concept – surfacing a hint.")
        elif action == Action.SHORTEN_QUIZ:
            bits.append("Engagement is dropping – shortening the quiz to lock in progress.")
        elif action == Action.EXTEND_QUIZ:
            bits.append(f"High engagement ({engagement:.2f}) – extending the quiz for deeper practice.")
        elif action == Action.RECOMMEND_REVISION:
            bits.append("Recurring mistakes detected – recommending a focused revision module.")
        elif action == Action.RECOMMEND_PROJECT:
            bits.append("Mastery signals strong – recommending an applied project to consolidate learning.")
        elif action == Action.RECOMMEND_RESOURCE:
            bits.append("Surfacing a curated resource aligned with the current topic.")

        if feedback and feedback.is_correct is True and feedback.streak_length >= 3:
            bits.append(f"({int(feedback.streak_length)} correct in a row.)")
        if feedback and feedback.is_correct is False and feedback.repeated_mistake:
            bits.append("(Same concept missed again – reinforcement scheduled.)")

        # Append the most informative reward note if we have one.
        for note in reward_notes:
            if note and note not in " ".join(bits).lower():
                bits.append(f"Signal: {note}.")
                break

        return " ".join(bits) or f"Selected '{action.value}' from current learner state."
