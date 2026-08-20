"""Tests for Stage 3 — Evidence holds (OEP-3.3 / OEP-3.4)."""

from decimal import Decimal

from oep.extraction.schemas import RawLossNotice, RecordIndexEntry
from oep.rules._stage3_hold import run_stage3
from oep.rules._types import ZERO, LineState

D = Decimal


def _line(documentation_status="sufficient", component=None, category="unit_restoration",
          amount="1000.00", status="covered", **kw):
    return LineState(
        source_index=0, description="Test", source_page=1,
        amount=D(amount), category=category,
        documentation_status=documentation_status,
        reference=None, evidence="Line 1: Test", component=component,
        service_start=None, gap_start=None, gap_end=None, stated_rate=None,
        source_document="3_Restoration_Cost_Register.docx",
        covered=D(amount), excluded=ZERO, held=ZERO, approved=ZERO,
        status=status, **kw,
    )


def _ln_with_condition(included: bool) -> RawLossNotice:
    status = "Included" if included else "Not included"
    return RawLossNotice(
        claim_id="OEP-27-0001",
        record_index=[
            RecordIndexEntry(
                registered_record="Premises condition evidence",
                packet_status=status,
                factual_scope="Factual observation only",
                source_page=2,
            ),
        ],
    )


def test_missing_held():
    ls = _line(documentation_status="missing")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.status == "needs_review"
    assert ls.held == D("1000.00")
    assert ls.covered == ZERO


def test_estimate_only_held():
    ls = _line(documentation_status="estimate_only")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.status == "needs_review"


def test_sufficient_not_held():
    ls = _line(documentation_status="sufficient")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.status == "covered"
    assert ls.covered == D("1000.00")


def test_already_excluded_skipped():
    ls = _line(documentation_status="missing", status="excluded")
    ls.excluded = ls.amount
    ls.covered = ZERO
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    # Should remain excluded, not re-held.
    assert ls.status == "excluded"
    assert ls.held == ZERO


def test_specialized_cleaning_held_without_condition_evidence():
    """Specialized cleaning held when record index says Not included."""
    ls = _line(documentation_status="sufficient", component="specialized cleaning")
    run_stage3([ls], loss_notice=_ln_with_condition(False))
    assert ls.status == "needs_review"
    assert ls.held == D("1000.00")
    assert "premises condition" in ls.rationale.lower()


def test_specialized_cleaning_not_held_with_condition_evidence():
    """Specialized cleaning NOT held when record index says Included."""
    ls = _line(documentation_status="sufficient", component="specialized cleaning")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.status == "covered"
    assert ls.held == ZERO


def test_specialized_cleaning_with_cost_register_and_included():
    """Condition evidence is read from record index, not document title.

    This test has a Restoration Cost Register (not a Condition Log) but
    record index says "Included" → should NOT be held.
    """
    ls = _line(documentation_status="sufficient", component="specialized cleaning")
    ls.source_document = "3_Restoration_Cost_Register.docx"
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.status == "covered"
    assert ls.held == ZERO


def test_hold_rule_trace():
    ls = _line(documentation_status="missing")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert len(ls.rule_trace) == 1
    assert ls.rule_trace[0].rule_id == "OEP-3.4"
    assert ls.rule_trace[0].outcome.value == "held"


def test_invariant_after_hold():
    ls = _line(documentation_status="missing", amount="500.00")
    run_stage3([ls], loss_notice=_ln_with_condition(True))
    assert ls.amount == ls.covered + ls.excluded + ls.held
