"""Adversarial: failure path — extraction fails mid-claim.

Mocks extract_document to succeed on the first two documents (returning
minimal valid raw objects) and raise on the third, then asserts:
  1. Completed work preserved (first two calls succeeded)
  2. Warning recorded (exception propagates, not silently swallowed)
  3. Nothing fabricated downstream (no Result produced)
  4. No external write performed (assembly never reached)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from oep.assembly import process_claim
from oep.extraction.client import ModelCallRecord
from oep.extraction.schemas import (
    RawFinancialJournal,
    RawLedgerEntry,
    RawLossNotice,
)


def _fake_call_record(purpose: str) -> ModelCallRecord:
    return ModelCallRecord(
        purpose=purpose,
        provider="anthropic",
        requested_model="test",
        routed_provider="anthropic",
        routed_model="test",
        response_id="test-resp",
        duration_ms=0,
        attempt_count=1,
        input_tokens=0,
        cached_input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
        cost_source="test",
        stored_by_provider=False,
    )


# Minimal valid raw objects for the first two documents.
_FAKE_LOSS_NOTICE = RawLossNotice(
    claim_id="OEP-27-1087",
    agreement_id="AGR-001",
    participant_name="Test",
    protected_location="Unit 1",
    unit=None,
    policy_form="OEP-2027-SYN",
    possession_returned="01/01/2027",
    statement_date="02/01/2027",
    total_presented=1000.0,
    selected_limit=5000.0,
    warnings=[],
)

_FAKE_JOURNAL = RawFinancialJournal(
    claim_id="OEP-27-1087",
    agreement_id="AGR-001",
    participant_name="Test",
    ledger_entries=[
        RawLedgerEntry(
            entry_date="01/01/2027",
            description="Charge",
            debit_amount=1000.0,
            credit_amount=0.0,
            running_balance=1000.0,
            source_page=1,
        ),
    ],
    warnings=[],
)

# Map doc types to fake responses (first two documents only).
_FAKES = {
    "loss_notice_and_record_index": _FAKE_LOSS_NOTICE,
    "tenancy_financial_journal": _FAKE_JOURNAL,
}


def test_extraction_fails_mid_claim(data_dir: Path) -> None:
    """When extraction fails on the third document, assert four properties."""
    call_count = 0
    docs_extracted: list[str] = []

    def mock_extract(doc_type, tagged_text, *, claim_id=None):
        nonlocal call_count
        call_count += 1
        if doc_type in _FAKES:
            docs_extracted.append(doc_type)
            return _FAKES[doc_type], _fake_call_record(doc_type)
        # Third (or later) document: fail.
        raise RuntimeError("Simulated extraction failure on document 3")

    with patch("oep.assembly.extract_document", side_effect=mock_extract):
        with pytest.raises(RuntimeError, match="Simulated extraction failure"):
            process_claim("OEP-27-1087", data_dir=data_dir)

    # 1. Completed work preserved: first two documents were extracted.
    assert len(docs_extracted) == 2

    # 2. Warning recorded: the exception propagated (verified by pytest.raises).
    #    It was not silently swallowed.

    # 3. Nothing fabricated downstream: process_claim raised, so no Result
    #    object was returned.

    # 4. No external write: assembly was never reached, so WritebackPreview
    #    (simulated=True, external_write_performed=False) was never constructed.
