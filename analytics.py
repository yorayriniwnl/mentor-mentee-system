"""
analytics.py — Platform-wide analytics and leaderboards.

Provides:
  • Top mentors by rating, sessions, or a composite score
  • Platform-wide session stats
  • Skill demand heatmap
  • Mentee engagement metrics
"""

from collections import Counter
from typing import Dict, List

import database as db

# ──────────────────────── Mentor leaderboard ─────────────────────

def _composite_score(mentor: Dict) -> float:
    """
    Composite leaderboard score:
      60% rating (normalised to 5) + 40% sessions (capped at 50)
    """
    rating_norm   = mentor.get("rating", 0.0) / 5.0
    sessions_norm = min(mentor.get("sessions_completed", 0), 50) / 50.0
    return round(0.60 * rating_norm + 0.40 * sessions_norm, 4)


def top_mentors(
    n: int = 10,
    sort_by: str = "composite",   # "composite" | "rating" | "sessions"
) -> List[Dict]:
    """
    Return the top-N mentors sorted by the chosen metric.
    Password hashes are excluded from the output.
    """
    mentors = db.get_users_by_role("mentor")

    if sort_by == "rating":
        key = lambda m: (m.get("rating", 0.0), m.get("sessions_completed", 0))
    elif sort_by == "sessions":
        key = lambda m: (m.get("sessions_completed", 0), m.get("rating", 0.0))
    else:
        key = _composite_score

    ranked = sorted(mentors, key=key, reverse=True)[:n]

    result = []
    for rank, mentor in enumerate(ranked, start=1):
        safe = {k: v for k, v in mentor.items() if k != "password"}
        safe["rank"]            = rank
        safe["composite_score"] = _composite_score(mentor)
        result.append(safe)
    return result


# ──────────────────────── Session analytics ─────────────────────

def session_stats() -> Dict:
    """
    Return aggregate session statistics:
      total, by_status counts, avg_duration, completion_rate
    """
    sessions = db.get_all_sessions()
    if not sessions:
        return {
            "total":           0,
            "by_status":       {},
            "avg_duration":    0,
            "completion_rate": 0.0,
        }

    status_counts = Counter(s.get("status", "unknown") for s in sessions)
    total_duration = sum(s.get("duration_minutes", 0) for s in sessions)
    avg_duration   = round(total_duration / len(sessions), 1)
    completed      = status_counts.get("completed", 0)
    completion_rate = round(completed / len(sessions) * 100, 1) if sessions else 0.0

    return {
        "total":           len(sessions),
        "by_status":       dict(status_counts),
        "avg_duration":    avg_duration,
        "completion_rate": completion_rate,
    }


def sessions_per_mentor() -> List[Dict]:
    """Return each mentor's session count (all statuses)."""
    mentors = db.get_users_by_role("mentor")
    all_sessions = db.get_all_sessions()

    result = []
    for mentor in mentors:
        mid = mentor["user_id"]
        count = sum(1 for s in all_sessions if s.get("mentor_id") == mid)
        result.append({
            "mentor_id":   mid,
            "mentor_name": mentor.get("name"),
            "session_count": count,
        })
    return sorted(result, key=lambda x: x["session_count"], reverse=True)


# ──────────────────────── Skill analytics ────────────────────────

def skill_demand() -> List[Dict]:
    """
    Return skills ranked by how many mentees want them.
    Useful for understanding platform demand.
    """
    mentees = db.get_users_by_role("mentee")
    counter: Counter = Counter()
    for mentee in mentees:
        for skill in mentee.get("skills", []):
            counter[skill.title()] += 1
    return [
        {"skill": skill, "demand": count}
        for skill, count in counter.most_common()
    ]


def skill_supply() -> List[Dict]:
    """Skills ranked by how many mentors offer them."""
    mentors = db.get_users_by_role("mentor")
    counter: Counter = Counter()
    for mentor in mentors:
        for skill in mentor.get("skills", []):
            counter[skill.title()] += 1
    return [
        {"skill": skill, "supply": count}
        for skill, count in counter.most_common()
    ]


def skill_gap() -> List[Dict]:
    """
    Identify skills in demand that have low supply.
    Returns list sorted by gap (demand - supply) descending.
    """
    demand = {d["skill"]: d["demand"] for d in skill_demand()}
    supply = {s["skill"]: s["supply"] for s in skill_supply()}
    all_skills = set(demand) | set(supply)

    gaps = []
    for skill in all_skills:
        d = demand.get(skill, 0)
        s = supply.get(skill, 0)
        gaps.append({"skill": skill, "demand": d, "supply": s, "gap": d - s})
    return sorted(gaps, key=lambda x: x["gap"], reverse=True)


# ──────────────────────── User stats ─────────────────────────────

def platform_summary() -> Dict:
    """High-level snapshot of the whole platform."""
    users    = db.get_all_users()
    mentors  = [u for u in users if u.get("role") == "mentor"]
    mentees  = [u for u in users if u.get("role") == "mentee"]
    feedback = db.get_all_feedback()

    avg_rating = (
        round(sum(f.get("rating", 0) for f in feedback) / len(feedback), 2)
        if feedback else 0.0
    )

    s_stats = session_stats()

    return {
        "total_users":       len(users),
        "total_mentors":     len(mentors),
        "total_mentees":     len(mentees),
        "total_feedback":    len(feedback),
        "avg_platform_rating": avg_rating,
        "sessions":          s_stats,
    }


def mentor_performance(mentor_id: str) -> Dict:
    """Detailed performance card for a single mentor."""
    mentor = db.get_user_by_id(mentor_id)
    if not mentor or mentor.get("role") != "mentor":
        return {}

    sessions  = db.get_sessions_for_user(mentor_id)
    feedbacks = db.get_feedback_for_user(mentor_id)

    completed  = [s for s in sessions if s.get("status") == "completed"]
    cancelled  = [s for s in sessions if s.get("status") == "cancelled"]
    requested  = [s for s in sessions if s.get("status") == "requested"]
    pending    = [s for s in sessions if s.get("status") == "pending"]
    confirmed  = [s for s in sessions if s.get("status") == "confirmed"]

    unique_mentees = len({s["mentee_id"] for s in sessions})

    return {
        "name":              mentor.get("name"),
        "rating":            mentor.get("rating", 0.0),
        "total_sessions":    len(sessions),
        "completed":         len(completed),
        "cancelled":         len(cancelled),
        "requested":         len(requested),
        "pending":           len(pending),
        "confirmed":         len(confirmed),
        "unique_mentees":    unique_mentees,
        "total_reviews":     len(feedbacks),
        "composite_score":   _composite_score(mentor),
    }
