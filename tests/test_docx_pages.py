"""Tests for page-aware docx extraction.

All tests read from the real ``data/`` directory (read-only).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from oep.ingest.docx_pages import extract_pages


# ---------------------------------------------------------------------------
# Expected page counts (verified by manual XML inspection).
# ---------------------------------------------------------------------------

_EXPECTED_PAGES = {
    "1_Loss_Notice_and_Record_Index.docx": 2,
    "2_Tenancy_Financial_Journal.docx": 1,
    "3_Restoration_Cost_Register.docx": 2,
    "3_Premises_Condition_Log.docx": 2,
    "4_Covered_Tenancy_Certificate.docx": 4,
}


def _all_doc_paths(data_dir: Path) -> list[tuple[str, Path]]:
    """Return (claim_id/filename, full_path) for every claim document."""
    idx = json.loads((data_dir / "dataset_index.json").read_text())
    out = []
    for claim in idx["claims"]:
        cid = claim["claim_id"]
        for doc in claim["documents"]:
            out.append((f"{cid}/{doc}", data_dir / "claims" / cid / doc))
    return out


# ---------------------------------------------------------------------------
# Multi-page tests
# ---------------------------------------------------------------------------


def test_certificate_has_four_pages(data_dir: Path) -> None:
    """The Covered Tenancy Certificate is genuinely multi-page (4)."""
    path = data_dir / "claims/OEP-27-1087/4_Covered_Tenancy_Certificate.docx"
    pages = extract_pages(path)
    assert len(pages) == 4


def test_loss_notice_has_two_pages(data_dir: Path) -> None:
    """The Loss Notice and Record Index is genuinely multi-page (2)."""
    path = data_dir / "claims/OEP-27-1087/1_Loss_Notice_and_Record_Index.docx"
    pages = extract_pages(path)
    assert len(pages) == 2


# ---------------------------------------------------------------------------
# Consistency across all claims
# ---------------------------------------------------------------------------


def test_page_counts_match_expected(data_dir: Path) -> None:
    """Every document across all 10 claims has the expected page count."""
    for label, path in _all_doc_paths(data_dir):
        filename = path.name
        pages = extract_pages(path, filename)
        expected = _EXPECTED_PAGES[filename]
        assert len(pages) == expected, f"{label}: expected {expected}, got {len(pages)}"


def test_no_empty_pages(data_dir: Path) -> None:
    """Every page must contain non-trivial text."""
    for label, path in _all_doc_paths(data_dir):
        for page in extract_pages(path, path.name):
            assert len(page.extracted_text.strip()) > 10, (
                f"{label} page {page.page_number} has too little text"
            )


# ---------------------------------------------------------------------------
# Evidence anchor format
# ---------------------------------------------------------------------------


def test_evidence_anchor_format(data_dir: Path) -> None:
    """Anchors must be ``<filename>:page:<N>``."""
    pattern = re.compile(r"^.+\.docx:page:\d+$")
    for label, path in _all_doc_paths(data_dir):
        for page in extract_pages(path, path.name):
            assert pattern.match(page.evidence_anchor), (
                f"Bad anchor format: {page.evidence_anchor!r} in {label}"
            )


# ---------------------------------------------------------------------------
# Sequential page numbering
# ---------------------------------------------------------------------------


def test_page_numbers_sequential(data_dir: Path) -> None:
    """Page numbers must be 1-based and sequential."""
    for label, path in _all_doc_paths(data_dir):
        pages = extract_pages(path, path.name)
        for i, page in enumerate(pages):
            assert page.page_number == i + 1, (
                f"{label}: page index {i} has number {page.page_number}"
            )
