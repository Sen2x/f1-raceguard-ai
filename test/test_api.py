from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_primary_selected():
    response = client.post(
        "/telemetry/evaluate",
        json={
            "primary": {
                "tyre_temperature": 97.2,
                "tyre_pressure": 22.4,
            },
            "backup": {
                "tyre_temperature": 96.5,
                "tyre_pressure": 22.1,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["selected_source"] == "PRIMARY"


def test_backup_selected():
    response = client.post(
        "/telemetry/evaluate",
        json={
            "primary": {
                "tyre_temperature": None,
                "tyre_pressure": "error",
            },
            "backup": {
                "tyre_temperature": 96.5,
                "tyre_pressure": 22.1,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["selected_source"] == "BACKUP"


def test_blocked():
    response = client.post(
        "/telemetry/evaluate",
        json={
            "primary": {
                "tyre_temperature": None,
                "tyre_pressure": "error",
            },
            "backup": {
                "tyre_temperature": None,
                "tyre_pressure": "error",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["selected_source"] == "BLOCKED"