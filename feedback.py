"""
feedback.py — Post-session ratings and written reviews.

Rules:
  • Only session participants may leave feedback.
  • Feedback can only be submitted for *completed* sessions.
  • One review per (session, reviewer) pair.
  • Ratings are 1-5 integers; comments are optional but cleaned.
"""

import re
from typing import Dict, List, Optional, Tuple

import database as db

MAX_COMMENT_LENGTH = 1000
MIN_RATING         = 1
MAX_RATING         = 5


# ──────────────────────── Helpers ───────────────────────────────

def _clean_comment(text: str) -> str:
    """Strip excessive whitespace and limit length."""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_COMMENT_LENGTH]


def _already_reviewed(session_id: str, reviewer_id: str) -> bool:
    return any(
        f.get("session_id") == session_id and f.get("reviewer_id") == reviewer_id
        for f in db.get_all_feedback()
    )


# ──────────────────────── Public API ─────────────────────────────

def submit_feedback(
    session_id: str,
    reviewer_id: str,
    rating: int,
    comment: str = "",
) -> Tuple[bool, str]:
    """
    Submit a rating + optional comment for a completed session.
    The reviewee is automatically determined (the other participant).
    """
    session = db.get_session_by_id(session_id)
    if not session:
        return False, "Session not found."

    if session.get("status") != "completed":
        return False, "Feedback can only be submitted for completed sessions."

    mentor_id  = session["mentor_id"]
    mentee_id  = session["mentee_id"]

    if reviewer_id not in (mentor_id, mentee_id):
        return False, "You are not a participant of this session."

    reviewee_id = mentee_id if reviewer_id == mentor_id else mentor_id

    if _already_reviewed(session_id, reviewer_id):
        return False, "You have already submitted feedback for this session."

    if not (MIN_RATING <= int(rating) <= MAX_RATING):
        return False, f"Rating must be between {MIN_RATING} and {MAX_RATING}."

    db.create_feedback({
        "session_id":  session_id,
        "reviewer_id": reviewer_id,
        "reviewee_id": reviewee_id,
        "rating":      int(rating),
        "comment":     _clean_comment(comment),
    })

    return True, "Feedback submitted. Thank you!"


def get_reviewable_sessions(reviewer_id: str) -> List[Dict]:
    """Return completed sessions the user can still review."""
    reviewer = db.get_user_by_id(reviewer_id)
    if not reviewer:
        return []

    result = []
    for session in db.get_sessions_for_user(reviewer_id):
        if session.get("status") != "completed":
            continue
        if _already_reviewed(session["session_id"], reviewer_id):
            continue

        other_id = session["mentee_id"] if reviewer_id == session.get("mentor_id") else session.get("mentor_id")
        other_user = db.get_user_by_id(other_id) if other_id else None
        result.append({
            **session,
            "other_name": other_user.get("name", "Unknown") if other_user else "Unknown",
        })

    return sorted(
        result,
        key=lambda s: (
            s.get("date", ""),
            s.get("time", ""),
            s.get("session_id", ""),
        ),
        reverse=True,
    )


def get_feedback_session_options(user_id: str) -> List[Dict]:
    """Return session choices for the feedback dropdown, including active sessions."""
    user = db.get_user_by_id(user_id)
    if not user:
        return []

    result = []
    for session in db.get_sessions_for_user(user_id):
        if session.get("status") == "cancelled":
            continue

        other_id = session["mentee_id"] if user_id == session.get("mentor_id") else session.get("mentor_id")
        other_user = db.get_user_by_id(other_id) if other_id else None
        already_reviewed = _already_reviewed(session["session_id"], user_id)
        result.append({
            **session,
            "other_name": other_user.get("name", "Unknown") if other_user else "Unknown",
            "already_reviewed": already_reviewed,
            "can_submit": session.get("status") == "completed" and not already_reviewed,
        })

    def sort_key(session: Dict) -> str:
        if session.get("requested_at"):
            return session["requested_at"]
        date_text = session.get("date", "")
        time_text = session.get("time", "")
        return f"{date_text}T{time_text}"

    return sorted(result, key=sort_key, reverse=True)


def get_feedback_for_mentor(mentor_id: str) -> List[Dict]:
    """Return all feedback received by a mentor, enriched with reviewer names."""
    feedbacks = db.get_feedback_for_user(mentor_id)
    result = []
    for f in feedbacks:
        reviewer = db.get_user_by_id(f["reviewer_id"])
        result.append({
            **f,
            "reviewer_name": reviewer.get("name", "Anonymous") if reviewer else "Anonymous",
        })
    return sorted(result, key=lambda x: x["timestamp"], reverse=True)


def get_feedback_for_mentee(mentee_id: str) -> List[Dict]:
    """Return all feedback received by a mentee."""
    feedbacks = db.get_feedback_for_user(mentee_id)
    result = []
    for f in feedbacks:
        reviewer = db.get_user_by_id(f["reviewer_id"])
        result.append({
            **f,
            "reviewer_name": reviewer.get("name", "Anonymous") if reviewer else "Anonymous",
        })
    return sorted(result, key=lambda x: x["timestamp"], reverse=True)


def get_average_rating(user_id: str) -> float:
    """Return the current average rating for any user."""
    user = db.get_user_by_id(user_id)
    return user.get("rating", 0.0) if user else 0.0


def get_session_feedback(session_id: str) -> Optional[Dict]:
    """Return feedback for a specific session, if any."""
    return db.get_feedback_by_session(session_id)


def get_feedback_summary(user_id: str) -> Dict:
    """
    Return a summary dict:
      average_rating, total_reviews, rating_distribution {1:n, 2:n, ...}
    """
    feedbacks = db.get_feedback_for_user(user_id)
    if not feedbacks:
        return {
            "average_rating":     0.0,
            "total_reviews":      0,
            "rating_distribution": {str(i): 0 for i in range(1, 6)},
        }

    distribution = {str(i): 0 for i in range(1, 6)}
    total = 0
    for f in feedbacks:
        r = int(f.get("rating", 0))
        if 1 <= r <= 5:
            distribution[str(r)] += 1
            total += r

    avg = round(total / len(feedbacks), 2) if feedbacks else 0.0
    return {
        "average_rating":      avg,
        "total_reviews":       len(feedbacks),
        "rating_distribution": distribution,
    }


def get_recent_reviews(user_id: str, limit: int = 5) -> List[Dict]:
    """Return the *limit* most recent feedback entries for a user."""
    return get_feedback_for_mentor(user_id)[:limit]
