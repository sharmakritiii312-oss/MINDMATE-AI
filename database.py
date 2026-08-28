"""
MindMate AI — SQLite Database Layer
Tables: users, mood_logs, sleep_logs, journal_entries, diet_logs, exercise_logs,
        wellness_scores, chat_sessions
"""
from __future__ import annotations

import sqlite3
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "data" / "mindmate.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db() -> None:
    """Create all tables if they don't exist."""
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL DEFAULT 'Student',
            age         INTEGER,
            weight_kg   REAL,
            height_cm   REAL,
            activity_level TEXT DEFAULT 'moderate',
            fitness_level  TEXT DEFAULT 'beginner',
            diet_prefs     TEXT DEFAULT '[]',
            wellness_goals TEXT DEFAULT '[]',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mood_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            logged_at   TEXT NOT NULL,
            mood_score  INTEGER NOT NULL,
            primary_emotion TEXT,
            emotions_json   TEXT DEFAULT '{}',
            note        TEXT,
            stress_score    INTEGER DEFAULT 0,
            energy_score    INTEGER DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS sleep_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            date            TEXT NOT NULL,
            bedtime         TEXT,
            wake_time       TEXT,
            duration_hours  REAL,
            quality_score   INTEGER,
            notes           TEXT,
            sleep_score     REAL
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            entry_type  TEXT DEFAULT 'reflection',
            content     TEXT NOT NULL,
            ai_insight  TEXT,
            mood_before INTEGER,
            mood_after  INTEGER,
            tags_json   TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS diet_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            logged_at   TEXT NOT NULL,
            meal_type   TEXT,
            description TEXT,
            water_ml    INTEGER DEFAULT 0,
            ai_feedback TEXT
        );

        CREATE TABLE IF NOT EXISTS exercise_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            logged_at       TEXT NOT NULL,
            activity_type   TEXT,
            duration_min    INTEGER,
            intensity       TEXT,
            notes           TEXT,
            ai_feedback     TEXT
        );

        CREATE TABLE IF NOT EXISTS wellness_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            date            TEXT NOT NULL,
            overall_score   REAL,
            mood_score      REAL,
            sleep_score     REAL,
            stress_score    REAL,
            activity_score  REAL,
            nutrition_score REAL,
            ai_summary      TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            title       TEXT
        );
        """)


# ── User helpers ──────────────────────────────────────────────────────────────

def get_or_create_user(user_id: str, name: str = "Student") -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row:
            return dict(row)
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            "INSERT INTO users(id,name,created_at) VALUES(?,?,?)",
            (user_id, name, now)
        )
        return {"id": user_id, "name": name, "created_at": now,
                "diet_prefs": "[]", "wellness_goals": "[]",
                "activity_level": "moderate", "fitness_level": "beginner"}


def update_user_profile(user_id: str, **kwargs) -> None:
    allowed = {"name","age","weight_kg","height_cm","activity_level",
               "fitness_level","diet_prefs","wellness_goals"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with _conn() as c:
        c.execute(f"UPDATE users SET {sets} WHERE id=?", (*fields.values(), user_id))


# ── Mood helpers ──────────────────────────────────────────────────────────────

def log_mood(user_id: str, mood_score: int, primary_emotion: str = "",
             emotions_json: dict = None, note: str = "",
             stress_score: int = 0, energy_score: int = 5) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO mood_logs(user_id,logged_at,mood_score,primary_emotion,
               emotions_json,note,stress_score,energy_score)
               VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, now, mood_score, primary_emotion,
             json.dumps(emotions_json or {}), note, stress_score, energy_score)
        )
        return cur.lastrowid


def get_mood_history(user_id: str, days: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM mood_logs WHERE user_id=?
               ORDER BY logged_at DESC LIMIT ?""",
            (user_id, days * 4)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Sleep helpers ─────────────────────────────────────────────────────────────

def log_sleep(user_id: str, date_str: str, bedtime: str, wake_time: str,
              duration_hours: float, quality_score: int,
              notes: str = "", sleep_score: float = 0.0) -> int:
    with _conn() as c:
        cur = c.execute(
            """INSERT OR REPLACE INTO sleep_logs
               (user_id,date,bedtime,wake_time,duration_hours,quality_score,notes,sleep_score)
               VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, date_str, bedtime, wake_time, duration_hours,
             quality_score, notes, sleep_score)
        )
        return cur.lastrowid


def get_sleep_history(user_id: str, days: int = 14) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM sleep_logs WHERE user_id=? ORDER BY date DESC LIMIT ?",
            (user_id, days)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Journal helpers ───────────────────────────────────────────────────────────

def save_journal_entry(user_id: str, content: str, entry_type: str = "reflection",
                       ai_insight: str = "", mood_before: int = 5,
                       mood_after: int = 5, tags: list = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO journal_entries
               (user_id,created_at,entry_type,content,ai_insight,mood_before,mood_after,tags_json)
               VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, now, entry_type, content, ai_insight,
             mood_before, mood_after, json.dumps(tags or []))
        )
        return cur.lastrowid


def get_journal_entries(user_id: str, limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM journal_entries WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Wellness score helpers ────────────────────────────────────────────────────

def save_wellness_score(user_id: str, date_str: str, overall: float,
                        mood: float, sleep: float, stress: float,
                        activity: float, nutrition: float, summary: str = "") -> None:
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO wellness_scores
               (user_id,date,overall_score,mood_score,sleep_score,stress_score,
                activity_score,nutrition_score,ai_summary)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (user_id, date_str, overall, mood, sleep, stress, activity, nutrition, summary)
        )


def get_wellness_history(user_id: str, days: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM wellness_scores WHERE user_id=?
               ORDER BY date DESC LIMIT ?""",
            (user_id, days)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Exercise log helpers ──────────────────────────────────────────────────────

def log_exercise(user_id: str, activity_type: str, duration_min: int,
                 intensity: str = "moderate", notes: str = "",
                 ai_feedback: str = "") -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO exercise_logs
               (user_id,logged_at,activity_type,duration_min,intensity,notes,ai_feedback)
               VALUES(?,?,?,?,?,?,?)""",
            (user_id, now, activity_type, duration_min, intensity, notes, ai_feedback)
        )
        return cur.lastrowid


def get_exercise_history(user_id: str, days: int = 14) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM exercise_logs WHERE user_id=?
               ORDER BY logged_at DESC LIMIT ?""",
            (user_id, days * 2)
        ).fetchall()
    return [dict(r) for r in rows]


# Initialise on import
init_db()
