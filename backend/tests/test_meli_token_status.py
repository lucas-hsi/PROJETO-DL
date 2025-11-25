from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_token_status_endpoint_returns_structure():
    resp = client.get("/api/meli/token/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token_valid" in data
    assert "refresh_token_exists" in data
    assert "monitor_running" in data
    assert isinstance(data["access_token_valid"], bool)
    assert isinstance(data["refresh_token_exists"], bool)
    assert isinstance(data["monitor_running"], bool)


def test_start_stop_token_monitor_endpoints():
    r1 = client.post("/api/meli/token/monitor/start")
    assert r1.status_code == 200
    r2 = client.post("/api/meli/token/monitor/stop")
    assert r2.status_code == 200