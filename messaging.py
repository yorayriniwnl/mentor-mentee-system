"""
messaging.py — Filtered chat between mentors and mentees.

Messages are auto-scanned for:
  • Profanity / abusive language
  • Phone numbers and email addresses (PII leak prevention)
  • Spam patterns (repeated chars, all-caps shouting)

Flagged messages are stored but hidden from the recipient until reviewed.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import database as db

# ──────────────────────── Filter word-list ───────────────────────
# Extend this list or replace with a proper library (e.g. `better-profanity`).

_BLOCKED_WORDS = [
    "spam", "scam", "idiot", "stupid", "dumb", "hate", "kill",
    "abuse", "fraud", "fake", "cheat",
]

# ──────────────────────── Filter functions ───────────────────────

def _contains_profanity(text: str) -> bool:
    lower = text.lower()
    return any(word in lower.split() for word in _BLOCKED_WORDS)


def _contains_pii(text: str) -> bool:
    """Detect phone numbers or email addresses."""
    phone_pattern = r"\b(\+?\d[\d\s\-().]{7,}\d)\b"
    email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"
    return bool(re.search(phone_pattern, text) or re.search(email_pattern, text))


def _is_spam(text: str) -> bool:
    """Flag messages that are mostly caps or have excessive repeated characters."""
    if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
        return True
    if re.search(r"(.)\1{5,}", text):   # 6+ repeated chars: "aaaaaa"
        return True
    return False


def _filter_message(content: str) -> Tuple[str, bool, str]:
    """
    Return (possibly_redacted_content, flagged, reason).
    PII is redacted inline; profanity/spam causes flagging.
    """
    reason_parts = []
    flagged = False

    # Redact PII in-place
    content = re.sub(
        r"\b(\+?\d[\d\s\-().]{7,}\d)\b", "[PHONE REDACTED]", content
    )
    content = re.sub(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
        "[EMAIL REDACTED]", content
    )

    if _contains_profanity(content):
        flagged = True
        reason_parts.append("profanity")

    if _is_spam(content):
        flagged = True
        reason_parts.append("spam")

    reason = ", ".join(reason_parts) if reason_parts else ""
    return content, flagged, reason


# ──────────────────────── Public API ─────────────────────────────

def send_message(
    sender_id: str,
    receiver_id: str,
    content: str,
    session_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Send a message from *sender_id* to *receiver_id*.

    Returns (success, info_string, message_dict_or_None).
    Flagged messages are stored but the caller is warned.
    """
    if not content.strip():
        return False, "Message content cannot be empty.", None

    sender   = db.get_user_by_id(sender_id)
    receiver = db.get_user_by_id(receiver_id)

    if not sender:
        return False, "Sender not found.", None
    if not receiver:
        return False, "Recipient not found.", None

    related_session = None
    if session_id:
        related_session = db.get_session_by_id(session_id)
        if not related_session:
            return False, "Session thread not found.", None
        participants = {related_session.get("mentor_id"), related_session.get("mentee_id")}
        if participants != {sender_id, receiver_id}:
            return False, "This session thread does not belong to the selected users.", None
    else:
        paired = any(
            (s["mentor_id"] == sender_id and s["mentee_id"] == receiver_id) or
            (s["mentor_id"] == receiver_id and s["mentee_id"] == sender_id)
            for s in db.get_all_sessions()
        )
        if not paired:
            return False, "You can only message users you have a session with.", None

    filtered_content, flagged, reason = _filter_message(content.strip())

    message = db.create_message({
        "sender_id":   sender_id,
        "receiver_id": receiver_id,
        "content":     filtered_content,
        "flagged":     flagged,
        "session_id":  related_session.get("session_id") if related_session else None,
    })

    if flagged:
        return True, f"Message sent but flagged for review ({reason}).", message
    return True, "Message sent.", message


def get_conversation(
    user_a: str,
    user_b: str,
    session_id: Optional[str] = None,
    include_flagged: bool = False,
) -> List[Dict]:
    """
    Retrieve the conversation thread between two users.
    Flagged messages are hidden by default (set include_flagged=True for admin view).
    """
    messages = db.get_conversation(user_a, user_b, session_id=session_id)
    if not include_flagged:
        messages = [m for m in messages if not m.get("flagged")]
    return messages


def _session_activity_key(session: Dict) -> str:
    """Return a sortable activity key for a session or request."""
    if session.get("resolved_at"):
        return session["resolved_at"]
    if session.get("requested_at"):
        return session["requested_at"]
    if session.get("date") and session.get("time"):
        return f"{session['date']}T{session['time']}"
    return session.get("date", "")


def _thread_label(session: Dict, contact_name: str) -> str:
    concern = (session.get("concern") or session.get("topic") or "Untitled issue").strip()
    return f"{concern} [{session['session_id']}]"


def get_inbox(user_id: str) -> List[Dict]:
    """
    Return all issue threads for a user, grouped by session, most recent first.
    """
    all_msgs = db.get_all_messages()
    relevant = [
        m for m in all_msgs
        if (m["receiver_id"] == user_id or m["sender_id"] == user_id)
        and not m.get("flagged")
    ]

    messages_by_session: Dict[str, List[Dict]] = {}
    unthreaded_messages: Dict[str, List[Dict]] = {}
    for m in relevant:
        if m.get("session_id"):
            messages_by_session.setdefault(m["session_id"], []).append(m)
            continue
        contact_id = m["sender_id"] if m["receiver_id"] == user_id else m["receiver_id"]
        unthreaded_messages.setdefault(contact_id, []).append(m)

    inbox = []
    seen_sessions = set()
    for session in sorted(db.get_sessions_for_user(user_id), key=_session_activity_key, reverse=True):
        if session.get("status") == "cancelled":
            continue
        session_id = session.get("session_id")
        if not session_id or session_id in seen_sessions:
            continue
        seen_sessions.add(session_id)

        if session.get("mentor_id") == user_id:
            contact_id = session.get("mentee_id")
        else:
            contact_id = session.get("mentor_id")
        contact_user = db.get_user_by_id(contact_id)
        if not contact_user:
            continue

        msgs_sorted = sorted(messages_by_session.get(session_id, []), key=lambda x: x["timestamp"])
        last_time = _session_activity_key(session)
        last_message = "No messages yet. Start this issue thread."
        if msgs_sorted:
            last_time = msgs_sorted[-1]["timestamp"]
            last_message = msgs_sorted[-1]["content"]

        inbox.append({
            "contact_id": contact_id,
            "contact_name": contact_user.get("name", "Unknown"),
            "session_id": session_id,
            "thread_label": _thread_label(session, contact_user.get("name", "Unknown")),
            "issue_title": session.get("concern") or session.get("topic") or "Untitled issue",
            "status": session.get("status", ""),
            "last_message": last_message,
            "last_time": last_time,
            "message_count": len(msgs_sorted),
        })

    for contact_id, msgs in unthreaded_messages.items():
        contact_user = db.get_user_by_id(contact_id)
        if not contact_user:
            continue
        msgs_sorted = sorted(msgs, key=lambda x: x["timestamp"])
        inbox.append({
            "contact_id": contact_id,
            "contact_name": contact_user.get("name", "Unknown"),
            "session_id": None,
            "thread_label": f"General [{contact_user.get('name', 'Unknown')}]",
            "issue_title": "General",
            "status": "",
            "last_message": msgs_sorted[-1]["content"],
            "last_time": msgs_sorted[-1]["timestamp"],
            "message_count": len(msgs_sorted),
        })

    inbox.sort(key=lambda x: x["last_time"], reverse=True)
    return inbox


def flag_message_manual(message_id: str) -> Tuple[bool, str]:
    """Manually flag a message (e.g. reported by a user)."""
    ok = db.flag_message(message_id)
    if ok:
        return True, "Message flagged for review."
    return False, "Message not found."


def get_flagged_messages() -> List[Dict]:
    """Admin: retrieve all flagged messages."""
    return db.get_flagged_messages()


def delete_message(message_id: str, requesting_user_id: str) -> Tuple[bool, str]:
    """
    Users may only delete their own sent messages.
    (Soft-delete via flagging; hard-delete not supported to preserve audit trail.)
    """
    all_msgs = db.get_all_messages()
    msg = next((m for m in all_msgs if m["message_id"] == message_id), None)
    if not msg:
        return False, "Message not found."
    if msg["sender_id"] != requesting_user_id:
        return False, "You can only delete your own messages."
    db.flag_message(message_id)
    return True, "Message removed from view."
