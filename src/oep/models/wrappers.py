"""Hand-written helpers over the generated Pydantic v2 models.

Responsibilities:
  - Import-time enforcement that every generated model forbids extra fields.
  - Load / dump helpers for result JSON files.
  - Authoritative JSON Schema validation via ``jsonschema`` (the schema file
    is the contract; Pydantic is for construction convenience).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import jsonschema
from pydantic import BaseModel, RootModel

from oep import config
from oep.models import output as _gen

# ---------------------------------------------------------------------------
# Import-time check: every generated BaseModel must have extra="forbid"
# ---------------------------------------------------------------------------

# RootModel subclasses are constrained-string wrappers (no dict fields).
# Empty placeholder models (no fields) also don't need the guard.
_SKIP_EXTRA_CHECK = frozenset({"RootModel"})


def _check_extra_forbid() -> None:
    missing = []
    for name, cls in inspect.getmembers(_gen, inspect.isclass):
        if name in _SKIP_EXTRA_CHECK:
            continue
        if not issubclass(cls, BaseModel) or cls is BaseModel:
            continue
        if issubclass(cls, RootModel):
            continue
        # Empty placeholder models (no declared fields) are harmless.
        if not cls.model_fields:
            continue
        if cls.model_config.get("extra") != "forbid":
            missing.append(name)
    if missing:
        raise RuntimeError(
            f"Generated models missing extra='forbid': {missing}. "
            "Re-run datamodel-codegen or check output_schema.json."
        )


_check_extra_forbid()

# Re-export the top-level model for convenience.
TopLevelResult = _gen.AlderquillOccupancyExitProtectionV2Result
Result = _gen.Result

# ---------------------------------------------------------------------------
# Load / dump
# ---------------------------------------------------------------------------


def load_result(path: Path) -> TopLevelResult:
    """Parse a JSON file into the top-level Pydantic model."""
    data = json.loads(path.read_text())
    return TopLevelResult.model_validate(data)


def dump_result(result: TopLevelResult) -> dict:
    """Serialize a top-level result back to a plain dict (JSON-safe types)."""
    return result.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Authoritative JSON Schema validation
# ---------------------------------------------------------------------------


def validate_against_schema(
    data: dict,
    schema_path: Path | None = None,
) -> list[str]:
    """Validate *data* against the raw JSON Schema file.

    Returns a list of human-readable error strings (empty on success).
    """
    schema_path = schema_path or config.OUTPUT_SCHEMA_PATH
    schema = json.loads(schema_path.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    return [str(e) for e in validator.iter_errors(data)]
