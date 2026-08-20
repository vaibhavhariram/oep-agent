"""Tests for Stage 6 — Credits, duplicates, recoveries (OEP-3.2 / OEP-4.1).

CRITICAL: proves that a duplicate reversal is removed exactly once.
"""

from decimal import Decimal

from oep.models.output import DocumentExtraction, DocumentType, EntryType, LedgerEntry, SourceFact
from oep.rules._stage6_credits import run_stage6
from oep.rules._types import ZERO, LineState

D = Decimal


def _line(source_index, description, amount, category="unit_restoration", status="covered", **kw):
    a = D(amount)
    return LineState(
        source_index=source_index, description=description, source_page=1,
        amount=a, category=category, documentation_status="sufficient",
        reference=None, evidence=f"Line {source_index + 1}: {description}",
        component=None, service_start=None, gap_start=None, gap_end=None,
        stated_rate=None, source_document="3_Restoration_Cost_Register.docx",
        covered=a if status == "covered" else ZERO,
        excluded=a if status == "excluded" else ZERO,
        held=ZERO, approved=ZERO, status=status,
        **kw,
    )


def _journal(entries):
    """Build a minimal DocumentExtraction with ledger entries."""
    ledger = []
    for desc, debit, credit, entry_type in entries:
        ledger.append(LedgerEntry(
            entry_date="01/01/2027",
            description=desc,
            charge_amount=debit,
            credit_amount=credit,
            running_balance=0.0,
            entry_type=entry_type,
            evidence=f"{desc}: debit ${debit:,.2f}, credit ${credit:,.2f}",
            source_page=1,
        ))
    return DocumentExtraction(
        document_type=DocumentType.tenancy_financial_journal,
        claim_id="OEP-27-0001", agreement_id=None, participant_name=None,
        protected_location=None, policy_form=None, claim_type=None,
        event_date=None, statement_date=None, protection_start=None,
        protection_end=None, claimed_total=None, ending_balance=None,
        facts=[SourceFact(field="claim_id", value="OEP-27-0001",
                          evidence="Claim ID OEP-27-0001", source_page=1)],
        limit_mentions=[], submitted_lines=[], ledger_entries=ledger,
        checklist_items=[], evidence_assertions=[], warnings=[],
    )


def test_6795_duplicate_removed_once():
    """OEP-27-6795: duplicate line 3 excluded, journal reversal skipped, $683 recovery applied once.

    Proves single removal: the $1,944 is removed ONCE (by Stage 2 exclusion),
    NOT twice (Stage 2 + journal reversal).
    """
    lines = [
        _line(0, "Primary wall and trim restoration", "1944.00"),
        _line(1, "Reletting interval", "759.00", category="reletting_gap"),
        _line(2, "Primary wall and trim restoration [DUPLICATE OF LINE 1]",
              "1944.00", category="duplicate", status="excluded"),
        _line(3, "Posted restoration supplement", "536.00"),
        _line(4, "Late amendment charge", "109.00", category="operator_fee", status="excluded"),
    ]

    journal = _journal([
        ("Primary wall and trim restoration", 1944.0, 0.0, EntryType.charge),
        ("Reletting interval", 759.0, 0.0, EntryType.charge),
        ("Primary wall and trim restoration [DUPLICATE OF LINE 1]", 1944.0, 0.0, EntryType.charge),
        ("Reversal for duplicated source line 3", 0.0, 1944.0, EntryType.reversal),
        ("Posted restoration supplement", 536.0, 0.0, EntryType.charge),
        ("Late amendment charge", 109.0, 0.0, EntryType.charge),
        ("Post-closeout payment or recovery", 0.0, 683.0, EntryType.recovery),
    ])

    run_stage6(lines, journal=journal)

    # Duplicate line: still excluded with $1944 (Stage 2 already did this).
    assert lines[2].excluded == D("1944.00")
    assert lines[2].covered == ZERO

    # Recovery of $683 applied ONCE: reduces covered amounts.
    total_covered = sum(ls.covered for ls in lines)
    total_excluded = sum(ls.excluded for ls in lines)

    # Sum check: total claimed = 1944+759+1944+536+109 = 5292
    total_claimed = sum(ls.amount for ls in lines)
    assert total_claimed == D("5292.00")

    # Recovery $683 moved from covered to excluded.
    # Pre-credit covered = 1944+759+536 = 3239
    # Post-credit covered = 3239 - 683 = 2556
    assert total_covered == D("2556.00"), f"Expected 2556 but got {total_covered}"

    # Invariant: claimed == covered + excluded + held
    total_held = sum(ls.held for ls in lines)
    assert total_claimed == total_covered + total_excluded + total_held


def test_recovery_applied_once():
    """A simple recovery reduces covered and increases excluded."""
    lines = [_line(0, "Wall repair", "1000.00")]
    journal = _journal([
        ("Wall repair", 1000.0, 0.0, EntryType.charge),
        ("Recovery", 0.0, 200.0, EntryType.recovery),
    ])
    run_stage6(lines, journal=journal)
    assert lines[0].covered == D("800.00")
    assert lines[0].excluded == D("200.00")
    assert lines[0].amount == lines[0].covered + lines[0].excluded + lines[0].held


def test_no_credits_no_change():
    """Journal with only charge entries doesn't modify lines."""
    lines = [_line(0, "Wall repair", "1000.00")]
    journal = _journal([("Wall repair", 1000.0, 0.0, EntryType.charge)])
    run_stage6(lines, journal=journal)
    assert lines[0].covered == D("1000.00")
    assert lines[0].excluded == ZERO
