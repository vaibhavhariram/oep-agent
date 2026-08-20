"""Stage 3 — Evidence holds (OEP-3.3 / OEP-3.4).

Hold lines that lack required evidence. Specialized cleaning lines require
premises condition evidence per the Loss Notice record index.
"""

from __future__ import annotations

from oep.models.output import EvidenceItem, Outcome, RuleTraceStep
from oep.extraction.schemas import RawLossNotice
from oep.rules._types import ZERO, LineState


def _has_condition_evidence(loss_notice: RawLossNotice) -> bool:
    """Check whether the Loss Notice record index includes premises condition evidence.

    The authoritative source is the record_index on the Loss Notice.
    Match the row whose registered_record refers to premises condition
    evidence, and read its packet_status.
    """
    for entry in loss_notice.record_index:
        if "premises condition" in entry.registered_record.lower():
            status = entry.packet_status.strip().lower()
            return status == "included"
    # No row found → evidence not mentioned → treat as not included.
    return False


def run_stage3(
    lines: list[LineState],
    *,
    loss_notice: RawLossNotice,
) -> None:
    """Hold lines lacking required evidence."""
    condition_evidence = _has_condition_evidence(loss_notice)

    for ls in lines:
        # Skip lines already excluded in Stage 2.
        if ls.status == "excluded":
            continue

        hold = False
        detail = ""
        rule_id = "OEP-3.4"

        if ls.documentation_status == "missing":
            hold = True
            detail = "No completed-work record is supplied."
        elif ls.documentation_status == "estimate_only":
            hold = True
            detail = "Only an unperformed estimate is supplied."
        elif ls.documentation_status == "unclear":
            hold = True
            detail = "Record status is unclear."
        elif ls.documentation_status == "sufficient":
            # Specialized cleaning needs premises condition evidence.
            if (
                ls.component is not None
                and ls.component.strip().lower() == "specialized cleaning"
                and not condition_evidence
            ):
                hold = True
                detail = "No premises condition record supports the specialized need."
        # not_applicable → skip (already excluded by category in Stage 2)

        if not hold:
            continue

        ls.held = ls.covered
        ls.covered = ZERO
        ls.status = "needs_review"
        ls.rationale = detail

        ls.rule_trace.append(RuleTraceStep(
            rule_id=rule_id,
            outcome=Outcome.held,
            input_amount=float(ls.amount),
            adjustment_amount=float(ls.amount),
            output_amount=0.0,
            detail=detail,
            evidence=[EvidenceItem(root=ls.evidence_anchor())],
        ))
