"""rate_limiter.py — Distributed-capable rate limiter with Redis backend and in-memory fallback.

Implements a sliding-window limiter using Redis sorted-sets when available, and a
simple in-memory deque-based fallback otherwise. The API is intentionally small
so it can be reused by decorators or middleware.
"""

from __future__ import annotations

import os
import time
import uuid
import logging
import threading
from collections import deque
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_HAS_REDIS = False
_REDIS_CLIENT = None
try:
    import redis as _redis
    _HAS_REDIS = True
except Exception:
    _redis = None
    _HAS_REDIS = False


class _RedisBackend:
    def __init__(self, url: Optional[str]):
        self.url = url or os.environ.get("REDIS_URL")
        if not self.url:
            raise RuntimeError("No REDIS_URL provided")
        self._client = _redis.from_url(self.url, decode_responses=True)

    def allow(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """Sliding-window via sorted set. Returns (allowed, retry_after_seconds)."""
        client = self._client
        now_ms = int(time.time() * 1000)
        window_ms = int(window * 1000)
        min_score = now_ms - window_ms
        member = f"{now_ms}-{uuid.uuid4().hex}"

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, min_score)
        pipe.zadd(key, {member: now_ms})
        pipe.zcard(key)
        pipe.zrange(key, 0, 0, withscores=True)
        pipe.expire(key, window)
        res = pipe.execute()

        count = int(res[2] or 0)
        earliest = None
        if res[3]:
            # res[3] is a list of tuples [(member, score)]
            try:
                earliest = int(float(res[3][0][1]))
            except Exception:
                earliest = None

        if count <= limit:
            return True, 0

        if earliest is None:
            return False, window

        retry_after_ms = window_ms - (now_ms - earliest)
        retry_after = int((retry_after_ms + 999) / 1000) if retry_after_ms > 0 else 1
        return False, retry_after

    def reset(self, key: Optional[str] = None) -> None:
        if key:
            try:
                self._client.delete(key)
            except Exception:
                logger.debug("Failed to delete redis key %s", key)
        else:
            if os.environ.get("ALLOW_REDIS_FLUSH", "0") in ("1", "true", "yes"):
                try:
                    self._client.flushdb()
                except Exception:
                    logger.debug("Failed to flush redis DB")
            else:
                logger.warning("Skipping full Redis flush; set ALLOW_REDIS_FLUSH=1 to enable")


class _MemoryBackend:
    def __init__(self):
        self._limits = {}
        self._lock = threading.RLock()

    def allow(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - window
        with self._lock:
            dq = self._limits.get(key)
            if dq is None:
                dq = deque()
                self._limits[key] = dq
            # remove old
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= limit:
                earliest = dq[0]
                retry_after = int(max(1, window - (now - earliest)))
                return False, retry_after
            dq.append(now)
            return True, 0

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key:
                self._limits.pop(key, None)
            else:
                self._limits.clear()


class RateLimiter:
    def __init__(self, redis_url: Optional[str] = None):
        self.backend = None
        if _HAS_REDIS and (redis_url or os.environ.get("REDIS_URL")):
            try:
                self.backend = _RedisBackend(redis_url)
            except Exception:
                logger.debug("Redis backend init failed; falling back to memory")
                self.backend = _MemoryBackend()
        else:
            self.backend = _MemoryBackend()

    def allow_request(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        try:
            return self.backend.allow(key, limit, window)
        except Exception:
            logger.exception("Rate limiter backend failure; allowing request by default")
            return True, 0

    def reset(self, key: Optional[str] = None) -> None:
        try:
            self.backend.reset(key)
        except Exception:
            logger.exception("Failed to reset rate limiter state")


# Default singleton used by decorators
default_rate_limiter = RateLimiter()
