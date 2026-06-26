"""
Learning environment.

A lightweight Gym-style environment that the trainer uses to turn an
:class:`Action` into an updated set of learner-controllable knobs
(``next_difficulty``, ``next_topic``, ``hint_required``, ``quiz_length_delta``,
etc.).

The class is split into:

* :class:`LearningEnvironment` – the side-effect-free "what does this
  action mean for the next quiz?" calculator. It is what the API uses
  to translate an RL decision into something the quiz generator can
  consume.

* :class:`SimulatedLearner` – an optional toy simulator used only for
  bootstrapping training before real interaction data is available.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .config import CONFIG, RLConfig
from .reward import RewardFunction
from .schemas import Action, LearnerState, StepFeedback
from .state_builder import StateBuilder

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EnvironmentEffect:
    """Concrete effects an action has on the next learning step."""

    next_difficulty: str
    quiz_length_delta: int = 0
    change_topic: bool = False
    deliver_hint: bool = False
    recommend_revision: bool = False
    recommend_project: bool = False
    recommend_resource: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "next_difficulty": self.next_difficulty,
            "quiz_length_delta": int(self.quiz_length_delta),
            "change_topic": bool(self.change_topic),
            "deliver_hint": bool(self.deliver_hint),
            "recommend_revision": bool(self.recommend_revision),
            "recommend_project": bool(self.recommend_project),
            "recommend_resource": bool(self.recommend_resource),
            "metadata": dict(self.metadata),
        }


class LearningEnvironment:
    """Maps actions to concrete environmental effects."""

    EXTEND_DELTA = 5
    SHORTEN_DELTA = -3

    def __init__(self, config: Optional[RLConfig] = None) -> None:
        self.config = config or CONFIG

    def apply(self, state: LearnerState, action: Action) -> EnvironmentEffect:
        bucket = state.difficulty_bucket
        next_bucket = bucket
        effect = EnvironmentEffect(next_difficulty=self.config.difficulty_label(bucket))

        if action == Action.INCREASE_DIFFICULTY:
            next_bucket = min(len(self.config.DIFFICULTY_LEVELS) - 1, bucket + 1)
        elif action == Action.DECREASE_DIFFICULTY:
            next_bucket = max(0, bucket - 1)
        elif action == Action.CHANGE_TOPIC:
            effect.change_topic = True
        elif action == Action.GIVE_HINT:
            effect.deliver_hint = True
        elif action == Action.EXTEND_QUIZ:
            effect.quiz_length_delta = self.EXTEND_DELTA
        elif action == Action.SHORTEN_QUIZ:
            effect.quiz_length_delta = self.SHORTEN_DELTA
        elif action == Action.RECOMMEND_REVISION:
            effect.recommend_revision = True
        elif action == Action.RECOMMEND_PROJECT:
            effect.recommend_project = True
        elif action == Action.RECOMMEND_RESOURCE:
            effect.recommend_resource = True

        effect.next_difficulty = self.config.difficulty_label(next_bucket)
        effect.metadata["from_difficulty"] = self.config.difficulty_label(bucket)
        effect.metadata["action"] = action.value
        return effect


# ---------------------------------------------------------------------------
# Simulator (training only)
# ---------------------------------------------------------------------------


class SimulatedLearner:
    """
    Toy stochastic learner used to bootstrap training before live data
    is available.  It is **not** used in production – live transitions
    come from real users via :mod:`rl.api`.

    The simulator's behaviour is intentionally simple but realistic
    enough to teach the agent useful priors:

    * Higher difficulty -> lower correct probability.
    * Fast/correct streaks build engagement and reduce dropout risk.
    * Repeated wrong answers ramp dropout risk quickly.
    * Hints raise success rate but eat engagement.
    """

    def __init__(self, seed: Optional[int] = None, config: Optional[RLConfig] = None) -> None:
        self.rng = random.Random(seed)
        self.config = config or CONFIG
        self.state_builder = StateBuilder(self.config)
        self.reward_fn = RewardFunction(self.config)
        self.env = LearningEnvironment(self.config)
        self._raw: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Episode lifecycle
    # ------------------------------------------------------------------ #
    def reset(self, domain: Optional[str] = None, profile: str = "Explorer") -> LearnerState:
        domain = domain or self.rng.choice(list(self.config.DEFAULT_DOMAINS))
        starting_difficulty = self.rng.choice([0, 1])
        self._raw = {
            "domain": domain,
            "profile": profile,
            "difficulty": self.config.difficulty_label(starting_difficulty),
            "accuracy": self.rng.uniform(0.4, 0.7),
            "response_time": self.rng.uniform(15.0, 30.0),
            "streak": 0,
            "wrong_answers": 0,
            "hints_used": 0,
            "engagement_score": self.rng.uniform(0.5, 0.8),
            "dropout_risk": self.rng.uniform(0.05, 0.30),
            "topic_performance": self.rng.uniform(0.4, 0.7),
        }
        return self.state_builder.build(self._raw)

    def step(self, state: LearnerState, action: Action) -> Tuple[LearnerState, float, bool, StepFeedback]:
        """Apply ``action``, return (next_state, reward, terminal, feedback)."""
        effect = self.env.apply(state, action)
        difficulty_idx = self.config.difficulty_bucket(effect.next_difficulty)

        # Probability of correct answer scales with topic perf and inversely with difficulty.
        base = 0.5 + 0.4 * float(self._raw.get("topic_performance", 0.5))
        difficulty_penalty = 0.18 * difficulty_idx
        hint_bonus = 0.20 if effect.deliver_hint else 0.0
        p_correct = max(0.05, min(0.95, base - difficulty_penalty + hint_bonus))

        is_correct = self.rng.random() < p_correct
        response_time = self.rng.uniform(8.0, 35.0)
        if is_correct and self.rng.random() < 0.3:
            response_time *= 0.6  # occasional fast correct answer

        # Update internal raw state
        self._raw["streak"] = (self._raw.get("streak", 0) + 1) if is_correct else 0
        if not is_correct:
            self._raw["wrong_answers"] = self._raw.get("wrong_answers", 0) + 1
        if effect.deliver_hint:
            self._raw["hints_used"] = self._raw.get("hints_used", 0) + 1
        self._raw["difficulty"] = effect.next_difficulty

        # Update soft signals
        new_accuracy = 0.85 * float(self._raw.get("accuracy", 0.5)) + 0.15 * (1.0 if is_correct else 0.0)
        new_engagement = 0.9 * float(self._raw.get("engagement_score", 0.6))
        if is_correct:
            new_engagement += 0.05
        else:
            new_engagement -= 0.04
        new_dropout = 0.85 * float(self._raw.get("dropout_risk", 0.2))
        if not is_correct:
            new_dropout += 0.07
        if effect.recommend_revision or effect.deliver_hint:
            new_dropout -= 0.03
        if action == Action.SHORTEN_QUIZ:
            new_dropout -= 0.05
        new_topic_perf = (
            float(self._raw.get("topic_performance", 0.5)) * 0.92
            + (0.08 if is_correct else 0.0)
        )

        if effect.change_topic:
            new_topic_perf = self.rng.uniform(0.3, 0.7)
            self._raw["streak"] = 0

        self._raw["accuracy"] = max(0.0, min(1.0, new_accuracy))
        self._raw["engagement_score"] = max(0.0, min(1.0, new_engagement))
        self._raw["dropout_risk"] = max(0.0, min(1.0, new_dropout))
        self._raw["topic_performance"] = max(0.0, min(1.0, new_topic_perf))
        self._raw["response_time"] = response_time

        feedback = StepFeedback(
            is_correct=is_correct,
            response_time_sec=response_time,
            expected_time_sec=25.0,
            used_hint=effect.deliver_hint,
            repeated_mistake=(not is_correct) and self._raw.get("wrong_answers", 0) >= 2,
            streak_length=self._raw["streak"],
        )

        next_state = self.state_builder.build(self._raw)

        # Episode terminates if dropout risk explodes or learner achieves mastery.
        terminal = self._raw["dropout_risk"] >= 0.92 or (
            self._raw["accuracy"] >= 0.92 and self._raw["streak"] >= 4
        )
        if terminal:
            feedback.quiz_completed = self._raw["accuracy"] >= 0.65
            feedback.quiz_dropped = not feedback.quiz_completed
            if feedback.quiz_completed:
                feedback.score_delta = 8.0
            else:
                feedback.score_delta = -8.0

        reward = self.reward_fn.compute(action, feedback).total
        return next_state, reward, terminal, feedback
