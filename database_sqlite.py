"""
database_sqlite.py — SQLite-backed adapter for the Mentor Mentee system.

This module provides a near-drop-in replacement for `database.py`.
It stores the same conceptual tables (`users`, `sessions`, `messages`, `feedback`)
in an on-disk SQLite database and exposes a similar function API used by the
application. It is intentionally conservative (no automatic runtime switch)
so the existing JSON backend remains the default until you opt-in.

Usage:
  export SQLITE_DB=/path/to/data.sqlite3
  python migrate_to_sqlite.py   # imports existing data.json into SQLite

The module keeps a simple connection + lock model which is appropriate for
single-process web servers and local CLI use. For production, use a dedicated
RDBMS (Postgres) and a connection pool.
"""

from __future__ import annotations

import os
import sqlite3
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.environ.get("SQLITE_DB") or os.path.join(os.path.dirname(__file__), "data.sqlite3")

# Module-level connection and lock
_conn: Optional[sqlite3.Connection] = None
_lock = threading.RLock()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL improves concurrency for readers/writers on SQLite
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        _conn = conn
        _ensure_schema()
    return _conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _ensure_schema() -> None:
    conn = _get_conn()
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                roll_no TEXT UNIQUE COLLATE NOCASE,
                email TEXT UNIQUE COLLATE NOCASE,
                password TEXT,
                role TEXT,
                contact_number TEXT,
                skills TEXT,
                experience_years INTEGER,
                rating REAL,
                sessions_completed INTEGER,
                availability TEXT,
                bio TEXT,
                hourly_rate REAL,
                assigned_mentor_id TEXT,
                profile_image TEXT,
                reg_no TEXT,
                school TEXT,
                program TEXT,
                semester TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                mentor_id TEXT,
                mentee_id TEXT,
                date TEXT,
                time TEXT,
                duration_minutes INTEGER,
                topic TEXT,
                concern TEXT,
                status TEXT,
                requested_at TEXT,
                resolved_at TEXT,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                sender_id TEXT,
                receiver_id TEXT,
                text TEXT,
                content TEXT,
                timestamp TEXT,
                flagged INTEGER DEFAULT 0,
                session_id TEXT
            );

            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                session_id TEXT,
                reviewer_id TEXT,
                reviewee_id TEXT,
                rating INTEGER,
                comment TEXT,
                timestamp TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_users_roll_no ON users(roll_no);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_sessions_mentor ON sessions(mentor_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_mentee ON sessions(mentee_id);
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
            CREATE TABLE IF NOT EXISTS tokens (
                jti TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TEXT,
                revoked_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id);
            """
        )


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _parse_json_field(val: Optional[str]):
    if val is None:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


# -------------------- Users --------------------


def get_all_users() -> List[Dict]:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM users ORDER BY name COLLATE NOCASE")
        rows = cur.fetchall()
    users = []
    for r in rows:
        d = _row_to_dict(r)
        if d.get("skills"):
            d["skills"] = _parse_json_field(d.get("skills"))
        else:
            d["skills"] = []
        if d.get("availability"):
            d["availability"] = _parse_json_field(d.get("availability"))
        else:
            d["availability"] = []
        users.append(d)
    return users


def get_user_by_id(user_id: str) -> Optional[Dict]:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email,))
        row = cur.fetchone()
    return _row_to_dict(row) if row else None


def get_user_by_roll_no(roll_no: str) -> Optional[Dict]:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM users WHERE roll_no = ? COLLATE NOCASE", (roll_no,))
        row = cur.fetchone()
    return _row_to_dict(row) if row else None


def get_users_by_role(role: str) -> List[Dict]:
    conn = _get_conn()
    with _lock:
        cur = conn.execute("SELECT * FROM users WHERE role = ? ORDER BY name COLLATE NOCASE", (role,))
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def create_user(user: Dict) -> Dict:
    conn = _get_conn()
    uid = user.get("user_id") or generate_id("u")
    skills = json.dumps(user.get("skills", []), ensure_ascii=False)
    availability = json.dumps(user.get("availability", []), ensure_ascii=False)
    now = now_iso()
    with _lock, conn:
        conn.execute(
            """
            INSERT INTO users (user_id, name, roll_no, email, password, role, contact_number,
                skills, experience_years, rating, sessions_completed, availability, bio,
                hourly_rate, assigned_mentor_id, profile_image, reg_no, school, program, semester, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                user.get("name"),
                user.get("roll_no"),
                user.get("email"),
                user.get("password"),
                user.get("role"),
                user.get("contact_number"),
                skills,
                user.get("experience_years", 0),
                user.get("rating", 0.0),
                user.get("sessions_completed", 0),
                availability,
                user.get("bio"),
                user.get("hourly_rate"),
                user.get("assigned_mentor_id"),
                user.get("profile_image"),
                user.get("reg_no"),
                user.get("school"),
                user.get("program"),
                user.get("semester"),
                now,
            ),
        )
    return get_user_by_id(uid)


def update_user(user_id: str, fields: Dict) -> Optional[Dict]:
    if not fields:
        return get_user_by_id(user_id)
    conn = _get_conn()
    allowed = []
    params = []
    for k, v in fields.items():
        if k in ("skills", "availability"):
            allowed.append(f"{k} = ?")
            params.append(json.dumps(v, ensure_ascii=False))
        else:
            allowed.append(f"{k} = ?")
            params.append(v)
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(allowed)} WHERE user_id = ?"
    with _lock, conn:
        conn.execute(sql, tuple(params))
    return get_user_by_id(user_id)


def delete_user(user_id: str) -> bool:
    conn = _get_conn()
    with _lock, conn:
        cur = conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    return cur.rowcount > 0


# -------------------- Sessions --------------------


def _normalize_session_id(session_id: Any) -> Any:
    return session_id.upper() if isinstance(session_id, str) else session_id


def get_all_sessions() -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM sessions ORDER BY requested_at DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_session_by_id(session_id: str) -> Optional[Dict]:
    normalized = _normalize_session_id(session_id)
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (normalized,)).fetchone()
    return _row_to_dict(row) if row else None


def get_sessions_for_user(user_id: str) -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE mentor_id = ? OR mentee_id = ? ORDER BY requested_at DESC",
            (user_id, user_id),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def create_session(session: Dict) -> Dict:
    conn = _get_conn()
    sid = session.get("session_id") or generate_id("S")
    sid = _normalize_session_id(sid)
    now = now_iso()
    with _lock, conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id, mentor_id, mentee_id, date, time, duration_minutes,
                topic, concern, status, requested_at, resolved_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                session.get("mentor_id"),
                session.get("mentee_id"),
                session.get("date"),
                session.get("time"),
                session.get("duration_minutes", 0),
                session.get("topic"),
                session.get("concern"),
                session.get("status", "pending"),
                session.get("requested_at", now),
                session.get("resolved_at"),
                session.get("notes"),
            ),
        )
    return get_session_by_id(sid)


def update_session(session_id: str, fields: Dict) -> Optional[Dict]:
    if not fields:
        return get_session_by_id(session_id)
    conn = _get_conn()
    parts = []
    params = []
    for k, v in fields.items():
        parts.append(f"{k} = ?")
        params.append(v)
    params.append(session_id)
    sql = f"UPDATE sessions SET {', '.join(parts)} WHERE session_id = ?"
    with _lock, conn:
        conn.execute(sql, tuple(params))
    return get_session_by_id(session_id)


def delete_session(session_id: str) -> bool:
    conn = _get_conn()
    with _lock, conn:
        cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    return cur.rowcount > 0


# -------------------- Messages --------------------


def get_all_messages() -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM messages ORDER BY timestamp").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_conversation(user_a: str, user_b: str, session_id: Optional[str] = None) -> List[Dict]:
    conn = _get_conn()
    with _lock:
        if session_id:
            rows = conn.execute(
                """
                SELECT * FROM messages WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
                AND session_id = ? ORDER BY timestamp
                """,
                (user_a, user_b, user_b, user_a, session_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM messages WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
                ORDER BY timestamp
                """,
                (user_a, user_b, user_b, user_a),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def create_message(message: Dict) -> Dict:
    conn = _get_conn()
    mid = message.get("message_id") or generate_id("m")
    ts = message.get("timestamp") or now_iso()
    text = message.get("text") or message.get("content")
    content = message.get("content") or message.get("text")
    flagged = 1 if message.get("flagged") else 0
    session_id = message.get("session_id")
    with _lock, conn:
        conn.execute(
            """
            INSERT INTO messages (message_id, sender_id, receiver_id, text, content, timestamp, flagged, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, message.get("sender_id"), message.get("receiver_id"), text, content, ts, flagged, session_id),
        )
    return get_all_messages()[-1] if get_all_messages() else {"message_id": mid}


def flag_message(message_id: str) -> bool:
    conn = _get_conn()
    with _lock, conn:
        cur = conn.execute("UPDATE messages SET flagged = 1 WHERE message_id = ?", (message_id,))
    return cur.rowcount > 0


def get_flagged_messages() -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM messages WHERE flagged = 1 ORDER BY timestamp").fetchall()
    return [_row_to_dict(r) for r in rows]


# -------------------- Feedback --------------------


def get_all_feedback() -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM feedback ORDER BY timestamp DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_feedback_for_user(user_id: str) -> List[Dict]:
    conn = _get_conn()
    with _lock:
        rows = conn.execute("SELECT * FROM feedback WHERE reviewee_id = ? ORDER BY timestamp DESC", (user_id,)).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_feedback_by_session(session_id: str) -> Optional[Dict]:
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT * FROM feedback WHERE session_id = ?", (session_id,)).fetchone()
    return _row_to_dict(row) if row else None


def create_feedback(feedback: Dict) -> Dict:
    conn = _get_conn()
    fid = feedback.get("feedback_id") or generate_id("f")
    ts = feedback.get("timestamp") or now_iso()
    with _lock, conn:
        conn.execute(
            """
            INSERT INTO feedback (feedback_id, session_id, reviewer_id, reviewee_id, rating, comment, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fid, feedback.get("session_id"), feedback.get("reviewer_id"), feedback.get("reviewee_id"), int(feedback.get("rating", 0)), feedback.get("comment", ""), ts),
        )
    return get_feedback_by_session(feedback.get("session_id")) or {"feedback_id": fid}


# -------------------- Token issuance / revocation --------------------

def create_token(jti: str, user_id: str) -> None:
    """Record a newly issued token (jti) for a user."""
    conn = _get_conn()
    now = now_iso()
    with _lock, conn:
        conn.execute(
            "INSERT OR REPLACE INTO tokens (jti, user_id, created_at, revoked_at) VALUES (?, ?, ?, NULL)",
            (jti, user_id, now),
        )


def revoke_token(jti: str) -> bool:
    """Mark a token as revoked. Returns True if a row was updated."""
    conn = _get_conn()
    now = now_iso()
    with _lock, conn:
        cur = conn.execute("UPDATE tokens SET revoked_at = ? WHERE jti = ? AND revoked_at IS NULL", (now, jti))
    return cur.rowcount > 0


def is_token_revoked(jti: str) -> bool:
    """Return True if the token has been revoked."""
    conn = _get_conn()
    with _lock:
        row = conn.execute("SELECT revoked_at FROM tokens WHERE jti = ?", (jti,)).fetchone()
    if not row:
        return False
    return bool(row["revoked_at"])


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return None
    d = {k: row[k] for k in row.keys()}
    # Normalize integer flags
    if "flagged" in d and d["flagged"] is not None:
        d["flagged"] = bool(d["flagged"])
    return d
