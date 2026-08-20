"""Check 2 — Limit agreement.

The Loss Notice "Selected limit" must agree with the Certificate
"Combined protection limit".  Disagreement is a material conflict.
"""

from __future__ import annotations

from decimal import Decimal

from oep.models.output import (
    ConflictValue,
    EvidenceItem,
    ResolutionStatus,
    SourceConflict,
)
from oep.extraction.schemas import RawCertificate, RawLossNotice
from oep.reconcile._types import CheckResult, DOC_FILENAME


def check_limit_agreement(
    loss_notice: RawLossNotice,
    certificate: RawCertificate,
) -> CheckResult:
    """Return a CheckResult for the limit-agreement reconciliation."""

    conflicts: list[SourceConflict] = []
    warnings: list[str] = []

    ln_limit = loss_notice.selected_limit
    cert_limit = certificate.combined_limit

    if ln_limit is None or cert_limit is None:
        if ln_limit is None:
            warnings.append("Loss Notice selected_limit is missing")
        if cert_limit is None:
            warnings.append("Certificate combined_limit is missing")
        return CheckResult(
            check_id="limit_agreement",
            passed=True,
            conflicts=conflicts,
            warnings=warnings,
        )

    if Decimal(str(ln_limit)) != Decimal(str(cert_limit)):
        conflicts.append(SourceConflict(
            field="selected_limit",
            values=[
                ConflictValue(
                    value=f"${ln_limit:,.2f}",
                    source_document=DOC_FILENAME["loss_notice"],
                    source_page=1,
                    evidence=f"Selected limit ${ln_limit:,.2f}",
                ),
                ConflictValue(
                    value=f"${cert_limit:,.2f}",
                    source_document=DOC_FILENAME["certificate"],
                    source_page=1,
                    evidence=f"Combined protection limit ${cert_limit:,.2f}",
                ),
            ],
            evidence=[
                EvidenceItem(root=f"{DOC_FILENAME['loss_notice']}:page:1"),
                EvidenceItem(root=f"{DOC_FILENAME['certificate']}:page:1"),
            ],
            resolution="Selected limit on Loss Notice disagrees with combined protection limit on Certificate",
            resolution_status=ResolutionStatus.unresolved,
        ))

    return CheckResult(
        check_id="limit_agreement",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )
