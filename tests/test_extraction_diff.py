"""Structural diff harness: normalization output vs labeled examples.

Compares the normalized extraction objects (assembled from deterministic
table-parser output, NOT from LLM calls) against the three labeled examples.

EXCLUDED from comparison (per spec):
  - rendered_pages[].extracted_text (placeholder in labeled files)
  - run_id
  - completed_at

This test constructs raw extraction objects FROM the deterministic table
parser and the real document text, then normalizes them, and compares the
resulting DocumentExtraction objects against the examples.  This validates
the normalization layer end-to-end WITHOUT requiring LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oep.ingest.packet import assemble_packet
from oep.extraction.normalize import (
    build_shared_header,
    normalize_all,
)
from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.table_parser import (
    parse_journal,
    parse_record_register,
    parse_source_lines,
)


_EXAMPLES = [
    ("OEP-27-1087", "OEP-27-1087_expected.json"),
    ("OEP-27-9062", "OEP-27-9062_expected.json"),
    ("OEP-27-9548", "OEP-27-9548_expected.json"),
]


def _build_raw_from_parser(claim_id: str, data_dir: Path) -> dict:
    """Build raw extraction objects from the deterministic table parser.

    This simulates what the LLM would return, but using the parser output
    so tests don't require API calls.
    """
    pkt = assemble_packet(claim_id, data_dir=data_dir)

    # --- Loss Notice: extract metadata from page text ---
    ln_pages = pkt.documents[0].pages
    ln_text = "\n".join(p.extracted_text for p in ln_pages)
    ln_raw = _parse_loss_notice_text(ln_text, claim_id)

    # --- Journal: use table parser ---
    journal_rows = parse_journal(pkt.documents[1].pages)
    j_raw = RawFinancialJournal(
        claim_id=claim_id,
        agreement_id=ln_raw.agreement_id,
        unit=ln_raw.unit,
        participant_name=ln_raw.participant_name,
        snapshot_date=ln_raw.statement_date,
        ledger_entries=[
            {
                "entry_date": r.entry_date,
                "description": r.description,
                "debit_amount": r.debit_amount,
                "credit_amount": r.credit_amount,
                "running_balance": r.running_balance,
                "source_page": r.source_page,
            }
            for r in journal_rows
        ],
    )

    # --- Source Register: use table parser ---
    src_lines = parse_source_lines(pkt.documents[2].pages)
    reg_rows = parse_record_register(pkt.documents[2].pages)
    doc3 = pkt.documents[2]
    doc3_text = doc3.pages[0].extracted_text
    doc_title = "Restoration Cost Register"
    if "Premises Condition Log" in doc3_text:
        doc_title = "Premises Condition Log"

    sr_raw = RawSourceRegister(
        document_title=doc_title,
        claim_id=claim_id,
        policy_number=ln_raw.policy_number,
        agreement_id=ln_raw.agreement_id,
        policy_form=ln_raw.policy_form,
        participant_name=ln_raw.participant_name,
        operator=ln_raw.operator,
        property_name=ln_raw.property_name,
        unit=ln_raw.unit,
        protected_location=ln_raw.protected_location,
        monthly_charge=ln_raw.monthly_charge,
        possession_returned=ln_raw.possession_returned,
        selected_limit=ln_raw.selected_limit,
        presented_source_lines=[
            {
                "line_number": sl.line_number,
                "description": sl.description,
                "source_category": sl.source_category,
                "gross_amount": sl.gross_amount,
                "source_page": sl.source_page,
            }
            for sl in src_lines
        ],
        source_record_register=[
            {
                "line_number": rr.line_number,
                "record_status": rr.record_status,
                "record_reference": rr.record_reference,
                "service_life_fact": rr.service_life_fact,
                "source_page": rr.source_page,
            }
            for rr in reg_rows
        ],
        factual_observations=[],
    )

    # --- Certificate: extract from page text ---
    cert_raw = _parse_certificate_text(pkt.documents[3].pages)

    return {
        "loss_notice": ln_raw,
        "journal": j_raw,
        "source_register": sr_raw,
        "certificate": cert_raw,
    }


def _parse_loss_notice_text(text: str, claim_id: str) -> RawLossNotice:
    """Extract Loss Notice fields from rendered page text (deterministic)."""
    lines = text.split("\n")

    def _find_field(label: str) -> str | None:
        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                for i, p in enumerate(parts):
                    if p.lower() == label.lower() and i + 1 < len(parts):
                        return parts[i + 1]
        return None

    def _find_money(label: str) -> float | None:
        val = _find_field(label)
        if val:
            val = val.replace("$", "").replace(",", "")
            try:
                return float(val)
            except ValueError:
                pass
        return None

    # Total presented
    total = None
    for line in lines:
        if "TOTAL PRESENTED" in line and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            for p in parts:
                p = p.replace("$", "").replace(",", "")
                try:
                    total = float(p)
                except ValueError:
                    continue

    return RawLossNotice(
        claim_id=_find_field("Claim ID"),
        policy_number=_find_field("Policy number"),
        agreement_id=_find_field("Tenancy ID"),
        policy_form=_find_field("Policy form"),
        participant_name=_find_field("Covered household"),
        operator=_find_field("Operator"),
        property_name=_find_field("Property"),
        unit=_find_field("Unit"),
        protected_location=_find_field("Property address"),
        monthly_charge=_find_money("Monthly charge"),
        possession_returned=_find_field("Possession returned"),
        selected_limit=_find_money("Selected limit"),
        tenancy_start=_find_field("Tenancy start"),
        report_date=_find_field("Report date"),
        statement_date=_find_field("Closeout statement date"),
        event_narrative=_find_field("Event narrative"),
        total_presented=total,
    )


def _parse_certificate_text(pages: list) -> RawCertificate:
    """Extract Certificate fields from rendered page text (deterministic)."""
    text = "\n".join(p.extracted_text for p in pages)
    lines = text.split("\n")

    def _find_field(label: str) -> str | None:
        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                for i, p in enumerate(parts):
                    if p.lower() == label.lower() and i + 1 < len(parts):
                        return parts[i + 1]
        return None

    def _find_money(label: str) -> float | None:
        val = _find_field(label)
        if val:
            val = val.replace("$", "").replace(",", "")
            try:
                return float(val)
            except ValueError:
                pass
        return None

    return RawCertificate(
        policy_number=_find_field("Policy number"),
        policy_form=_find_field("Policy form"),
        agreement_id=_find_field("Tenancy reference"),
        participant_name=_find_field("Covered household"),
        operator=_find_field("Housing operator"),
        property_and_unit=_find_field("Property and unit"),
        protected_location=_find_field("Covered premises"),
        certificate_period_raw=_find_field("Certificate period"),
        monthly_charge=_find_money("Monthly occupancy charge"),
        combined_limit=_find_money("Combined protection limit"),
        deductible=_find_money("Certificate deductible"),
    )


# ===================================================================
# Structural diff: compare extraction fields
# ===================================================================


def _diff_extractions(actual: dict, expected: dict, path: str = "") -> list[str]:
    """Compare two extraction dicts field by field. Returns list of differences."""
    diffs: list[str] = []

    # Keys to skip.
    skip_keys = {"rendered_pages", "run_id", "completed_at"}

    if isinstance(actual, dict) and isinstance(expected, dict):
        all_keys = sorted(set(list(actual.keys()) + list(expected.keys())))
        for k in all_keys:
            if k in skip_keys:
                continue
            kpath = f"{path}.{k}" if path else k
            if k not in actual:
                diffs.append(f"{kpath}: missing in actual")
            elif k not in expected:
                diffs.append(f"{kpath}: extra in actual")
            else:
                diffs.extend(_diff_extractions(actual[k], expected[k], kpath))
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            diffs.append(f"{path}: list length {len(actual)} != {len(expected)}")
        else:
            for i in range(len(actual)):
                diffs.extend(
                    _diff_extractions(actual[i], expected[i], f"{path}[{i}]")
                )
    elif actual != expected:
        # Allow float/int comparison tolerance.
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if abs(actual - expected) < 0.005:
                return diffs
        diffs.append(f"{path}: {actual!r} != {expected!r}")

    return diffs


# ===================================================================
# Tests
# ===================================================================


@pytest.mark.parametrize("claim_id, example_file", _EXAMPLES)
def test_normalization_matches_example_extraction(
    data_dir: Path, claim_id: str, example_file: str
) -> None:
    """Normalized extraction objects must structurally match the labeled examples.

    This test uses the deterministic table parser (no LLM calls) to build
    raw extraction objects, normalizes them, and compares against the
    example's extraction fields.
    """
    raw = _build_raw_from_parser(claim_id, data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )

    expected_data = json.loads(
        (data_dir / "examples" / example_file).read_text()
    )
    expected_docs = expected_data["results"][0]["documents"]

    for actual_ext, expected_doc in zip(normalized, expected_docs):
        actual_dict = actual_ext.model_dump(mode="json")
        expected_ext = expected_doc["extraction"]

        diffs = _diff_extractions(actual_dict, expected_ext)
        if diffs:
            diff_str = "\n  ".join(diffs[:20])
            doc_type = expected_doc["document_type"]
            pytest.fail(
                f"{claim_id}/{doc_type}: {len(diffs)} diff(s):\n  {diff_str}"
            )
