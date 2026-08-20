"""Check 6 — Notice deadline (OEP-5.1).

statement_date minus event_date (possession return) must be <= 105 days.
"""

from __future__ import annotations

from oep.models.output import (
    ConflictValue,
    DocumentExtraction,
    EvidenceItem,
    ResolutionStatus,
    SourceConflict,
)
from oep.extraction.normalize import parse_date
from oep.reconcile._types import CheckResult, DOC_FILENAME


def check_notice_deadline(
    normalized: list[DocumentExtraction],
) -> CheckResult:
    """Return a CheckResult for the notice-deadline check."""

    conflicts: list[SourceConflict] = []
    warnings: list[str] = []

    header = normalized[0]
    statement_date = parse_date(header.statement_date)
    event_date = parse_date(header.event_date)

    if statement_date is None:
        warnings.append("statement_date is missing")
    if event_date is None:
        warnings.append("event_date (possession return) is missing")

    if statement_date and event_date:
        gap_days = (statement_date - event_date).days
        if gap_days > 105:
            conflicts.append(SourceConflict(
                field="notice_deadline",
                values=[
                    ConflictValue(
                        value=statement_date.isoformat(),
                        source_document=DOC_FILENAME["loss_notice"],
                        source_page=1,
                        evidence=f"Statement date {statement_date.isoformat()}",
                    ),
                    ConflictValue(
                        value=event_date.isoformat(),
                        source_document=DOC_FILENAME["loss_notice"],
                        source_page=1,
                        evidence=f"Possession returned {event_date.isoformat()}",
                    ),
                ],
                evidence=[
                    EvidenceItem(root=f"{DOC_FILENAME['loss_notice']}:page:1"),
                ],
                resolution=f"Statement date is {gap_days} days after possession return, exceeding 105-day notice deadline (OEP-5.1)",
                resolution_status=ResolutionStatus.unresolved,
            ))

    return CheckResult(
        check_id="notice_deadline",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )
