from typing import Any

from pydantic import BaseModel


class TelemetryRequest(BaseModel):
    primary: dict[str, Any]
    backup: dict[str, Any]


class TelemetryResponse(BaseModel):
    selected_source: str
    status: str
    reasons: list[str]