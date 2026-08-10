from typing import Any

from src.datahub_client import get_downstream_entities, make_urn
from src.incident_reporter import report_incident
from src.mcp_datahub_client import get_downstream_entities_sync


def get_entity_name(entity_urn: str) -> str:
    """Извлекает короткое имя сущности из DataHub URN."""
    try:
        return entity_urn.rsplit(",", 2)[1]
    except IndexError as error:
        raise ValueError(f"Invalid DataHub URN: {entity_urn}") from error


def _resolve_downstream_urns(source_urn: str) -> tuple[list[str], str]:
    """Resolves downstream lineage via the DataHub MCP agent.

    Falls back to the direct GraphQL client if the MCP Server is
    unreachable (e.g. not deployed in this environment), so impact
    analysis keeps working without it.
    """
    try:
        return get_downstream_entities_sync(source_urn), "datahub-mcp-server"
    except Exception as exc:
        print(f"DataHub MCP agent unavailable, falling back to direct GraphQL: {exc}")
        return get_downstream_entities(source_urn), "graphql"


def analyze_impact(
    source_entity: str,
    problem_title: str,
    problem_description: str,
) -> dict[str, Any]:
    """Находит затронутые компоненты через DataHub MCP-агент и регистрирует инцидент."""

    source_urn = make_urn(source_entity)
    downstream_urns, impact_source = _resolve_downstream_urns(source_urn)

    affected_entities = [
        get_entity_name(entity_urn)
        for entity_urn in downstream_urns
    ]

    affected_text = (
        ", ".join(affected_entities)
        if affected_entities
        else "No downstream components found"
    )

    incident = {
        "resource_urn": source_urn,
        "title": problem_title,
        "description": (
            f"{problem_description}\n\n"
            f"Affected downstream components: {affected_text}"
        ),
        "custom_type": "RaceGuard impact analysis",
    }

    report_incident(incident)

    return {
        "source_entity": source_entity,
        "source_urn": source_urn,
        "affected_entities": affected_entities,
        "affected_urns": downstream_urns,
        "affected_count": len(affected_entities),
        "impact_source": impact_source,
    }


if __name__ == "__main__":
    result = analyze_impact(
        source_entity="backup_tyre_sensor",
        problem_title="Backup tyre sensor impact analysis",
        problem_description=(
            "Integration test for automatic downstream impact detection. "
            "No sensor measurements or fabricated metrics were added."
        ),
    )

    print("\nImpact analysis completed.")
    print(f"Source entity: {result['source_entity']}")
    print(f"Affected count: {result['affected_count']}")

    for entity_name in result["affected_entities"]:
        print(f"- {entity_name}")