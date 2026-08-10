from dataclasses import dataclass
from src.telemetry_validator import ValidationResult


@dataclass
class FallbackResult:
    selected_source: str
    reasons: list[str]


def choose_source(
    primary_result: ValidationResult,
    backup_result: ValidationResult,
) -> FallbackResult:
    reasons = []

    if primary_result.valid:
        reasons.append("Primary telemetry is valid")

        return FallbackResult(
            selected_source="PRIMARY",
            reasons=reasons,
        )

    if backup_result.valid:
        reasons.append("Primary telemetry is invalid")
        reasons.extend(primary_result.reasons)
        reasons.append("Backup telemetry is valid")

        return FallbackResult(
            selected_source="BACKUP",
            reasons=reasons,
        )

    reasons.append("Primary telemetry is invalid")
    reasons.extend(primary_result.reasons)

    reasons.append("Backup telemetry is invalid")
    reasons.extend(backup_result.reasons)

    return FallbackResult(
        selected_source="BLOCKED",
        reasons=reasons,
    )