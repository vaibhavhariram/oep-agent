"""Adversarial: reconciliation — identifier and limit disagreements."""

from __future__ import annotations

from eval.adversarial.conftest import (
    assert_check_fails_and_blocks,
    make_conflict,
    make_packet,
    make_recon,
    make_rules,
)
from oep.gate import build_gate


def test_identifier_disagreement() -> None:
    """An identifier disagreement across documents must fail reconciliation and block auto_approve."""
    conflict = make_conflict(
        "claim_id",
        "OEP-27-0001",
        "OEP-27-9999",
        doc1="1_Loss_Notice_and_Record_Index.docx",
        doc2="4_Covered_Tenancy_Certificate.docx",
    )
    recon = make_recon(conflicts=[conflict])
    gate = build_gate(
        packet=make_packet(),
        recon=recon,
        rules=make_rules(),
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "reconciliation")
    # Verify the conflict carries provenance from both documents.
    assert len(conflict.values) == 2
    assert conflict.values[0].source_document != conflict.values[1].source_document


def test_limit_disagreement() -> None:
    """A limit disagreement between Loss Notice and Certificate must fail reconciliation."""
    conflict = make_conflict(
        "selected_limit",
        "$5,000.00",
        "$3,000.00",
        doc1="1_Loss_Notice_and_Record_Index.docx",
        doc2="4_Covered_Tenancy_Certificate.docx",
    )
    recon = make_recon(conflicts=[conflict])
    gate = build_gate(
        packet=make_packet(),
        recon=recon,
        rules=make_rules(),
        claim_id="OEP-27-0001",
    )
    assert_check_fails_and_blocks(gate, "reconciliation")
