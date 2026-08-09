from fastapi import FastAPI

from app.schemas import TelemetryRequest, TelemetryResponse

app = FastAPI(
    title="F1 RaceGuard AI",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telemetry/evaluate", response_model=TelemetryResponse)
def evaluate_telemetry(data: TelemetryRequest):
    """
    Temporary API integration layer.

    Luka's fallback_manager will replace this temporary
    validation logic when his module is merged.
    """

    primary = data.primary
    backup = data.backup

    reasons = []

    primary_valid = (
        primary.get("tyre_temperature") is not None
        and isinstance(primary.get("tyre_temperature"), (int, float))
        and primary.get("tyre_pressure") is not None
        and isinstance(primary.get("tyre_pressure"), (int, float))
    )

    if primary_valid:
        return TelemetryResponse(
            selected_source="PRIMARY",
            status="OK",
            reasons=[],
        )

    reasons.append("Primary telemetry is invalid")

    backup_valid = (
        backup.get("tyre_temperature") is not None
        and isinstance(backup.get("tyre_temperature"), (int, float))
        and backup.get("tyre_pressure") is not None
        and isinstance(backup.get("tyre_pressure"), (int, float))
    )

    if backup_valid:
        return TelemetryResponse(
            selected_source="BACKUP",
            status="DEGRADED",
            reasons=reasons,
        )

    reasons.append("Backup telemetry is invalid")

    return TelemetryResponse(
        selected_source="BLOCKED",
        status="BLOCKED",
        reasons=reasons,
    )