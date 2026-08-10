from fastapi import FastAPI

from app.schemas import TelemetryRequest, TelemetryResponse
from src.telemetry_validator import validate_telemetry
from src.fallback_manager import choose_source
from src.impact_analyzer import analyze_impact


app = FastAPI(
    title="F1 RaceGuard AI",
    version="1.0.0",
)


REQUIRED_FIELDS = [
    "tyre_temperature",
    "tyre_pressure",
]

FIELD_TYPES = {
    "tyre_temperature": float,
    "tyre_pressure": float,
}

PRIMARY_SENSOR_ENTITY = "primary_tyre_sensor"

STATUS_BY_SOURCE = {
    "PRIMARY": "OK",
    "BACKUP": "DEGRADED",
    "BLOCKED": "BLOCKED",
}

INCIDENT_TITLES = {
    "BACKUP": "Primary tyre sensor telemetry failure",
    "BLOCKED": "Telemetry unavailable",
}

INCIDENT_DESCRIPTIONS = {
    "BACKUP": (
        "Primary telemetry failed validation. "
        "RaceGuard switched to backup telemetry."
    ),
    "BLOCKED": (
        "Primary and backup telemetry failed validation. "
        "Race strategy output was blocked."
    ),
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telemetry/evaluate", response_model=TelemetryResponse)
def evaluate_telemetry(data: TelemetryRequest):
    primary_result = validate_telemetry(
        telemetry=data.primary,
        required_fields=REQUIRED_FIELDS,
        field_types=FIELD_TYPES,
    )

    backup_result = validate_telemetry(
        telemetry=data.backup,
        required_fields=REQUIRED_FIELDS,
        field_types=FIELD_TYPES,
    )

    fallback_result = choose_source(
        primary_result=primary_result,
        backup_result=backup_result,
    )

    selected_source = fallback_result.selected_source
    status = STATUS_BY_SOURCE[selected_source]

    if selected_source != "PRIMARY":
        try:
            analyze_impact(
                source_entity=PRIMARY_SENSOR_ENTITY,
                problem_title=INCIDENT_TITLES[selected_source],
                problem_description=INCIDENT_DESCRIPTIONS[selected_source],
            )
        except Exception as exc:
            print(f"DataHub impact analysis failed: {exc}")

    return TelemetryResponse(
        selected_source=selected_source,
        status=status,
        reasons=fallback_result.reasons,
    )
