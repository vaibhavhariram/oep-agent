"""Tests for Check 3 — Totals chain."""

from __future__ import annotations

from oep.extraction.schemas import (
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.normalize import normalize_all
from oep.reconcile._totals import check_totals_chain


def _normalize(ln, j, sr):
    """Shortcut: normalise four docs and return the list."""
    from oep.extraction.schemas import RawCertificate

    cert = RawCertificate(certificate_period_raw="2027-01-01 through 2027-12-31")
    return normalize_all(
        loss_notice=ln,
        journal=j,
        source_register=sr,
        certificate=cert,
    )


def _make_journal(entries):
    """Build a RawFinancialJournal from a list of (desc, debit, credit, balance) tuples."""
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
    """Build a RawSourceRegister from a list of (desc, category, amount) tuples."""
    return RawSourceRegister(
        document_title="Restoration Cost Register",
        presented_source_lines=[
            {
                "line_number": i + 1,
                "description": desc,
                "source_category": cat,
                "gross_amount": amt,
                "source_page": 1,
            }
            for i, (desc, cat, amt) in enumerate(lines)
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


def test_all_three_pass():
    """All three comparisons pass when amounts are consistent."""
    sr = _make_register([
        ("Wall repair", "Premises restoration", 1000.00),
        ("Floor fix", "Premises restoration", 500.00),
    ])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=1500.00)
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 1000.00),
        ("Floor fix", 500.00, 0.0, 1500.00),
    ])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert result.passed
    assert result.conflicts == []


def test_3a_fails_sum_vs_claimed():
    """3a fails when submitted lines don't sum to claimed_total."""
    sr = _make_register([
        ("Wall repair", "Premises restoration", 1000.00),
    ])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=2000.00)  # wrong
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 1000.00),
    ])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert not result.passed
    fields = [c.field for c in result.conflicts]
    assert "totals_chain_3a" in fields


def test_3b_fails_journal_internal():
    """3b fails when charges - credits != ending_balance."""
    sr = _make_register([
        ("Wall repair", "Premises restoration", 1000.00),
    ])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=1000.00)
    j = _make_journal([
        ("Wall repair", 1000.00, 0.0, 999.00),  # bad balance
    ])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert not result.passed
    fields = [c.field for c in result.conflicts]
    assert "totals_chain_3b" in fields


def test_3c_fails_register_vs_journal():
    """3c fails when charge total != submitted total."""
    sr = _make_register([
        ("Wall repair", "Premises restoration", 1000.00),
    ])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=1000.00)
    j = _make_journal([
        ("Wall repair", 800.00, 0.0, 800.00),  # wrong charge
    ])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert not result.passed
    fields = [c.field for c in result.conflicts]
    assert "totals_chain_3c" in fields


def test_journal_with_credits_passes():
    """Reversals and credits don't break gross comparisons.

    claimed_total=5292, charges sum to 5292, credits sum to 2627,
    ending_balance = 5292 - 2627 = 2665.  All three checks pass.
    """
    sr = _make_register([
        ("Line A", "Premises restoration", 1944.00),
        ("Line B", "Premises restoration", 1944.00),
        ("Line C", "Occupancy balance", 1404.00),
    ])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=5292.00)
    j = _make_journal([
        ("Line A", 1944.00, 0.0, 1944.00),
        ("Line B", 1944.00, 0.0, 3888.00),
        ("Line C", 1404.00, 0.0, 5292.00),
        ("Reversal of Line A", 0.0, 1944.00, 3348.00),
        ("Recovery", 0.0, 683.00, 2665.00),
    ])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert result.passed, (
        f"Expected pass but got conflicts: {[c.field for c in result.conflicts]}"
    )


def test_empty_submitted_lines():
    """Empty register should still work (sum=0)."""
    sr = _make_register([])
    ln = RawLossNotice(claim_id="OEP-27-0001", total_presented=0.0)
    j = _make_journal([])
    normalized = _normalize(ln, j, sr)
    result = check_totals_chain(ln, j, normalized, sr.document_title)
    assert result.passed
