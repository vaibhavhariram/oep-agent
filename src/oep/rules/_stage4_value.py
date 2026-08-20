"""Stage 4 — Remaining-service valuation (OEP-4.2 / OEP-3.6).

For scheduled components, eligible value = gross * remaining / scheduled,
Decimal ROUND_HALF_UP to cents.  Expired components have no remaining value.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from oep.models.output import EvidenceItem, Outcome, RuleTraceStep
from oep.rules._types import CENT, COMPONENT_SCHEDULE, ZERO, LineState


def whole_months(start: date, end: date) -> int:
    """Count whole calendar months from *start* to *end*."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def compute_remaining_value(
    gross: Decimal,
    service_start: date,
    event_date: date,
    scheduled_months: int,
) -> Decimal:
    """Compute eligible service value per OEP-4.2."""
    used = whole_months(service_start, event_date)
    remaining = max(0, scheduled_months - used)
    if remaining == 0:
        return ZERO
    return (gross * Decimal(remaining) / Decimal(scheduled_months)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def run_stage4(lines: list[LineState], *, event_date: date) -> None:
    """Apply remaining-service valuation to scheduled components."""
    for ls in lines:
        # Skip excluded or held lines.
        if ls.status in ("excluded", "needs_review"):
            continue

        if ls.component is None or ls.service_start is None:
            continue

        scheduled = COMPONENT_SCHEDULE.get(ls.component.strip().lower())
        if scheduled is None:
            # Not a scheduled component (labor, etc.) → no reduction.
            continue

        eligible = compute_remaining_value(
            ls.covered, ls.service_start, event_date, scheduled
        )
        reduction = ls.covered - eligible

        if reduction <= ZERO:
            continue

        input_amount = ls.covered
        ls.excluded += reduction
        ls.covered = eligible

        if eligible == ZERO:
            ls.status = "excluded"
            detail = (
                f"Component fully expired ({ls.component}, "
                f"{scheduled} month schedule); no remaining service value."
            )
        else:
            ls.status = "partially_covered"
            detail = (
                f"Remaining-service reduction for {ls.component}: "
                f"eligible ${eligible:,.2f} of ${input_amount:,.2f}."
            )

        ls.rationale = detail

        ls.rule_trace.append(RuleTraceStep(
            rule_id="OEP-4.2",
            outcome=Outcome.applied,
            input_amount=float(input_amount),
            adjustment_amount=float(reduction),
            output_amount=float(eligible),
            detail=detail,
            evidence=[EvidenceItem(root=ls.evidence_anchor())],
        ))
