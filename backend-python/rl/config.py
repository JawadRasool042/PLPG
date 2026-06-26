"""
Centralized configuration for the RL module.

All hyperparameters, reward weights, bucket boundaries and storage
paths live here so they can be tuned without touching the algorithm
code. Values are sourced from environment variables when present so
the module is easy to retune in production without redeploys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class QLearningHyperparameters:
    """Tabular Q-learning hyperparameters."""

    alpha: float = field(default_factory=lambda: _env_float("RL_Q_ALPHA", 0.15))
    gamma: float = field(default_factory=lambda: _env_float("RL_Q_GAMMA", 0.90))
    epsilon_start: float = field(default_factory=lambda: _env_float("RL_Q_EPSILON_START", 0.30))
    epsilon_min: float = field(default_factory=lambda: _env_float("RL_Q_EPSILON_MIN", 0.05))
    epsilon_decay: float = field(default_factory=lambda: _env_float("RL_Q_EPSILON_DECAY", 0.995))
    optimistic_init: float = field(default_factory=lambda: _env_float("RL_Q_OPTIMISTIC_INIT", 0.5))
    max_state_history: int = field(default_factory=lambda: _env_int("RL_Q_HISTORY_LIMIT", 5000))


@dataclass(slots=True)
class RewardConfig:
    """Reward weights for shaping the agent's learning signal."""

    correct: float = field(default_factory=lambda: _env_float("RL_R_CORRECT", 5.0))
    fast_correct_bonus: float = field(default_factory=lambda: _env_float("RL_R_FAST_BONUS", 3.0))
    slow_correct_penalty: float = field(default_factory=lambda: _env_float("RL_R_SLOW_PENALTY", -1.0))
    streak_bonus_per_step: float = field(default_factory=lambda: _env_float("RL_R_STREAK_STEP", 1.0))
    wrong: float = field(default_factory=lambda: _env_float("RL_R_WRONG", -3.0))
    repeated_mistake_extra: float = field(default_factory=lambda: _env_float("RL_R_REPEAT_WRONG", -2.0))
    hint_penalty: float = field(default_factory=lambda: _env_float("RL_R_HINT", -1.0))
    quiz_completed: float = field(default_factory=lambda: _env_float("RL_R_QUIZ_DONE", 10.0))
    quiz_dropped: float = field(default_factory=lambda: _env_float("RL_R_QUIZ_DROP", -15.0))
    improved_score: float = field(default_factory=lambda: _env_float("RL_R_IMPROVED", 8.0))
    declined_score: float = field(default_factory=lambda: _env_float("RL_R_DECLINED", -3.0))
    return_next_session: float = field(default_factory=lambda: _env_float("RL_R_RETURN", 12.0))

    # Caps so a single transition cannot dominate Q-values.
    reward_clip_low: float = field(default_factory=lambda: _env_float("RL_R_CLIP_LOW", -25.0))
    reward_clip_high: float = field(default_factory=lambda: _env_float("RL_R_CLIP_HIGH", 30.0))


@dataclass(slots=True)
class StateBuckets:
    """Boundaries used to discretise continuous signals into state buckets."""

    accuracy_bins: tuple = (0.40, 0.60, 0.80)             # -> 4 buckets
    response_time_bins_sec: tuple = (8.0, 20.0)           # -> 3 buckets (fast/med/slow)
    streak_bins: tuple = (1, 3)                           # -> 3 buckets
    wrong_bins: tuple = (1, 3)                            # -> 3 buckets
    hint_bins: tuple = (0, 2)                             # -> 3 buckets
    engagement_bins: tuple = (0.4, 0.7)                   # -> 3 buckets
    dropout_risk_bins: tuple = (0.3, 0.6)                 # -> 3 buckets
    topic_perf_bins: tuple = (0.5, 0.75)                  # -> 3 buckets


@dataclass(slots=True)
class StorageConfig:
    """Where the SQLite policy & transition store lives."""

    db_path: str = field(
        default_factory=lambda: os.getenv(
            "RL_DB_PATH",
            str(Path(__file__).resolve().parent.parent / "data" / "rl_engine.sqlite3"),
        )
    )
    policy_scope: str = field(default_factory=lambda: os.getenv("RL_POLICY_SCOPE", "per_domain"))
    # Versioning lets us migrate Q-tables forward without losing data.
    schema_version: int = 1


@dataclass(slots=True)
class TrainerConfig:
    """Offline replay-training configuration."""

    batch_size: int = field(default_factory=lambda: _env_int("RL_TRAIN_BATCH_SIZE", 256))
    epochs: int = field(default_factory=lambda: _env_int("RL_TRAIN_EPOCHS", 5))
    min_transitions: int = field(default_factory=lambda: _env_int("RL_TRAIN_MIN_TRANSITIONS", 32))
    cold_start_explore_epsilon: float = field(default_factory=lambda: _env_float("RL_COLD_EPSILON", 0.50))


@dataclass(slots=True)
class RLConfig:
    """Top-level configuration aggregator."""

    q: QLearningHyperparameters = field(default_factory=QLearningHyperparameters)
    reward: RewardConfig = field(default_factory=RewardConfig)
    buckets: StateBuckets = field(default_factory=StateBuckets)
    storage: StorageConfig = field(default_factory=StorageConfig)
    trainer: TrainerConfig = field(default_factory=TrainerConfig)

    # Mapping from numeric difficulty bucket to human-readable label.
    DIFFICULTY_LEVELS: tuple = ("beginner", "intermediate", "advanced")

    # Default supported domains. Falls back gracefully if engine domain list differs.
    DEFAULT_DOMAINS: tuple = (
        "Coding",
        "Web Development",
        "Game Development",
        "Cybersecurity",
        "Data Science",
        "Mobile Development",
        "Cloud Computing",
        "AI & Machine Learning",
        "Physical Games / Sports",
    )

    def difficulty_label(self, bucket: int) -> str:
        bucket = max(0, min(len(self.DIFFICULTY_LEVELS) - 1, int(bucket)))
        return self.DIFFICULTY_LEVELS[bucket]

    def difficulty_bucket(self, label: str) -> int:
        if not label:
            return 0
        norm = str(label).strip().lower()
        # Accept synonyms used by the legacy quiz API.
        if norm in {"beginner", "easy", "1", "low"}:
            return 0
        if norm in {"intermediate", "medium", "2", "mid"}:
            return 1
        if norm in {"advanced", "hard", "3", "expert", "high"}:
            return 2
        # Unknown -> intermediate is the safest default.
        return 1


CONFIG = RLConfig()
