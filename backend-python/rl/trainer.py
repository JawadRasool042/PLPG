"""
Training utilities.

Two training modes are supported:

1. **Offline batch replay** – sweep through stored transitions and
   apply the Q-learning update repeatedly. This is what the
   ``POST /api/rl/train`` endpoint triggers.

2. **Simulator bootstrap** – when there are not yet enough real
   transitions, synthesise episodes against
   :class:`rl.environment.SimulatedLearner` so the agent has sensible
   priors before its first real user.

Both modes work against the same :class:`QLearningAgent` instance and
persist results via :class:`RLRepository`.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import CONFIG, RLConfig
from .environment import SimulatedLearner
from .q_learning import QLearningAgent
from .schemas import Action, ACTION_INDEX, ACTION_LIST, LearnerState
from .state_builder import StateBuilder
from .storage import RLRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TrainingReport:
    mode: str
    episodes: int = 0
    steps: int = 0
    avg_reward: float = 0.0
    td_error_mean: float = 0.0
    td_error_max: float = 0.0
    epsilon_after: float = 0.0
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "episodes": int(self.episodes),
            "steps": int(self.steps),
            "avg_reward": round(float(self.avg_reward), 4),
            "td_error_mean": round(float(self.td_error_mean), 4),
            "td_error_max": round(float(self.td_error_max), 4),
            "epsilon_after": round(float(self.epsilon_after), 4),
            "extras": dict(self.extras),
        }


class RLTrainer:
    """High-level trainer that orchestrates Q-learning updates."""

    def __init__(
        self,
        agent: QLearningAgent,
        repository: RLRepository,
        config: Optional[RLConfig] = None,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.config = config or CONFIG
        self.state_builder = StateBuilder(self.config)

    # ------------------------------------------------------------------ #
    # Replay training (offline)
    # ------------------------------------------------------------------ #
    def replay_train(
        self,
        *,
        epochs: Optional[int] = None,
        batch_size: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> TrainingReport:
        """
        Replay stored transitions and apply Q-learning updates.

        Returns a :class:`TrainingReport` summarising progress so it
        can be returned by the API.
        """
        epochs = epochs if epochs is not None else self.config.trainer.epochs
        batch_size = batch_size if batch_size is not None else self.config.trainer.batch_size

        transitions = list(self.repository.iter_transitions(user_id=user_id))
        report = TrainingReport(mode="replay")
        if len(transitions) < self.config.trainer.min_transitions:
            report.extras["skipped_reason"] = (
                f"Need at least {self.config.trainer.min_transitions} transitions, "
                f"got {len(transitions)}."
            )
            report.epsilon_after = self.agent.epsilon
            return report

        rng = random.Random()
        td_errors: List[float] = []
        rewards: List[float] = []

        for _epoch in range(int(epochs)):
            shuffled = transitions[:]
            rng.shuffle(shuffled)
            for start in range(0, len(shuffled), int(batch_size)):
                batch = shuffled[start : start + int(batch_size)]
                for tr in batch:
                    state = self._state_from_storage(tr.get("state_json"))
                    next_state = self._state_from_storage(tr.get("next_state_json"))
                    if state is None:
                        continue
                    try:
                        action = Action.from_str(tr["action"])
                    except ValueError:
                        continue
                    reward = float(tr.get("reward") or 0.0)
                    terminal = bool(tr.get("terminal"))
                    td = self.agent.update(state, action, reward, next_state, terminal)
                    td_errors.append(abs(td))
                    rewards.append(reward)
                    report.steps += 1
                    if terminal:
                        report.episodes += 1

        if td_errors:
            report.td_error_mean = sum(td_errors) / len(td_errors)
            report.td_error_max = max(td_errors)
        if rewards:
            report.avg_reward = sum(rewards) / len(rewards)
        report.epsilon_after = self.agent.epsilon
        report.extras["transition_count"] = len(transitions)
        return report

    # ------------------------------------------------------------------ #
    # Simulator bootstrap
    # ------------------------------------------------------------------ #
    def simulate_train(
        self,
        *,
        episodes: int = 200,
        max_steps: int = 30,
        seed: Optional[int] = None,
    ) -> TrainingReport:
        """Use the toy simulator to seed the Q-table before real users arrive."""
        sim = SimulatedLearner(seed=seed, config=self.config)
        report = TrainingReport(mode="simulator")
        td_errors: List[float] = []
        rewards: List[float] = []

        for _ep in range(int(episodes)):
            state = sim.reset()
            steps = 0
            while steps < int(max_steps):
                action, _, _ = self.agent.select_action(state)
                next_state, reward, terminal, _ = sim.step(state, action)
                td = self.agent.update(state, action, reward, next_state, terminal)
                td_errors.append(abs(td))
                rewards.append(reward)
                state = next_state
                steps += 1
                report.steps += 1
                if terminal:
                    break
            report.episodes += 1

        if td_errors:
            report.td_error_mean = sum(td_errors) / len(td_errors)
            report.td_error_max = max(td_errors)
        if rewards:
            report.avg_reward = sum(rewards) / len(rewards)
        report.epsilon_after = self.agent.epsilon
        return report

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _state_from_storage(self, payload: Optional[Dict[str, Any]]) -> Optional[LearnerState]:
        if not payload:
            return None
        try:
            raw = payload.get("raw") or {}
            return LearnerState(
                domain=str(payload.get("domain") or raw.get("domain") or ""),
                profile=str(payload.get("profile") or raw.get("profile") or "Explorer"),
                difficulty_bucket=int(payload.get("difficulty_bucket", 0)),
                accuracy_bucket=int(payload.get("accuracy_bucket", 0)),
                response_time_bucket=int(payload.get("response_time_bucket", 0)),
                streak_bucket=int(payload.get("streak_bucket", 0)),
                wrong_bucket=int(payload.get("wrong_bucket", 0)),
                hint_bucket=int(payload.get("hint_bucket", 0)),
                engagement_bucket=int(payload.get("engagement_bucket", 0)),
                dropout_risk_bucket=int(payload.get("dropout_risk_bucket", 0)),
                topic_perf_bucket=int(payload.get("topic_perf_bucket", 0)),
                raw=raw if isinstance(raw, dict) else {},
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Could not restore LearnerState from storage: %s", exc)
            return None
