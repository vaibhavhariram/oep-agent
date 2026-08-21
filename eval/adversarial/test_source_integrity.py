"""Adversarial: source integrity — missing file, extra file, hash mismatch, unreadable."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from oep.gate import build_gate
from oep.ingest.errors import ExtraFileError, HashMismatchError, MissingFileError
from oep.ingest.packet import assemble_packet

from eval.adversarial.conftest import (
    REFERENCE_CLAIM,
    assert_check_fails_and_blocks,
    copy_claim_to_tmp,
    make_packet,
    make_recon,
    make_rules,
)


def test_missing_file(tmp_path: Path, data_dir: Path) -> None:
    """A registered file removed from disk must raise MissingFileError."""
    tmp_data = copy_claim_to_tmp(tmp_path, data_dir)
    claim_dir = tmp_data / "claims" / REFERENCE_CLAIM
    # Remove the first document.
    first_doc = sorted(claim_dir.glob("*.docx"))[0]
    first_doc.unlink()
    with pytest.raises(MissingFileError):
        assemble_packet(REFERENCE_CLAIM, data_dir=tmp_data)


def test_extra_file(tmp_path: Path, data_dir: Path) -> None:
    """An unregistered file in the claim directory must raise ExtraFileError."""
    tmp_data = copy_claim_to_tmp(tmp_path, data_dir)
    claim_dir = tmp_data / "claims" / REFERENCE_CLAIM
    (claim_dir / "5_Rogue_Document.docx").write_bytes(b"unexpected")
    with pytest.raises(ExtraFileError):
        assemble_packet(REFERENCE_CLAIM, data_dir=tmp_data)


def test_sha256_mismatch(tmp_path: Path, data_dir: Path) -> None:
    """A corrupted file must raise HashMismatchError."""
    tmp_data = copy_claim_to_tmp(tmp_path, data_dir)
    claim_dir = tmp_data / "claims" / REFERENCE_CLAIM
    target = sorted(claim_dir.glob("*.docx"))[0]
    target.write_bytes(b"corrupted content that will not match the sha256")
    with pytest.raises(HashMismatchError):
        assemble_packet(REFERENCE_CLAIM, data_dir=tmp_data)


def test_unreadable_docx_gate_blocks() -> None:
    """A document with zero processed pages must fail source_integrity and block auto_approve."""
    packet = make_packet(page_count=0)
    recon = make_recon()
    rules = make_rules()
    gate = build_gate(packet=packet, recon=recon, rules=rules, claim_id="OEP-27-0001")
    assert_check_fails_and_blocks(gate, "source_integrity")
