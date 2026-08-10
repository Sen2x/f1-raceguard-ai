# F1 RaceGuard AI

F1 RaceGuard AI is a safety layer designed to protect a race strategy system from invalid, missing, corrupted, or stale telemetry data.

The system validates incoming telemetry before it reaches downstream strategy components. If the primary telemetry source is unreliable, the system can safely switch to a backup source. If neither source is reliable, the telemetry is blocked.

DataHub is used to represent data lineage, analyze downstream impact, and support incident reporting. Impact analysis is performed through the official **DataHub MCP Server**, so the impact check is a real agentic tool call rather than a hardcoded GraphQL query (see [DataHub Integration](#3-datahub-integration) below).

The high-level flow is:

```text
Primary Telemetry ──┐
                    ├──> Telemetry Validation
Backup Telemetry ───┘
                         │
                         ▼
                  Fallback Manager
                         │
                         ▼
              PRIMARY / BACKUP / BLOCKED
                         │
                         ▼
                 RaceGuard Service
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        PRIMARY decision       BACKUP / BLOCKED
              │                     │
              │                     ▼
              │         DataHub Impact Analysis
              │         (DataHub MCP Server agent,
              │          GraphQL fallback)
              │                     │
              │                     ▼
              │              Incident Handling
              │
              ▼
        Continue normally
```

---
## Demo

F1 RaceGuard AI demonstrates three safety decisions:

1. `PRIMARY` — healthy primary telemetry is accepted.
2. `BACKUP` — invalid primary telemetry triggers automatic fallback.
3. `BLOCKED` — the strategy input is blocked when both sources are invalid.

For `BACKUP` and `BLOCKED`, RaceGuard automatically:

- queries downstream lineage through the DataHub MCP Server;
- identifies affected data components;
- creates an active Incident in DataHub;
- preserves the telemetry decision even if DataHub is unavailable.

### Demonstrated failure flow

```text
Invalid primary telemetry
        ↓
BACKUP selected
        ↓
DataHub MCP lineage analysis
        ↓
Affected component: raw_telemetry
        ↓
DataHub Incident created automatically
```

### Video

Demo video: **[add video link here]**

### Evidence

- FastAPI response with `BACKUP / DEGRADED`;
- automatic DataHub Incident creation;
- Incident linked to `primary_tyre_sensor`;
- affected downstream component `raw_telemetry`.

---

## Team

F1 RaceGuard AI was developed collaboratively for the hackathon.

### Sen2x

GitHub:

```text
https://github.com/Sen2x
```

### DaniilsLukaMiskins

GitHub:

```text
https://github.com/DaniilsLukaMiskins
```

### RizskajaVecna

GitHub:

```text
https://github.com/RizskajaVecna
```

---

## Main Components

### 1. Telemetry Validation

File:

```text
src/telemetry_validator.py
```

The telemetry validator checks a single telemetry package and returns a structured validation result.

It supports:

- required field validation;
- value type validation;
- rejection of `None`;
- rejection of `NaN`;
- rejection of positive and negative infinity;
- timestamp freshness validation;
- configurable numeric limits.

Physical Formula 1 limits are not hardcoded into the validator.

Any minimum or maximum values must be supplied through configuration.

Example result:

```python
ValidationResult(
    valid=False,
    reasons=[
        "Field 'tyre_temperature' cannot be None"
    ],
)
```

### 2. Safe Fallback Selection

File:

```text
src/fallback_manager.py
```

The fallback manager receives validation results for the primary and backup telemetry sources.

It returns one of three decisions:

| Decision | Meaning |
| --- | --- |
| `PRIMARY` | Primary telemetry is valid and can be used |
| `BACKUP` | Primary telemetry is invalid, but backup telemetry is valid |
| `BLOCKED` | Both telemetry sources are invalid |

Example:

```text
Primary telemetry: invalid
Backup telemetry: valid

Decision: BACKUP
```

The result also contains structured reasons explaining the decision.

Example:

```python
FallbackResult(
    selected_source="BACKUP",
    reasons=[
        "Primary telemetry is invalid",
        "Field 'tyre_temperature' cannot be None",
        "Backup telemetry is valid",
    ],
)
```

### 3. DataHub Integration

Files:

```text
scripts/register_metadata.py
src/datahub_client.py
src/mcp_datahub_client.py
src/impact_analyzer.py
src/incident_reporter.py
```

DataHub is used for metadata and lineage management. The project models the flow of telemetry through downstream components so that a failure in an upstream source can be analyzed and reported as an incident.

Conceptually, the lineage is:

```text
Primary Telemetry Source ─┐
                          ├──> Raw Telemetry
Backup Telemetry Source ──┘
                                │
                                ▼
                       Validated Telemetry
                                │
                                ▼
                       Strategy Features
                                │
                                ▼
                       Strategy Components
                                │
                                ▼
                       Strategy Output
```

#### DataHub MCP Server (agentic component)

`src/mcp_datahub_client.py` drives the official [DataHub MCP Server](https://github.com/acryldata/mcp-server-datahub) (`mcp-server-datahub`) as a Model Context Protocol tool server: it spawns the server as a subprocess over stdio, lists its published tools, and calls the `search` and `get_lineage` tools — the same interface an AI agent client (e.g. Claude Desktop) uses to explore DataHub.

`analyze_impact()` in `src/impact_analyzer.py` uses this agent to resolve downstream impact:

```text
BACKUP / BLOCKED decision
        │
        ▼
analyze_impact(source_entity, ...)
        │
        ▼
DataHub MCP Server: get_lineage(urn, upstream=False)
        │
        ├── succeeds ──> downstream entities resolved via the MCP agent
        │
        └── unreachable ──> falls back to src/datahub_client.py
                             (direct GraphQL query)
        │
        ▼
report_incident() raises the incident in DataHub,
including the affected downstream components
```

The result of `analyze_impact()` includes an `impact_source` field (`"datahub-mcp-server"` or `"graphql"`) so it's always visible which path produced the impact analysis.

Configuration (same environment variables the DataHub CLI and other DataHub tooling use):

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATAHUB_GMS_URL` | DataHub GMS endpoint the MCP Server connects to | `http://localhost:8080` |
| `DATAHUB_GMS_TOKEN` | Personal access token (if your DataHub instance requires auth) | not set |
| `DATAHUB_MCP_COMMAND` / `DATAHUB_MCP_ARGS` | Override how the MCP Server process is launched | `python -m mcp_server_datahub` |
| `DATAHUB_MCP_TIMEOUT_SECONDS` | Max time to wait for the MCP Server before falling back to GraphQL | `8` |

You can exercise the agent directly:

```bash
python -m src.mcp_datahub_client
```

This lists the tools published by the DataHub MCP Server, resolves `primary_tyre_sensor` through the `search` tool, and prints its downstream lineage via `get_lineage`.

#### Metadata, lineage and incidents

- `scripts/register_metadata.py` registers the RaceGuard entities and lineage edges in DataHub (run once against a DataHub instance to seed it).
- `src/datahub_client.py` is the direct GraphQL client, used as a fallback when the MCP Server isn't reachable.
- `src/incident_reporter.py` raises a DataHub incident (`raiseIncident` mutation) for a given resource URN.
- `src/impact_analyzer.py` ties the two together: resolve downstream impact (via the MCP agent, falling back to GraphQL), then report the incident with the affected components listed in its description.

### 4. RaceGuard Service

File:

```text
app/main.py
app/schemas.py
```

The service layer is the FastAPI application that orchestrates the other components. It does not duplicate telemetry validation or DataHub logic — it wires them together:

```text
telemetry input
      ↓
telemetry validator   (src/telemetry_validator.py)
      ↓
fallback manager       (src/fallback_manager.py)
      ↓
RaceGuard service       (app/main.py)
      ↓
DataHub impact analysis (src/impact_analyzer.py, MCP agent + GraphQL fallback)
      ↓
incident handling       (src/incident_reporter.py)
```

It exposes:

- `GET /health` — liveness check.
- `POST /telemetry/evaluate` — evaluates primary/backup telemetry and returns the RaceGuard decision.

## Three Scenarios

`POST /telemetry/evaluate` takes `primary` and `backup` telemetry packages and always resolves to exactly one of three scenarios.

### PRIMARY — the primary sensor is healthy

```bash
curl -X POST http://localhost:8000/telemetry/evaluate \
  -H "Content-Type: application/json" \
  -d '{
        "primary": {"tyre_temperature": 97.2, "tyre_pressure": 22.4},
        "backup":  {"tyre_temperature": 96.5, "tyre_pressure": 22.1}
      }'
```

```json
{
  "selected_source": "PRIMARY",
  "status": "OK",
  "reasons": ["Primary telemetry is valid"]
}
```

No DataHub call is made — the primary source is preferred whenever it is usable.

### BACKUP — the primary sensor is faulty, backup takes over

```bash
curl -X POST http://localhost:8000/telemetry/evaluate \
  -H "Content-Type: application/json" \
  -d '{
        "primary": {"tyre_temperature": null, "tyre_pressure": "error"},
        "backup":  {"tyre_temperature": 96.5, "tyre_pressure": 22.1}
      }'
```

```json
{
  "selected_source": "BACKUP",
  "status": "DEGRADED",
  "reasons": [
    "Primary telemetry is invalid",
    "Field 'tyre_temperature' cannot be None",
    "Field 'tyre_pressure' must be of type float",
    "Backup telemetry is valid"
  ]
}
```

RaceGuard runs `analyze_impact()` for `primary_tyre_sensor`, resolves the affected downstream components through the DataHub MCP Server, and raises a `Primary tyre sensor telemetry failure` incident in DataHub.

### BLOCKED — both sensors are faulty

```bash
curl -X POST http://localhost:8000/telemetry/evaluate \
  -H "Content-Type: application/json" \
  -d '{
        "primary": {"tyre_temperature": null, "tyre_pressure": "error"},
        "backup":  {"tyre_temperature": null, "tyre_pressure": "error"}
      }'
```

```json
{
  "selected_source": "BLOCKED",
  "status": "BLOCKED",
  "reasons": [
    "Primary telemetry is invalid",
    "Field 'tyre_temperature' cannot be None",
    "Field 'tyre_pressure' must be of type float",
    "Backup telemetry is invalid",
    "Field 'tyre_temperature' cannot be None",
    "Field 'tyre_pressure' must be of type float"
  ]
}
```

RaceGuard again runs `analyze_impact()` and raises a `Telemetry unavailable` incident in DataHub. If DataHub (or the MCP Server) is unreachable, the API still returns `200 OK` with the `BLOCKED` decision — telemetry safety does not depend on DataHub being available.

## Telemetry Validation

Telemetry is represented as a Python dictionary.

Example:

```python
telemetry = {
    "timestamp": "2026-08-08T14:32:10Z",
    "tyre_temperature": 96.5,
    "tyre_pressure": 22.1,
}
```

The validator receives:

- the telemetry dictionary;
- required field names;
- expected field types;
- optional numeric limits;
- optional maximum telemetry age.

Example:

```python
result = validate_telemetry(
    telemetry=telemetry,
    required_fields=[
        "tyre_temperature",
        "tyre_pressure",
    ],
    field_types={
        "timestamp": str,
        "tyre_temperature": float,
        "tyre_pressure": float,
    },
    max_age_seconds=10,
)
```

The function returns a `ValidationResult`.

```python
ValidationResult(
    valid=True,
    reasons=[],
)
```

If validation fails, the result contains one or more reasons.

```python
ValidationResult(
    valid=False,
    reasons=[
        "Field 'tyre_temperature' cannot be None"
    ],
)
```

## Validation Rules

### Required Fields

Required fields are supplied through configuration.

For example:

```python
required_fields = [
    "tyre_temperature",
    "tyre_pressure",
]
```

If a required field is missing, the telemetry is rejected.

### Type Validation

Expected Python types are also configured externally.

Example:

```python
field_types = {
    "timestamp": str,
    "tyre_temperature": float,
    "tyre_pressure": float,
}
```

A value with the wrong type causes validation to fail.

### None Values

Values equal to `None` are rejected.

Example:

```python
{
    "tyre_temperature": None
}
```

### NaN and Infinity

The validator rejects non-finite numeric values:

```python
float("nan")
float("inf")
float("-inf")
```

These values are not considered safe telemetry even though they are valid Python floating-point values.

### Timestamp Freshness

If a telemetry packet contains a `timestamp` and `max_age_seconds` is configured, the validator checks whether the telemetry is stale.

Example timestamp:

```text
2026-08-08T14:32:10Z
```

If the telemetry is older than the configured maximum age, validation fails.

An invalid timestamp format is also rejected.

If `timestamp` is not present and is not listed as a required field, its absence does not automatically invalidate the telemetry.

## Configurable Limits

The validator does not contain hardcoded Formula 1 physical limits.

Numeric limits must be provided through configuration.

Example:

```python
limits = {
    "some_numeric_field": {
        "min": 0.0,
        "max": 100.0,
    }
}
```

The validator only checks limits that were explicitly supplied.

This keeps generic validation logic separate from domain-specific telemetry configuration.

## Fallback Logic

After both telemetry sources have been validated, their `ValidationResult` objects are passed to the fallback manager.

Example:

```python
decision = choose_source(
    primary_result=primary_result,
    backup_result=backup_result,
)
```

### PRIMARY

If the primary source is valid:

```text
PRIMARY valid
BACKUP valid or invalid
```

the result is:

```text
PRIMARY
```

The primary source is preferred whenever it is usable.

### BACKUP

If:

```text
PRIMARY invalid
BACKUP valid
```

the result is:

```text
BACKUP
```

Reasons from the rejected primary source are preserved in the result.

### BLOCKED

If:

```text
PRIMARY invalid
BACKUP invalid
```

the result is:

```text
BLOCKED
```

This prevents unreliable telemetry from being passed further into the system.

## Project Structure

```text
f1-raceguard-ai/
│
├── app/
│   ├── main.py
│   └── schemas.py
│
├── scripts/
│   └── register_metadata.py
│
├── src/
│   ├── __init__.py
│   ├── datahub_client.py
│   ├── mcp_datahub_client.py
│   ├── impact_analyzer.py
│   ├── incident_reporter.py
│   ├── telemetry_validator.py
│   └── fallback_manager.py
│
├── test/
│   └── test_api.py
│
├── tests/
│   ├── test_impact_analyzer.py
│   ├── test_incident_reporter.py
│   ├── test_telemetry_validator.py
│   └── test_fallback_manager.py
│
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Installation

Clone the repository:

```bash
git clone https://github.com/Sen2x/f1-raceguard-ai.git
cd f1-raceguard-ai
```

Install the project dependencies (FastAPI service, DataHub client, DataHub MCP Server, and test tooling):

```bash
python -m pip install -r requirements.txt
```

Run the service:

```bash
python -m uvicorn app.main:app --reload
```

The API is then available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

DataHub impact analysis and incident reporting need a reachable DataHub instance. Point the DataHub MCP Server and the GraphQL fallback at it with:

```bash
export DATAHUB_GMS_URL=http://localhost:8080
export DATAHUB_GMS_TOKEN=<your-personal-access-token>   # optional
```

Without a reachable DataHub instance, the `BACKUP` and `BLOCKED` scenarios still work — the impact analysis call fails gracefully and is logged, it does not block the API response. It will add up to `DATAHUB_MCP_TIMEOUT_SECONDS` (default 8s) of latency for the MCP attempt before falling back to GraphQL and returning; lower it (or point `DATAHUB_GMS_URL` at a real instance) for a snappier demo.

To seed DataHub with the RaceGuard entities and lineage used by this project:

```bash
python scripts/register_metadata.py
```

## Running Tests

Run all available tests:

```bash
python -m pytest -v
```

Run only telemetry validation tests:

```bash
python -m pytest tests/test_telemetry_validator.py -v
```

Run only fallback manager tests:

```bash
python -m pytest tests/test_fallback_manager.py -v
```

Run only the API integration tests (all three scenarios):

```bash
python -m pytest test/test_api.py -v
```

All unit and integration tests use local test data and mocks — none of them make real network calls or spawn the DataHub MCP Server, per the project's testing principles below.

## Telemetry Validator Test Coverage

The validator is tested for:

- valid telemetry;
- missing required fields;
- `None` values;
- invalid value types;
- `NaN`;
- positive infinity;
- negative infinity;
- values below configured minimums;
- values above configured maximums;
- fresh timestamps;
- stale timestamps;
- missing optional timestamps;
- invalid timestamp formats.

## Fallback Manager Test Coverage

The fallback manager is tested for all three source-selection outcomes:

- `PRIMARY`;
- `BACKUP`;
- `BLOCKED`.

## API Integration Test Coverage

`test/test_api.py` drives the FastAPI app end-to-end (via `TestClient`) for all three scenarios, mocking `analyze_impact` so no real DataHub/MCP call is made:

- `PRIMARY` — impact analysis is not triggered;
- `BACKUP` — impact analysis is triggered with the correct incident details;
- `BLOCKED` — impact analysis is triggered with the correct incident details;
- DataHub being unreachable does not break the API response.

## Design Principles

The project follows several important design principles:

- telemetry validation is separated from service orchestration;
- fallback logic is separated from individual field validation;
- DataHub logic is separated from telemetry validation;
- physical limits are configuration-driven rather than hardcoded;
- invalid telemetry should not silently reach downstream components;
- the primary telemetry source is preferred whenever it is valid;
- backup telemetry is used only when the primary source is unsuitable;
- if neither source can be trusted, telemetry is blocked;
- DataHub impact analysis prefers the MCP Server agent and degrades to direct GraphQL, but a DataHub outage never blocks the API response;
- unit tests should not rely on real external services;
- the project does not introduce a new machine-learning model.

## Team Responsibilities

The project is divided into independent components to reduce merge conflicts and duplicated logic.

### DataHub

Responsible for:

- metadata registration;
- lineage;
- downstream impact analysis via the DataHub MCP Server (with GraphQL fallback);
- incident reporting.

Main files:

```text
scripts/register_metadata.py
src/datahub_client.py
src/mcp_datahub_client.py
src/impact_analyzer.py
src/incident_reporter.py
```

### Telemetry Validation and Fallback

Responsible for:

- telemetry validation;
- structured validation reasons;
- configurable limits;
- timestamp freshness checks;
- primary/backup source selection;
- blocking unreliable telemetry.

Main files:

```text
src/telemetry_validator.py
src/fallback_manager.py
tests/test_telemetry_validator.py
tests/test_fallback_manager.py
```

### Service Integration

Responsible for:

- orchestrating telemetry validation;
- calling fallback selection;
- producing the external RaceGuard decision;
- connecting failure decisions to DataHub impact analysis;
- keeping integration logic separate from validation rules.

Main files:

```text
app/main.py
app/schemas.py
test/test_api.py
```

## Development Workflow

Feature development is performed in separate Git branches.

Examples:

```text
feature/datahub
feature/telemetry-validation
feature/api
feature/integration
```

Changes should be reviewed through Pull Requests before being merged into `main`.

## Limitations

F1 RaceGuard AI currently focuses on:

- telemetry validation;
- safe source selection;
- metadata lineage;
- downstream impact analysis;
- incident handling and service integration.

The project does not:

- train a new Formula 1 strategy model;
- connect directly to a real Formula 1 car;
- claim real-world prediction accuracy;
- define authoritative Formula 1 sensor limits;
- assume physical thresholds that were not supplied through configuration.

## License

F1 RaceGuard AI is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for the full text.
