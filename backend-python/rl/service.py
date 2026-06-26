"""
RL service – the single orchestration entry point.

This is the layer used by both:

* the public Flask API (``rl.api``)
* internal callers (e.g. quiz routes that want the next adaptive action
  without exposing it as a separate HTTP round-trip).

The service is a process-wide singleton (`get_service()`) so the
in-memory Q-table can serve concurrent requests without re-loading
from disk on every call. All writes are persisted, so the singleton
restores cleanly after a process restart.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import CONFIG, RLConfig
from .environment import LearningEnvironment
from .policy import Policy
from .q_learning import QLearningAgent
from .reward import RewardFunction
from .schemas import (
    Action,
    Decision,
    EpisodeStatus,
    LearnerState,
    StepFeedback,
)
from .state_builder import StateBuilder
from .storage import RLRepository
from .trainer import RLTrainer, TrainingReport

logger = logging.getLogger(__name__)


GLOBAL_SCOPE = "global"


def _domain_scope(domain: str) -> str:
    return f"domain:{domain.strip()}"


class RLService:
    """High-level facade used by API and quiz integration code."""

    # Sessions older than this threshold count as a "next session" return.
    NEW_SESSION_THRESHOLD_MIN = 30

    def __init__(self, config: Optional[RLConfig] = None, repository: Optional[RLRepository] = None) -> None:
        self.config = config or CONFIG
        self.repository = repository or RLRepository(config=self.config)
        self.state_builder = StateBuilder(self.config)
        self.reward_fn = RewardFunction(self.config)
        self.environment = LearningEnvironment(self.config)
        self._lock = threading.RLock()
        self._agents: Dict[str, QLearningAgent] = {}
        self._policies: Dict[str, Policy] = {}

    # ------------------------------------------------------------------ #
    # Agent / policy lifecycle
    # ------------------------------------------------------------------ #
    def _get_agent(self, scope: str) -> QLearningAgent:
        with self._lock:
            agent = self._agents.get(scope)
            if agent is not None:
                return agent
            stored = self.repository.load_policy(scope)
            if stored and stored.get("q_table_json"):
                try:
                    agent = QLearningAgent.from_json(stored["q_table_json"], hyper=self.config.q)
                    agent.epsilon = float(stored.get("epsilon") or agent.epsilon)
                    agent.episodes_trained = int(stored.get("episodes_trained") or 0)
                    agent.steps_trained = int(stored.get("steps_trained") or 0)
                    agent.version = int(stored.get("version") or 1)
                    logger.info("Loaded policy '%s' (states=%d, episodes=%d)",
                                scope, agent.state_count(), agent.episodes_trained)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch on load
                    logger.exception("Failed to load policy '%s': %s", scope, exc)
                    agent = QLearningAgent(hyper=self.config.q)
            else:
                agent = QLearningAgent(hyper=self.config.q)
            self._agents[scope] = agent
            return agent

    def _get_policy(self, scope: str) -> Policy:
        with self._lock:
            policy = self._policies.get(scope)
            if policy is not None:
                return policy
            policy = Policy(self._get_agent(scope), reward_fn=self.reward_fn, config=self.config)
            self._policies[scope] = policy
            return policy

    def _scope_for(self, domain: Optional[str]) -> str:
        if not domain:
            return GLOBAL_SCOPE
        if self.config.storage.policy_scope == "global":
            return GLOBAL_SCOPE
        return _domain_scope(domain)

    def _persist_agent(self, scope: str) -> None:
        agent = self._agents.get(scope)
        if agent is None:
            return
        agent.version += 1
        self.repository.save_policy(
            scope,
            agent.to_json(),
            episodes_trained=agent.episodes_trained,
            steps_trained=agent.steps_trained,
            epsilon=agent.epsilon,
            version=agent.version,
        )

    # ------------------------------------------------------------------ #
    # Public operations
    # ------------------------------------------------------------------ #
    def next_action(
        self,
        user_id: str,
        payload: Dict[str, Any],
        *,
        force_explore: bool = False,
    ) -> Decision:
        """Return the next adaptive action for the learner."""
        if not user_id:
            raise ValueError("user_id is required")

        state = self.state_builder.build(payload)
        scope = self._scope_for(state.domain)
        policy = self._get_policy(scope)

        # Cold start if we have very little data anywhere.
        cold_start = self.repository.transition_count() < self.config.trainer.min_transitions

        active_episode = self.repository.get_active_episode(user_id, state.domain)
        if active_episode:
            episode_id = int(active_episode["id"])
        else:
            episode_id = self.repository.start_episode(
                user_id,
                state.domain,
                metadata={"profile": state.profile},
            )

        decision = policy.decide(state, force_explore=force_explore, cold_start=cold_start)
        decision.episode_id = episode_id

        # Audit trail – every recommendation is logged.
        self.repository.log_action(
            user_id=user_id,
            episode_id=episode_id,
            action=decision.action.value,
            reason=decision.reason,
            expected_reward=decision.expected_reward,
            next_difficulty=decision.next_difficulty,
            exploration=decision.exploration,
        )
        return decision

    def update_reward(
        self,
        user_id: str,
        action: str,
        feedback_payload: Dict[str, Any],
        previous_state_payload: Optional[Dict[str, Any]] = None,
        next_state_payload: Optional[Dict[str, Any]] = None,
        *,
        episode_id: Optional[int] = None,
        terminal: bool = False,
    ) -> Dict[str, Any]:
        """
        Record a transition and apply a Q-learning update.

        Either ``previous_state_payload`` or ``next_state_payload`` is
        required so the agent can position the transition in state-space.
        """
        if not user_id:
            raise ValueError("user_id is required")
        if not previous_state_payload and not next_state_payload:
            raise ValueError("previous_state or next_state is required")

        # Build states – previous is what was used to choose the action,
        # next is the resulting state after the user's response.
        prev_payload = previous_state_payload or next_state_payload or {}
        next_payload = next_state_payload or previous_state_payload or {}
        prev_state = self.state_builder.build(prev_payload)
        next_state = self.state_builder.build(next_payload) if next_state_payload is not None else None

        try:
            action_enum = Action.from_str(action)
        except ValueError as exc:
            raise ValueError(f"Unknown action '{action}'") from exc

        feedback = self._coerce_feedback(feedback_payload)

        # Cross-session bonus: did the user return after a long gap?
        feedback.returned_next_session = self._was_return_session(user_id) or feedback.returned_next_session

        breakdown = self.reward_fn.compute(action_enum, feedback)

        scope = self._scope_for(prev_state.domain)
        agent = self._get_agent(scope)

        # Resolve / open episode
        if episode_id is None:
            active_episode = self.repository.get_active_episode(user_id, prev_state.domain)
            episode_id = int(active_episode["id"]) if active_episode else self.repository.start_episode(
                user_id, prev_state.domain, metadata={"profile": prev_state.profile}
            )
        step = self._next_step_index(episode_id)

        td_error = agent.update(prev_state, action_enum, breakdown.total, next_state, terminal)
        self.repository.insert_transition(
            user_id=user_id,
            episode_id=episode_id,
            step=step,
            state=prev_state.to_dict(),
            action=action_enum.value,
            reward=breakdown.total,
            next_state=next_state.to_dict() if next_state else None,
            terminal=terminal,
            feedback={
                "is_correct": feedback.is_correct,
                "response_time_sec": feedback.response_time_sec,
                "expected_time_sec": feedback.expected_time_sec,
                "used_hint": feedback.used_hint,
                "repeated_mistake": feedback.repeated_mistake,
                "streak_length": feedback.streak_length,
                "quiz_completed": feedback.quiz_completed,
                "quiz_dropped": feedback.quiz_dropped,
                "score_delta": feedback.score_delta,
                "returned_next_session": feedback.returned_next_session,
                "notes": feedback.notes,
            },
            meta={
                "td_error": float(td_error),
                "reward_components": breakdown.components,
                "reward_notes": breakdown.notes,
            },
        )
        self.repository.update_episode_totals(episode_id, added_reward=breakdown.total, added_steps=1)

        if terminal:
            status = EpisodeStatus.COMPLETED if not feedback.quiz_dropped else EpisodeStatus.DROPPED
            self.repository.close_episode(episode_id, status=status)
            self._update_user_session(
                user_id,
                domain=prev_state.domain,
                last_score=feedback.score_delta if feedback.score_delta is not None else None,
            )
            self._persist_agent(scope)

        # Persist roughly every 25 in-flight steps to limit IO.
        if not terminal and (agent.steps_trained % 25 == 0):
            self._persist_agent(scope)

        return {
            "episode_id": episode_id,
            "step": step,
            "reward": round(float(breakdown.total), 4),
            "td_error": round(float(td_error), 6),
            "components": breakdown.to_dict()["components"],
            "notes": breakdown.notes,
            "policy_version": agent.version,
            "epsilon": round(float(agent.epsilon), 4),
        }

    def get_policy_summary(self, user_id: str) -> Dict[str, Any]:
        """Return policy + recent activity for a specific user."""
        sessions = self.repository.get_user_session(user_id) or {}
        episodes = self.repository.list_episodes(user_id, limit=20)
        actions = self.repository.latest_actions(user_id, limit=20)
        last_domain = sessions.get("last_domain") if sessions else None
        scope = self._scope_for(last_domain) if last_domain else GLOBAL_SCOPE
        agent = self._get_agent(scope)

        return {
            "user_id": user_id,
            "scope": scope,
            "policy": {
                "epsilon": round(agent.epsilon, 4),
                "version": agent.version,
                "episodes_trained": agent.episodes_trained,
                "steps_trained": agent.steps_trained,
                "states_covered": agent.state_count(),
                "top_actions": agent.top_actions(top_n=5),
            },
            "session": sessions,
            "recent_episodes": episodes,
            "recent_actions": actions,
        }

    def list_policies(self) -> List[Dict[str, Any]]:
        return self.repository.list_policies()

    def train(
        self,
        *,
        mode: str = "replay",
        episodes: int = 200,
        epochs: Optional[int] = None,
        batch_size: Optional[int] = None,
        user_id: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> TrainingReport:
        """Trigger offline replay training (default) or simulator bootstrap."""
        scope = self._scope_for(None)
        # Train across all domain scopes when running global training,
        # otherwise we only update the global agent.  For per-domain
        # training the API can call this for each domain via ``user_id``
        # or ``scope`` extension; current MVP uses the global aggregator.
        agent = self._get_agent(scope)
        trainer = RLTrainer(agent, self.repository, config=self.config)

        if mode == "simulator":
            report = trainer.simulate_train(episodes=episodes, seed=seed)
        else:
            report = trainer.replay_train(epochs=epochs, batch_size=batch_size, user_id=user_id)

        # Persist the updated agent.
        self._persist_agent(scope)
        return report

    def history(self, user_id: str, limit: int = 25) -> Dict[str, Any]:
        return {
            "transitions": self.repository.latest_transitions(user_id, limit=limit),
            "actions": self.repository.latest_actions(user_id, limit=limit),
            "episodes": self.repository.list_episodes(user_id, limit=limit),
        }

    def explain_action_effect(self, state_payload: Dict[str, Any], action: str) -> Dict[str, Any]:
        state = self.state_builder.build(state_payload)
        try:
            action_enum = Action.from_str(action)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        effect = self.environment.apply(state, action_enum)
        return effect.to_dict()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _next_step_index(self, episode_id: int) -> int:
        """Return the next zero-based step index for an episode."""
        with self.repository.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM rl_transitions WHERE episode_id=?",
                (int(episode_id),),
            ).fetchone()
        return int(row["c"]) if row else 0

    def _coerce_feedback(self, payload: Optional[Dict[str, Any]]) -> StepFeedback:
        if not payload:
            return StepFeedback()
        return StepFeedback(
            is_correct=_optional_bool(payload.get("is_correct")),
            response_time_sec=_optional_float(payload.get("response_time_sec") or payload.get("response_time")),
            expected_time_sec=float(payload.get("expected_time_sec") or 25.0),
            used_hint=bool(payload.get("used_hint", False)),
            repeated_mistake=bool(payload.get("repeated_mistake", False)),
            streak_length=int(payload.get("streak_length") or payload.get("streak") or 0),
            quiz_completed=bool(payload.get("quiz_completed", False)),
            quiz_dropped=bool(payload.get("quiz_dropped", False)),
            score_delta=_optional_float(payload.get("score_delta")),
            returned_next_session=bool(payload.get("returned_next_session", False)),
            notes=payload.get("notes"),
        )

    def _was_return_session(self, user_id: str) -> bool:
        session = self.repository.get_user_session(user_id)
        if not session or not session.get("last_session_at"):
            return False
        try:
            last = datetime.fromisoformat(str(session["last_session_at"]))
        except ValueError:
            return False
        return datetime.utcnow() - last >= timedelta(minutes=self.NEW_SESSION_THRESHOLD_MIN)

    def _update_user_session(
        self,
        user_id: str,
        *,
        domain: Optional[str] = None,
        last_score: Optional[float] = None,
    ) -> None:
        self.repository.upsert_user_session(
            user_id,
            last_session_at=datetime.utcnow(),
            last_score=last_score,
            last_domain=domain,
            increment_episodes=True,
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------


_service_lock = threading.Lock()
_service_singleton: Optional[RLService] = None


def get_service() -> RLService:
    """Return a process-wide :class:`RLService` instance."""
    global _service_singleton
    if _service_singleton is None:
        with _service_lock:
            if _service_singleton is None:
                _service_singleton = RLService()
    return _service_singleton


# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in {"true", "1", "yes", "correct"}:
            return True
        if norm in {"false", "0", "no", "wrong", "incorrect"}:
            return False
    return None
