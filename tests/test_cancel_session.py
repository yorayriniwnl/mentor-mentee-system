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


def test_create_and_cancel_session(client):
    # Create a mentee user
    rv = client.post(
        "/users",
        json={
            "name": "Test Mentee",
            "roll_no": "TST_CANCEL_001",
            "email": "t_cancel@example.com",
            "password": "Test123!",
        },
    )
    if rv.status_code == 201:
        j = rv.get_json()
        assert j and j.get("ok") is True
        mentee_id = j["user"]["user_id"]
    elif rv.status_code == 409:
        # User already exists from prior runs; find it
        rv2 = client.get("/users")
        assert rv2.status_code == 200
        users = rv2.get_json().get("users", [])
        found = next((u for u in users if u.get("roll_no") == "TST_CANCEL_001"), None)
        assert found is not None
        mentee_id = found["user_id"]
    else:
        pytest.fail(f"Unexpected status {rv.status_code}")

    # Pick the first available mentor
    rv = client.get("/mentors")
    assert rv.status_code == 200
    j = rv.get_json()
    mentors = j.get("mentors") or []
    assert len(mentors) > 0
    mentor_id = mentors[0]["user_id"]

    # Obtain a JWT token for the mentee we just created
    rv = client.post(
        "/token",
        json={"roll_no": "TST_CANCEL_001", "password": "Test123!"},
    )
    assert rv.status_code == 200
    j = rv.get_json()
    token = j.get("token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}

    # Create a session
    rv = client.post(
        "/sessions",
        json={
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "date": "2026-04-07",
            "time": "09:00",
        },
        headers=headers,
    )
    assert rv.status_code == 201
    j = rv.get_json()
    assert j and j.get("ok") is True
    session_id = j["session"]["session_id"]

    # Cancel the session
    rv = client.post(f"/sessions/{session_id}/cancel", headers=headers)
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get("ok") is True
    assert j["session"]["status"] == "cancelled"

    # Verify via GET
    rv = client.get(f"/sessions/{session_id}")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j and j.get("ok") is True
    assert j["session"]["status"] == "cancelled"
