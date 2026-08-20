"""Check 4 — Journal / register alignment.

Every submitted line should have a corresponding charge-type ledger
entry by description and amount.  Matching is greedy in source order:
iterate submitted lines, for each find the first unconsumed charge
entry with matching (description, amount), and mark it consumed.

Non-charge entries (payment, credit, recovery, reversal, adjustment)
are expected in the journal and excluded from matching.

Reports orphans on either side.
"""

from __future__ import annotations

from decimal import Decimal

from oep.models.output import (
    ConflictValue,
    DocumentExtraction,
    EntryType,
    EvidenceItem,
    ResolutionStatus,
    SourceConflict,
)
from oep.reconcile._types import CheckResult, DOC_FILENAME, doc3_filename


def check_journal_register_alignment(
    normalized: list[DocumentExtraction],
    source_register_title: str,
) -> CheckResult:
    """Return a CheckResult for journal/register alignment."""

    doc3_fn = doc3_filename(source_register_title)
    conflicts: list[SourceConflict] = []

    submitted_lines = normalized[2].submitted_lines
    # Only charge-type entries participate in matching.
    charge_entries = [
        e for e in normalized[1].ledger_entries
        if e.entry_type == EntryType.charge
    ]

    consumed = [False] * len(charge_entries)
    unmatched_submitted: list[int] = []

    # Greedy match in source order.
    for sl in submitted_lines:
        sl_key = (sl.description.strip().lower(), Decimal(str(sl.amount)))
        matched = False
        for j, ce in enumerate(charge_entries):
            if consumed[j]:
                continue
            ce_key = (ce.description.strip().lower(), Decimal(str(ce.charge_amount)))
            if sl_key == ce_key:
                consumed[j] = True
                matched = True
                break
        if not matched:
            unmatched_submitted.append(sl.source_index)

    # Orphan submitted lines.
    for idx in unmatched_submitted:
        sl = next(s for s in submitted_lines if s.source_index == idx)
        conflicts.append(SourceConflict(
            field="journal_register_alignment",
            values=[
                ConflictValue(
                    value=f"{sl.description} ${sl.amount:,.2f}",
                    source_document=doc3_fn,
                    source_page=sl.source_page,
                    evidence=sl.evidence,
                ),
                ConflictValue(
                    value="no matching charge entry",
                    source_document=DOC_FILENAME["journal"],
                    source_page=1,
                    evidence="No corresponding journal charge entry found",
                ),
            ],
            evidence=[
                EvidenceItem(root=f"{doc3_fn}:page:{sl.source_page}"),
            ],
            resolution="Submitted line has no corresponding journal charge entry",
            resolution_status=ResolutionStatus.unresolved,
        ))

    # Orphan charge entries.
    for j, ce in enumerate(charge_entries):
        if consumed[j]:
            continue
        conflicts.append(SourceConflict(
            field="journal_register_alignment",
            values=[
                ConflictValue(
                    value=f"{ce.description} ${ce.charge_amount:,.2f}",
                    source_document=DOC_FILENAME["journal"],
                    source_page=ce.source_page,
                    evidence=ce.evidence,
                ),
                ConflictValue(
                    value="no matching submitted line",
                    source_document=doc3_fn,
                    source_page=1,
                    evidence="No corresponding submitted line found",
                ),
            ],
            evidence=[
                EvidenceItem(root=f"{DOC_FILENAME['journal']}:page:{ce.source_page}"),
            ],
            resolution="Journal charge entry has no corresponding submitted line",
            resolution_status=ResolutionStatus.unresolved,
        ))

    return CheckResult(
        check_id="journal_register_alignment",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
    )
