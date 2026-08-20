"""Reconciliation module — cross-document fact comparison.

Public API:
    reconcile_all(...)  → ReconciliationResult
"""

from __future__ import annotations

from oep.models.output import DocumentExtraction
from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.reconcile._types import CheckResult, ReconciliationResult
from oep.reconcile._identity import check_identifier_chain
from oep.reconcile._limits import check_limit_agreement
from oep.reconcile._totals import check_totals_chain
from oep.reconcile._alignment import check_journal_register_alignment
from oep.reconcile._coverage import check_coverage_window
from oep.reconcile._notice import check_notice_deadline

__all__ = [
    "reconcile_all",
    "CheckResult",
    "ReconciliationResult",
]


def reconcile_all(
    *,
    loss_notice: RawLossNotice,
    journal: RawFinancialJournal,
    source_register: RawSourceRegister,
    certificate: RawCertificate,
    normalized: list[DocumentExtraction],
) -> ReconciliationResult:
    """Run all reconciliation checks and return a structured result."""

    checks = [
        check_identifier_chain(loss_notice, journal, source_register, certificate),
        check_limit_agreement(loss_notice, certificate),
        check_totals_chain(
            loss_notice, journal, normalized,
            source_register_title=source_register.document_title,
        ),
        check_journal_register_alignment(
            normalized,
            source_register_title=source_register.document_title,
        ),
        check_coverage_window(normalized),
        check_notice_deadline(normalized),
    ]

    all_conflicts = []
    all_warnings = []
    for c in checks:
        all_conflicts.extend(c.conflicts)
        all_warnings.extend(c.warnings)

    return ReconciliationResult(
        checks=checks,
        all_conflicts=all_conflicts,
        warnings=all_warnings,
    )
