"""Adversarial: coverage window — possession return outside certificate period."""

from __future__ import annotations

from eval.adversarial.conftest import (
    assert_check_fails_and_blocks,
    make_doc_extraction,
    make_packet,
    make_recon,
    make_rules,
)
from oep.gate import build_gate
from oep.reconcile._coverage import check_coverage_window


def test_event_outside_certificate_period() -> None:
    """Possession return outside the certificate period must produce a conflict and block auto_approve."""
    # Event date is 2025-06-15, but certificate covers 2024-01-01 through 2024-12-31.
    normalized = [
        make_doc_extraction(
            event_date="2025-06-15",
            protection_start="2024-01-01",
            protection_end="2024-12-31",
        )
        for _ in range(4)
    ]

    result = check_coverage_window(normalized)
    assert not result.passed, "Coverage window check should have failed"
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.field == "coverage_window"

    # Build full gate to verify the conflict blocks auto_approve.
    recon = make_recon(conflicts=result.conflicts)
    gate = build_gate(
        packet=make_packet(),
        recon=recon,
        rules=make_rules(),
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "reconciliation")
