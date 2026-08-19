"""Tests for the deterministic table parser.

Compares parser output against the labeled examples' extraction objects
for the journal and source register.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oep.ingest.packet import assemble_packet
from oep.extraction.table_parser import (
    parse_journal,
    parse_source_lines,
    parse_record_register,
)


_EXAMPLES = [
    ("OEP-27-1087", "OEP-27-1087_expected.json"),
    ("OEP-27-9062", "OEP-27-9062_expected.json"),
    ("OEP-27-9548", "OEP-27-9548_expected.json"),
]


def _load_example_extraction(data_dir: Path, filename: str, doc_type: str) -> dict:
    """Load the extraction object for a given doc_type from a labeled example."""
    data = json.loads((data_dir / "examples" / filename).read_text())
    for doc in data["results"][0]["documents"]:
        if doc["document_type"] == doc_type:
            return doc["extraction"]
    raise ValueError(f"Doc type {doc_type!r} not found in {filename}")


# ===================================================================
# Journal parser vs labeled examples
# ===================================================================


@pytest.mark.parametrize("claim_id, example_file", _EXAMPLES)
def test_journal_parser_matches_example(
    data_dir: Path, claim_id: str, example_file: str
) -> None:
    """Deterministic journal parse must match the example's ledger_entries."""
    pkt = assemble_packet(claim_id)
    parsed = parse_journal(pkt.documents[1].pages)

    expected = _load_example_extraction(
        data_dir, example_file, "tenancy_financial_journal"
    )
    expected_entries = expected["ledger_entries"]

    assert len(parsed) == len(expected_entries), (
        f"{claim_id}: row count {len(parsed)} != {len(expected_entries)}"
    )

    for i, (p, e) in enumerate(zip(parsed, expected_entries)):
        assert p.description == e["description"], (
            f"{claim_id} row {i}: description mismatch"
        )
        assert abs(p.debit_amount - e["charge_amount"]) < 0.005, (
            f"{claim_id} row {i}: debit mismatch"
        )
        assert abs(p.credit_amount - e["credit_amount"]) < 0.005, (
            f"{claim_id} row {i}: credit mismatch"
        )
        assert abs(p.running_balance - e["running_balance"]) < 0.005, (
            f"{claim_id} row {i}: balance mismatch"
        )


# ===================================================================
# Source-lines parser vs labeled examples
# ===================================================================


@pytest.mark.parametrize("claim_id, example_file", _EXAMPLES)
def test_source_lines_parser_matches_example(
    data_dir: Path, claim_id: str, example_file: str
) -> None:
    """Deterministic source-line parse must match the example's submitted_lines."""
    pkt = assemble_packet(claim_id)
    parsed = parse_source_lines(pkt.documents[2].pages)

    # Find the right doc type for doc 3.
    doc3_type = pkt.documents[2].document_type
    expected = _load_example_extraction(data_dir, example_file, doc3_type)
    expected_lines = expected["submitted_lines"]

    assert len(parsed) == len(expected_lines), (
        f"{claim_id}: line count {len(parsed)} != {len(expected_lines)}"
    )

    for i, (p, e) in enumerate(zip(parsed, expected_lines)):
        assert p.description == e["description"], (
            f"{claim_id} line {p.line_number}: description mismatch: "
            f"parser={p.description!r}, expected={e['description']!r}"
        )
        assert abs(p.gross_amount - e["amount"]) < 0.005, (
            f"{claim_id} line {p.line_number}: amount mismatch"
        )
        assert p.source_category == e["category_hint"], (
            f"{claim_id} line {p.line_number}: category mismatch: "
            f"parser={p.source_category!r}, expected={e['category_hint']!r}"
        )


# ===================================================================
# Record register parser vs labeled examples
# ===================================================================


@pytest.mark.parametrize("claim_id, example_file", _EXAMPLES)
def test_record_register_parser_matches_example(
    data_dir: Path, claim_id: str, example_file: str
) -> None:
    """Deterministic record-register parse must match the example's submitted_lines
    for reference and documentation_status fields."""
    pkt = assemble_packet(claim_id)
    parsed = parse_record_register(pkt.documents[2].pages)

    doc3_type = pkt.documents[2].document_type
    expected = _load_example_extraction(data_dir, example_file, doc3_type)
    expected_lines = expected["submitted_lines"]

    assert len(parsed) == len(expected_lines), (
        f"{claim_id}: register row count {len(parsed)} != {len(expected_lines)}"
    )

    for i, (p, e) in enumerate(zip(parsed, expected_lines)):
        # Reference: parser returns None for "None stated", examples use null.
        assert p.record_reference == e["reference"], (
            f"{claim_id} line {p.line_number}: reference mismatch: "
            f"parser={p.record_reference!r}, expected={e['reference']!r}"
        )


# ===================================================================
# All 10 claims parse without error
# ===================================================================


def test_all_claims_parse(all_claim_ids: list[str]) -> None:
    """Parser must handle all 10 claims without crashing."""
    for cid in all_claim_ids:
        pkt = assemble_packet(cid)
        j = parse_journal(pkt.documents[1].pages)
        assert len(j) > 0, f"{cid}: no journal rows"
        sl = parse_source_lines(pkt.documents[2].pages)
        assert len(sl) > 0, f"{cid}: no source lines"
        rr = parse_record_register(pkt.documents[2].pages)
        assert len(rr) == len(sl), f"{cid}: register/source line count mismatch"
