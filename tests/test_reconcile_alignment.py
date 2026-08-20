"""Tests for Check 4 — Journal/register alignment."""

from __future__ import annotations

from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.normalize import normalize_all
from oep.reconcile._alignment import check_journal_register_alignment


def _normalize(sr, j):
    """Shortcut: normalise with minimal loss notice and certificate."""
    ln = RawLossNotice(claim_id="OEP-27-0001")
    cert = RawCertificate(certificate_period_raw="2027-01-01 through 2027-12-31")
    return normalize_all(loss_notice=ln, journal=j, source_register=sr, certificate=cert)


def _make_journal(entries):
    return RawFinancialJournal(
        ledger_entries=[
            {
                "entry_date": "01/01/2027",
                "description": desc,
                "debit_amount": debit,
                "credit_amount": credit,
                "running_balance": bal,
                "source_page": 1,
            }
            for desc, debit, credit, bal in entries
        ],
    )


def _make_register(lines):
    return RawSourceRegister(
        document_title="Restoration Cost Register",
        presented_source_lines=[
            {
                "line_number": i + 1,
                "description": desc,
                "source_category": "Premises restoration",
                "gross_amount": amt,
                "source_page": 1,
            }
            for i, (desc, amt) in enumerate(lines)
        ],
        source_record_register=[
            {
                "line_number": i + 1,
                "record_status": "Paid record supplied",
                "source_page": 2,
            }
            for i in range(len(lines))
        ],
    )


def test_all_lines_match():
    sr = _make_register([("Wall repair", 1000.00), ("Floor fix", 500.00)])
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 1000.00),
        ("Floor fix", 500.00, 0.0, 1500.00),
    ])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert result.passed
    assert result.conflicts == []


def test_orphan_submitted_line():
    sr = _make_register([("Wall repair", 1000.00), ("Roof fix", 800.00)])
    j = _make_journal([("Wall repair", 1000.00, 0.0, 1000.00)])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert not result.passed
    assert len(result.conflicts) == 1
    assert "Roof fix" in result.conflicts[0].values[0].value


def test_orphan_charge_entry():
    sr = _make_register([("Wall repair", 1000.00)])
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 1000.00),
        ("Extra charge", 200.00, 0.0, 1200.00),
    ])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert not result.passed
    assert len(result.conflicts) == 1
    assert "Extra charge" in result.conflicts[0].values[0].value


def test_non_charge_entries_excluded():
    """Payments, credits, reversals etc. are expected journal entries."""
    sr = _make_register([("Wall repair", 1000.00)])
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 1000.00),
        ("Payment received", 0.0, 500.00, 500.00),  # credit → excluded
        ("Reversal", 0.0, 200.00, 300.00),           # credit → excluded
    ])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert result.passed


def test_duplicate_description_amount_greedy_match():
    """Two lines with same (description, amount) matched greedily in order."""
    sr = _make_register([("Repair", 1944.00), ("Repair", 1944.00)])
    j = _make_journal([
        ("Repair", 1944.00, 0.0, 1944.00),
        ("Repair", 1944.00, 0.0, 3888.00),
    ])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert result.passed
    assert result.conflicts == []


def test_duplicate_with_one_missing_charge():
    """Two submitted lines, only one charge entry → one orphan."""
    sr = _make_register([("Repair", 1944.00), ("Repair", 1944.00)])
    j = _make_journal([
        ("Repair", 1944.00, 0.0, 1944.00),
    ])
    normalized = _normalize(sr, j)
    result = check_journal_register_alignment(normalized, sr.document_title)
    assert not result.passed
    assert len(result.conflicts) == 1
