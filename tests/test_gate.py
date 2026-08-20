"""Tests for the verification gate and routing logic."""

from __future__ import annotations

from decimal import Decimal

from oep.gate import build_gate, determine_disposition_from_rules
from oep.ingest.packet import ClaimPacket, DocumentPacket
from oep.models.output import Disposition, Route
from oep.reconcile._types import ReconciliationResult
from oep.rules._types import ZERO, LineState, RulesResult

D = Decimal


def _packet(claim_id="OEP-27-0001"):
    return ClaimPacket(
        claim_id=claim_id,
        label="test",
        documents=[
            DocumentPacket(
                filename=f"{i}_doc.docx", document_type="test",
                sha256="a" * 64, page_count=1, provenance="test", pages=[],
            )
            for i in range(1, 5)
        ],
    )


def _recon(conflicts=0):
    from oep.models.output import ConflictValue, EvidenceItem, ResolutionStatus, SourceConflict
    sc = []
    for _ in range(conflicts):
        sc.append(SourceConflict(
            field="test", resolution="test", resolution_status=ResolutionStatus.unresolved,
            values=[
                ConflictValue(value="a", source_document="d1", source_page=1, evidence="e"),
                ConflictValue(value="b", source_document="d2", source_page=1, evidence="e"),
            ],
            evidence=[EvidenceItem(root="test")],
        ))
    return ReconciliationResult(checks=[], all_conflicts=sc, warnings=[])


def _line(covered="1000.00", excluded="0.00", held="0.00"):
    a = D(covered) + D(excluded) + D(held)
    return LineState(
        source_index=0, description="Test", source_page=1,
        amount=a, category="unit_restoration", documentation_status="sufficient",
        reference=None, evidence="Line 1: Test", component=None,
        service_start=None, gap_start=None, gap_end=None, stated_rate=None,
        source_document="3_doc.docx",
        covered=D(covered), excluded=D(excluded), held=D(held), approved=ZERO,
    )


def _rules(lines=None, **totals):
    if lines is None:
        lines = [_line()]
    return RulesResult(
        lines=lines,
        claimed_total=sum(l.amount for l in lines),
        covered_total=totals.get("covered", sum(l.covered for l in lines)),
        excluded_total=totals.get("excluded", sum(l.excluded for l in lines)),
        held_total=totals.get("held", sum(l.held for l in lines)),
        approved_total=totals.get("approved", ZERO),
    )


def test_auto_approve():
    """Score 100, no held → auto_approve."""
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=_rules(), claim_id="OEP-27-0001",
    )
    assert gate.route == Route.auto_approve
    assert gate.score == 100.0
    assert gate.eligible_for_stp is True
    assert not gate.hard_failure


def test_partial_approve_with_hold():
    """Covered > 0 and held > 0 → partial_approve_with_hold."""
    lines = [_line(covered="500.00", held="500.00")]
    gate = build_gate(
        packet=_packet(), recon=_recon(),
        rules=_rules(lines=lines), claim_id="OEP-27-0001",
    )
    assert gate.route == Route.partial_approve_with_hold
    assert gate.score == 90.0
    assert gate.eligible_for_stp is False


def test_human_review_all_held():
    """Held > 0, covered == 0 → human_review."""
    lines = [_line(covered="0.00", held="1000.00")]
    gate = build_gate(
        packet=_packet(), recon=_recon(),
        rules=_rules(lines=lines), claim_id="OEP-27-0001",
    )
    assert gate.route == Route.human_review


def test_human_review_hard_failure():
    """Material conflict → reconciliation fails → human_review."""
    gate = build_gate(
        packet=_packet(), recon=_recon(conflicts=1),
        rules=_rules(), claim_id="OEP-27-0001",
    )
    assert gate.route == Route.human_review
    assert gate.hard_failure is True
    assert gate.score < 100.0


def test_five_checks():
    """Exactly 5 checks with correct IDs."""
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=_rules(), claim_id="OEP-27-0001",
    )
    assert len(gate.checks) == 5
    ids = {c.id for c in gate.checks}
    assert ids == {"source_integrity", "reconciliation", "policy_support",
                   "amount_safety", "unresolved_evidence"}


def test_weights_sum_100():
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=_rules(), claim_id="OEP-27-0001",
    )
    assert sum(c.weight for c in gate.checks) == 100.0


def test_threshold_is_90():
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=_rules(), claim_id="OEP-27-0001",
    )
    assert gate.threshold == 90.0


def test_auto_approve_never_with_held():
    """INVARIANT: auto_approve must never occur when held > 0."""
    lines = [_line(covered="500.00", held="500.00")]
    gate = build_gate(
        packet=_packet(), recon=_recon(),
        rules=_rules(lines=lines), claim_id="OEP-27-0001",
    )
    assert gate.route != Route.auto_approve


def test_auto_approve_never_with_conflicts():
    """INVARIANT: auto_approve must never occur with material conflicts."""
    gate = build_gate(
        packet=_packet(), recon=_recon(conflicts=1),
        rules=_rules(), claim_id="OEP-27-0001",
    )
    assert gate.route != Route.auto_approve


def test_disposition_escalated_when_human_review():
    rules = _rules(lines=[_line(covered="0.00", held="1000.00")])
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=rules, claim_id="OEP-27-0001",
    )
    disp = determine_disposition_from_rules(gate, rules)
    assert disp == Disposition.escalated


def test_disposition_approved_when_auto_approve():
    rules = _rules()
    gate = build_gate(
        packet=_packet(), recon=_recon(), rules=rules, claim_id="OEP-27-0001",
    )
    disp = determine_disposition_from_rules(gate, rules)
    assert disp == Disposition.approved
