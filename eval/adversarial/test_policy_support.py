"""Adversarial: policy support — absent clause_id and wrong source_page."""

from __future__ import annotations

import pytest

from eval.adversarial.conftest import (
    assert_check_fails_and_blocks,
    get_check,
    make_line,
    make_packet,
    make_recon,
    make_rules,
)
from oep.gate import build_gate
from oep.models.output import Route


def test_absent_clause_id() -> None:
    """A rule_id absent from the clause store must fail policy_support and block auto_approve."""
    line = make_line(rule_ids=["NONEXISTENT-99"])
    rules = make_rules(lines=[line])
    gate = build_gate(
        packet=make_packet(),
        recon=make_recon(),
        rules=rules,
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "policy_support")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Gate checks clause_id existence but not source_page correctness. "
        "A citation with a valid clause_id and wrong source_page passes the check. "
        "This is a known gap — see KNOWN_LIMITATIONS.md."
    ),
)
def test_wrong_source_page() -> None:
    """A valid clause_id with wrong source_page SHOULD fail policy_support.

    This test documents a gap: _check_policy_support only verifies clause_id
    existence in CLAUSE_BY_ID, not page correctness.  The assertion below
    expects the check to fail; since it does not, the test is marked xfail.
    """
    # OEP-4.1 is a valid clause_id (page 4 in the store).
    # The rule trace step is built by make_line with rule_id="OEP-4.1",
    # and source_page in the trace step is irrelevant to the gate check.
    line = make_line(rule_ids=["OEP-4.1"])
    # We cannot inject a wrong source_page into the gate check because
    # _check_policy_support only calls CLAUSE_BY_ID.get(step.rule_id) —
    # it never inspects source_page at all.
    rules = make_rules(lines=[line])
    gate = build_gate(
        packet=make_packet(),
        recon=make_recon(),
        rules=rules,
        claim_id="OEP-27-0001",
    )
    # This WILL pass (check passes, route may be auto_approve).
    # The xfail marker means the test is expected to fail this assertion.
    check = get_check(gate, "policy_support")
    assert not check.passed, "policy_support should fail on wrong source_page"
    assert gate.route != Route.auto_approve
