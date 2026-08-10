from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.main.analyze_impact")
def test_primary_selected(mock_analyze_impact):
    """PRIMARY scenario: the primary sensor is healthy and is used directly."""
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
    body = response.json()
    assert body["selected_source"] == "PRIMARY"
    assert body["status"] == "OK"

    mock_analyze_impact.assert_not_called()


@patch("app.main.analyze_impact")
def test_backup_selected(mock_analyze_impact):
    """BACKUP scenario: the primary sensor is faulty, the backup sensor is used."""
    mock_analyze_impact.return_value = {
        "source_entity": "primary_tyre_sensor",
        "affected_entities": ["raw_telemetry"],
        "affected_count": 1,
        "impact_source": "datahub-mcp-server",
    }

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
    body = response.json()
    assert body["selected_source"] == "BACKUP"
    assert body["status"] == "DEGRADED"

    mock_analyze_impact.assert_called_once()
    call_kwargs = mock_analyze_impact.call_args.kwargs
    assert call_kwargs["source_entity"] == "primary_tyre_sensor"
    assert "backup" in call_kwargs["problem_description"].lower()


@patch("app.main.analyze_impact")
def test_blocked(mock_analyze_impact):
    """BLOCKED scenario: both sensors are faulty, telemetry is blocked."""
    mock_analyze_impact.return_value = {
        "source_entity": "primary_tyre_sensor",
        "affected_entities": [],
        "affected_count": 0,
        "impact_source": "graphql",
    }

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
    body = response.json()
    assert body["selected_source"] == "BLOCKED"
    assert body["status"] == "BLOCKED"

    mock_analyze_impact.assert_called_once()
    call_kwargs = mock_analyze_impact.call_args.kwargs
    assert call_kwargs["source_entity"] == "primary_tyre_sensor"
    assert "blocked" in call_kwargs["problem_description"].lower()


@patch("app.main.analyze_impact")
def test_backup_scenario_survives_datahub_failure(mock_analyze_impact):
    """DataHub being unreachable must not break the API response."""
    mock_analyze_impact.side_effect = RuntimeError("DataHub unreachable")

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
