from unittest.mock import patch

from src.impact_analyzer import analyze_impact, get_entity_name


def test_get_entity_name() -> None:
    entity_urn = (
        "urn:li:dataset:"
        "(urn:li:dataPlatform:raceguard,raw_telemetry,PROD)"
    )

    assert get_entity_name(entity_urn) == "raw_telemetry"


@patch("src.impact_analyzer.report_incident")
@patch("src.impact_analyzer.get_downstream_entities")
def test_analyze_impact(
    mock_get_downstream_entities,
    mock_report_incident,
) -> None:
    mock_get_downstream_entities.return_value = [
        (
            "urn:li:dataset:"
            "(urn:li:dataPlatform:raceguard,raw_telemetry,PROD)"
        ),
        (
            "urn:li:dataset:"
            "(urn:li:dataPlatform:raceguard,validated_telemetry,PROD)"
        ),
    ]

    result = analyze_impact(
        source_entity="primary_tyre_sensor",
        problem_title="Test sensor incident",
        problem_description="Automated unit test.",
    )

    assert result["source_entity"] == "primary_tyre_sensor"
    assert result["affected_entities"] == [
        "raw_telemetry",
        "validated_telemetry",
    ]
    assert result["affected_count"] == 2

    mock_get_downstream_entities.assert_called_once_with(
        result["source_urn"]
    )
    mock_report_incident.assert_called_once()

    incident = mock_report_incident.call_args.args[0]

    assert incident["title"] == "Test sensor incident"
    assert "raw_telemetry" in incident["description"]
    assert "validated_telemetry" in incident["description"]