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
    assert rv.status_code == 201
    j = rv.get_json()
    assert j and j.get("ok") is True
    mentee_id = j["user"]["user_id"]

    # Pick the first available mentor
    rv = client.get("/mentors")
    assert rv.status_code == 200
    j = rv.get_json()
    mentors = j.get("mentors") or []
    assert len(mentors) > 0
    mentor_id = mentors[0]["user_id"]

    # Create a session
    rv = client.post(
        "/sessions",
        json={
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "date": "2026-04-07",
            "time": "09:00",
        },
    )
    assert rv.status_code == 201
    j = rv.get_json()
    assert j and j.get("ok") is True
    session_id = j["session"]["session_id"]

    # Cancel the session
    rv = client.post(f"/sessions/{session_id}/cancel")
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
