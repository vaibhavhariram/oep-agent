"""Stage 6 — Credits, duplicates, recoveries applied ONCE (OEP-3.2 / OEP-4.1).

CRITICAL: check whether the journal has ALREADY reversed a duplicate before
the rules engine removes it.  Removing it again double-counts.

Credits move amount from covered to excluded to preserve the line invariant
(claimed == covered + excluded + held).

Known limitation: attribution of an unattributed recovery to a specific line
is genuinely ambiguous.  We allocate greedily in source_index order and record
the choice in the rule_trace detail.
"""

from __future__ import annotations

import re
from decimal import Decimal

from oep.models.output import (
    DocumentExtraction,
    EntryType,
    EvidenceItem,
    Outcome,
    RuleTraceStep,
)
from oep.rules._types import ZERO, LineState

_REVERSAL_LINE_RE = re.compile(r"source line\s*(\d+)", re.IGNORECASE)
_DUPLICATE_RE = re.compile(r"duplicat", re.IGNORECASE)


def run_stage6(
    lines: list[LineState],
    *,
    journal: DocumentExtraction,
) -> None:
    """Apply credits, recoveries, and reversals exactly once."""

    # Collect indices of lines excluded as duplicate in Stage 2.
    excluded_duplicate_indices: set[int] = {
        ls.source_index
        for ls in lines
        if ls.status == "excluded" and ls.category == "duplicate"
    }

    credit_types = {EntryType.credit, EntryType.reversal, EntryType.recovery}

    for entry in journal.ledger_entries:
        if entry.entry_type not in credit_types:
            continue

        credit_amount = Decimal(str(entry.credit_amount))
        if credit_amount <= ZERO:
            continue

        # Check if this reversal targets an already-excluded duplicate.
        is_duplicate_reversal = False
        m = _REVERSAL_LINE_RE.search(entry.description)
        if m and _DUPLICATE_RE.search(entry.description):
            referenced_line = int(m.group(1)) - 1  # 0-based
            if referenced_line in excluded_duplicate_indices:
                is_duplicate_reversal = True

        if is_duplicate_reversal:
            # Skip: already handled by Stage 2 exclusion.
            continue

        # Apply credit: move from covered to excluded, greedy in source order.
        remaining_credit = credit_amount
        for ls in sorted(lines, key=lambda l: l.source_index):
            if remaining_credit <= ZERO:
                break
            if ls.covered <= ZERO:
                continue

            deduction = min(ls.covered, remaining_credit)
            ls.covered -= deduction
            ls.excluded += deduction
            remaining_credit -= deduction

            detail = (
                f"Journal credit applied: {entry.description} "
                f"(${credit_amount:,.2f}); allocated ${deduction:,.2f} "
                f"to line {ls.source_index + 1} in source order."
            )

            ls.rule_trace.append(RuleTraceStep(
                rule_id="OEP-3.2",
                outcome=Outcome.applied,
                input_amount=float(ls.covered + deduction),
                adjustment_amount=float(deduction),
                output_amount=float(ls.covered),
                detail=detail,
                evidence=[EvidenceItem(root=ls.evidence_anchor())],
            ))

            if ls.covered == ZERO and ls.held == ZERO:
                ls.status = "excluded"
            elif ls.covered < ls.amount and ls.covered > ZERO:
                ls.status = "partially_covered"
