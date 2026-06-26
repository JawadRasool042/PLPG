"""SQLite-ready persistence for learning intelligence artifacts."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


class LearningPathRepository:
    """SQLite repository with a PostgreSQL-friendly schema shape."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "LEARNING_PATH_DB_PATH",
            str(Path(__file__).resolve().parent.parent / "data" / "learning_intelligence.sqlite3"),
        )
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        schema = """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT,
            full_name TEXT,
            learning_level TEXT,
            learning_style TEXT,
            weekly_availability_hours INTEGER,
            personality TEXT,
            preferences_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            raw_inputs_json TEXT NOT NULL,
            signal_summary_json TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            primary_domain TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            confidence_json TEXT NOT NULL,
            top_domains_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            streak_days INTEGER NOT NULL DEFAULT 0,
            weekly_score REAL NOT NULL DEFAULT 0,
            achievement_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS roadmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            roadmap_json TEXT NOT NULL,
            market_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            quiz_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            quiz_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 0,
            summary_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
        with self.connection() as conn:
            conn.executescript(schema)

    def upsert_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, full_name, learning_level, learning_style,
                                   weekly_availability_hours, personality, preferences_json,
                                   created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    email=excluded.email,
                    full_name=excluded.full_name,
                    learning_level=excluded.learning_level,
                    learning_style=excluded.learning_style,
                    weekly_availability_hours=excluded.weekly_availability_hours,
                    personality=excluded.personality,
                    preferences_json=excluded.preferences_json,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    payload.get("email"),
                    payload.get("full_name") or payload.get("name"),
                    payload.get("learning_level"),
                    payload.get("learning_style"),
                    payload.get("weekly_availability_hours"),
                    payload.get("personality"),
                    json.dumps(payload.get("preferences", {})),
                    now,
                    now,
                ),
            )

    def save_assessment(self, user_id: str, raw_inputs: Dict[str, Any], signal_summary: Dict[str, Any], profile: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO assessments (user_id, raw_inputs_json, signal_summary_json, profile_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, json.dumps(raw_inputs), json.dumps(signal_summary), json.dumps(profile), now),
            )

    def save_prediction(self, user_id: str, primary_domain: str, profile: Dict[str, Any], confidence: Dict[str, Any], top_domains: List[Dict[str, Any]]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO predictions (user_id, primary_domain, profile_json, confidence_json, top_domains_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    primary_domain,
                    json.dumps(profile),
                    json.dumps(confidence),
                    json.dumps(top_domains),
                    now,
                ),
            )

    def save_progress(self, user_id: str, domain: str, xp: int, level: int, streak_days: int, weekly_score: float, achievements: List[str]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO progress (user_id, domain, xp, level, streak_days, weekly_score, achievement_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, domain, xp, level, streak_days, weekly_score, json.dumps(achievements), now, now),
            )

    def save_roadmap(self, user_id: str, domain: str, roadmap: Dict[str, Any], market: Dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO roadmaps (user_id, domain, roadmap_json, market_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, domain, json.dumps(roadmap), json.dumps(market), now, now),
            )

    def save_quiz(self, user_id: str, domain: str, quiz_payload: Dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quizzes (user_id, domain, quiz_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, domain, json.dumps(quiz_payload), now),
            )
            return int(cursor.lastrowid)

    def save_quiz_attempt(
        self,
        user_id: str,
        quiz_id: int,
        domain: str,
        answers: Dict[str, Any],
        score: float,
        summary: Optional[Dict[str, Any]] = None,
    ) -> int:
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO quiz_attempts (user_id, quiz_id, domain, answers_json, score, summary_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, quiz_id, domain, json.dumps(answers), float(score), json.dumps(summary or {}), now),
            )
            return int(cursor.lastrowid)

    def get_latest_prediction(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "primary_domain": row["primary_domain"],
                "profile": json.loads(row["profile_json"]),
                "confidence": json.loads(row["confidence_json"]),
                "top_domains": json.loads(row["top_domains_json"]),
                "created_at": row["created_at"],
            }

    def get_latest_roadmap(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM roadmaps WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "domain": row["domain"],
                "roadmap": json.loads(row["roadmap_json"]),
                "career_market": json.loads(row["market_json"]),
                "created_at": row["created_at"],
            }

    def get_latest_progress(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM progress WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "domain": row["domain"],
                "xp": row["xp"],
                "level": row["level"],
                "streak_days": row["streak_days"],
                "weekly_score": row["weekly_score"],
                "achievements": json.loads(row["achievement_json"] or "[]"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def get_latest_quiz(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM quizzes WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "quiz_id": row["id"],
                "domain": row["domain"],
                "quiz": json.loads(row["quiz_json"]),
                "created_at": row["created_at"],
            }

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            user_row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not user_row:
                return None

        return {
            "user": {
                "id": user_id,
                "email": user_row["email"],
                "full_name": user_row["full_name"],
                "learning_level": user_row["learning_level"],
                "learning_style": user_row["learning_style"],
                "weekly_availability_hours": user_row["weekly_availability_hours"],
                "personality": user_row["personality"],
                "preferences": json.loads(user_row["preferences_json"] or "{}"),
                "updated_at": user_row["updated_at"],
            },
            "latest_prediction": self.get_latest_prediction(user_id),
            "latest_roadmap": self.get_latest_roadmap(user_id),
            "latest_progress": self.get_latest_progress(user_id),
            "latest_quiz": self.get_latest_quiz(user_id),
        }
