"""Tests for Stage 4 — Remaining-service valuation (OEP-4.2 / OEP-3.6).

Acceptance values verified against the specification.
"""

from datetime import date
from decimal import Decimal

import pytest

from oep.rules._stage4_value import compute_remaining_value, run_stage4, whole_months
from oep.rules._types import ZERO, LineState

D = Decimal


def _line(component, service_start, amount, **kw):
    return LineState(
        source_index=0, description="Test", source_page=1,
        amount=D(amount), category="unit_restoration",
        documentation_status="sufficient", reference=None,
        evidence="Line 1: Test", component=component,
        service_start=service_start, gap_start=None, gap_end=None,
        stated_rate=None, source_document="3_Restoration_Cost_Register.docx",
        covered=D(amount), excluded=ZERO, held=ZERO, approved=ZERO,
        **kw,
    )


# -------------------------------------------------------------------
# whole_months
# -------------------------------------------------------------------


def test_whole_months_exact():
    assert whole_months(date(2018, 10, 9), date(2027, 4, 9)) == 102


def test_whole_months_partial():
    assert whole_months(date(2018, 10, 10), date(2027, 4, 9)) == 101


def test_whole_months_same_date():
    assert whole_months(date(2027, 1, 1), date(2027, 1, 1)) == 0


# -------------------------------------------------------------------
# Acceptance values (exact)
# -------------------------------------------------------------------

_ACCEPTANCE = [
    # (component, service_start, event_date, scheduled, gross, expected)
    ("floor finish",      date(2018, 10, 9), date(2027, 4, 9),  120, "960.00",  "144.00"),
    ("window treatment",  date(2020, 4, 9),  date(2027, 4, 9),   96, "504.00",   "63.00"),
    ("countertop panel",  date(2018, 4, 9),  date(2027, 4, 9),  120, "1080.00", "108.00"),
    ("floor finish",      date(2023, 12, 12), date(2027, 9, 12), 120, "648.00",  "405.00"),
    ("carpet",            date(2019, 3, 27), date(2027, 3, 27),  84, "1075.00",   "0.00"),
    ("window treatment",  date(2018, 3, 27), date(2027, 3, 27),  96,  "438.00",   "0.00"),
    ("door closer",       date(2025, 3, 27), date(2027, 3, 27),  72,  "528.00", "352.00"),
]


@pytest.mark.parametrize(
    "component, start, event, scheduled, gross, expected",
    _ACCEPTANCE,
    ids=[
        "4706-L1-floor-finish",
        "4706-L2-window-treatment",
        "4706-L4-countertop-panel",
        "5804-L3-floor-finish",
        "8150-L1-carpet-expired",
        "8150-L2-window-expired",
        "8150-L4-door-closer",
    ],
)
def test_acceptance_value(component, start, event, scheduled, gross, expected):
    result = compute_remaining_value(D(gross), start, event, scheduled)
    assert result == D(expected), f"Expected {expected}, got {result}"


# -------------------------------------------------------------------
# Stage 4 integration
# -------------------------------------------------------------------


def test_stage4_depreciation_reduces_covered():
    ls = _line("floor finish", date(2018, 10, 9), "960.00")
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert ls.covered == D("144.00")
    assert ls.excluded == D("816.00")
    assert ls.status == "partially_covered"
    assert ls.amount == ls.covered + ls.excluded + ls.held


def test_stage4_expired_sets_excluded():
    ls = _line("carpet", date(2019, 3, 27), "1075.00")
    run_stage4([ls], event_date=date(2027, 3, 27))
    assert ls.covered == ZERO
    assert ls.excluded == D("1075.00")
    assert ls.status == "excluded"


def test_stage4_labor_no_reduction():
    ls = _line("electrical labor", date(2018, 1, 1), "715.00")
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert ls.covered == D("715.00")
    assert ls.excluded == ZERO


def test_stage4_floor_labor_no_reduction():
    """'floor labor' is labor, not 'floor finish' — no reduction."""
    ls = _line("floor labor", date(2018, 1, 1), "500.00")
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert ls.covered == D("500.00")
    assert ls.excluded == ZERO


def test_stage4_no_component_skipped():
    ls = _line(None, None, "1000.00")
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert ls.covered == D("1000.00")


def test_stage4_skips_excluded_lines():
    ls = _line("floor finish", date(2018, 10, 9), "960.00", status="excluded")
    ls.excluded = ls.amount
    ls.covered = ZERO
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert ls.excluded == D("960.00")


def test_stage4_partially_covered_status():
    """Depreciated lines with eligible > 0 get partially_covered."""
    ls = _line("door closer", date(2025, 3, 27), "528.00")
    run_stage4([ls], event_date=date(2027, 3, 27))
    assert ls.status == "partially_covered"
    assert ls.covered == D("352.00")
    assert ls.excluded == D("176.00")


def test_stage4_rule_trace():
    ls = _line("floor finish", date(2018, 10, 9), "960.00")
    run_stage4([ls], event_date=date(2027, 4, 9))
    assert len(ls.rule_trace) == 1
    assert ls.rule_trace[0].rule_id == "OEP-4.2"
