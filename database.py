"""
database.py — runtime-selection shim for persistence backends.

By default the legacy JSON-backed implementation is used. To switch to the
SQLite adapter set `DB_ENGINE=sqlite` or `USE_SQLITE=1` in the environment.
This file re-exports the selected backend's public API so the rest of the
codebase can continue to `import database` unchanged.
"""

import os
from typing import Any

# Runtime selection: allow explicit ORM backend, then SQLite, then JSON
_engine = os.environ.get("DB_ENGINE", "").lower()
_use_orm = _engine == "orm" or os.environ.get("USE_SQLALCHEMY", "").lower() in ("1", "true", "yes")
_use_sqlite = _engine == "sqlite" or os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes")

if _use_orm:
    import database_sqlalchemy as _backend
elif _use_sqlite:
    import database_sqlite as _backend
else:
    import database_json as _backend

# Re-export public names from the selected backend
for _name in dir(_backend):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_backend, _name)

__all__ = [n for n in dir(_backend) if not n.startswith("_")]
