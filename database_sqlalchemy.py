"""database_sqlalchemy.py — SQLAlchemy-backed adapter compatible with existing API.

This module provides the same public functions as the other backends so the
application can switch to an ORM-based implementation by setting
`DB_ENGINE=orm` or `USE_SQLALCHEMY=1`.

The implementation is intentionally conservative: it creates tables via
`Base.metadata.create_all(engine)` and stores list fields as JSON-encoded
text to maintain parity with the JSON/SQLite backends.
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

DB_PATH = os.environ.get("SQLALCHEMY_DATABASE_URI") or (
    ("sqlite:///" + (os.environ.get("SQLITE_DB") or os.path.join(os.path.dirname(__file__), "data.sqlite3")))
)

_engine = None
_Session = None


def _get_engine():
    global _engine, _Session
    if _engine is None:
        connect_args = {}
        if DB_PATH.startswith("sqlite"):
            # allow multi-threaded access for test servers
            connect_args = {"connect_args": {"check_same_thread": False}}
        _engine = create_engine(DB_PATH, echo=False, future=True, **(connect_args or {}))
        _Session = scoped_session(sessionmaker(bind=_engine, future=True, expire_on_commit=False))
        Base.metadata.create_all(_engine)
    return _engine


def _get_session():
    _get_engine()
    return _Session()


Base = declarative_base()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    name = Column(String)
    roll_no = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(Text)
    role = Column(String)
    contact_number = Column(String)
    skills = Column(Text)
    experience_years = Column(Integer)
    rating = Column(Float)
    sessions_completed = Column(Integer)
    availability = Column(Text)
    bio = Column(Text)
    hourly_rate = Column(Float)
    assigned_mentor_id = Column(String)
    profile_image = Column(String)
    reg_no = Column(String)
    school = Column(String)
    program = Column(String)
    semester = Column(String)
    created_at = Column(String)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "roll_no": self.roll_no,
            "email": self.email,
            "password": self.password,
            "role": self.role,
            "contact_number": self.contact_number,
            "skills": json.loads(self.skills) if self.skills else [],
            "experience_years": self.experience_years,
            "rating": self.rating,
            "sessions_completed": self.sessions_completed,
            "availability": json.loads(self.availability) if self.availability else [],
            "bio": self.bio,
            "hourly_rate": self.hourly_rate,
            "assigned_mentor_id": self.assigned_mentor_id,
            "profile_image": self.profile_image,
            "reg_no": self.reg_no,
            "school": self.school,
            "program": self.program,
            "semester": self.semester,
            "created_at": self.created_at,
        }


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True)
    mentor_id = Column(String, index=True)
    mentee_id = Column(String, index=True)
    date = Column(String)
    time = Column(String)
    duration_minutes = Column(Integer)
    topic = Column(String)
    concern = Column(Text)
    status = Column(String)
    requested_at = Column(String)
    resolved_at = Column(String)
    notes = Column(Text)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "mentor_id": self.mentor_id,
            "mentee_id": self.mentee_id,
            "date": self.date,
            "time": self.time,
            "duration_minutes": self.duration_minutes,
            "topic": self.topic,
            "concern": self.concern,
            "status": self.status,
            "requested_at": self.requested_at,
            "resolved_at": self.resolved_at,
            "notes": self.notes,
        }


class Message(Base):
    __tablename__ = "messages"
    message_id = Column(String, primary_key=True)
    sender_id = Column(String, index=True)
    receiver_id = Column(String, index=True)
    text = Column(Text)
    content = Column(Text)
    timestamp = Column(String)
    flagged = Column(Boolean, default=False)
    session_id = Column(String, index=True)

    def to_dict(self):
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "text": self.text,
            "content": self.content,
            "timestamp": self.timestamp,
            "flagged": bool(self.flagged),
            "session_id": self.session_id,
        }


class Feedback(Base):
    __tablename__ = "feedback"
    feedback_id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    reviewer_id = Column(String)
    reviewee_id = Column(String, index=True)
    rating = Column(Integer)
    comment = Column(Text)
    timestamp = Column(String)

    def to_dict(self):
        return {
            "feedback_id": self.feedback_id,
            "session_id": self.session_id,
            "reviewer_id": self.reviewer_id,
            "reviewee_id": self.reviewee_id,
            "rating": self.rating,
            "comment": self.comment,
            "timestamp": self.timestamp,
        }


class Token(Base):
    __tablename__ = "tokens"
    jti = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    created_at = Column(String)
    revoked_at = Column(String, nullable=True)


# -------------------- Users --------------------


def get_all_users() -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(User).order_by(User.name).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def get_user_by_id(user_id: str) -> Optional[Dict]:
    s = _get_session()
    try:
        r = s.get(User, user_id)
        return r.to_dict() if r else None
    finally:
        s.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    s = _get_session()
    try:
        r = s.query(User).filter(User.email.ilike(email)).first()
        return r.to_dict() if r else None
    finally:
        s.close()


def get_user_by_roll_no(roll_no: str) -> Optional[Dict]:
    s = _get_session()
    try:
        r = s.query(User).filter(User.roll_no.ilike(roll_no)).first()
        return r.to_dict() if r else None
    finally:
        s.close()


def get_users_by_role(role: str) -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(User).filter(User.role == role).order_by(User.name).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def create_user(user: Dict) -> Dict:
    s = _get_session()
    try:
        uid = user.get("user_id") or generate_id("u")
        now = now_iso()
        u = User(
            user_id=uid,
            name=user.get("name"),
            roll_no=user.get("roll_no"),
            email=user.get("email"),
            password=user.get("password"),
            role=user.get("role"),
            contact_number=user.get("contact_number"),
            skills=json.dumps(user.get("skills", []), ensure_ascii=False),
            experience_years=user.get("experience_years", 0),
            rating=user.get("rating", 0.0),
            sessions_completed=user.get("sessions_completed", 0),
            availability=json.dumps(user.get("availability", []), ensure_ascii=False),
            bio=user.get("bio"),
            hourly_rate=user.get("hourly_rate"),
            assigned_mentor_id=user.get("assigned_mentor_id"),
            profile_image=user.get("profile_image"),
            reg_no=user.get("reg_no"),
            school=user.get("school"),
            program=user.get("program"),
            semester=user.get("semester"),
            created_at=now,
        )
        s.add(u)
        s.commit()
        return get_user_by_id(uid)
    finally:
        s.close()


def update_user(user_id: str, fields: Dict) -> Optional[Dict]:
    s = _get_session()
    try:
        u = s.get(User, user_id)
        if not u:
            return None
        for k, v in fields.items():
            if k in ("skills", "availability"):
                setattr(u, k, json.dumps(v, ensure_ascii=False))
            else:
                setattr(u, k, v)
        s.add(u)
        s.commit()
        return get_user_by_id(user_id)
    finally:
        s.close()


def delete_user(user_id: str) -> bool:
    s = _get_session()
    try:
        u = s.get(User, user_id)
        if not u:
            return False
        s.delete(u)
        s.commit()
        return True
    finally:
        s.close()


# -------------------- Sessions --------------------


def get_all_sessions() -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Session).order_by(Session.requested_at.desc()).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def get_session_by_id(session_id: str) -> Optional[Dict]:
    s = _get_session()
    try:
        r = s.get(Session, session_id)
        return r.to_dict() if r else None
    finally:
        s.close()


def get_sessions_for_user(user_id: str) -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Session).filter((Session.mentor_id == user_id) | (Session.mentee_id == user_id)).order_by(Session.requested_at.desc()).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def create_session(session: Dict) -> Dict:
    s = _get_session()
    try:
        sid = session.get("session_id") or generate_id("S")
        now = now_iso()
        sess = Session(
            session_id=sid,
            mentor_id=session.get("mentor_id"),
            mentee_id=session.get("mentee_id"),
            date=session.get("date"),
            time=session.get("time"),
            duration_minutes=session.get("duration_minutes", 0),
            topic=session.get("topic"),
            concern=session.get("concern"),
            status=session.get("status", "pending"),
            requested_at=session.get("requested_at", now),
            resolved_at=session.get("resolved_at"),
            notes=session.get("notes"),
        )
        s.add(sess)
        s.commit()
        return get_session_by_id(sid)
    finally:
        s.close()


def update_session(session_id: str, fields: Dict) -> Optional[Dict]:
    s = _get_session()
    try:
        sess = s.get(Session, session_id)
        if not sess:
            return None
        for k, v in fields.items():
            setattr(sess, k, v)
        s.add(sess)
        s.commit()
        return get_session_by_id(session_id)
    finally:
        s.close()


def delete_session(session_id: str) -> bool:
    s = _get_session()
    try:
        sess = s.get(Session, session_id)
        if not sess:
            return False
        s.delete(sess)
        s.commit()
        return True
    finally:
        s.close()


# -------------------- Messages --------------------


def get_all_messages() -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Message).order_by(Message.timestamp).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def get_conversation(user_a: str, user_b: str, session_id: Optional[str] = None) -> List[Dict]:
    s = _get_session()
    try:
        q = s.query(Message).filter(
            ((Message.sender_id == user_a) & (Message.receiver_id == user_b)) | ((Message.sender_id == user_b) & (Message.receiver_id == user_a))
        )
        if session_id:
            q = q.filter(Message.session_id == session_id)
        rows = q.order_by(Message.timestamp).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def create_message(message: Dict) -> Dict:
    s = _get_session()
    try:
        mid = message.get("message_id") or generate_id("m")
        ts = message.get("timestamp") or now_iso()
        text = message.get("text") or message.get("content")
        content = message.get("content") or message.get("text")
        flagged = bool(message.get("flagged"))
        msg = Message(
            message_id=mid,
            sender_id=message.get("sender_id"),
            receiver_id=message.get("receiver_id"),
            text=text,
            content=content,
            timestamp=ts,
            flagged=flagged,
            session_id=message.get("session_id"),
        )
        s.add(msg)
        s.commit()
        return get_all_messages()[-1] if get_all_messages() else {"message_id": mid}
    finally:
        s.close()


def flag_message(message_id: str) -> bool:
    s = _get_session()
    try:
        m = s.get(Message, message_id)
        if not m:
            return False
        m.flagged = True
        s.add(m)
        s.commit()
        return True
    finally:
        s.close()


def get_flagged_messages() -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Message).filter(Message.flagged == True).order_by(Message.timestamp).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


# -------------------- Feedback --------------------


def get_all_feedback() -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Feedback).order_by(Feedback.timestamp.desc()).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def get_feedback_for_user(user_id: str) -> List[Dict]:
    s = _get_session()
    try:
        rows = s.query(Feedback).filter(Feedback.reviewee_id == user_id).order_by(Feedback.timestamp.desc()).all()
        return [r.to_dict() for r in rows]
    finally:
        s.close()


def get_feedback_by_session(session_id: str) -> Optional[Dict]:
    s = _get_session()
    try:
        r = s.query(Feedback).filter(Feedback.session_id == session_id).first()
        return r.to_dict() if r else None
    finally:
        s.close()


def create_feedback(feedback: Dict) -> Dict:
    s = _get_session()
    try:
        fid = feedback.get("feedback_id") or generate_id("f")
        ts = feedback.get("timestamp") or now_iso()
        f = Feedback(
            feedback_id=fid,
            session_id=feedback.get("session_id"),
            reviewer_id=feedback.get("reviewer_id"),
            reviewee_id=feedback.get("reviewee_id"),
            rating=int(feedback.get("rating", 0)),
            comment=feedback.get("comment", ""),
            timestamp=ts,
        )
        s.add(f)
        s.commit()
        # Recalculate rating
        _recalculate_rating(feedback.get("reviewee_id"))
        return get_feedback_by_session(feedback.get("session_id")) or {"feedback_id": fid}
    finally:
        s.close()


def _recalculate_rating(user_id: str) -> None:
    ratings = [f["rating"] for f in get_feedback_for_user(user_id) if isinstance(f.get("rating"), (int, float))]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    update_user(user_id, {"rating": avg})


# -------------------- Tokens --------------------


def create_token(jti: str, user_id: str) -> None:
    s = _get_session()
    try:
        now = now_iso()
        t = Token(jti=jti, user_id=user_id, created_at=now, revoked_at=None)
        s.merge(t)
        s.commit()
    finally:
        s.close()


def revoke_token(jti: str) -> bool:
    s = _get_session()
    try:
        t = s.get(Token, jti)
        if not t or t.revoked_at:
            return False
        t.revoked_at = now_iso()
        s.add(t)
        s.commit()
        return True
    finally:
        s.close()


def is_token_revoked(jti: str) -> bool:
    s = _get_session()
    try:
        t = s.get(Token, jti)
        return bool(t and t.revoked_at)
    finally:
        s.close()
