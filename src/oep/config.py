"""Central path configuration for the OEP claims agent.

All data paths derive from a single DATA_DIR, which defaults to ``./data``
relative to the repository root.  Override with the ``OEP_DATA_DIR``
environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR: Path = Path(os.environ.get("OEP_DATA_DIR", _REPO_ROOT / "data"))

CLAIMS_DIR: Path = DATA_DIR / "claims"
EXAMPLES_DIR: Path = DATA_DIR / "examples"
POLICY_DIR: Path = DATA_DIR / "policy"

DATASET_INDEX_PATH: Path = DATA_DIR / "dataset_index.json"
OUTPUT_SCHEMA_PATH: Path = DATA_DIR / "output_schema.json"
POLICY_DOCX_PATH: Path = POLICY_DIR / "00_Master_Form_OEP-2027-SYN.docx"
