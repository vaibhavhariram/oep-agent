"""Stage 7 — Sum and cap (OEP-2.4).

approved_total = min(covered_total, policy_limit).
Allocate the cap GREEDILY across lines in source_index order.
"""

from __future__ import annotations

from decimal import Decimal

from oep.rules._types import ZERO, LineState


def run_stage7(lines: list[LineState], *, policy_limit: Decimal) -> None:
    """Apply policy limit cap with greedy allocation in source order."""
    covered_total = sum((ls.covered for ls in lines), ZERO)
    approved_total = min(covered_total, policy_limit)

    remaining = approved_total
    for ls in sorted(lines, key=lambda l: l.source_index):
        if remaining <= ZERO or ls.covered <= ZERO:
            ls.approved = ZERO
            continue
        ls.approved = min(ls.covered, remaining)
        remaining -= ls.approved
