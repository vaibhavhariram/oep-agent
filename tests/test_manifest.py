"""Tests for manifest verification.

Failure-mode tests create isolated structures under ``tmp_path`` —
the real ``data/`` directory is never modified.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from oep.ingest.errors import (
    ClaimNotFoundError,
    ExtraFileError,
    FileUnreadableError,
    HashMismatchError,
    MissingFileError,
    PathTraversalError,
)
from oep.ingest.manifest import compute_sha256, verify_claim_packet


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_all_claims_verify(data_dir: Path, all_claim_ids: list[str]) -> None:
    """Every registered claim should verify without error."""
    for cid in all_claim_ids:
        claim = verify_claim_packet(cid, data_dir=data_dir)
        assert claim["claim_id"] == cid
        assert len(claim["documents"]) == 4


# ---------------------------------------------------------------------------
# Helpers for building isolated test data under tmp_path
# ---------------------------------------------------------------------------


def _make_mini_index(
    tmp_data: Path,
    claim_id: str,
    documents: list[str],
    *,
    file_overrides: dict[str, dict] | None = None,
) -> None:
    """Write a minimal dataset_index.json under *tmp_data*.

    *file_overrides* lets tests inject bad hashes etc.
    """
    files: list[dict] = []
    claim_dir = tmp_data / "claims" / claim_id
    for doc in documents:
        rel = f"claims/{claim_id}/{doc}"
        path = claim_dir / doc
        entry = {
            "path": rel,
            "sha256": compute_sha256(path) if path.exists() else "0" * 64,
            "size": path.stat().st_size if path.exists() else 0,
        }
        if file_overrides and rel in file_overrides:
            entry.update(file_overrides[rel])
        files.append(entry)

    index = {
        "schema_version": 1,
        "claims": [
            {"claim_id": claim_id, "label": "test", "documents": documents}
        ],
        "files": files,
    }
    (tmp_data / "dataset_index.json").write_text(json.dumps(index))


def _copy_claim(src_data: Path, tmp_data: Path, claim_id: str) -> list[str]:
    """Copy a claim folder from real data into tmp_data. Return doc names."""
    idx = json.loads((src_data / "dataset_index.json").read_text())
    claim = next(c for c in idx["claims"] if c["claim_id"] == claim_id)
    dst = tmp_data / "claims" / claim_id
    dst.mkdir(parents=True, exist_ok=True)
    for doc in claim["documents"]:
        shutil.copy2(src_data / "claims" / claim_id / doc, dst / doc)
    return list(claim["documents"])


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

_TEST_CLAIM = "OEP-27-1087"


def test_claim_not_found(data_dir: Path) -> None:
    with pytest.raises(ClaimNotFoundError):
        verify_claim_packet("OEP-27-0000", data_dir=data_dir)


def test_missing_file(tmp_path: Path, data_dir: Path) -> None:
    docs = _copy_claim(data_dir, tmp_path, _TEST_CLAIM)
    # Remove one document.
    (tmp_path / "claims" / _TEST_CLAIM / docs[0]).unlink()
    _make_mini_index(tmp_path, _TEST_CLAIM, docs)

    with pytest.raises(MissingFileError):
        verify_claim_packet(_TEST_CLAIM, data_dir=tmp_path)


def test_extra_file(tmp_path: Path, data_dir: Path) -> None:
    docs = _copy_claim(data_dir, tmp_path, _TEST_CLAIM)
    _make_mini_index(tmp_path, _TEST_CLAIM, docs)
    # Drop an unexpected file into the claim directory.
    (tmp_path / "claims" / _TEST_CLAIM / "unexpected.txt").write_text("oops")

    with pytest.raises(ExtraFileError):
        verify_claim_packet(_TEST_CLAIM, data_dir=tmp_path)


def test_hash_mismatch(tmp_path: Path, data_dir: Path) -> None:
    docs = _copy_claim(data_dir, tmp_path, _TEST_CLAIM)
    _make_mini_index(tmp_path, _TEST_CLAIM, docs)
    # Corrupt a file after the index was written with the original hash.
    target = tmp_path / "claims" / _TEST_CLAIM / docs[0]
    target.write_bytes(b"corrupted content")

    with pytest.raises(HashMismatchError):
        verify_claim_packet(_TEST_CLAIM, data_dir=tmp_path)


def test_path_traversal(tmp_path: Path, data_dir: Path) -> None:
    docs = _copy_claim(data_dir, tmp_path, _TEST_CLAIM)
    # Replace a document name with a traversal path in the index.
    bad_docs = ["../../../etc/passwd"] + docs[1:]
    _make_mini_index(tmp_path, _TEST_CLAIM, bad_docs)

    with pytest.raises(PathTraversalError):
        verify_claim_packet(_TEST_CLAIM, data_dir=tmp_path)


def test_file_unreadable(tmp_path: Path, data_dir: Path) -> None:
    docs = _copy_claim(data_dir, tmp_path, _TEST_CLAIM)
    _make_mini_index(tmp_path, _TEST_CLAIM, docs)
    # Remove read permission on one file.
    target = tmp_path / "claims" / _TEST_CLAIM / docs[0]
    target.chmod(0o000)
    try:
        with pytest.raises(FileUnreadableError):
            verify_claim_packet(_TEST_CLAIM, data_dir=tmp_path)
    finally:
        target.chmod(0o644)  # restore so tmp_path cleanup works
