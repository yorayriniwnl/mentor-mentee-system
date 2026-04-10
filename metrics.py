"""metrics.py — Lightweight Prometheus metrics helper (optional dependency).

Provides counters for rate-limit allowed/blocked events and a helper to
render the metrics output. The module is defensive: when `prometheus_client`
is not installed, functions become no-ops and `/metrics` will return 501.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROM = True
except Exception:
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    _HAS_PROM = False


if _HAS_PROM:
    RATE_ALLOWED = Counter(
        "app_rate_limit_allowed_total",
        "Number of allowed requests by rate limiter",
        ["prefix"],
    )
    RATE_BLOCKED = Counter(
        "app_rate_limit_blocked_total",
        "Number of blocked requests by rate limiter",
        ["prefix"],
    )
else:
    RATE_ALLOWED = None
    RATE_BLOCKED = None


def inc_allowed(prefix: str) -> None:
    if not _HAS_PROM:
        return
    try:
        RATE_ALLOWED.labels(prefix=prefix).inc()
    except Exception:
        logger.exception("Failed to increment allowed metric")


def inc_blocked(prefix: str) -> None:
    if not _HAS_PROM:
        return
    try:
        RATE_BLOCKED.labels(prefix=prefix).inc()
    except Exception:
        logger.exception("Failed to increment blocked metric")


def metrics_output() -> Optional[bytes]:
    if not _HAS_PROM:
        return None
    try:
        return generate_latest()
    except Exception:
        logger.exception("Failed to render metrics")
        return None


def content_type() -> str:
    return CONTENT_TYPE_LATEST if _HAS_PROM else "text/plain; version=0.0.4"
