"""Check 1 — Identifier chain.

Compare claim_id, agreement_id, participant_name, protected_location,
and policy_form across all documents that state the field.  The
certificate has no claim_id; that absence is expected, not a conflict.
"""

from __future__ import annotations

from oep.models.output import (
    ConflictValue,
    EvidenceItem,
    ResolutionStatus,
    SourceConflict,
)
from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.reconcile._types import CheckResult, DOC_FILENAME, doc3_filename


def _norm(val: str) -> str:
    """Normalise a string for comparison: strip + lowercase."""
    return " ".join(val.strip().lower().split())


def check_identifier_chain(
    loss_notice: RawLossNotice,
    journal: RawFinancialJournal,
    source_register: RawSourceRegister,
    certificate: RawCertificate,
) -> CheckResult:
    """Return a CheckResult for the identifier-chain reconciliation."""

    doc3_fn = doc3_filename(source_register.document_title)

    # (field_name, list of (raw_value, doc_filename, source_page) )
    field_sources: list[tuple[str, list[tuple[str | None, str, int]]]] = [
        (
            "claim_id",
            [
                (loss_notice.claim_id, DOC_FILENAME["loss_notice"], 1),
                (journal.claim_id, DOC_FILENAME["journal"], 1),
                (source_register.claim_id, doc3_fn, 1),
                # Certificate has no claim_id — intentionally omitted.
            ],
        ),
        (
            "agreement_id",
            [
                (loss_notice.agreement_id, DOC_FILENAME["loss_notice"], 1),
                (journal.agreement_id, DOC_FILENAME["journal"], 1),
                (source_register.agreement_id, doc3_fn, 1),
                (certificate.agreement_id, DOC_FILENAME["certificate"], 1),
            ],
        ),
        (
            "participant_name",
            [
                (loss_notice.participant_name, DOC_FILENAME["loss_notice"], 1),
                (journal.participant_name, DOC_FILENAME["journal"], 1),
                (source_register.participant_name, doc3_fn, 1),
                (certificate.participant_name, DOC_FILENAME["certificate"], 1),
            ],
        ),
        (
            "protected_location",
            [
                (loss_notice.protected_location, DOC_FILENAME["loss_notice"], 1),
                (source_register.protected_location, doc3_fn, 1),
                (certificate.protected_location, DOC_FILENAME["certificate"], 1),
            ],
        ),
        (
            "policy_form",
            [
                (loss_notice.policy_form, DOC_FILENAME["loss_notice"], 1),
                (source_register.policy_form, doc3_fn, 1),
                (certificate.policy_form, DOC_FILENAME["certificate"], 1),
            ],
        ),
    ]

    conflicts: list[SourceConflict] = []
    warnings: list[str] = []

    for field_name, sources in field_sources:
        # Keep only non-None entries.
        present = [
            (val, doc_fn, page)
            for val, doc_fn, page in sources
            if val is not None
        ]
        if len(present) < 2:
            continue

        # Group by normalised value.
        groups: dict[str, list[tuple[str, str, int]]] = {}
        for val, doc_fn, page in present:
            key = _norm(val)
            groups.setdefault(key, []).append((val, doc_fn, page))

        if len(groups) <= 1:
            continue

        # Build a SourceConflict with one ConflictValue per distinct value.
        values: list[ConflictValue] = []
        evidence_items: list[EvidenceItem] = []
        for entries in groups.values():
            for val, doc_fn, page in entries:
                values.append(ConflictValue(
                    value=val,
                    source_document=doc_fn,
                    source_page=page,
                    evidence=f"{field_name}={val!r} in {doc_fn}",
                ))
                evidence_items.append(
                    EvidenceItem(root=f"{doc_fn}:page:{page}"),
                )

        conflicts.append(SourceConflict(
            field=field_name,
            values=values,
            evidence=evidence_items,
            resolution="Cross-document disagreement",
            resolution_status=ResolutionStatus.unresolved,
        ))

    return CheckResult(
        check_id="identifier_chain",
        passed=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )
