"""
migrate_to_sqlite.py — Import `data.json` into the SQLite adapter.

This script is safe to run locally. It will back up any existing SQLite
database at `SQLITE_DB` (or default `data.sqlite3`) and create a fresh
SQLite database populated from `data.json` in the repository.

Usage:
  python migrate_to_sqlite.py

Be sure to set `SQLITE_DB` if you want the DB in a custom location.
"""

import os
import json
import shutil
import time
import sys

from pathlib import Path

HERE = Path(__file__).parent
DATA_JSON = HERE / "data.json"

def main():
    # Determine backend selection and import the matching module
    engine = os.environ.get("DB_ENGINE", "").lower()
    use_orm = engine == "orm" or os.environ.get("USE_SQLALCHEMY", "").lower() in ("1", "true", "yes")
    use_sqlite = engine == "sqlite" or os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes")

    if use_orm:
        import database_sqlalchemy as db_mod
        # DB_PATH may be a SQLAlchemy URL (e.g. sqlite:///./file)
        raw = getattr(db_mod, "DB_PATH", None)
        db_file = None
        if raw and raw.startswith("sqlite:///"):
            db_file = Path(raw.replace("sqlite:///", ""))
        elif raw and raw == ":memory:":
            db_file = None
        elif raw:
            db_file = Path(raw)
    elif use_sqlite:
        import database_sqlite as db_mod
        db_file = Path(db_mod.DB_PATH) if getattr(db_mod, "DB_PATH", None) != ":memory:" else None
    else:
        # Default to SQLite adapter for disk-backed DB
        import database_sqlite as db_mod
        db_file = Path(db_mod.DB_PATH) if getattr(db_mod, "DB_PATH", None) != ":memory:" else None

    if db_file and db_file.exists():
        bak = db_file.with_suffix(db_file.suffix + f".bak.{int(time.time())}")
        print(f"Backing up existing DB: {db_file} -> {bak}")
        shutil.copy2(db_file, bak)
        try:
            db_file.unlink()
        except Exception:
            print("Could not remove existing DB file. Aborting.")
            sys.exit(1)

    # Ensure schema exists for the selected backend
    try:
        if hasattr(db_mod, "_get_conn"):
            # sqlite adapter exposes a connection helper
            conn = db_mod._get_conn()
            # Clear existing tables if present
            cur = conn.cursor()
            with conn:
                cur.execute("DELETE FROM users")
                cur.execute("DELETE FROM sessions")
                cur.execute("DELETE FROM messages")
                cur.execute("DELETE FROM feedback")
        elif hasattr(db_mod, "_get_engine"):
            # ORM backend: recreate schema
            eng = db_mod._get_engine()
            db_mod.Base.metadata.drop_all(bind=eng)
            db_mod.Base.metadata.create_all(bind=eng)
        else:
            # Unknown backend — continue
            pass
    except Exception:
        # Ignore schema-clear errors on fresh DBs
        pass

    if not DATA_JSON.exists():
        print(f"Source data.json not found at {DATA_JSON}. Nothing to import.")
        return

    with open(DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    users = data.get("users", [])
    sessions = data.get("sessions", [])
    messages = data.get("messages", [])
    feedback = data.get("feedback", [])

    print(f"Importing {len(users)} users, {len(sessions)} sessions, {len(messages)} messages, {len(feedback)} feedback entries")

    try:
        # Insert records using the selected backend's public API
        for u in users:
            db_mod.create_user(u)

        for s in sessions:
            db_mod.create_session(s)

        for m in messages:
            db_mod.create_message(m)

        for f in feedback:
            db_mod.create_feedback(f)

    except Exception as exc:
        print("Error during import:", exc)
        sys.exit(1)

    print("Import complete.")


if __name__ == "__main__":
    main()
