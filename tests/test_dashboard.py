# PROMPT: Add tests for the live dashboard surface so the bonus real-time UI stays reachable from docker compose.
# CHANGES MADE: I kept the test at the HTTP boundary and asserted stable UI/API shape rather than brittle HTML styling.

from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_page_is_served():
    client = TestClient(app)
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Store Intelligence Live Dashboard" in response.text
    assert "/stores/${storeId}/live" in response.text
