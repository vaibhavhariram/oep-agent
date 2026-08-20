"""Tests for Stage 7 — Sum and cap (OEP-2.4)."""

from decimal import Decimal

from oep.rules._stage7_cap import run_stage7
from oep.rules._types import ZERO, LineState

D = Decimal


def _line(source_index, covered):
    return LineState(
        source_index=source_index, description=f"Line {source_index + 1}",
        source_page=1, amount=D(covered), category="unit_restoration",
        documentation_status="sufficient", reference=None,
        evidence=f"Line {source_index + 1}: Test",
        component=None, service_start=None, gap_start=None, gap_end=None,
        stated_rate=None, source_document="3_Restoration_Cost_Register.docx",
        covered=D(covered), excluded=ZERO, held=ZERO, approved=ZERO,
    )


def test_9062_greedy_allocation():
    """OEP-27-9062: covered 1725/1284/412 with limit 2675 → approved 1725/950/0."""
    lines = [_line(0, "1725.00"), _line(1, "1284.00"), _line(2, "412.00")]
    run_stage7(lines, policy_limit=D("2675.00"))
    assert lines[0].approved == D("1725.00")
    assert lines[1].approved == D("950.00")
    assert lines[2].approved == ZERO
    assert sum(ls.approved for ls in lines) == D("2675.00")


def test_9548_greedy_allocation():
    """OEP-27-9548: covered 1837/711 with limit 2290 → approved 1837/453."""
    lines = [_line(0, "1837.00"), _line(1, "711.00")]
    run_stage7(lines, policy_limit=D("2290.00"))
    assert lines[0].approved == D("1837.00")
    assert lines[1].approved == D("453.00")
    assert sum(ls.approved for ls in lines) == D("2290.00")


def test_no_cap_needed():
    """Covered total under limit → all approved."""
    lines = [_line(0, "500.00"), _line(1, "300.00")]
    run_stage7(lines, policy_limit=D("1000.00"))
    assert lines[0].approved == D("500.00")
    assert lines[1].approved == D("300.00")


def test_all_excluded():
    """No covered amounts → zero approved."""
    lines = [_line(0, "0.00"), _line(1, "0.00")]
    for ls in lines:
        ls.excluded = ls.amount
        ls.covered = ZERO
    run_stage7(lines, policy_limit=D("5000.00"))
    assert sum(ls.approved for ls in lines) == ZERO


def test_greedy_order_matters():
    """Earlier lines consume the limit first."""
    lines = [_line(0, "100.00"), _line(1, "200.00"), _line(2, "300.00")]
    run_stage7(lines, policy_limit=D("250.00"))
    assert lines[0].approved == D("100.00")
    assert lines[1].approved == D("150.00")
    assert lines[2].approved == ZERO
