"""
booking.py - Session request and scheduling helpers.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import database as db

VALID_STATUSES = ("requested", "pending", "confirmed", "cancelled", "completed")
MIN_DURATION = 30
MAX_DURATION = 180


def _parse_date(date_str: str) -> Optional[date]:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def _has_conflict(mentor_id: str, date_str: str, time_str: str, exclude_id: str = "") -> bool:
    """Check whether a mentor already has a scheduled session at the given date/time."""
    for s in db.get_sessions_for_user(mentor_id):
        if s.get("session_id") == exclude_id:
            continue
        if (
            s.get("mentor_id") == mentor_id
            and s.get("date") == date_str
            and s.get("time") == time_str
            and s.get("status") in ("pending", "confirmed")
        ):
            return True
    return False


def book_session(mentee_id: str, concern: str) -> Tuple[bool, str]:
    """
    Raise a session request for the mentee's assigned mentor.
    The request is stored with status 'requested'.
    """
    mentee = db.get_user_by_id(mentee_id)
    if not mentee or mentee.get("role") != "mentee":
        return False, "Invalid mentee ID."

    mentor_id = db.get_assigned_mentor_id(mentee_id)
    mentor = db.get_user_by_id(mentor_id) if mentor_id else None
    if not mentor or mentor.get("role") != "mentor":
        return False, "No assigned mentor found for this student."

    concern = concern.strip()
    if not concern:
        return False, "Concern cannot be empty."

    active_session = next(
        (
            s for s in db.get_sessions_for_user(mentee_id)
            if s.get("mentor_id") == mentor_id
            and s.get("status") in ("requested", "pending", "confirmed")
        ),
        None,
    )
    if active_session:
        return False, f"You already have an active request with {mentor.get('name')}."

    session = db.create_session(
        {
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "date": "",
            "time": "",
            "duration_minutes": 0,
            "topic": concern,
            "concern": concern,
            "status": "requested",
            "requested_at": db.now_iso(),
        }
    )
    return True, f"Request sent to {mentor.get('name')} (ID: {session['session_id']})."


def resolve_session_request(session_id: str, mentor_id: str) -> Tuple[bool, str]:
    """Move a mentor's incoming request into a pending resolution state."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if session.get("mentor_id") != mentor_id:
        return False, "Only the assigned mentor can resolve this request."

    status = session.get("status")
    if status == "requested":
        db.update_session(session_id, {"status": "pending"})
        return True, "Request marked as pending."
    if status == "pending":
        return True, "Request is already pending."
    return False, f"Cannot resolve a session in '{status}' state."


def mark_session_resolved(session_id: str, mentor_id: str) -> Tuple[bool, str]:
    """Allow a mentor to mark a request or session as resolved/completed."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if session.get("mentor_id") != mentor_id:
        return False, "Only the assigned mentor can mark this session as resolved."

    status = session.get("status")
    if status in ("completed", "cancelled"):
        return False, f"Session is already '{status}'."
    if status not in ("requested", "pending", "confirmed"):
        return False, f"Cannot mark a session in '{status}' state as resolved."

    db.update_session(session_id, {"status": "completed", "resolved_at": db.now_iso()})
    mentor = db.get_user_by_id(mentor_id)
    if mentor:
        db.update_user(mentor_id, {"sessions_completed": mentor.get("sessions_completed", 0) + 1})
    return True, "Session marked as resolved."


def confirm_session(session_id: str, mentor_id: str) -> Tuple[bool, str]:
    """Mentor confirms a pending scheduled session."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if session.get("mentor_id") != mentor_id:
        return False, "Only the assigned mentor can confirm this session."
    if session.get("status") != "pending":
        return False, f"Session is already '{session['status']}'."
    db.update_session(session_id, {"status": "confirmed"})
    return True, "Session confirmed."


def cancel_session(session_id: str, requesting_user_id: str) -> Tuple[bool, str]:
    """Either party can cancel a session request that isn't yet completed."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if requesting_user_id not in (session.get("mentor_id"), session.get("mentee_id")):
        return False, "You are not a participant of this session."
    if session.get("status") in ("cancelled", "completed"):
        return False, f"Session is already '{session['status']}'."
    db.update_session(session_id, {"status": "cancelled"})
    return True, "Session cancelled."


def complete_session(session_id: str, mentor_id: str, notes: str = "") -> Tuple[bool, str]:
    """Mentor marks a confirmed session as completed."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if session.get("mentor_id") != mentor_id:
        return False, "Only the assigned mentor can complete this session."
    if session.get("status") != "confirmed":
        return False, "Only confirmed sessions can be marked as completed."
    db.update_session(session_id, {"status": "completed", "notes": notes.strip()})
    mentor = db.get_user_by_id(mentor_id)
    if mentor:
        db.update_user(mentor_id, {"sessions_completed": mentor.get("sessions_completed", 0) + 1})
    return True, "Session marked as completed."


def reschedule_session(
    session_id: str,
    requesting_user_id: str,
    new_date: str,
    new_time: str,
) -> Tuple[bool, str]:
    """Reschedule a pending or confirmed session to a new date/time."""
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."
    if requesting_user_id not in (session.get("mentor_id"), session.get("mentee_id")):
        return False, "You are not a participant of this session."
    if session.get("status") in ("cancelled", "completed", "requested"):
        return False, "Cannot reschedule this session."

    parsed = _parse_date(new_date)
    if not parsed:
        return False, "Invalid date format."
    if parsed < date.today():
        return False, "Cannot reschedule to a past date."
    if not _parse_time(new_time):
        return False, "Invalid time format."

    mentor_id = session["mentor_id"]
    if _has_conflict(mentor_id, new_date, new_time, exclude_id=session_id):
        return False, "Mentor already has a session at that new date and time."

    db.update_session(session_id, {"date": new_date, "time": new_time, "status": "pending"})
    return True, "Session rescheduled. Awaiting mentor re-confirmation."


def get_upcoming_sessions(user_id: str) -> List[Dict]:
    """Return active requests and future sessions for a user."""
    today = date.today().isoformat()
    unresolved = [
        s for s in db.get_sessions_for_user(user_id)
        if s.get("status") in ("requested", "pending")
        and not s.get("date")
    ]
    scheduled = [
        s for s in db.get_sessions_for_user(user_id)
        if s.get("date", "") >= today and s.get("status") in ("pending", "confirmed")
    ]
    unresolved = sorted(unresolved, key=lambda s: s.get("requested_at", ""), reverse=True)
    scheduled = sorted(scheduled, key=lambda s: (s["date"], s["time"]))
    return unresolved + scheduled


def get_session_history(user_id: str) -> List[Dict]:
    """Return past or completed/cancelled sessions for a user."""
    today = date.today().isoformat()
    sessions = [
        s for s in db.get_sessions_for_user(user_id)
        if s.get("date", "") < today or s.get("status") in ("completed", "cancelled")
    ]
    return sorted(sessions, key=lambda s: (s.get("date", ""), s.get("time", "")), reverse=True)


def get_resolved_sessions(user_id: str) -> List[Dict]:
    """Return sessions marked completed/resolved for a user, newest first."""
    sessions = [
        s for s in db.get_sessions_for_user(user_id)
        if s.get("status") == "completed"
    ]

    def sort_key(session: Dict) -> str:
        if session.get("resolved_at"):
            return session["resolved_at"]
        if session.get("date") and session.get("time"):
            return f"{session['date']}T{session['time']}"
        return session.get("requested_at", "")

    return sorted(sessions, key=sort_key, reverse=True)


def get_session_details(session_id: str) -> Optional[Dict]:
    """Return enriched session info including mentor and mentee names."""
    session = db.get_session_by_id(session_id)
    if not session:
        return None
    mentor = db.get_user_by_id(session["mentor_id"])
    mentee = db.get_user_by_id(session["mentee_id"])
    return {
        **session,
        "concern": session.get("concern", session.get("topic", "")),
        "mentor_name": mentor.get("name", "Unknown") if mentor else "Unknown",
        "mentee_name": mentee.get("name", "Unknown") if mentee else "Unknown",
    }
