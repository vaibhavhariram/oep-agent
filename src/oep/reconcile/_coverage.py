"""Check 5 — Coverage window (OEP-1.2).

Possession return (event_date) must fall within the certificate
period [protection_start, protection_end].  Outside the window is
a hard coverage failure.
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


def check_coverage_window(
    normalized: list[DocumentExtraction],
) -> CheckResult:
    """Return a CheckResult for the coverage-window check."""

    conflicts: list[SourceConflict] = []
    warnings: list[str] = []

    header = normalized[0]
    event_date = parse_date(header.event_date)
    protection_start = parse_date(header.protection_start)
    protection_end = parse_date(header.protection_end)

    if event_date is None:
        warnings.append("event_date (possession return) is missing")
    if protection_start is None or protection_end is None:
        warnings.append("Certificate period dates are missing")

    if event_date and protection_start and protection_end:
        if not (protection_start <= event_date <= protection_end):
            conflicts.append(SourceConflict(
                field="coverage_window",
                values=[
                    ConflictValue(
                        value=event_date.isoformat(),
                        source_document=DOC_FILENAME["loss_notice"],
                        source_page=1,
                        evidence=f"Possession returned {event_date.isoformat()}",
                    ),
                    ConflictValue(
                        value=f"{protection_start.isoformat()} through {protection_end.isoformat()}",
                        source_document=DOC_FILENAME["certificate"],
                        source_page=1,
                        evidence=f"Certificate period {protection_start.isoformat()} through {protection_end.isoformat()}",
                    ),
                ],
                evidence=[
                    EvidenceItem(root=f"{DOC_FILENAME['loss_notice']}:page:1"),
                    EvidenceItem(root=f"{DOC_FILENAME['certificate']}:page:1"),
                ],
                resolution="Possession return date falls outside certificate coverage period (OEP-1.2)",
                resolution_status=ResolutionStatus.unresolved,
            ))

    return CheckResult(
        check_id="coverage_window",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )
