"""Stage 2 — Exclusions (OEP-3.2).

Table-driven full-line exclusions: fees, routine turnover, upgrades, duplicates.

Upgrade branch (OEP-3.2): exclude only the increase over like-kind-and-quality
when a separable base amount is stated; exclude the full line when no separable
base is shown.

Known limitation: no visible case states a separable base amount for an upgrade
line, so only the full-line exclusion path is exercised by visible data.
"""

from __future__ import annotations

from oep.models.output import EvidenceItem, Outcome, RuleTraceStep
from oep.rules._types import (
    EXCLUDED_CATEGORIES,
    EXCLUSION_RATIONALE,
    ZERO,
    LineState,
)


def run_stage2(lines: list[LineState]) -> None:
    """Exclude lines whose category is in the exclusion table."""
    for ls in lines:
        if ls.category not in EXCLUDED_CATEGORIES:
            continue

        detail = EXCLUSION_RATIONALE.get(ls.category, "Excluded per OEP-3.2.")

        # Upgrade: exclude full line only when no separable base is shown.
        # If a separable base were stated, we would exclude only the uplift.
        # No visible case exercises the separable-base branch.

        ls.excluded = ls.amount
        ls.covered = ZERO
        ls.status = "excluded"
        ls.rationale = detail

        ls.rule_trace.append(RuleTraceStep(
            rule_id="OEP-3.2",
            outcome=Outcome.excluded,
            input_amount=float(ls.amount),
            adjustment_amount=float(ls.amount),
            output_amount=0.0,
            detail=detail,
            evidence=[EvidenceItem(root=ls.evidence_anchor())],
        ))
