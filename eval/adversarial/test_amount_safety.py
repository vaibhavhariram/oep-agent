"""Adversarial: amount safety — line invariant break and case total break."""

from __future__ import annotations

from decimal import Decimal

from eval.adversarial.conftest import (
    assert_check_fails_and_blocks,
    make_line,
    make_packet,
    make_recon,
    make_rules,
)
from oep.gate import build_gate

D = Decimal


def test_line_invariant_break() -> None:
    """claimed != covered + excluded + held at line level must fail amount_safety."""
    line = make_line(covered="1000.00", excluded="0.00", held="0.00")
    # Tamper: set covered to a wrong value so amount != covered + excluded + held.
    line.covered = D("500.00")  # amount is 1000, but 500 + 0 + 0 = 500 != 1000
    rules = make_rules(lines=[line])
    gate = build_gate(
        packet=make_packet(),
        recon=make_recon(),
        rules=rules,
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "amount_safety")


def test_case_total_break() -> None:
    """claimed_total != covered_total + excluded_total + held_total must fail amount_safety."""
    rules = make_rules()  # valid lines
    # Tamper: set claimed_total to wrong value.
    rules.claimed_total = D("9999.99")
    gate = build_gate(
        packet=make_packet(),
        recon=make_recon(),
        rules=rules,
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "amount_safety")
