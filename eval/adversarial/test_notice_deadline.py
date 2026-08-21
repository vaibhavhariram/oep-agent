"""Adversarial: notice deadline — statement date > 105 days after possession return."""

from __future__ import annotations

from eval.adversarial.conftest import (
    assert_check_fails_and_blocks,
    make_doc_extraction,
    make_packet,
    make_recon,
    make_rules,
)
from oep.gate import build_gate
from oep.reconcile._notice import check_notice_deadline


def test_statement_exceeds_105_days() -> None:
    """Statement date > 105 days after possession return must produce a conflict and block auto_approve."""
    # 135-day gap: event 2024-01-01, statement 2024-05-15.
    normalized = [
        make_doc_extraction(
            event_date="2024-01-01",
            statement_date="2024-05-15",
        )
        for _ in range(4)
    ]

    result = check_notice_deadline(normalized)
    assert not result.passed, "Notice deadline check should have failed"
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.field == "notice_deadline"
    assert "135" in conflict.resolution  # 135 days

    # Build full gate to verify the conflict blocks auto_approve.
    recon = make_recon(conflicts=result.conflicts)
    gate = build_gate(
        packet=make_packet(),
        recon=recon,
        rules=make_rules(),
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "reconciliation")
