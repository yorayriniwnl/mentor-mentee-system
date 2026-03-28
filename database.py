"""
database.py — JSON-backed data store for the Mentor System.
All modules interact with data exclusively through this layer.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


# ─────────────────────────── Core I/O ───────────────────────────

def _normalize_session_id(session_id: Any) -> Any:
    return session_id.upper() if isinstance(session_id, str) else session_id


def _normalize_session_references(data: Dict[str, Any]) -> bool:
    changed = False

    for session in data.get("sessions", []):
        normalized = _normalize_session_id(session.get("session_id"))
        if normalized and session.get("session_id") != normalized:
            session["session_id"] = normalized
            changed = True

    for feedback in data.get("feedback", []):
        normalized = _normalize_session_id(feedback.get("session_id"))
        if normalized and feedback.get("session_id") != normalized:
            feedback["session_id"] = normalized
            changed = True

    for message in data.get("messages", []):
        normalized = _normalize_session_id(message.get("session_id"))
        if normalized and message.get("session_id") != normalized:
            message["session_id"] = normalized
            changed = True
        if not message.get("session_id"):
            inferred = _infer_message_session_id(data, message)
            if inferred:
                message["session_id"] = inferred
                changed = True

    return changed


def _session_activity_key(session: Dict[str, Any]) -> str:
    if session.get("requested_at"):
        return session["requested_at"]
    if session.get("resolved_at"):
        return session["resolved_at"]
    if session.get("date") and session.get("time"):
        return f"{session['date']}T{session['time']}"
    return session.get("date", "")


def _infer_message_session_id(data: Dict[str, Any], message: Dict[str, Any]) -> Optional[str]:
    sender_id = message.get("sender_id")
    receiver_id = message.get("receiver_id")
    if not sender_id or not receiver_id:
        return None

    shared_sessions = [
        session for session in data.get("sessions", [])
        if {session.get("mentor_id"), session.get("mentee_id")} == {sender_id, receiver_id}
        and session.get("status") != "cancelled"
        and session.get("session_id")
    ]
    if not shared_sessions:
        return None

    ordered_sessions = sorted(shared_sessions, key=_session_activity_key)
    message_time = message.get("timestamp", "")
    eligible_sessions = [
        session for session in ordered_sessions
        if _session_activity_key(session) <= message_time
    ]
    target_session = eligible_sessions[-1] if eligible_sessions else ordered_sessions[0]
    return target_session.get("session_id")


def _load() -> Dict[str, Any]:
    """Load the entire database from disk."""
    if not os.path.exists(DATA_FILE):
        _init_empty()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if _normalize_session_references(data):
        _save(data)

    return data


def _save(data: Dict[str, Any]) -> None:
    """Persist the entire database to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _init_empty() -> None:
    """Create a blank database file."""
    _save({"users": [], "sessions": [], "messages": [], "feedback": []})


# ─────────────────────────── Helpers ────────────────────────────

def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    return datetime.now().isoformat()


# ─────────────────────────── Users ──────────────────────────────

def get_all_users() -> List[Dict]:
    return _load()["users"]


def get_user_by_id(user_id: str) -> Optional[Dict]:
    return next((u for u in get_all_users() if u["user_id"] == user_id), None)


def get_user_by_email(email: str) -> Optional[Dict]:
    return next((u for u in get_all_users() if u["email"].lower() == email.lower()), None)


def get_user_by_roll_no(roll_no: str) -> Optional[Dict]:
    return next((u for u in get_all_users() if u.get("roll_no", "").lower() == roll_no.lower()), None)


def get_users_by_role(role: str) -> List[Dict]:
    return [u for u in get_all_users() if u.get("role") == role]


def get_assigned_mentor_id(mentee_id: str) -> Optional[str]:
    """Return the mentor explicitly assigned to a mentee, with session fallback."""
    mentee = get_user_by_id(mentee_id)
    if not mentee or mentee.get("role") != "mentee":
        return None

    mentor_id = mentee.get("assigned_mentor_id")
    mentor = get_user_by_id(mentor_id) if mentor_id else None
    if mentor and mentor.get("role") == "mentor":
        return mentor_id

    sessions = sorted(
        [
            s for s in get_sessions_for_user(mentee_id)
            if s.get("mentee_id") == mentee_id
        ],
        key=lambda s: (s.get("date", ""), s.get("time", "")),
        reverse=True,
    )

    for allowed_statuses in (("requested", "confirmed", "completed", "pending"), None):
        for session in sessions:
            if allowed_statuses and session.get("status") not in allowed_statuses:
                continue
            mentor_id = session.get("mentor_id")
            mentor = get_user_by_id(mentor_id) if mentor_id else None
            if mentor and mentor.get("role") == "mentor":
                return mentor_id

    return None


def get_assigned_mentor(mentee_id: str) -> Optional[Dict]:
    """Return the mentor assigned to a mentee, if any."""
    mentor_id = get_assigned_mentor_id(mentee_id)
    return get_user_by_id(mentor_id) if mentor_id else None


def create_user(user: Dict) -> Dict:
    data = _load()
    user.setdefault("user_id", generate_id("u"))
    user.setdefault("sessions_completed", 0)
    user.setdefault("rating", 0.0)
    data["users"].append(user)
    _save(data)
    return user


def update_user(user_id: str, fields: Dict) -> Optional[Dict]:
    data = _load()
    for u in data["users"]:
        if u["user_id"] == user_id:
            u.update(fields)
            _save(data)
            return u
    return None


def delete_user(user_id: str) -> bool:
    data = _load()
    before = len(data["users"])
    data["users"] = [u for u in data["users"] if u["user_id"] != user_id]
    _save(data)
    return len(data["users"]) < before


# ─────────────────────────── Sessions ───────────────────────────

def get_all_sessions() -> List[Dict]:
    return _load()["sessions"]


def get_session_by_id(session_id: str) -> Optional[Dict]:
    normalized_id = _normalize_session_id(session_id)
    return next((s for s in get_all_sessions() if s["session_id"] == normalized_id), None)


def get_sessions_for_user(user_id: str) -> List[Dict]:
    return [
        s for s in get_all_sessions()
        if s.get("mentor_id") == user_id or s.get("mentee_id") == user_id
    ]


def create_session(session: Dict) -> Dict:
    data = _load()
    session.setdefault("session_id", generate_id("S"))
    session["session_id"] = _normalize_session_id(session["session_id"])
    session.setdefault("status", "pending")
    session.setdefault("notes", "")
    data["sessions"].append(session)
    _save(data)
    return session


def update_session(session_id: str, fields: Dict) -> Optional[Dict]:
    data = _load()
    normalized_id = _normalize_session_id(session_id)
    for s in data["sessions"]:
        if s["session_id"] == normalized_id:
            s.update(fields)
            _save(data)
            return s
    return None


def delete_session(session_id: str) -> bool:
    data = _load()
    normalized_id = _normalize_session_id(session_id)
    before = len(data["sessions"])
    data["sessions"] = [s for s in data["sessions"] if s["session_id"] != normalized_id]
    _save(data)
    return len(data["sessions"]) < before


# ─────────────────────────── Messages ───────────────────────────

def get_all_messages() -> List[Dict]:
    return _load()["messages"]


def get_conversation(user_a: str, user_b: str, session_id: Optional[str] = None) -> List[Dict]:
    normalized_session_id = _normalize_session_id(session_id)
    return sorted(
        [
            m for m in get_all_messages()
            if (
                (
                    (m["sender_id"] == user_a and m["receiver_id"] == user_b)
                    or (m["sender_id"] == user_b and m["receiver_id"] == user_a)
                )
                and (normalized_session_id is None or m.get("session_id") == normalized_session_id)
            )
        ],
        key=lambda m: m["timestamp"],
    )


def create_message(message: Dict) -> Dict:
    data = _load()
    message.setdefault("message_id", generate_id("m"))
    message.setdefault("timestamp", now_iso())
    message.setdefault("flagged", False)
    if "session_id" in message:
        message["session_id"] = _normalize_session_id(message["session_id"])
    data["messages"].append(message)
    _save(data)
    return message


def flag_message(message_id: str) -> bool:
    data = _load()
    for m in data["messages"]:
        if m["message_id"] == message_id:
            m["flagged"] = True
            _save(data)
            return True
    return False


def get_flagged_messages() -> List[Dict]:
    return [m for m in get_all_messages() if m.get("flagged")]


# ─────────────────────────── Feedback ───────────────────────────

def get_all_feedback() -> List[Dict]:
    return _load()["feedback"]


def get_feedback_for_user(user_id: str) -> List[Dict]:
    return [f for f in get_all_feedback() if f.get("reviewee_id") == user_id]


def get_feedback_by_session(session_id: str) -> Optional[Dict]:
    normalized_id = _normalize_session_id(session_id)
    return next((f for f in get_all_feedback() if f.get("session_id") == normalized_id), None)


def create_feedback(feedback: Dict) -> Dict:
    data = _load()
    if "session_id" in feedback:
        feedback["session_id"] = _normalize_session_id(feedback["session_id"])
    feedback.setdefault("feedback_id", generate_id("f"))
    feedback.setdefault("timestamp", now_iso())
    data["feedback"].append(feedback)
    _save(data)
    # Recalculate reviewee's average rating
    _recalculate_rating(feedback["reviewee_id"])
    return feedback


def _recalculate_rating(user_id: str) -> None:
    ratings = [
        f["rating"] for f in get_feedback_for_user(user_id)
        if isinstance(f.get("rating"), (int, float))
    ]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    update_user(user_id, {"rating": avg})
