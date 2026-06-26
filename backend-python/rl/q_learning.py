"""
Tabular Q-learning agent.

The agent is intentionally lightweight (a defaultdict-backed table) so
the production deployment doesn't need a deep-learning runtime. The
public API mirrors what a future Deep Q-Network agent would expose
(``select_action``, ``update``, ``save``, ``load``, ``q_values``), so
the policy / service layers can be swapped to DQN later without
re-plumbing.
"""

from __future__ import annotations

import json
import logging
import random
import threading
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import CONFIG, QLearningHyperparameters
from .schemas import Action, ACTION_INDEX, ACTION_LIST, LearnerState

logger = logging.getLogger(__name__)

# A state key is a tuple; an action key is the Action enum value.
_StateKey = Tuple[Any, ...]


class QLearningAgent:
    """Thread-safe tabular Q-learning agent."""

    def __init__(
        self,
        hyper: Optional[QLearningHyperparameters] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.hyper = hyper or CONFIG.q
        self._rng = rng or random.Random()
        self._lock = threading.RLock()
        self._q_table: Dict[_StateKey, List[float]] = defaultdict(self._initial_action_values)
        self.epsilon: float = self.hyper.epsilon_start
        self.episodes_trained: int = 0
        self.steps_trained: int = 0
        self.version: int = 1

    # ------------------------------------------------------------------ #
    # Q-value access helpers
    # ------------------------------------------------------------------ #
    def _initial_action_values(self) -> List[float]:
        # Optimistic initialisation encourages exploration in early training.
        return [self.hyper.optimistic_init for _ in ACTION_LIST]

    def q_values(self, state: LearnerState) -> Dict[str, float]:
        """Return a JSON-friendly mapping of action -> Q-value."""
        with self._lock:
            row = self._q_table[state.to_key()]
            return {a.value: round(float(row[ACTION_INDEX[a]]), 4) for a in ACTION_LIST}

    def best_action(self, state: LearnerState) -> Tuple[Action, float]:
        """Return the greedy action (ties broken randomly) and its Q-value."""
        with self._lock:
            row = self._q_table[state.to_key()]
            best_value = max(row)
            candidates = [i for i, v in enumerate(row) if v == best_value]
            choice = self._rng.choice(candidates)
            return ACTION_LIST[choice], float(best_value)

    # ------------------------------------------------------------------ #
    # Action selection
    # ------------------------------------------------------------------ #
    def select_action(
        self,
        state: LearnerState,
        *,
        valid_actions: Optional[Iterable[Action]] = None,
        force_explore: bool = False,
    ) -> Tuple[Action, bool, float]:
        """
        Epsilon-greedy action selection.

        Returns ``(action, exploration_flag, expected_q_value)``.
        ``valid_actions`` lets the caller mask actions that don't make
        sense in the current context (e.g. cannot increase difficulty
        if already at advanced).
        """
        with self._lock:
            row = self._q_table[state.to_key()]
            allowed = list(valid_actions) if valid_actions else list(ACTION_LIST)
            if not allowed:
                allowed = list(ACTION_LIST)

            explore = force_explore or (self._rng.random() < self.epsilon)
            if explore:
                action = self._rng.choice(allowed)
                return action, True, float(row[ACTION_INDEX[action]])

            best_action: Optional[Action] = None
            best_value = float("-inf")
            for action in allowed:
                value = row[ACTION_INDEX[action]]
                if value > best_value:
                    best_action = action
                    best_value = value
            assert best_action is not None
            return best_action, False, float(best_value)

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    def update(
        self,
        state: LearnerState,
        action: Action,
        reward: float,
        next_state: Optional[LearnerState],
        terminal: bool,
    ) -> float:
        """Apply the Bellman update and return the TD error."""
        with self._lock:
            s_key = state.to_key()
            row = self._q_table[s_key]
            current = row[ACTION_INDEX[action]]

            if terminal or next_state is None:
                target = float(reward)
            else:
                next_row = self._q_table[next_state.to_key()]
                target = float(reward) + self.hyper.gamma * max(next_row)

            td_error = target - current
            row[ACTION_INDEX[action]] = current + self.hyper.alpha * td_error
            self.steps_trained += 1

            if terminal:
                self.episodes_trained += 1
                self._decay_epsilon()

            return td_error

    def _decay_epsilon(self) -> None:
        self.epsilon = max(self.hyper.epsilon_min, self.epsilon * self.hyper.epsilon_decay)

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #
    def to_serialisable(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "version": self.version,
                "epsilon": self.epsilon,
                "episodes_trained": self.episodes_trained,
                "steps_trained": self.steps_trained,
                "actions": [a.value for a in ACTION_LIST],
                "table": [
                    {"state": list(state_key), "values": list(values)}
                    for state_key, values in self._q_table.items()
                ],
            }

    def to_json(self) -> str:
        return json.dumps(self.to_serialisable(), separators=(",", ":"))

    @classmethod
    def from_serialisable(
        cls,
        payload: Dict[str, Any],
        hyper: Optional[QLearningHyperparameters] = None,
    ) -> "QLearningAgent":
        agent = cls(hyper=hyper)
        if not isinstance(payload, dict):
            return agent
        agent.epsilon = float(payload.get("epsilon", agent.hyper.epsilon_start))
        agent.episodes_trained = int(payload.get("episodes_trained", 0))
        agent.steps_trained = int(payload.get("steps_trained", 0))
        agent.version = int(payload.get("version", 1))

        action_order = payload.get("actions") or [a.value for a in ACTION_LIST]
        action_remap = [ACTION_INDEX[Action.from_str(name)] for name in action_order]

        with agent._lock:
            for entry in payload.get("table", []):
                try:
                    state_key = tuple(entry["state"])
                    raw_values = entry["values"]
                except (KeyError, TypeError):
                    continue
                row = agent._initial_action_values()
                for src_idx, dest_idx in enumerate(action_remap):
                    if src_idx < len(raw_values):
                        try:
                            row[dest_idx] = float(raw_values[src_idx])
                        except (TypeError, ValueError):
                            continue
                agent._q_table[state_key] = row
        return agent

    @classmethod
    def from_json(cls, raw: str, hyper: Optional[QLearningHyperparameters] = None) -> "QLearningAgent":
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("QLearningAgent.from_json: invalid payload (%s); returning fresh agent", exc)
            return cls(hyper=hyper)
        return cls.from_serialisable(payload, hyper=hyper)

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #
    def state_count(self) -> int:
        with self._lock:
            return len(self._q_table)

    def top_actions(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Return the top-N (state, action, q) triples for inspection."""
        with self._lock:
            scored: List[Tuple[float, Tuple[Any, ...], Action]] = []
            for state_key, row in self._q_table.items():
                for idx, value in enumerate(row):
                    scored.append((float(value), state_key, ACTION_LIST[idx]))
            scored.sort(reverse=True, key=lambda x: x[0])
            return [
                {"state": list(state_key), "action": action.value, "q": round(value, 4)}
                for value, state_key, action in scored[:top_n]
            ]
