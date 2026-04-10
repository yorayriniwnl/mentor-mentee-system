"""throttle.py — Public decorators and key helpers for rate limiting.

This module delegates to `rate_limiter.default_rate_limiter` which prefers a
Redis-backed sliding-window limiter and falls back to an in-memory deque.
"""

from functools import wraps
from flask import request, jsonify

from rate_limiter import default_rate_limiter
try:
    import metrics as _metrics
    _inc_allowed = getattr(_metrics, "inc_allowed", lambda prefix: None)
    _inc_blocked = getattr(_metrics, "inc_blocked", lambda prefix: None)
except Exception:
    _inc_allowed = lambda prefix: None
    _inc_blocked = lambda prefix: None


def rate_limit(limit: int = 5, window: int = 60, key_func=None, prefix: str = "rl"):
    """Decorator enforcing `limit` requests per `window` seconds using the
    configured rate limiter backend.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                actor = key_func() if callable(key_func) else (request.remote_addr or "anon")
            except Exception:
                actor = request.remote_addr or "anon"

            key = f"{prefix}:{actor}"
            allowed, retry_after = default_rate_limiter.allow_request(key, limit, window)
            if allowed:
                try:
                    _inc_allowed(prefix)
                except Exception:
                    pass
            else:
                try:
                    _inc_blocked(prefix)
                except Exception:
                    pass
                return (
                    jsonify({"ok": False, "error": "rate limit exceeded", "retry_after": retry_after}),
                    429,
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def key_by_roll_no():
    def inner():
        data = request.get_json(silent=True) or {}
        roll = data.get("roll_no") or data.get("roll") or data.get("username")
        if roll:
            return f"roll:{str(roll).lower()}"
        return request.remote_addr or "anon"

    return inner


def key_by_ip():
    def inner():
        return request.remote_addr or "anon"

    return inner


def _reset_all():
    """Reset internal counters (useful for tests)."""
    default_rate_limiter.reset(None)
