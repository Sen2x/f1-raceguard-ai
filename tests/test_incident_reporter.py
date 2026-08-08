from unittest.mock import Mock, patch

import pytest

from src.incident_reporter import report_incident


def make_incident() -> dict[str, str]:
    return {
        "resource_urn": (
            "urn:li:dataset:"
            "(urn:li:dataPlatform:raceguard,"
            "primary_tyre_sensor,PROD)"
        ),
        "title": "Primary tyre sensor unavailable",
        "description": "Automated unit test.",
        "custom_type": "Sensor availability",
    }


@patch("src.incident_reporter.requests.post")
def test_report_incident_success(mock_post: Mock) -> None:
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": {
            "raiseIncident": "urn:li:incident:test-incident-id",
        }
    }
    mock_post.return_value = mock_response

    report_incident(make_incident())

    mock_post.assert_called_once()
    mock_response.raise_for_status.assert_called_once()

    request_data = mock_post.call_args.kwargs["json"]
    incident_input = request_data["variables"]["input"]

    assert incident_input["type"] == "CUSTOM"
    assert incident_input["title"] == "Primary tyre sensor unavailable"
    assert incident_input["customType"] == "Sensor availability"
    assert incident_input["resourceUrn"].endswith(
        "primary_tyre_sensor,PROD)"
    )


@patch("src.incident_reporter.requests.post")
def test_report_incident_missing_required_field(
    mock_post: Mock,
) -> None:
    incident = make_incident()
    del incident["title"]

    with pytest.raises(
        ValueError,
        match="Missing required incident fields: title",
    ):
        report_incident(incident)

    mock_post.assert_not_called()


@patch("src.incident_reporter.requests.post")
def test_report_incident_graphql_error(mock_post: Mock) -> None:
    mock_response = Mock()
    mock_response.json.return_value = {
        "errors": [
            {
                "message": "DataHub rejected the incident",
            }
        ]
    }
    mock_post.return_value = mock_response

    with pytest.raises(RuntimeError, match="DataHub GraphQL error"):
        report_incident(make_incident())

    mock_response.raise_for_status.assert_called_once()