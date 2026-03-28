"""
matching.py — Weighted mentor-matching engine.

Scoring breakdown (total = 100 pts):
  • Skill overlap        40 pts
  • Availability overlap 25 pts
  • Experience level     20 pts
  • Rating               15 pts
"""

from typing import Dict, List, Tuple

import database as db

# ──────────────────────── Weight constants ───────────────────────

W_SKILLS       = 40
W_AVAILABILITY = 25
W_EXPERIENCE   = 20
W_RATING       = 15

MAX_RATING     = 5.0
MAX_EXPERIENCE = 15      # years – score saturates here


# ──────────────────────── Sub-scorers ────────────────────────────

def _skill_score(mentor_skills: List[str], mentee_skills: List[str]) -> float:
    """
    Jaccard-like overlap: points based on how many mentee skills the mentor covers.
    Full score when the mentor covers every skill the mentee wants.
    """
    if not mentee_skills:
        return W_SKILLS / 2  # neutral when no preference
    m_set = {s.lower() for s in mentor_skills}
    t_set = {s.lower() for s in mentee_skills}
    overlap = len(m_set & t_set)
    return W_SKILLS * (overlap / len(t_set))


def _availability_score(mentor_avail: List[str], mentee_avail: List[str]) -> float:
    """Points for shared available days."""
    if not mentee_avail:
        return W_AVAILABILITY / 2
    m_set = {d.lower() for d in mentor_avail}
    t_set = {d.lower() for d in mentee_avail}
    overlap = len(m_set & t_set)
    return W_AVAILABILITY * (overlap / len(t_set))


def _experience_score(mentor_years: int) -> float:
    """
    Linearly scales up to MAX_EXPERIENCE years, then caps.
    A mentor with 0 years still gets a small base score.
    """
    clamped = min(mentor_years, MAX_EXPERIENCE)
    return W_EXPERIENCE * (clamped / MAX_EXPERIENCE)


def _rating_score(mentor_rating: float, sessions_completed: int) -> float:
    """
    Weighted rating – mentors with <5 sessions get a slight penalty
    to avoid over-ranking brand-new accounts with a single perfect review.
    """
    if sessions_completed < 5:
        effective = mentor_rating * 0.75
    else:
        effective = mentor_rating
    return W_RATING * (effective / MAX_RATING)


# ──────────────────────── Main scorer ────────────────────────────

def score_mentor(mentor: Dict, mentee: Dict) -> float:
    """Return a 0-100 compatibility score for a (mentor, mentee) pair."""
    s = 0.0
    s += _skill_score(
        mentor.get("skills", []),
        mentee.get("skills", []),
    )
    s += _availability_score(
        mentor.get("availability", []),
        mentee.get("availability", []),
    )
    s += _experience_score(mentor.get("experience_years", 0))
    s += _rating_score(
        mentor.get("rating", 0.0),
        mentor.get("sessions_completed", 0),
    )
    return round(s, 2)


def score_breakdown(mentor: Dict, mentee: Dict) -> Dict[str, float]:
    """Return per-component scores for display / debugging."""
    return {
        "skill_score":        round(_skill_score(mentor.get("skills", []), mentee.get("skills", [])), 2),
        "availability_score": round(_availability_score(mentor.get("availability", []), mentee.get("availability", [])), 2),
        "experience_score":   round(_experience_score(mentor.get("experience_years", 0)), 2),
        "rating_score":       round(_rating_score(mentor.get("rating", 0.0), mentor.get("sessions_completed", 0)), 2),
        "total":              score_mentor(mentor, mentee),
    }


# ──────────────────────── Public API ─────────────────────────────

def find_matches(
    mentee_id: str,
    top_n: int = 5,
    min_score: float = 0.0,
) -> List[Tuple[Dict, float]]:
    """
    Return the top-N mentors ranked by compatibility with *mentee_id*.

    Returns a list of (mentor_profile, score) tuples, highest score first.
    Excludes mentors the mentee has already booked a confirmed session with.
    """
    mentee = db.get_user_by_id(mentee_id)
    if not mentee:
        return []

    assigned_mentor = db.get_assigned_mentor(mentee_id)
    if assigned_mentor:
        score = score_mentor(assigned_mentor, mentee)
        if score < min_score:
            return []
        safe = {k: v for k, v in assigned_mentor.items() if k != "password"}
        return [(safe, score)]

    # Exclude mentors already paired with this mentee (confirmed sessions)
    confirmed_mentor_ids = {
        s["mentor_id"]
        for s in db.get_sessions_for_user(mentee_id)
        if s.get("status") == "confirmed"
    }

    mentors = [
        u for u in db.get_users_by_role("mentor")
        if u["user_id"] not in confirmed_mentor_ids
    ]

    scored = [
        (mentor, score_mentor(mentor, mentee))
        for mentor in mentors
    ]
    # Filter by minimum score, sort descending
    filtered = [(m, s) for m, s in scored if s >= min_score]
    filtered.sort(key=lambda x: x[1], reverse=True)

    # Strip password before returning
    results = []
    for mentor, s in filtered[:top_n]:
        safe = {k: v for k, v in mentor.items() if k != "password"}
        results.append((safe, s))

    return results


def get_match_details(mentor_id: str, mentee_id: str) -> Dict:
    """
    Return a full breakdown of why a specific mentor-mentee pair scored as they did.
    """
    mentor = db.get_user_by_id(mentor_id)
    mentee = db.get_user_by_id(mentee_id)
    if not mentor or not mentee:
        return {}

    shared_skills = list(
        {s.lower() for s in mentor.get("skills", [])}
        & {s.lower() for s in mentee.get("skills", [])}
    )
    shared_days = list(
        {d.lower() for d in mentor.get("availability", [])}
        & {d.lower() for d in mentee.get("availability", [])}
    )

    breakdown = score_breakdown(mentor, mentee)
    return {
        "mentor_name":    mentor.get("name"),
        "mentee_name":    mentee.get("name"),
        "shared_skills":  shared_skills,
        "shared_days":    shared_days,
        "scores":         breakdown,
    }
