"""Tests for Stage 2 — Exclusions (OEP-3.2)."""

from decimal import Decimal

from oep.rules._stage2_exclude import run_stage2
from oep.rules._types import ZERO, LineState

D = Decimal


def _line(category="unit_restoration", amount="1000.00", **kw):
    return LineState(
        source_index=0, description="Test", source_page=1,
        amount=D(amount), category=category, documentation_status="sufficient",
        reference=None, evidence="Line 1: Test", component=None,
        service_start=None, gap_start=None, gap_end=None, stated_rate=None,
        source_document="3_Restoration_Cost_Register.docx",
        covered=D(amount), excluded=ZERO, held=ZERO, approved=ZERO,
        **kw,
    )


def test_fee_excluded():
    ls = _line(category="operator_fee", amount="124.00")
    run_stage2([ls])
    assert ls.status == "excluded"
    assert ls.excluded == D("124.00")
    assert ls.covered == ZERO


def test_ordinary_upkeep_excluded():
    ls = _line(category="ordinary_upkeep", amount="142.00")
    run_stage2([ls])
    assert ls.status == "excluded"
    assert ls.excluded == D("142.00")


def test_upgrade_excluded():
    ls = _line(category="upgrade", amount="193.00")
    run_stage2([ls])
    assert ls.status == "excluded"
    assert ls.excluded == D("193.00")


def test_duplicate_excluded():
    ls = _line(category="duplicate", amount="1944.00")
    run_stage2([ls])
    assert ls.status == "excluded"
    assert ls.excluded == D("1944.00")


def test_restoration_not_excluded():
    ls = _line(category="unit_restoration")
    run_stage2([ls])
    assert ls.status == "covered"
    assert ls.covered == D("1000.00")
    assert ls.excluded == ZERO


def test_occupancy_balance_not_excluded():
    ls = _line(category="occupancy_balance")
    run_stage2([ls])
    assert ls.status == "covered"


def test_reletting_gap_not_excluded():
    ls = _line(category="reletting_gap")
    run_stage2([ls])
    assert ls.status == "covered"


def test_rule_trace_appended():
    ls = _line(category="operator_fee")
    run_stage2([ls])
    assert len(ls.rule_trace) == 1
    assert ls.rule_trace[0].rule_id == "OEP-3.2"
    assert ls.rule_trace[0].outcome.value == "excluded"


def test_invariant_after_exclusion():
    ls = _line(category="operator_fee", amount="124.00")
    run_stage2([ls])
    assert ls.amount == ls.covered + ls.excluded + ls.held
