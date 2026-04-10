import os
# Run tests against an in-memory SQLite DB seeded from data.json
os.environ.setdefault("USE_SQLITE", "1")
os.environ.setdefault("SQLITE_DB", ":memory:")
import migrate_to_sqlite
migrate_to_sqlite.main()

import pytest
from app import app


@pytest.fixture(scope="module")
def client():
    return app.test_client()


def test_health(client):
    rv = client.get("/health")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get("status") == "ok"


def test_mentors(client):
    rv = client.get("/mentors")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get("ok") is True
    assert isinstance(j.get("mentors"), list)


def test_sessions(client):
    rv = client.get("/sessions")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get("ok") is True
    assert isinstance(j.get("sessions"), list)
