import pytest
from src.telemetry_validator import validate_telemetry
from datetime import datetime, timezone


def test_valid_telemetry():
    telemetry = {
        "tyre_temperature": 96.5,
        "tyre_pressure": 22.1,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is True
    assert result.reasons == []





def test_missing_required_field():
    telemetry = {
        "tyre_temperature": 96.5,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is False
    assert "Missing required field: tyre_pressure" in result.reasons




def test_none_value_is_invalid():
    telemetry = {
        "tyre_temperature": None,
        "tyre_pressure": 22.1,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' cannot be None" in result.reasons



def test_invalid_type():
    telemetry = {
        "tyre_temperature": "error",
        "tyre_pressure": 22.1,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' must be of type float" in result.reasons



def test_nan_value_is_invalid():
    telemetry = {
        "tyre_temperature": float("nan"),
        "tyre_pressure": 22.1,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' must be a finite number" in result.reasons



@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_infinite_value_is_invalid(value):
    telemetry = {
        "tyre_temperature": value,
        "tyre_pressure": 22.1,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature", "tyre_pressure"],
        field_types={
            "tyre_temperature": float,
            "tyre_pressure": float,
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' must be a finite number" in result.reasons

def test_value_below_configured_minimum_is_invalid():
    telemetry = {
        "tyre_temperature": 60.0,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature"],
        field_types={
            "tyre_temperature": float,
        },
        limits={
            "tyre_temperature": {
                "min": 70.0,
                "max": 120.0,
            }
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' is below minimum" in result.reasons


def test_value_above_configured_maximum_is_invalid():
    telemetry = {
        "tyre_temperature": 130.0,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature"],
        field_types={
            "tyre_temperature": float,
        },
        limits={
            "tyre_temperature": {
                "min": 70.0,
                "max": 120.0,
            }
        },
    )

    assert result.valid is False
    assert "Field 'tyre_temperature' is above maximum" in result.reasons


def test_fresh_timestamp_is_valid():
    telemetry = {
        "timestamp": "2026-08-08T14:32:10Z",
        "tyre_temperature": 96.5,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature"],
        field_types={
            "timestamp": str,
            "tyre_temperature": float,
        },
        max_age_seconds=10,
        now=datetime(2026, 8, 8, 14, 32, 15, tzinfo=timezone.utc),
    )

    assert result.valid is True


def test_stale_timestamp_is_invalid():
    telemetry = {
        "timestamp": "2026-08-08T14:32:00Z",
        "tyre_temperature": 96.5,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature"],
        field_types={
            "timestamp": str,
            "tyre_temperature": float,
        },
        max_age_seconds=10,
        now=datetime(2026, 8, 8, 14, 32, 20, tzinfo=timezone.utc),
    )

    assert result.valid is False
    assert "Telemetry timestamp is stale" in result.reasons



def test_missing_timestamp_is_allowed_when_not_required():
    telemetry = {
        "tyre_temperature": 96.5,
    }

    result = validate_telemetry(
        telemetry=telemetry,
        required_fields=["tyre_temperature"],
        field_types={
            "tyre_temperature": float,
        },
        max_age_seconds=10,
    )

    assert result.valid is True
    assert result.reasons == []