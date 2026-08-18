"""Shared pytest fixtures.

IMPORTANT: The real ``data/`` directory is strictly read-only.
Tests that need to simulate failures (missing files, bad hashes, etc.)
must create isolated copies under ``tmp_path``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def data_dir() -> Path:
    """Return the real (read-only) data directory."""
    return Path(__file__).resolve().parents[1] / "data"


@pytest.fixture()
def claims_dir(data_dir: Path) -> Path:
    return data_dir / "claims"


@pytest.fixture()
def all_claim_ids(data_dir: Path) -> list[str]:
    """Return all claim IDs from the dataset index."""
    idx = json.loads((data_dir / "dataset_index.json").read_text())
    return [c["claim_id"] for c in idx["claims"]]
