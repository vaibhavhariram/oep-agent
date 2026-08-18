"""Dataset manifest loading and per-claim packet verification.

Loads ``dataset_index.json`` and, for a given claim id, asserts:
  - the claim exists in the index,
  - exactly the registered files are present on disk (no missing, no extras),
  - SHA-256 hashes match,
  - no path-traversal in filenames,
  - every file is readable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from oep import config
from oep.ingest.errors import (
    ClaimNotFoundError,
    ExtraFileError,
    FileUnreadableError,
    HashMismatchError,
    MissingFileError,
    PathTraversalError,
)

# Files that are expected OS artifacts and should be ignored when checking
# for extra files in a claim directory.
_IGNORED_FILES = frozenset({".DS_Store"})


def load_index(index_path: Path | None = None) -> dict:
    """Load and return the parsed dataset_index.json."""
    index_path = index_path or config.DATASET_INDEX_PATH
    return json.loads(index_path.read_text())


def get_claim(claim_id: str, index: dict | None = None) -> dict:
    """Return the claim entry for *claim_id*, or raise."""
    index = index or load_index()
    for claim in index["claims"]:
        if claim["claim_id"] == claim_id:
            return claim
    raise ClaimNotFoundError(f"Claim {claim_id!r} not found in dataset index")


def compute_sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_hash_lookup(index: dict) -> dict[str, str]:
    """Return {relative_path: sha256} from the files array."""
    return {entry["path"]: entry["sha256"] for entry in index["files"]}


def verify_claim_packet(
    claim_id: str,
    data_dir: Path | None = None,
    index: dict | None = None,
) -> dict:
    """Verify manifest integrity for a claim.

    Returns the claim entry dict on success.  Raises a specific
    :class:`ManifestError` subclass on the first failure detected.
    """
    data_dir = data_dir or config.DATA_DIR
    index = index or load_index(data_dir / "dataset_index.json")
    claim = get_claim(claim_id, index)
    hash_lookup = _build_hash_lookup(index)

    claim_dir = data_dir / "claims" / claim_id
    registered: set[str] = set()

    for filename in claim["documents"]:
        # --- path-traversal guard ---
        if ".." in filename or filename.startswith("/"):
            raise PathTraversalError(
                f"Unsafe path component in document name: {filename!r}"
            )

        registered.add(filename)
        file_path = claim_dir / filename

        # --- existence ---
        if not file_path.exists():
            raise MissingFileError(
                f"Registered file missing: {file_path}"
            )

        # --- readability ---
        try:
            with open(file_path, "rb") as f:
                f.read(1)
        except OSError as exc:
            raise FileUnreadableError(
                f"Cannot read {file_path}: {exc}"
            ) from exc

        # --- hash ---
        rel_path = f"claims/{claim_id}/{filename}"
        expected_hash = hash_lookup.get(rel_path)
        if expected_hash is None:
            raise HashMismatchError(
                f"No hash entry in index for {rel_path!r}"
            )
        actual_hash = compute_sha256(file_path)
        if actual_hash != expected_hash:
            raise HashMismatchError(
                f"Hash mismatch for {rel_path}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    # --- extra files ---
    if claim_dir.is_dir():
        on_disk = {
            p.name
            for p in claim_dir.iterdir()
            if p.name not in _IGNORED_FILES
        }
        extras = on_disk - registered
        if extras:
            raise ExtraFileError(
                f"Unregistered files in {claim_dir}: {sorted(extras)}"
            )

    return claim
