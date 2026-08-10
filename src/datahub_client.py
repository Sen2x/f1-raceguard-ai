from typing import Any

import requests
from datahub.emitter import mce_builder as builder


DATAHUB_GRAPHQL_URL = "http://localhost:8080/api/graphql"
PLATFORM = "raceguard"
ENVIRONMENT = "PROD"


def make_urn(entity_name: str) -> str:
    """Создаёт полный DataHub URN по короткому имени сущности."""
    return builder.make_dataset_urn(
        platform=PLATFORM,
        name=entity_name,
        env=ENVIRONMENT,
    )


def get_downstream_entities(source_urn: str) -> list[str]:
    """Возвращает URN всех сущностей, зависящих от source_urn."""
    query = """
    query SearchDownstreamLineage($input: SearchAcrossLineageInput!) {
      searchAcrossLineage(input: $input) {
        searchResults {
          entity {
            urn
          }
          degree
        }
      }
    }
    """

    variables: dict[str, Any] = {
        "input": {
            "urn": source_urn,
            "direction": "DOWNSTREAM",
            "query": "*",
            "start": 0,
            "count": 100,
        }
    }

    response = requests.post(
        DATAHUB_GRAPHQL_URL,
        json={
            "query": query,
            "variables": variables,
        },
        timeout=15,
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("errors"):
        raise RuntimeError(f"DataHub GraphQL error: {payload['errors']}")

    results = payload["data"]["searchAcrossLineage"]["searchResults"]

    ordered_results = sorted(
        results,
        key=lambda item: item.get("degree", 0),
    )

    return [item["entity"]["urn"] for item in ordered_results]


if __name__ == "__main__":
    sensor_urn = make_urn("primary_tyre_sensor")

    print(f"Source: {sensor_urn}")
    print("Downstream entities:")

    for entity_urn in get_downstream_entities(sensor_urn):
        print(f"- {entity_urn}")