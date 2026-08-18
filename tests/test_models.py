"""Tests for generated Pydantic models and JSON Schema validation.

Round-trip and schema tests use the labeled example files in ``data/examples/``
(read-only — never modified).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, RootModel, ValidationError

from oep.models import output as gen_module
from oep.models.wrappers import (
    TopLevelResult,
    dump_result,
    load_result,
    validate_against_schema,
)


# ---------------------------------------------------------------------------
# Round-trip: load → parse → dump → compare
# ---------------------------------------------------------------------------

_EXAMPLE_FILES = [
    "OEP-27-1087_expected.json",
    "OEP-27-9062_expected.json",
    "OEP-27-9548_expected.json",
]


@pytest.mark.parametrize("filename", _EXAMPLE_FILES)
def test_round_trip(data_dir: Path, filename: str) -> None:
    """Load an example JSON, parse into Pydantic, re-serialize, and compare."""
    path = data_dir / "examples" / filename
    original = json.loads(path.read_text())

    model = load_result(path)
    serialized = dump_result(model)

    assert serialized == original, (
        f"Round-trip mismatch for {filename}"
    )


# ---------------------------------------------------------------------------
# JSON Schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", _EXAMPLE_FILES)
def test_schema_validation(data_dir: Path, filename: str) -> None:
    """Each example must validate against output_schema.json."""
    path = data_dir / "examples" / filename
    data = json.loads(path.read_text())

    errors = validate_against_schema(data)
    assert errors == [], f"Schema errors for {filename}: {errors}"


# ---------------------------------------------------------------------------
# extra="forbid" on all generated models
# ---------------------------------------------------------------------------


def test_all_models_forbid_extra() -> None:
    """Every generated BaseModel with fields must have extra='forbid'."""
    for name, cls in inspect.getmembers(gen_module, inspect.isclass):
        if not issubclass(cls, BaseModel) or cls is BaseModel:
            continue
        if issubclass(cls, RootModel):
            continue
        if not cls.model_fields:
            continue
        assert cls.model_config.get("extra") == "forbid", (
            f"{name} is missing extra='forbid'"
        )


# ---------------------------------------------------------------------------
# Extra fields are actually rejected
# ---------------------------------------------------------------------------


def test_extra_field_rejected(data_dir: Path) -> None:
    """Adding a spurious key to a result must raise ValidationError."""
    path = data_dir / "examples" / _EXAMPLE_FILES[0]
    data = json.loads(path.read_text())
    data["results"][0]["spurious_key"] = "should fail"

    with pytest.raises(ValidationError):
        TopLevelResult.model_validate(data)
