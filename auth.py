"""
auth.py — Registration, login, and password management.
Passwords are hashed with bcrypt; plain-text is never stored.
"""

import re
from typing import Optional, Tuple
import os
import jwt
from datetime import datetime, timezone, timedelta

import bcrypt

import database as db

# JWT configuration
JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY") or "dev-secret"


def generate_token(user_id: str, hours: int = 4) -> str:
    """Generate a JWT for a user_id valid for `hours` hours."""
    now = datetime.now(timezone.utc)
    payload = {"user_id": user_id, "iat": now, "exp": now + timedelta(hours=hours)}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    # PyJWT may return bytes in older versions — ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT and return the payload, or None on error/expiry."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

# ─────────────────────────── Password helpers ───────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* as a UTF-8 string."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─────────────────────────── Validation ─────────────────────────

def _strong_password(password: str) -> Tuple[bool, str]:
    """Return (ok, reason).  Requires 8+ chars, digit, uppercase, special."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character."
    return True, ""


# ─────────────────────────── Public API ─────────────────────────

def login(roll_no: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Authenticate a user using Roll No and password.
    Returns (True, user_dict) on success or (False, None) on failure.
    """
    user = db.get_user_by_roll_no(roll_no)
    if not user:
        return False, None
    if not verify_password(password, user.get("password", "")):
        return False, None
    # Return a copy without the password field
    safe = {k: v for k, v in user.items() if k != "password"}
    return True, safe


def change_password(user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Change a user's password after verifying the old one.
    """
    user = db.get_user_by_id(user_id)
    if not user:
        return False, "User not found."
    if not verify_password(old_password, user.get("password", "")):
        return False, "Current password is incorrect."
    ok, reason = _strong_password(new_password)
    if not ok:
        return False, reason
    db.update_user(user_id, {"password": hash_password(new_password)})
    return True, "Password changed successfully."


def reset_password(roll_no: str, new_password: str) -> Tuple[bool, str]:
    """
    Admin / forgot-password flow: reset without checking the old password.
    In production this would be gated behind an email OTP.
    """
    user = db.get_user_by_roll_no(roll_no)
    if not user:
        return False, "No account found with that roll number."
    ok, reason = _strong_password(new_password)
    if not ok:
        return False, reason
    db.update_user(user["user_id"], {"password": hash_password(new_password)})
    return True, "Password reset successfully."


def get_profile(user_id: str) -> Optional[dict]:
    """Return user profile without the password hash."""
    user = db.get_user_by_id(user_id)
    if not user:
        return None
    return {k: v for k, v in user.items() if k != "password"}


def update_profile(user_id: str, fields: dict) -> Tuple[bool, str]:
    """
    Update allowed profile fields for a user.
    Password updates must go through change_password().
    """
    FORBIDDEN = {"user_id", "password", "role"}
    safe_fields = {k: v for k, v in fields.items() if k not in FORBIDDEN}
    if not safe_fields:
        return False, "No valid fields to update."
    updated = db.update_user(user_id, safe_fields)
    if not updated:
        return False, "User not found."
    return True, "Profile updated successfully."
