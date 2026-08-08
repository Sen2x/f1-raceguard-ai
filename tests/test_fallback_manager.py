from src.fallback_manager import choose_source
from src.telemetry_validator import ValidationResult


def test_primary_is_selected_when_valid():
    primary_result = ValidationResult(
        valid=True,
        reasons=[],
    )

    backup_result = ValidationResult(
        valid=True,
        reasons=[],
    )

    result = choose_source(
        primary_result=primary_result,
        backup_result=backup_result,
    )

    assert result.selected_source == "PRIMARY"
    assert result.reasons == ["Primary telemetry is valid"]


def test_backup_is_selected_when_primary_is_invalid():
    primary_result = ValidationResult(
        valid=False,
        reasons=["Primary sensor value is invalid"],
    )

    backup_result = ValidationResult(
        valid=True,
        reasons=[],
    )

    result = choose_source(
        primary_result=primary_result,
        backup_result=backup_result,
    )

    assert result.selected_source == "BACKUP"
    assert result.reasons == [
        "Primary telemetry is invalid",
        "Primary sensor value is invalid",
        "Backup telemetry is valid",
    ]

def test_blocked_when_both_sources_are_invalid():
    primary_result = ValidationResult(
        valid=False,
        reasons=["Primary sensor value is invalid"],
    )

    backup_result = ValidationResult(
        valid=False,
        reasons=["Backup sensor value is invalid"],
    )

    result = choose_source(
        primary_result=primary_result,
        backup_result=backup_result,
    )

    assert result.selected_source == "BLOCKED"
    assert result.reasons == [
        "Primary telemetry is invalid",
        "Primary sensor value is invalid",
        "Backup telemetry is invalid",
        "Backup sensor value is invalid",
    ]

