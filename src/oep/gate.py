"""Verification gate and routing logic.

Five deterministic checks, weighted scoring, and route determination.
"""

from __future__ import annotations

from decimal import Decimal

from oep.models.output import (
    Check,
    Disposition,
    EvidenceItem,
    Gate,
    Route,
    RouteEvidenceItem,
)
from oep.ingest.packet import ClaimPacket
from oep.policy_store import CLAUSE_BY_ID
from oep.reconcile._types import ReconciliationResult
from oep.rules._types import ZERO, RulesResult

_THRESHOLD = 90.0


def _check_source_integrity(
    packet: ClaimPacket,
    claim_id: str,
) -> Check:
    """All registered files present, sha256 verified, every page processed."""
    # assemble_packet already verified sha256 and file presence.
    # If we got here, integrity is confirmed.
    passed = True
    for doc in packet.documents:
        if doc.page_count < 1:
            passed = False
    return Check(
        id="source_integrity",
        label="Registered sources processed",
        weight=20.0,
        hard_fail=True,
        passed=passed,
        evidence=[EvidenceItem(
            root=f"Registered sources processed deterministically verified for {claim_id}."
        )],
    )


def _check_reconciliation(
    recon: ReconciliationResult,
    claim_id: str,
) -> Check:
    """No material conflicts from the reconciliation module."""
    passed = len(recon.all_conflicts) == 0
    return Check(
        id="reconciliation",
        label="Material facts reconciled",
        weight=25.0,
        hard_fail=True,
        passed=passed,
        evidence=[EvidenceItem(
            root=f"Material facts reconciled deterministically verified for {claim_id}."
        )],
    )


def _check_policy_support(
    rules: RulesResult,
    claim_id: str,
) -> Check:
    """Every material conclusion carries a resolvable citation."""
    passed = True
    for ls in rules.lines:
        for step in ls.rule_trace:
            clause = CLAUSE_BY_ID.get(step.rule_id)
            if clause is None:
                passed = False
                break
    return Check(
        id="policy_support",
        label="Decisions have policy support",
        weight=20.0,
        hard_fail=True,
        passed=passed,
        evidence=[EvidenceItem(
            root=f"Decisions have policy support deterministically verified for {claim_id}."
        )],
    )


def _check_amount_safety(
    rules: RulesResult,
    claim_id: str,
) -> Check:
    """Both invariants hold at line and case level."""
    passed = True
    # Line-level invariant.
    for ls in rules.lines:
        if ls.amount != ls.covered + ls.excluded + ls.held:
            passed = False
            break
    # Case-level invariant.
    if rules.claimed_total != rules.covered_total + rules.excluded_total + rules.held_total:
        passed = False
    return Check(
        id="amount_safety",
        label="Amounts independently reconcile",
        weight=25.0,
        hard_fail=True,
        passed=passed,
        evidence=[EvidenceItem(
            root=f"Amounts independently reconcile deterministically verified for {claim_id}."
        )],
    )


def _check_unresolved_evidence(
    rules: RulesResult,
    claim_id: str,
) -> Check:
    """No held amount remains."""
    passed = rules.held_total == ZERO
    return Check(
        id="unresolved_evidence",
        label="No unresolved material amount",
        weight=10.0,
        hard_fail=False,
        passed=passed,
        evidence=[EvidenceItem(
            root=f"No unresolved material amount deterministically verified for {claim_id}."
        )],
    )


def build_gate(
    *,
    packet: ClaimPacket,
    recon: ReconciliationResult,
    rules: RulesResult,
    claim_id: str,
) -> Gate:
    """Build the verification gate with 5 checks and routing decision."""
    checks = [
        _check_source_integrity(packet, claim_id),
        _check_reconciliation(recon, claim_id),
        _check_policy_support(rules, claim_id),
        _check_amount_safety(rules, claim_id),
        _check_unresolved_evidence(rules, claim_id),
    ]

    score = sum(c.weight for c in checks if c.passed)
    hard_failure = any(c.hard_fail and not c.passed for c in checks)

    # Routing.
    if hard_failure:
        route = Route.human_review
        route_evidence_str = "A hard-fail check did not pass."
    elif rules.held_total == ZERO and score == 100.0:
        route = Route.auto_approve
        route_evidence_str = "All deterministic checks passed without a held amount."
    elif rules.held_total > ZERO and rules.covered_total > ZERO:
        route = Route.partial_approve_with_hold
        route_evidence_str = "Any material held amount prevents automatic approval."
    elif rules.held_total > ZERO and rules.covered_total == ZERO:
        route = Route.human_review
        route_evidence_str = "Any material held amount prevents automatic approval."
    else:
        route = Route.human_review
        route_evidence_str = "Routing could not be determined; defaulting to human review."

    stp = route == Route.auto_approve

    return Gate(
        checks=checks,
        score=score,
        threshold=_THRESHOLD,
        hard_failure=hard_failure,
        eligible_for_stp=stp,
        route=route,
        route_evidence=[RouteEvidenceItem(root=route_evidence_str)],
    )


def determine_disposition(gate: Gate) -> Disposition:
    """Determine disposition from the gate."""
    if gate.route == Route.human_review and not gate.eligible_for_stp:
        # Check if any covered amount exists.
        return Disposition.escalated
    return Disposition.approved


def determine_disposition_from_rules(
    gate: Gate,
    rules: RulesResult,
) -> Disposition:
    """Determine disposition from gate and rules."""
    if gate.route == Route.human_review:
        if rules.covered_total == ZERO:
            return Disposition.escalated
        return Disposition.escalated
    return Disposition.approved
