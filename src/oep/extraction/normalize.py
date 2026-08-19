"""Deterministic normalization: raw LLM extraction → output-schema extraction.

The model reads, code normalizes.  This module contains every mapping table,
date conversion, and evidence string builder.  Nothing here calls an LLM.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from oep.models.output import (
    ChecklistItem,
    DocumentExtraction,
    DocumentType,
    DocumentationStatus,
    EntryType,
    EvidenceAssertion,
    LedgerEntry,
    MoneyMention,
    SourceFact,
    SubmittedLine,
)
from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)


# ===================================================================
# §6 — Mapping tables
# ===================================================================

# source_category (verbatim from doc) → source_classification (enum)
CATEGORY_MAP: dict[str, str] = {
    "occupancy balance": "occupancy_balance",
    "premises restoration": "unit_restoration",
    "reletting gap": "reletting_gap",
    "upgrade or elective improvement": "upgrade",
    "fee or service charge": "operator_fee",
}

# record_status (verbatim from doc) → documentation_status (enum)
# Matched case-insensitively on normalized whitespace.
RECORD_STATUS_MAP: dict[str, str] = {
    "no supporting record supplied": "missing",
    "no record supplied": "missing",
    "estimate only — work unfinished": "estimate_only",
    "estimate only \u2014 work unfinished": "estimate_only",
    "estimate supplied": "estimate_only",
    "paid record or executed work order supplied": "sufficient",
    "paid record supplied": "sufficient",
    "executed work order supplied": "sufficient",
    "supported by tenancy journal": "sufficient",
    "record not applicable": "not_applicable",
}


def map_source_classification(
    raw_category: str,
    warnings: list[str],
) -> str:
    """Map a verbatim source_category to a source_classification enum value."""
    key = raw_category.strip().lower()
    mapped = CATEGORY_MAP.get(key)
    if mapped is None:
        warnings.append(
            f"Unknown source_category {raw_category!r} — mapped to 'unclassified'"
        )
        return "unclassified"
    return mapped


def map_documentation_status(
    raw_status: str,
    warnings: list[str],
) -> str:
    """Map a verbatim record_status to a documentation_status enum value."""
    key = " ".join(raw_status.strip().lower().split())
    mapped = RECORD_STATUS_MAP.get(key)
    if mapped is None:
        warnings.append(
            f"Unknown record_status {raw_status!r} — mapped to 'unclear'"
        )
        return "unclear"
    return mapped


# ===================================================================
# §6 — Date handling
# ===================================================================

_DATE_PATTERNS = [
    ("%m/%d/%Y", None),       # 02/04/2027
    ("%Y-%m-%d", None),       # 2027-02-04
    ("%B %d, %Y", None),      # February 04, 2027
]


def parse_date(raw: str | None) -> date | None:
    """Parse a raw date string into a ``date`` object, or None."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt, _ in _DATE_PATTERNS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def date_to_iso(d: date | None) -> str | None:
    """Serialize a date as ISO YYYY-MM-DD, or None."""
    return d.isoformat() if d else None


def date_to_mmddyyyy(d: date | None) -> str | None:
    """Serialize a date as MM/DD/YYYY, or None."""
    return d.strftime("%m/%d/%Y") if d else None


# ===================================================================
# §6 — Evidence string builders
# ===================================================================


def evidence_submitted_line(
    line_number: int,
    description: str,
    amount: float,
) -> str:
    """``Line {n}: {description} — ${amount:,.2f}``"""
    return f"Line {line_number}: {description} \u2014 ${amount:,.2f}"


def evidence_ledger_entry(
    description: str,
    debit: float,
    credit: float,
) -> str:
    """``{description}: debit ${debit:,.2f}, credit ${credit:,.2f}``"""
    return f"{description}: debit ${debit:,.2f}, credit ${credit:,.2f}"


def evidence_limit_mention(label: str, amount: float) -> str:
    """``{label} ${amount:,.2f}``"""
    return f"{label} ${amount:,.2f}"


def evidence_fact(claim_id: str) -> str:
    """``Claim ID {claim_id}``"""
    return f"Claim ID {claim_id}"


# ===================================================================
# §6 — Shared header block
# ===================================================================


def _build_shared_header(
    *,
    claim_id: str | None,
    agreement_id: str | None,
    participant_name: str | None,
    protected_location: str | None,
    policy_form: str | None,
    event_date: date | None,
    statement_date: date | None,
    protection_start: date | None,
    protection_end: date | None,
    claimed_total: float | None,
    ending_balance: float | None,
) -> dict:
    """Return the header fields shared across all four extraction objects."""
    return {
        "claim_id": claim_id,
        "agreement_id": agreement_id,
        "participant_name": participant_name,
        "protected_location": protected_location,
        "policy_form": policy_form,
        "claim_type": "occupancy_exit_protection",
        "event_date": date_to_iso(event_date),
        "statement_date": date_to_iso(statement_date),
        "protection_start": date_to_iso(protection_start),
        "protection_end": date_to_iso(protection_end),
        "claimed_total": claimed_total,
        "ending_balance": ending_balance,
    }


# ===================================================================
# §6 — Reletting gap date/rate parsing from service_life_fact
# ===================================================================

_GAP_PATTERN = re.compile(
    r"Gap:\s*(\S+)\s*[\u2013\u2014-]\s*(\S+)\s+at\s+\$?([\d,.]+)/day"
)


def _parse_gap_facts(service_life_fact: str | None) -> dict:
    """Extract gap start, end, and daily rate from a service_life_fact string."""
    result: dict = {
        "protected_period_start": None,
        "protected_period_end": None,
        "stated_rate": None,
    }
    if not service_life_fact:
        return result
    m = _GAP_PATTERN.search(service_life_fact)
    if m:
        result["protected_period_start"] = date_to_iso(parse_date(m.group(1)))
        result["protected_period_end"] = date_to_iso(parse_date(m.group(2)))
        try:
            result["stated_rate"] = float(m.group(3).replace(",", ""))
        except ValueError:
            pass
    return result


# ===================================================================
# §6 — Component service-life parsing from service_life_fact
# ===================================================================

_SERVICE_START_PATTERN = re.compile(
    r"Service start:\s*(\S+)"
)


def _parse_service_facts(service_life_fact: str | None) -> dict:
    """Extract first_use_date from a service_life_fact mentioning service start."""
    result: dict = {"first_use_date": None, "useful_life_months": None, "life_used_months": None}
    if not service_life_fact:
        return result
    m = _SERVICE_START_PATTERN.search(service_life_fact)
    if m:
        result["first_use_date"] = date_to_iso(parse_date(m.group(1)))
    return result


# ===================================================================
# Per-document normalization
# ===================================================================


def normalize_loss_notice(
    raw: RawLossNotice,
    header: dict,
) -> DocumentExtraction:
    """Normalize a raw Loss Notice extraction."""
    warnings: list[str] = list(raw.warnings)

    limit_mentions: list[MoneyMention] = []
    if raw.selected_limit is not None:
        limit_mentions.append(MoneyMention(
            label="Combined protection limit",
            amount=raw.selected_limit,
            evidence=evidence_limit_mention("Combined protection limit", raw.selected_limit),
            source_page=1,
        ))

    facts = [SourceFact(
        field="claim_id",
        value=header["claim_id"] or "",
        evidence=evidence_fact(header["claim_id"] or ""),
        source_page=1,
    )]

    return DocumentExtraction(
        document_type=DocumentType.loss_notice_and_record_index,
        **header,
        facts=facts,
        limit_mentions=limit_mentions,
        submitted_lines=[],
        ledger_entries=[],
        checklist_items=[],
        evidence_assertions=[],
        warnings=warnings,
    )


def normalize_financial_journal(
    raw: RawFinancialJournal,
    header: dict,
) -> DocumentExtraction:
    """Normalize a raw Financial Journal extraction."""
    warnings: list[str] = list(raw.warnings)

    entries: list[LedgerEntry] = []
    for e in raw.ledger_entries:
        # Determine entry_type from debit/credit.
        if e.credit_amount > 0 and e.debit_amount == 0:
            entry_type = EntryType.credit
        elif e.debit_amount < 0:
            entry_type = EntryType.reversal
        else:
            entry_type = EntryType.charge

        entries.append(LedgerEntry(
            entry_date=e.entry_date,
            description=e.description,
            charge_amount=e.debit_amount,
            credit_amount=e.credit_amount,
            running_balance=e.running_balance,
            entry_type=entry_type,
            evidence=evidence_ledger_entry(e.description, e.debit_amount, e.credit_amount),
            source_page=e.source_page,
        ))

    facts = [SourceFact(
        field="claim_id",
        value=header["claim_id"] or "",
        evidence=evidence_fact(header["claim_id"] or ""),
        source_page=1,
    )]

    return DocumentExtraction(
        document_type=DocumentType.tenancy_financial_journal,
        **header,
        facts=facts,
        limit_mentions=[],
        submitted_lines=[],
        ledger_entries=entries,
        checklist_items=[],
        evidence_assertions=[],
        warnings=warnings,
    )


def normalize_source_register(
    raw: RawSourceRegister,
    header: dict,
) -> DocumentExtraction:
    """Normalize a raw Source Register (Cost Register or Condition Log)."""
    warnings: list[str] = list(raw.warnings)

    # Build a lookup from line_number → record register entry.
    register_by_line = {r.line_number: r for r in raw.source_record_register}

    doc_type = (
        DocumentType.premises_condition_log
        if "condition log" in (raw.document_title or "").lower()
        else DocumentType.restoration_cost_register
    )

    submitted: list[SubmittedLine] = []
    for sl in raw.presented_source_lines:
        reg = register_by_line.get(sl.line_number)

        # Map category and documentation status.
        classification = map_source_classification(sl.source_category, warnings)
        doc_status = (
            map_documentation_status(reg.record_status, warnings)
            if reg else "unclear"
        )

        # Reference: null if "None stated" or absent.
        reference = None
        if reg and reg.record_reference:
            reference = reg.record_reference

        # Parse gap or service-life facts.
        service_fact = reg.service_life_fact if reg else None
        gap = _parse_gap_facts(service_fact)
        svc = _parse_service_facts(service_fact)

        submitted.append(SubmittedLine(
            source_index=sl.line_number - 1,  # 0-based
            source_page=sl.source_page,
            amount=sl.gross_amount,
            description=sl.description,
            category_hint=sl.source_category,
            source_classification=classification,
            documentation_status=doc_status,
            reference=reference,
            evidence=evidence_submitted_line(sl.line_number, sl.description, sl.gross_amount),
            first_use_date=svc["first_use_date"] or gap.get("first_use_date"),
            useful_life_months=svc["useful_life_months"],
            life_used_months=svc["life_used_months"],
            protected_period_start=gap["protected_period_start"],
            protected_period_end=gap["protected_period_end"],
            stated_rate=gap["stated_rate"],
            adjustments=[],
        ))

    facts = [SourceFact(
        field="claim_id",
        value=header["claim_id"] or "",
        evidence=evidence_fact(header["claim_id"] or ""),
        source_page=1,
    )]

    return DocumentExtraction(
        document_type=doc_type,
        **header,
        facts=facts,
        limit_mentions=[],
        submitted_lines=submitted,
        ledger_entries=[],
        checklist_items=[],
        evidence_assertions=[],
        warnings=warnings,
    )


def normalize_certificate(
    raw: RawCertificate,
    header: dict,
) -> DocumentExtraction:
    """Normalize a raw Certificate extraction."""
    warnings: list[str] = list(raw.warnings)

    limit_mentions: list[MoneyMention] = []
    if raw.combined_limit is not None:
        limit_mentions.append(MoneyMention(
            label="Combined protection limit",
            amount=raw.combined_limit,
            evidence=evidence_limit_mention("Combined protection limit", raw.combined_limit),
            source_page=1,
        ))

    facts = [SourceFact(
        field="claim_id",
        value=header["claim_id"] or "",
        evidence=evidence_fact(header["claim_id"] or ""),
        source_page=1,
    )]

    return DocumentExtraction(
        document_type=DocumentType.covered_tenancy_certificate,
        **header,
        facts=facts,
        limit_mentions=limit_mentions,
        submitted_lines=[],
        ledger_entries=[],
        checklist_items=[],
        evidence_assertions=[],
        warnings=warnings,
    )


# ===================================================================
# Top-level: assemble all four normalized extractions
# ===================================================================


def build_shared_header(
    loss_notice: RawLossNotice,
    journal: RawFinancialJournal,
    certificate: RawCertificate,
) -> dict:
    """Derive the shared header block from cross-document fields.

    Field derivations (§6):
      - event_date ← Loss Notice "Possession returned"
      - statement_date ← Loss Notice "Closeout statement date" (= statement_date)
      - protection_start / protection_end ← Certificate certificate_period_raw
      - claimed_total ← Loss Notice total_presented
      - ending_balance ← final running_balance in journal
      - protected_location built from Loss Notice fields
    """
    # Parse dates.
    event_date = parse_date(loss_notice.possession_returned)
    statement_date = parse_date(loss_notice.statement_date)

    # Split certificate period.
    protection_start: date | None = None
    protection_end: date | None = None
    if certificate.certificate_period_raw:
        parts = certificate.certificate_period_raw.split("through")
        if len(parts) == 2:
            protection_start = parse_date(parts[0].strip())
            protection_end = parse_date(parts[1].strip())

    # Ending balance from journal.
    ending_balance: float | None = None
    if journal.ledger_entries:
        ending_balance = journal.ledger_entries[-1].running_balance

    # Protected location — use Loss Notice value, append unit if separate.
    protected_location = loss_notice.protected_location
    if protected_location and loss_notice.unit:
        # If unit is not already in the address, append it.
        if loss_notice.unit not in protected_location:
            protected_location = f"{protected_location} \u00b7 Unit {loss_notice.unit}"

    return _build_shared_header(
        claim_id=loss_notice.claim_id,
        agreement_id=loss_notice.agreement_id or certificate.agreement_id,
        participant_name=loss_notice.participant_name or certificate.participant_name,
        protected_location=protected_location or certificate.protected_location,
        policy_form=loss_notice.policy_form or certificate.policy_form,
        event_date=event_date,
        statement_date=statement_date,
        protection_start=protection_start,
        protection_end=protection_end,
        claimed_total=loss_notice.total_presented,
        ending_balance=ending_balance,
    )


def normalize_all(
    loss_notice: RawLossNotice,
    journal: RawFinancialJournal,
    source_register: RawSourceRegister,
    certificate: RawCertificate,
) -> list[DocumentExtraction]:
    """Normalize all four raw extractions into schema-compliant objects.

    Returns a list of four ``DocumentExtraction`` objects in document order.
    """
    header = build_shared_header(loss_notice, journal, certificate)

    return [
        normalize_loss_notice(loss_notice, header),
        normalize_financial_journal(journal, header),
        normalize_source_register(source_register, header),
        normalize_certificate(certificate, header),
    ]
