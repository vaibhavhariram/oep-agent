"""Policy rules engine — OEP-4.1 ordered calculation.

Public API:
    apply_rules(...)  → RulesResult
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from oep.extraction.normalize import parse_date
from oep.extraction.schemas import RawLossNotice, RawSourceRegister
from oep.models.output import (
    Citation,
    DecisionLine,
    DocumentExtraction,
    EvidenceItem,
    Outcome,
    RuleTraceStep,
    Status2,
)
from oep.reconcile._types import doc3_filename
from oep.rules._types import (
    CITATIONS,
    CITATIONS_BY_CATEGORY,
    RULE_ID_BY_CATEGORY,
    ZERO,
    LineState,
    RulesResult,
    parse_component,
    parse_service_start,
)
from oep.rules._stage1_classify import run_stage1
from oep.rules._stage2_exclude import run_stage2
from oep.rules._stage3_hold import run_stage3
from oep.rules._stage4_value import run_stage4
from oep.rules._stage5_gap import run_stage5
from oep.rules._stage6_credits import run_stage6
from oep.rules._stage7_cap import run_stage7

__all__ = ["apply_rules", "RulesResult"]


def _build_line_states(
    normalized: list[DocumentExtraction],
    source_register: RawSourceRegister,
) -> list[LineState]:
    """Construct LineState objects from normalized register + raw record register."""
    doc3_fn = doc3_filename(source_register.document_title)

    # Build lookup from 1-based line_number → raw record register entry.
    reg_by_line = {r.line_number: r for r in source_register.source_record_register}

    lines: list[LineState] = []
    for sl in normalized[2].submitted_lines:
        reg = reg_by_line.get(sl.source_index + 1)
        fact = reg.service_life_fact if reg else None

        component = parse_component(fact)
        service_start_str = parse_service_start(fact)
        service_start = parse_date(service_start_str) if service_start_str else None

        gap_start = parse_date(sl.protected_period_start) if sl.protected_period_start else None
        gap_end = parse_date(sl.protected_period_end) if sl.protected_period_end else None
        stated_rate = Decimal(str(sl.stated_rate)) if sl.stated_rate is not None else None

        ls = LineState(
            source_index=sl.source_index,
            description=sl.description,
            source_page=sl.source_page,
            amount=Decimal(str(sl.amount)),
            category=sl.source_classification,
            documentation_status=sl.documentation_status.value if hasattr(sl.documentation_status, 'value') else str(sl.documentation_status),
            reference=sl.reference,
            evidence=sl.evidence,
            component=component,
            service_start=service_start,
            gap_start=gap_start,
            gap_end=gap_end,
            stated_rate=stated_rate,
            source_document=doc3_fn,
            covered=Decimal(str(sl.amount)),
            excluded=ZERO,
            held=ZERO,
            approved=ZERO,
        )
        lines.append(ls)

    return lines


def _finalize_trace(lines: list[LineState]) -> None:
    """Append the final 'applied' trace step for lines that passed all stages."""
    for ls in lines:
        if ls.rule_trace:
            # Already has trace steps from a stage that modified it.
            continue
        if ls.status in ("excluded", "needs_review"):
            continue

        rule_id = RULE_ID_BY_CATEGORY.get(ls.category, "OEP-4.1")
        ls.rule_trace.append(RuleTraceStep(
            rule_id=rule_id,
            outcome=Outcome.applied,
            input_amount=float(ls.amount),
            adjustment_amount=0.0,
            output_amount=float(ls.covered),
            detail="No exclusion, hold, offset, or valuation reduction applies.",
            evidence=[EvidenceItem(root=ls.evidence_anchor())],
        ))
        if not ls.rationale:
            ls.rationale = "No exclusion, hold, offset, or valuation reduction applies."


def _build_citations(ls: LineState) -> list[Citation]:
    """Build citations for a DecisionLine based on category and status."""
    if ls.status == "excluded" and ls.category in (
        "operator_fee", "ordinary_upkeep", "upgrade", "duplicate"
    ):
        return [CITATIONS["OEP-3.2"]]

    if ls.status == "needs_review":
        return [CITATIONS["OEP-3.4"]]

    # Covered or partially_covered lines.
    cites = CITATIONS_BY_CATEGORY.get(ls.category, [])
    if cites:
        return list(cites)

    return [CITATIONS["OEP-4.1"]]


def _to_decision_line(ls: LineState) -> DecisionLine:
    """Convert a LineState to a DecisionLine output object."""
    return DecisionLine(
        source_index=ls.source_index,
        source_page=ls.source_page,
        claimed_amount=float(ls.amount),
        covered_amount=float(ls.covered),
        excluded_amount=float(ls.excluded),
        held_amount=float(ls.held),
        approved_amount=float(ls.approved),
        description=ls.description,
        category=ls.category,
        status=Status2(ls.status),
        rationale=ls.rationale or "Processed.",
        source_document=ls.source_document,
        source_evidence=ls.evidence,
        rule_trace=ls.rule_trace if ls.rule_trace else None,
        citations=_build_citations(ls),
    )


def apply_rules(
    *,
    loss_notice: RawLossNotice,
    source_register: RawSourceRegister,
    normalized: list[DocumentExtraction],
    policy_limit: Decimal,
    event_date: date,
) -> RulesResult:
    """Apply all 7 rules stages and return a RulesResult."""

    lines = _build_line_states(normalized, source_register)
    warnings: list[str] = []

    # Stage 1: Classification (no-op, already done in normalization).
    run_stage1(lines)

    # Stage 2: Exclusions.
    run_stage2(lines)

    # Stage 3: Evidence holds.
    run_stage3(lines, loss_notice=loss_notice)

    # Stage 4: Remaining-service valuation.
    run_stage4(lines, event_date=event_date)

    # Stage 5: Reletting gap boundary.
    run_stage5(
        lines,
        event_date=event_date,
        factual_observations=source_register.factual_observations,
    )

    # Stage 6: Credits, duplicates, recoveries.
    run_stage6(lines, journal=normalized[1])

    # Stage 7: Sum and cap.
    run_stage7(lines, policy_limit=policy_limit)

    # Final: append "applied" trace for untouched lines.
    _finalize_trace(lines)

    # Compute case totals.
    claimed_total = sum((ls.amount for ls in lines), ZERO)
    covered_total = sum((ls.covered for ls in lines), ZERO)
    excluded_total = sum((ls.excluded for ls in lines), ZERO)
    held_total = sum((ls.held for ls in lines), ZERO)
    approved_total = sum((ls.approved for ls in lines), ZERO)

    # Assert case-level invariant.
    assert claimed_total == covered_total + excluded_total + held_total, (
        f"Case invariant broken: claimed={claimed_total} != "
        f"covered={covered_total} + excluded={excluded_total} + held={held_total}"
    )

    return RulesResult(
        lines=lines,
        warnings=warnings,
        claimed_total=claimed_total,
        covered_total=covered_total,
        excluded_total=excluded_total,
        held_total=held_total,
        approved_total=approved_total,
    )
