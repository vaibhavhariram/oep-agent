"""Stage 1 — Classification (OEP-3.1).

Classification is already performed by the normalization layer via CATEGORY_MAP.
This stage is a no-op; the final "applied" trace step for passing lines is
appended in __init__.py after all stages complete.
"""

from __future__ import annotations

from oep.rules._types import LineState


def run_stage1(lines: list[LineState]) -> None:
    """Verify classification is present. No mutations."""
    for ls in lines:
        if not ls.category:
            ls.status = "needs_review"
            ls.rationale = "Unclassified source line."
