from typing import Any

from src.datahub_client import get_downstream_entities, make_urn
from src.incident_reporter import report_incident

def get_entity_name(entity_urn: str) -> str:
    """Извлекает короткое имя сущности из DataHub URN."""
    try:
        return entity_urn.rsplit(",", 2)[1]
    except IndexError as error:
        raise ValueError(f"Invalid DataHub URN: {entity_urn}") from error


def analyze_impact(
    source_entity: str,
    problem_title: str,
    problem_description: str,
) -> dict[str, Any]:
    """Находит затронутые компоненты и регистрирует инцидент."""

    source_urn = make_urn(source_entity)
    downstream_urns = get_downstream_entities(source_urn)

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