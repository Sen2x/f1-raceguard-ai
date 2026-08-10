import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ValidationResult:
    valid: bool
    reasons: list[str]

def validate_telemetry(
        telemetry: dict,
        required_fields: list[str],
        field_types: dict[str, type],
        limits: dict[str, dict[str, float]] | None = None,
        max_age_seconds: float | None = None,
        now: datetime | None = None,
) -> ValidationResult:
        reasons = []

        for field in required_fields:
            if field not in telemetry:
                reasons.append(f"Missing required field: {field}")

        for field, value in telemetry.items():
            if value is None:
                reasons.append(f"Field '{field}' cannot be None")

        for field, expected_type in field_types.items():
            if field in telemetry and telemetry[field] is not None:
                if not isinstance(telemetry[field], expected_type):
                    reasons.append(
                        f"Field '{field}' must be of type {expected_type.__name__}"
                    )

        for field, value in telemetry.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if not math.isfinite(value):
                    reasons.append(
                        f"Field '{field}' must be a finite number"
                    )

        if limits is not None:
            for field, bounds in limits.items():
                if field in telemetry:
                    value = telemetry[field]

                    if isinstance(value, (int, float)) and math.isfinite(value):
                        if "min" in bounds and value < bounds["min"]:
                            reasons.append(
                                f"Field '{field}' is below minimum"
                            )

                        if "max" in bounds and value > bounds["max"]:
                            reasons.append(
                                f"Field '{field}' is above maximum"
                            )


        if "timestamp" in telemetry and max_age_seconds is not None:
            timestamp_value = telemetry["timestamp"]

            if isinstance(timestamp_value, str):
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_value.replace("Z", "+00:00")
                    )

                    current_time = now or datetime.now(timezone.utc)
                    age_seconds = (current_time - timestamp).total_seconds()

                    if age_seconds > max_age_seconds:
                        reasons.append("Telemetry timestamp is stale")

                except ValueError:
                    reasons.append("Timestamp has invalid format")


        return ValidationResult(
        valid=len(reasons) == 0,
        reasons=reasons,
    )

        

        