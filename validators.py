"""
validators.py — Small input validation helpers used by the API.

Keep these lightweight to avoid adding heavy dependencies. For stronger
validation use pydantic or Marshmallow when moving to a full API service.
"""

import re
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: Any) -> bool:
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_RE.match(email.strip()))


def is_safe_text(value: Any, max_length: int = 1024) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    s = value.strip()
    return 0 < len(s) <= max_length


def safe_roll_no(roll: Any) -> bool:
    if not roll or not isinstance(roll, str):
        return False
    r = roll.strip()
    return 2 <= len(r) <= 64
