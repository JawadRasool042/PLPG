"""
RL persistence layer.

Schema (SQLite for development, PostgreSQL-ready):

    rl_episodes
        id, user_id, domain, started_at, ended_at, total_reward,
        steps, status, metadata_json

    rl_transitions
        id, episode_id, user_id, step, state_json, action,
        reward, next_state_json, terminal, feedback_json,
        meta_json, created_at

    rl_actions_log
        id, user_id, episode_id, action, reason, expected_reward,
        next_difficulty, exploration, created_at

    rl_policy
        id, scope, q_table_json, episodes_trained, steps_trained,
        epsilon, version, schema_version, updated_at

    rl_user_session
        user_id, last_session_at, last_score, last_domain,
        total_episodes

The ``policy.scope`` column lets us keep one Q-table per domain
(``"domain:Web Development"``) plus a fallback ``"global"`` policy
that consolidates cross-domain experience.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .config import CONFIG, RLConfig
from .schemas import EpisodeStatus

logger = logging.getLogger(__name__)


class RLRepository:
    """SQLite-backed repository with a PostgreSQL-friendly schema."""

    def __init__(self, db_path: Optional[str] = None, config: Optional[RLConfig] = None) -> None:
        self.config = config or CONFIG
        self.db_path = db_path or self.config.storage.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # SQLite + threading: serialise writes through this lock.
        self._lock = threading.RLock()
        self._init_schema()

    # ------------------------------------------------------------------ #
    # Connection management
    # ------------------------------------------------------------------ #
    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            with self._lock:
                yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Schema bootstrap
    # ------------------------------------------------------------------ #
    def _init_schema(self) -> None:
        ddl = """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS rl_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            total_reward REAL NOT NULL DEFAULT 0,
            steps INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_rl_episodes_user
            ON rl_episodes (user_id, started_at DESC);

        CREATE TABLE IF NOT EXISTS rl_transitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            step INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            action TEXT NOT NULL,
            reward REAL NOT NULL,
            next_state_json TEXT,
            terminal INTEGER NOT NULL DEFAULT 0,
            feedback_json TEXT,
            meta_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(episode_id) REFERENCES rl_episodes(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_rl_transitions_user
            ON rl_transitions (user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_rl_transitions_episode
            ON rl_transitions (episode_id);

        CREATE TABLE IF NOT EXISTS rl_actions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            episode_id INTEGER,
            action TEXT NOT NULL,
            reason TEXT,
            expected_reward REAL,
            next_difficulty TEXT,
            exploration INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_rl_actions_user
            ON rl_actions_log (user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS rl_policy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL UNIQUE,
            q_table_json TEXT NOT NULL,
            episodes_trained INTEGER NOT NULL DEFAULT 0,
            steps_trained INTEGER NOT NULL DEFAULT 0,
            epsilon REAL NOT NULL DEFAULT 0,
            version INTEGER NOT NULL DEFAULT 1,
            schema_version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rl_user_session (
            user_id TEXT PRIMARY KEY,
            last_session_at TEXT,
            last_score REAL,
            last_domain TEXT,
            total_episodes INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """
        with self.connection() as conn:
            conn.executescript(ddl)

    # ------------------------------------------------------------------ #
    # Episode helpers
    # ------------------------------------------------------------------ #
    def start_episode(self, user_id: str, domain: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rl_episodes (user_id, domain, started_at, status, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, domain, now, EpisodeStatus.ACTIVE.value, json.dumps(metadata or {})),
            )
            return int(cursor.lastrowid)

    def update_episode_totals(
        self,
        episode_id: int,
        *,
        added_reward: float,
        added_steps: int = 1,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE rl_episodes
                   SET total_reward = total_reward + ?,
                       steps = steps + ?
                 WHERE id = ?
                """,
                (float(added_reward), int(added_steps), int(episode_id)),
            )

    def close_episode(
        self,
        episode_id: int,
        status: EpisodeStatus = EpisodeStatus.COMPLETED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            if metadata is None:
                conn.execute(
                    "UPDATE rl_episodes SET ended_at=?, status=? WHERE id=?",
                    (now, status.value, int(episode_id)),
                )
            else:
                conn.execute(
                    "UPDATE rl_episodes SET ended_at=?, status=?, metadata_json=? WHERE id=?",
                    (now, status.value, json.dumps(metadata), int(episode_id)),
                )

    def get_active_episode(self, user_id: str, domain: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM rl_episodes
                 WHERE user_id=? AND domain=? AND status=?
                 ORDER BY id DESC LIMIT 1
                """,
                (user_id, domain, EpisodeStatus.ACTIVE.value),
            ).fetchone()
        return _row_to_dict(row)

    def list_episodes(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM rl_episodes WHERE user_id=?
                 ORDER BY id DESC LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Transitions
    # ------------------------------------------------------------------ #
    def insert_transition(
        self,
        *,
        user_id: str,
        episode_id: int,
        step: int,
        state: Dict[str, Any],
        action: str,
        reward: float,
        next_state: Optional[Dict[str, Any]],
        terminal: bool,
        feedback: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rl_transitions
                    (episode_id, user_id, step, state_json, action, reward,
                     next_state_json, terminal, feedback_json, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(episode_id),
                    user_id,
                    int(step),
                    json.dumps(state),
                    action,
                    float(reward),
                    json.dumps(next_state) if next_state is not None else None,
                    1 if terminal else 0,
                    json.dumps(feedback or {}),
                    json.dumps(meta or {}),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def iter_transitions(self, *, user_id: Optional[str] = None, limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        query = "SELECT * FROM rl_transitions"
        params: List[Any] = []
        if user_id:
            query += " WHERE user_id=?"
            params.append(user_id)
        query += " ORDER BY id ASC"
        if limit:
            query += " LIMIT ?"
            params.append(int(limit))

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r, json_fields=("state_json", "next_state_json", "feedback_json", "meta_json")) for r in rows]

    def transition_count(self) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM rl_transitions").fetchone()
        return int(row["c"]) if row else 0

    def latest_transitions(self, user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM rl_transitions WHERE user_id=?
                 ORDER BY id DESC LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        return [
            _row_to_dict(r, json_fields=("state_json", "next_state_json", "feedback_json", "meta_json"))
            for r in rows
        ]

    # ------------------------------------------------------------------ #
    # Actions log (audit trail)
    # ------------------------------------------------------------------ #
    def log_action(
        self,
        *,
        user_id: str,
        episode_id: Optional[int],
        action: str,
        reason: str,
        expected_reward: float,
        next_difficulty: str,
        exploration: bool,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO rl_actions_log
                    (user_id, episode_id, action, reason, expected_reward,
                     next_difficulty, exploration, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    int(episode_id) if episode_id is not None else None,
                    action,
                    reason,
                    float(expected_reward),
                    next_difficulty,
                    1 if exploration else 0,
                    now,
                ),
            )

    def latest_actions(self, user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM rl_actions_log WHERE user_id=?
                 ORDER BY id DESC LIMIT ?
                """,
                (user_id, int(limit)),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Policy persistence
    # ------------------------------------------------------------------ #
    def save_policy(
        self,
        scope: str,
        q_table_json: str,
        *,
        episodes_trained: int,
        steps_trained: int,
        epsilon: float,
        version: int,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO rl_policy (scope, q_table_json, episodes_trained, steps_trained,
                                       epsilon, version, schema_version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scope) DO UPDATE SET
                    q_table_json = excluded.q_table_json,
                    episodes_trained = excluded.episodes_trained,
                    steps_trained = excluded.steps_trained,
                    epsilon = excluded.epsilon,
                    version = excluded.version,
                    schema_version = excluded.schema_version,
                    updated_at = excluded.updated_at
                """,
                (
                    scope,
                    q_table_json,
                    int(episodes_trained),
                    int(steps_trained),
                    float(epsilon),
                    int(version),
                    int(self.config.storage.schema_version),
                    now,
                ),
            )

    def load_policy(self, scope: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM rl_policy WHERE scope=?",
                (scope,),
            ).fetchone()
        return _row_to_dict(row)

    def list_policies(self) -> List[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT scope, episodes_trained, steps_trained, epsilon, version, updated_at FROM rl_policy"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Cross-session signals
    # ------------------------------------------------------------------ #
    def upsert_user_session(
        self,
        user_id: str,
        *,
        last_session_at: datetime,
        last_score: Optional[float] = None,
        last_domain: Optional[str] = None,
        increment_episodes: bool = False,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT total_episodes FROM rl_user_session WHERE user_id=?",
                (user_id,),
            ).fetchone()
            total = (int(existing["total_episodes"]) if existing else 0) + (1 if increment_episodes else 0)
            conn.execute(
                """
                INSERT INTO rl_user_session (user_id, last_session_at, last_score, last_domain,
                                             total_episodes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_session_at = excluded.last_session_at,
                    last_score = COALESCE(excluded.last_score, rl_user_session.last_score),
                    last_domain = COALESCE(excluded.last_domain, rl_user_session.last_domain),
                    total_episodes = excluded.total_episodes,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    last_session_at.isoformat(),
                    float(last_score) if last_score is not None else None,
                    last_domain,
                    total,
                    now,
                ),
            )

    def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM rl_user_session WHERE user_id=?",
                (user_id,),
            ).fetchone()
        return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(
    row: Optional[sqlite3.Row],
    json_fields: Iterable[str] = (),
) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    data = {key: row[key] for key in row.keys()}
    for field_name in json_fields:
        raw = data.get(field_name)
        if raw is None:
            continue
        try:
            data[field_name] = json.loads(raw)
        except (TypeError, ValueError):
            # Leave the raw string in-place; caller can handle it.
            continue
    # Decode the generic metadata_json column if present.
    if "metadata_json" in data and data["metadata_json"]:
        try:
            data["metadata"] = json.loads(data["metadata_json"])
        except (TypeError, ValueError):
            data["metadata"] = {}
    return data
