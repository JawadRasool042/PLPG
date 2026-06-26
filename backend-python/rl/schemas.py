"""
Strongly-typed schemas for the RL pipeline.

Using dataclasses (slots=True) keeps the runtime cheap while still
producing serialisable, validated payloads for the API layer.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Action(str, Enum):
    """Discrete actions the RL agent can output."""

    INCREASE_DIFFICULTY = "increase_difficulty"
    DECREASE_DIFFICULTY = "decrease_difficulty"
    KEEP_DIFFICULTY = "keep_difficulty"
    CHANGE_TOPIC = "change_topic"
    GIVE_HINT = "give_hint"
    SHORTEN_QUIZ = "shorten_quiz"
    EXTEND_QUIZ = "extend_quiz"
    RECOMMEND_REVISION = "recommend_revision"
    RECOMMEND_PROJECT = "recommend_project"
    RECOMMEND_RESOURCE = "recommend_resource"

    @classmethod
    def from_str(cls, value: str) -> "Action":
        if isinstance(value, Action):
            return value
        norm = str(value or "").strip().lower()
        for action in cls:
            if action.value == norm:
                return action
        raise ValueError(f"Unknown action: {value!r}")


# Stable index ordering used by the Q-table and storage layer.
ACTION_LIST: List[Action] = list(Action)
ACTION_INDEX: Dict[Action, int] = {a: i for i, a in enumerate(ACTION_LIST)}


class EpisodeStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    EXPIRED = "expired"


@dataclass(slots=True)
class LearnerState:
    """
    Discretised representation of a learner's situation.

    The tuple `to_key()` is what the tabular Q-learning agent uses as
    the dictionary key. The vector form is exposed for future extension
    to function approximators (DQN, contextual bandits).
    """

    domain: str
    profile: str
    difficulty_bucket: int
    accuracy_bucket: int
    response_time_bucket: int
    streak_bucket: int
    wrong_bucket: int
    hint_bucket: int
    engagement_bucket: int
    dropout_risk_bucket: int
    topic_perf_bucket: int

    # Continuous metadata kept for logging/diagnostics; NOT used for the Q-key.
    raw: Dict[str, float] = field(default_factory=dict)

    def to_key(self) -> Tuple[Any, ...]:
        return (
            self.domain,
            self.profile,
            self.difficulty_bucket,
            self.accuracy_bucket,
            self.response_time_bucket,
            self.streak_bucket,
            self.wrong_bucket,
            self.hint_bucket,
            self.engagement_bucket,
            self.dropout_risk_bucket,
            self.topic_perf_bucket,
        )

    def to_vector(self) -> List[float]:
        """Numerical vector representation (DQN-ready)."""
        return [
            float(self.difficulty_bucket),
            float(self.accuracy_bucket),
            float(self.response_time_bucket),
            float(self.streak_bucket),
            float(self.wrong_bucket),
            float(self.hint_bucket),
            float(self.engagement_bucket),
            float(self.dropout_risk_bucket),
            float(self.topic_perf_bucket),
        ]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StepFeedback:
    """
    Outcome of a single learner-environment interaction (typically one
    answered question or a session-level signal). Consumed by the
    reward function to compute the scalar reward for the transition.
    """

    is_correct: Optional[bool] = None
    response_time_sec: Optional[float] = None
    expected_time_sec: float = 25.0
    used_hint: bool = False
    repeated_mistake: bool = False
    streak_length: int = 0
    quiz_completed: bool = False
    quiz_dropped: bool = False
    score_delta: Optional[float] = None       # current - previous quiz score (0..100)
    returned_next_session: bool = False
    notes: Optional[str] = None


@dataclass(slots=True)
class Decision:
    """
    The output of the RL policy returned to API callers and the frontend.
    Mirrors the JSON contract requested in the project spec.
    """

    state: LearnerState
    action: Action
    reason: str
    expected_reward: float
    next_difficulty: str
    exploration: bool
    policy_version: int
    episode_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": {
                "domain": self.state.domain,
                "profile": self.state.profile,
                "difficulty": self.state.raw.get("difficulty_label", ""),
                "accuracy": round(float(self.state.raw.get("accuracy", 0.0)), 4),
                "response_time": round(float(self.state.raw.get("response_time", 0.0)), 2),
                "streak": int(self.state.raw.get("streak", 0)),
                "wrong_answers": int(self.state.raw.get("wrong_answers", 0)),
                "hints_used": int(self.state.raw.get("hints_used", 0)),
                "engagement_score": round(float(self.state.raw.get("engagement_score", 0.0)), 3),
                "dropout_risk": round(float(self.state.raw.get("dropout_risk", 0.0)), 3),
                "topic_performance": round(float(self.state.raw.get("topic_performance", 0.0)), 3),
                "buckets": {
                    "difficulty": self.state.difficulty_bucket,
                    "accuracy": self.state.accuracy_bucket,
                    "response_time": self.state.response_time_bucket,
                    "streak": self.state.streak_bucket,
                    "wrong": self.state.wrong_bucket,
                    "hint": self.state.hint_bucket,
                    "engagement": self.state.engagement_bucket,
                    "dropout_risk": self.state.dropout_risk_bucket,
                    "topic_performance": self.state.topic_perf_bucket,
                },
            },
            "action": self.action.value,
            "reason": self.reason,
            "reward": round(float(self.expected_reward), 4),
            "next_difficulty": self.next_difficulty,
            "exploration": self.exploration,
            "policy_version": self.policy_version,
            "episode_id": self.episode_id,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Transition:
    """One (s, a, r, s', done) tuple persisted to storage."""

    user_id: str
    episode_id: int
    step: int
    state: LearnerState
    action: Action
    reward: float
    next_state: Optional[LearnerState]
    terminal: bool
    feedback: StepFeedback
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_storage_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "episode_id": self.episode_id,
            "step": self.step,
            "state": self.state.to_dict() if self.state else None,
            "action": self.action.value,
            "reward": float(self.reward),
            "next_state": self.next_state.to_dict() if self.next_state else None,
            "terminal": bool(self.terminal),
            "feedback": asdict(self.feedback),
            "created_at": self.created_at.isoformat(),
        }
