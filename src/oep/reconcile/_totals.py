"""Check 3 — Totals chain.

Three separate comparisons (all via Decimal):
  3a. sum(submitted_lines.amount) == claimed_total       [gross vs gross]
  3b. sum(charges) - sum(credits) == ending_balance      [journal internal]
  3c. sum(charges) == sum(submitted_lines.amount)        [register vs journal]

Reports which specific comparison failed.
"""

from __future__ import annotations

from decimal import Decimal

from oep.models.output import (
    ConflictValue,
    DocumentExtraction,
    EvidenceItem,
    ResolutionStatus,
    SourceConflict,
)
from oep.extraction.schemas import RawFinancialJournal, RawLossNotice
from oep.reconcile._types import CheckResult, DOC_FILENAME, doc3_filename

_ZERO = Decimal("0")


def check_totals_chain(
    loss_notice: RawLossNotice,
    journal: RawFinancialJournal,
    normalized: list[DocumentExtraction],
    source_register_title: str,
) -> CheckResult:
    """Return a CheckResult for the totals-chain reconciliation."""

    doc3_fn = doc3_filename(source_register_title)
    conflicts: list[SourceConflict] = []
    warnings: list[str] = []

    # --- Gather amounts ---

    # Sum of submitted line amounts (from normalised source register).
    sum_submitted = sum(
        (Decimal(str(sl.amount)) for sl in normalized[2].submitted_lines),
        _ZERO,
    )

    # Claimed total (Loss Notice gross total).
    claimed_total: Decimal | None = None
    if loss_notice.total_presented is not None:
        claimed_total = Decimal(str(loss_notice.total_presented))

    # Journal charge / credit sums + ending balance.
    sum_charges = _ZERO
    sum_credits = _ZERO
    for entry in normalized[1].ledger_entries:
        sum_charges += Decimal(str(entry.charge_amount))
        sum_credits += Decimal(str(entry.credit_amount))

    ending_balance: Decimal | None = None
    if journal.ledger_entries:
        ending_balance = Decimal(str(journal.ledger_entries[-1].running_balance))

    # --- 3a: gross vs gross ---
    if claimed_total is not None and sum_submitted != claimed_total:
        conflicts.append(SourceConflict(
            field="totals_chain_3a",
            values=[
                ConflictValue(
                    value=f"${sum_submitted:,.2f}",
                    source_document=doc3_fn,
                    source_page=1,
                    evidence=f"sum(submitted_lines) = ${sum_submitted:,.2f}",
                ),
                ConflictValue(
                    value=f"${claimed_total:,.2f}",
                    source_document=DOC_FILENAME["loss_notice"],
                    source_page=1,
                    evidence=f"claimed_total = ${claimed_total:,.2f}",
                ),
            ],
            evidence=[
                EvidenceItem(root=f"{doc3_fn}:page:1"),
                EvidenceItem(root=f"{DOC_FILENAME['loss_notice']}:page:1"),
            ],
            resolution="sum(submitted_lines) != claimed_total",
            resolution_status=ResolutionStatus.unresolved,
        ))

    # --- 3b: journal internal (charges - credits == ending balance) ---
    if ending_balance is not None:
        net = sum_charges - sum_credits
        if net != ending_balance:
            conflicts.append(SourceConflict(
                field="totals_chain_3b",
                values=[
                    ConflictValue(
                        value=f"${net:,.2f}",
                        source_document=DOC_FILENAME["journal"],
                        source_page=1,
                        evidence=f"sum(charges) - sum(credits) = ${net:,.2f}",
                    ),
                    ConflictValue(
                        value=f"${ending_balance:,.2f}",
                        source_document=DOC_FILENAME["journal"],
                        source_page=1,
                        evidence=f"ending_balance = ${ending_balance:,.2f}",
                    ),
                ],
                evidence=[
                    EvidenceItem(root=f"{DOC_FILENAME['journal']}:page:1"),
                ],
                resolution="sum(charges) - sum(credits) != ending_balance",
                resolution_status=ResolutionStatus.unresolved,
            ))

    # --- 3c: register vs journal (charge total == submitted total) ---
    if sum_charges != sum_submitted:
        conflicts.append(SourceConflict(
            field="totals_chain_3c",
            values=[
                ConflictValue(
                    value=f"${sum_charges:,.2f}",
                    source_document=DOC_FILENAME["journal"],
                    source_page=1,
                    evidence=f"sum(charge_entries) = ${sum_charges:,.2f}",
                ),
                ConflictValue(
                    value=f"${sum_submitted:,.2f}",
                    source_document=doc3_fn,
                    source_page=1,
                    evidence=f"sum(submitted_lines) = ${sum_submitted:,.2f}",
                ),
            ],
            evidence=[
                EvidenceItem(root=f"{DOC_FILENAME['journal']}:page:1"),
                EvidenceItem(root=f"{doc3_fn}:page:1"),
            ],
            resolution="sum(charge_entries) != sum(submitted_lines)",
            resolution_status=ResolutionStatus.unresolved,
        ))

    return CheckResult(
        check_id="totals_chain",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )
