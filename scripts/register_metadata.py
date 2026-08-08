from collections import defaultdict

from datahub.emitter import mce_builder as builder
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    DatasetLineageTypeClass,
    DatasetPropertiesClass,
    UpstreamClass,
    UpstreamLineageClass,
)


DATAHUB_SERVER = "http://localhost:8080"
PLATFORM = "raceguard"
ENVIRONMENT = "PROD"

ENTITIES = {
    "primary_tyre_sensor": "Primary tyre temperature sensor",
    "backup_tyre_sensor": "Backup tyre temperature sensor",
    "raw_telemetry": "Raw telemetry received from race car sensors",
    "validated_telemetry": "Telemetry validated before strategy calculation",
    "strategy_features": "Features prepared for the race strategy model",
    "pit_stop_model": "Model that calculates pit-stop strategy",
    "race_strategy_output": "Final race strategy decision",
}

LINEAGE = [
    ("primary_tyre_sensor", "raw_telemetry"),
    ("backup_tyre_sensor", "raw_telemetry"),
    ("raw_telemetry", "validated_telemetry"),
    ("validated_telemetry", "strategy_features"),
    ("strategy_features", "pit_stop_model"),
    ("pit_stop_model", "race_strategy_output"),
]


def make_urn(entity_name: str) -> str:
    return builder.make_dataset_urn(
        platform=PLATFORM,
        name=entity_name,
        env=ENVIRONMENT,
    )


def register_entities(emitter: DatahubRestEmitter) -> None:
    for entity_name, description in ENTITIES.items():
        event = MetadataChangeProposalWrapper(
            entityUrn=make_urn(entity_name),
            aspect=DatasetPropertiesClass(
                name=entity_name,
                description=description,
                customProperties={
                    "project": "F1 RaceGuard AI",
                    "environment": ENVIRONMENT,
                },
            ),
        )

        emitter.emit(event)
        print(f"Created entity: {entity_name}")


def register_lineage(emitter: DatahubRestEmitter) -> None:
    upstreams_by_downstream = defaultdict(list)

    for upstream_name, downstream_name in LINEAGE:
        upstreams_by_downstream[downstream_name].append(
            UpstreamClass(
                dataset=make_urn(upstream_name),
                type=DatasetLineageTypeClass.TRANSFORMED,
            )
        )

    for downstream_name, upstreams in upstreams_by_downstream.items():
        event = MetadataChangeProposalWrapper(
            entityUrn=make_urn(downstream_name),
            aspect=UpstreamLineageClass(upstreams=upstreams),
        )

        emitter.emit(event)

        for upstream in upstreams:
            print(f"Created lineage: {upstream.dataset} -> {downstream_name}")


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=DATAHUB_SERVER)

    print("Checking connection to DataHub...")
    emitter.test_connection()

    register_entities(emitter)
    register_lineage(emitter)

    print("RaceGuard metadata registration completed successfully.")


if __name__ == "__main__":
    main()