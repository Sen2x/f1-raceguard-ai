# F1 RaceGuard AI

F1 RaceGuard AI is a safety layer designed to protect a race strategy system from invalid, missing, corrupted, or stale telemetry data.

The system validates incoming telemetry before it reaches downstream strategy components. If the primary telemetry source is unreliable, the system can safely switch to a backup source. If neither source is reliable, the telemetry is blocked.

DataHub is used to represent data lineage, analyze downstream impact, and support incident reporting.

## Project Goal

A race strategy system depends on telemetry data.

If a sensor sends invalid or outdated data, using it without validation may cause downstream components to operate on unreliable information.

F1 RaceGuard AI adds a protection layer between telemetry sources and the rest of the system.

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
              │            DataHub Impact Analysis
              │                     │
              │                     ▼
              │              Incident Handling
              │
              ▼
        Continue normally
```

---

## Team

LunarSafe AI was developed collaboratively for the hackathon.

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
src/impact_analyzer.py
src/incident_reporter.py
```

DataHub is used for metadata and lineage management.

The project models the flow of telemetry through downstream components so that a failure in an upstream source can be analyzed.

The DataHub part supports:

- metadata registration;
- data lineage;
- downstream impact analysis;
- incident reporting.

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

### 4. RaceGuard Service

The service layer is responsible for connecting the independent project components.

Its intended responsibility is:

```text
telemetry input
      ↓
telemetry validator
      ↓
fallback manager
      ↓
RaceGuard service
      ↓
DataHub impact analysis
      ↓
incident handling
```

The service layer should orchestrate the existing modules rather than duplicate telemetry validation or DataHub logic.

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

## Example Scenario

Primary telemetry:

```python
primary = {
    "timestamp": "2026-08-08T14:32:10Z",
    "tyre_temperature": None,
    "tyre_pressure": "error",
}
```

Backup telemetry:

```python
backup = {
    "timestamp": "2026-08-08T14:32:10Z",
    "tyre_temperature": 96.5,
    "tyre_pressure": 22.1,
}
```

The primary source fails validation because it contains invalid values.

The backup source passes validation.

Expected source decision:

```text
BACKUP
```

The fallback result can contain reasons such as:

```python
FallbackResult(
    selected_source="BACKUP",
    reasons=[
        "Primary telemetry is invalid",
        "Field 'tyre_temperature' cannot be None",
        "Field 'tyre_pressure' must be of type float",
        "Backup telemetry is valid",
    ],
)
```

## Project Structure

```text
f1-raceguard-ai/
│
├── scripts/
│   └── register_metadata.py
│
├── src/
│   ├── __init__.py
│   ├── datahub_client.py
│   ├── impact_analyzer.py
│   ├── incident_reporter.py
│   ├── telemetry_validator.py
│   └── fallback_manager.py
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

Additional service-layer files may be added as integration work is completed.

## Installation

Clone the repository:

```bash
git clone https://github.com/Sen2x/f1-raceguard-ai.git
cd f1-raceguard-ai
```

Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

The DataHub modules also require the DataHub Python package in the local development environment:

```bash
python -m pip install acryl-datahub
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

The telemetry and fallback unit tests use local test data and do not perform network requests.

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
- unit tests should not rely on real external services;
- the project does not introduce a new machine-learning model.

## Team Responsibilities

The project is divided into independent components to reduce merge conflicts and duplicated logic.

### DataHub

Responsible for:

- metadata registration;
- lineage;
- downstream impact analysis;
- incident reporting.

Main files:

```text
scripts/register_metadata.py
src/datahub_client.py
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

## Development Workflow

Feature development is performed in separate Git branches.

Examples:

```text
feature/datahub
feature/telemetry-validation
feature/raceguard-service
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

See the `LICENSE` file for licensing information.
