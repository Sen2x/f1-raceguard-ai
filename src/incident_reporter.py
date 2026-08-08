from typing import Any

import requests


DATAHUB_GRAPHQL_URL = "http://localhost:8080/api/graphql"


def report_incident(incident: dict[str, Any]) -> None:
    """Регистрирует реальный инцидент компонента в DataHub."""

    required_fields = {
        "resource_urn",
        "title",
        "description",
    }

    missing_fields = required_fields - incident.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Missing required incident fields: {missing}")

    mutation = """
    mutation RaiseIncident($input: RaiseIncidentInput!) {
      raiseIncident(input: $input)
    }
    """

    variables = {
        "input": {
            "type": "CUSTOM",
            "customType": incident.get(
                "custom_type",
                "RaceGuard sensor incident",
            ),
            "title": incident["title"],
            "description": incident["description"],
            "resourceUrn": incident["resource_urn"],
        }
    }

    response = requests.post(
        DATAHUB_GRAPHQL_URL,
        json={
            "query": mutation,
            "variables": variables,
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("errors"):
        raise RuntimeError(
            f"DataHub GraphQL error: {payload['errors']}"
        )

    incident_urn = payload["data"]["raiseIncident"]

    print("Incident registered successfully.")
    print(f"Incident URN: {incident_urn}")


if __name__ == "__main__":
    test_incident = {
        "resource_urn": (
            "urn:li:dataset:"
            "(urn:li:dataPlatform:raceguard,"
            "primary_tyre_sensor,PROD)"
        ),
        "title": "Primary tyre sensor unavailable",
        "description": (
            "Test incident created during RaceGuard integration. "
            "No real sensor measurements were added."
        ),
        "custom_type": "Sensor availability",
    }

    report_incident(test_incident)