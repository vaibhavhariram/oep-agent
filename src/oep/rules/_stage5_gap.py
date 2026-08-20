"""Stage 5 — Reletting gap boundary (OEP-2.2).

Gap begins the day AFTER possession return.  Ends at the EARLIEST of:
  - stated ready or replacement cutoff
  - 30th calendar day after return

Cutoff day is INCLUSIVE.  Days outside the supported window are excluded
as out-of-period (OEP-3.2), producing a partially_covered line.

Known limitation: OEP-2.2 also lists "replacement occupancy" as a third
boundary.  No visible case states one, so it is not implemented.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from oep.extraction.normalize import parse_date
from oep.extraction.schemas import RawFactualObservation
from oep.models.output import EvidenceItem, Outcome, RuleTraceStep
from oep.rules._types import ZERO, LineState


def parse_ready_cutoff(
    factual_observations: list[RawFactualObservation],
) -> date | None:
    """Parse the ready-cutoff date from factual observations."""
    for obs in factual_observations:
        if "cutoff" in obs.observation.lower():
            d = parse_date(obs.recorded_fact)
            if d is not None:
                return d
    return None


def run_stage5(
    lines: list[LineState],
    *,
    event_date: date,
    factual_observations: list[RawFactualObservation],
) -> None:
    """Apply gap boundary to reletting-gap lines."""
    ready_cutoff = parse_ready_cutoff(factual_observations)
    thirty_day = event_date + timedelta(days=30)
    cutoff = min(ready_cutoff, thirty_day) if ready_cutoff else thirty_day

    for ls in lines:
        if ls.category != "reletting_gap":
            continue
        if ls.status in ("excluded", "needs_review"):
            continue
        if ls.gap_start is None or ls.gap_end is None or ls.stated_rate is None:
            continue

        # If gap is within the supported window, no trim.
        if ls.gap_end <= cutoff:
            continue

        total_days = (ls.gap_end - ls.gap_start).days + 1  # inclusive
        supported_days = max(0, (cutoff - ls.gap_start).days + 1)  # inclusive

        input_amount = ls.covered
        covered = Decimal(supported_days) * ls.stated_rate
        # Derive excluded from claimed to preserve invariant by construction.
        excluded = ls.amount - covered - ls.held

        ls.covered = covered
        ls.excluded = excluded
        ls.status = "partially_covered"

        excluded_days = total_days - supported_days
        detail = (
            f"Gap trimmed: {supported_days} supported day(s), "
            f"{excluded_days} day(s) outside boundary."
        )
        ls.rationale = detail

        ls.rule_trace.append(RuleTraceStep(
            rule_id="OEP-2.2",
            outcome=Outcome.applied,
            input_amount=float(input_amount),
            adjustment_amount=float(input_amount - covered),
            output_amount=float(covered),
            detail=detail,
            evidence=[EvidenceItem(root=ls.evidence_anchor())],
        ))

        # Assert invariant inside the stage.
        ls.check_invariant()
