from fastapi import FastAPI

from app.schemas import TelemetryRequest, TelemetryResponse
from src.telemetry_validator import validate_telemetry
from src.fallback_manager import choose_source
from src.incident_reporter import report_incident


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telemetry/evaluate", response_model=TelemetryResponse)
def evaluate_telemetry(data: TelemetryRequest):
    primary = data.primary
    backup = data.backup

    primary_result = validate_telemetry(
        telemetry=primary,
        required_fields=REQUIRED_FIELDS,
        field_types=FIELD_TYPES,
    )

    backup_result = validate_telemetry(
        telemetry=backup,
        required_fields=REQUIRED_FIELDS,
        field_types=FIELD_TYPES,
    )

    fallback_result = choose_source(
        primary_result=primary_result,
        backup_result=backup_result,
    )

    selected_source = fallback_result.selected_source

    if selected_source == "PRIMARY":
        status = "OK"

    elif selected_source == "BACKUP":
        status = "DEGRADED"

        try:
            report_incident(
                {
                    "resource_urn": (
                        "urn:li:dataset:"
                        "(urn:li:dataPlatform:raceguard,"
                        "primary_tyre_sensor,PROD)"
                    ),
                    "title": "Primary tyre sensor telemetry failure",
                    "description": (
                        "Primary telemetry failed validation. "
                        "RaceGuard switched to backup telemetry."
                    ),
                    "custom_type": "RaceGuard telemetry fallback",
                }
            )
        except Exception as exc:
            print(f"DataHub incident reporting failed: {exc}")

    else:
        status = "BLOCKED"

        try:
            report_incident(
                {
                    "resource_urn": (
                        "urn:li:dataset:"
                        "(urn:li:dataPlatform:raceguard,"
                        "primary_tyre_sensor,PROD)"
                    ),
                    "title": "Telemetry unavailable",
                    "description": (
                        "Primary and backup telemetry failed validation. "
                        "Race strategy output was blocked."
                    ),
                    "custom_type": "RaceGuard telemetry blocked",
                }
            )
        except Exception as exc:
            print(f"DataHub incident reporting failed: {exc}")

    return TelemetryResponse(
        selected_source=selected_source,
        status=status,
        reasons=fallback_result.reasons,
    )