"""logging_config.py — Structured logging and optional Sentry integration.

Configures a JSON-friendly logger (when `python-json-logger` is available),
adds a Flask request-context filter to attach `request_id` and `remote_addr`
into log records, and optionally initializes Sentry when `SENTRY_DSN` is set.

This module is defensive: it works without the extra packages installed and
will not raise during import in test environments.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

from flask import has_request_context, request, g

try:
    from pythonjsonlogger import jsonlogger
    _HAS_JSONLOGGER = True
except Exception:
    jsonlogger = None
    _HAS_JSONLOGGER = False


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = getattr(g, "request_id", None) if has_request_context() else None
            record.remote_addr = request.remote_addr if has_request_context() else None
        except Exception:
            record.request_id = None
            record.remote_addr = None
        return True


def _make_formatter() -> logging.Formatter:
    if _HAS_JSONLOGGER:
        # JSON formatter will include whatever attributes are set on the record
        return jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(remote_addr)s")
    return logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s [request_id=%(request_id)s remote=%(remote_addr)s]")


def init_logging(app: Optional[object] = None) -> None:
    """Initialize root logging and (optionally) attach Flask hooks."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(_make_formatter())
    handler.addFilter(RequestContextFilter())

    # Ensure at least one handler is present and adopt our formatter
    if not root.handlers:
        root.addHandler(handler)
    else:
        for h in list(root.handlers):
            h.setFormatter(handler.formatter)
            h.addFilter(RequestContextFilter())

    # Optional Sentry integration
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FlaskIntegration()],
                traces_sample_rate=float(os.environ.get("SENTRY_TRACES", "0.0")),
            )
            root.info("Sentry initialized")
        except Exception:
            root.exception("Failed to initialize Sentry (continuing)")

    # If a Flask app is provided, register request-id middleware
    if app is not None:
        @app.before_request
        def _assign_request_id():
            rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            g.request_id = rid

        @app.after_request
        def _add_request_id(resp):
            try:
                resp.headers["X-Request-ID"] = g.request_id
            except Exception:
                pass
            return resp
