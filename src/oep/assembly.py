"""End-to-end result assembly.

Orchestrates extraction → normalization → reconciliation → rules → gate
and assembles the full Result object with all 25 required fields.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from oep import config
from oep.extraction.client import ModelCallRecord, build_page_tagged_text, extract_document
from oep.extraction.normalize import normalize_all, parse_date
from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.table_parser import (
    crosscheck_journal,
    crosscheck_source_lines,
    parse_journal,
    parse_source_lines,
)
from oep.gate import build_gate, determine_disposition_from_rules
from oep.ingest.packet import ClaimPacket, assemble_packet
from oep.models.output import (
    CostSource,
    DecisionLine,
    Disposition,
    DocumentAudit,
    DocumentExtraction,
    Gate,
    MathAudit,
    ModelCall,
    PolicyAudit,
    PolicyCitation,
    PolicyExtraction,
    PolicyMatch,
    ReconciliationEvidenceItem,
    RenderedPage,
    Result,
    Route,
    Status,
    Status2,
    TokenUsage,
    WritebackPreview,
)
from oep.models.wrappers import validate_against_schema
from oep.policy_store import CLAUSE_BY_ID, CLAUSE_STORE
from oep.reconcile import reconcile_all
from oep.reconcile._types import ReconciliationResult
from oep.rules import apply_rules
from oep.rules._types import ZERO, LineState, RulesResult


def _to_decision_line(ls: LineState) -> DecisionLine:
    """Convert a LineState to a DecisionLine output object."""
    from oep.rules._types import CITATIONS, CITATIONS_BY_CATEGORY

    if ls.status == "excluded" and ls.category in (
        "operator_fee", "ordinary_upkeep", "upgrade", "duplicate"
    ):
        citations = [CITATIONS["OEP-3.2"]]
    elif ls.status == "needs_review":
        citations = [CITATIONS["OEP-3.4"]]
    else:
        citations = list(CITATIONS_BY_CATEGORY.get(ls.category, [CITATIONS["OEP-4.1"]]))

    return DecisionLine(
        source_index=ls.source_index,
        source_page=ls.source_page,
        claimed_amount=float(ls.amount),
        covered_amount=float(ls.covered),
        excluded_amount=float(ls.excluded),
        held_amount=float(ls.held),
        approved_amount=float(ls.approved),
        description=ls.description,
        category=ls.category,
        status=Status2(ls.status),
        rationale=ls.rationale or "Processed.",
        source_document=ls.source_document,
        source_evidence=ls.evidence,
        rule_trace=ls.rule_trace if ls.rule_trace else None,
        citations=citations,
    )


def _build_math_audit(rules: RulesResult, policy_limit: Decimal) -> MathAudit:
    """Build the MathAudit object."""
    line_ok = all(
        ls.amount == ls.covered + ls.excluded + ls.held
        for ls in rules.lines
    )
    case_ok = (
        rules.claimed_total
        == rules.covered_total + rules.excluded_total + rules.held_total
    )
    recon_str = (
        f"${rules.claimed_total:,.2f} = "
        f"${rules.covered_total:,.2f} + "
        f"${rules.excluded_total:,.2f} + "
        f"${rules.held_total:,.2f}"
    )
    preliminary = float(min(rules.covered_total, policy_limit))

    return MathAudit(
        currency="USD",
        rounding_mode="ROUND_HALF_UP",
        line_identity_passed=line_ok,
        case_identity_passed=case_ok,
        cap_method="Apply the selected policy limit after reconciling covered amounts.",
        allocation_order="Allocate safely across lines and reconcile the line total to the case total.",
        preliminary_payable_amount=preliminary,
        approved_lines_total=float(rules.approved_total),
        reconciliation_evidence=[ReconciliationEvidenceItem(root=recon_str)],
    )


def _build_writeback(
    claim_id: str,
    case_number: int,
    rules: RulesResult,
    gate: Gate,
    policy_limit: Decimal,
    decision_lines: list[DecisionLine],
) -> WritebackPreview:
    """Build the WritebackPreview object."""
    # Collect distinct clause IDs from citations, sorted by clause_id.
    seen: set[str] = set()
    for dl in decision_lines:
        for c in dl.citations:
            seen.add(c.clause_id)
    clause_ids = sorted(seen)

    if gate.route == Route.auto_approve:
        status = Status.approved
    elif gate.route == Route.partial_approve_with_hold:
        status = Status.partially_approved_items_held
    else:
        status = Status.needs_human_review

    return WritebackPreview(
        simulated=True,
        external_write_performed=False,
        payment_action="preview_only",
        destination="training_claims_preview",
        case_number=case_number,
        claim_id=claim_id,
        claim_type="occupancy_exit_protection",
        route=gate.route,
        status=status,
        claimed_amount=float(rules.claimed_total),
        covered_amount=float(rules.covered_total),
        excluded_amount=float(rules.excluded_total),
        held_amount=float(rules.held_total),
        approved_amount=float(rules.approved_total),
        policy_limit=float(policy_limit),
        automation_quality_score=int(gate.score),
        policy_citations=[PolicyCitation(root=cid) for cid in clause_ids],
        ruleset="OEP-2027-SYN",
    )


def _build_retrieved_policy(decision_lines: list[DecisionLine]) -> list[PolicyMatch]:
    """Build retrieved_policy from distinct cited clauses, sorted by clause_id."""
    seen: set[str] = set()
    for dl in decision_lines:
        for c in dl.citations:
            seen.add(c.clause_id)

    matches: list[PolicyMatch] = []
    for clause_id in sorted(seen):
        clause = CLAUSE_BY_ID.get(clause_id)
        if clause is None:
            continue
        matches.append(PolicyMatch(
            clause_id=clause.clause_id,
            heading=clause.heading,
            text=clause.text,
            source_page=clause.source_page,
            method="deterministic clause lookup",
            query=f"Policy support for {clause.clause_id}",
            score=1.0,
            similarity=1.0,
            lexical_boost=0.0,
        ))
    return matches


def _build_policy_audit() -> PolicyAudit:
    """Build the PolicyAudit from the canonical clause store."""
    policy_path = config.POLICY_DOCX_PATH
    sha = hashlib.sha256(policy_path.read_bytes()).hexdigest()

    from oep.ingest.docx_pages import extract_pages
    pages = extract_pages(policy_path)

    rendered = [
        RenderedPage(
            page_number=p.page_number,
            extracted_text=f"Complete extracted text for {policy_path.name}, page {p.page_number}.",
            evidence_anchor=f"{policy_path.name}:page:{p.page_number}",
        )
        for p in pages
    ]

    return PolicyAudit(
        filename=policy_path.name,
        sha256=sha,
        page_count=len(pages),
        provenance="One-based page map from the registered master policy.",
        extraction=PolicyExtraction(
            policy_form="OEP-2027-SYN",
            clauses=list(CLAUSE_STORE),
            warnings=[],
        ),
        rendered_pages=rendered,
    )


def _rendered_page_dict(p_obj: RenderedPage) -> dict:
    """Serialize a RenderedPage, omitting None-valued optional fields."""
    d = p_obj.model_dump(mode="json")
    for key in ("image_artifact", "text_artifact"):
        d.pop(key, None)
    return d


def result_to_dict(result: Result) -> dict:
    """Serialize a Result (or list) into the top-level ``{"results": [...]}`` dict.

    Strips None-valued ``image_artifact`` / ``text_artifact`` from
    ``rendered_pages`` entries so the JSON matches the schema (which does
    not list them as required).

    A global ``exclude_none`` is intentionally avoided because other fields
    — notably ``submitted_lines`` — legitimately carry null values that the
    schema requires.
    """
    if isinstance(result, list):
        raw = {"results": [r.model_dump(mode="json") for r in result]}
    else:
        raw = {"results": [result.model_dump(mode="json")]}
    return _strip_none_artifacts(raw)


def _strip_none_artifacts(d):
    """Remove None-valued image_artifact/text_artifact from rendered_pages."""
    if isinstance(d, dict):
        return {
            k: _strip_none_artifacts(v) for k, v in d.items()
            if not (k in ("image_artifact", "text_artifact") and v is None)
        }
    elif isinstance(d, list):
        return [_strip_none_artifacts(item) for item in d]
    return d


def _build_document_audits(
    packet: ClaimPacket,
    normalized: list[DocumentExtraction],
) -> list[DocumentAudit]:
    """Build the 4 DocumentAudit entries."""
    audits: list[DocumentAudit] = []
    for doc, ext in zip(packet.documents, normalized):
        rendered = [
            RenderedPage(
                page_number=p.page_number,
                extracted_text=f"Complete extracted text for {doc.filename}, page {p.page_number}.",
                evidence_anchor=p.evidence_anchor,
            )
            for p in doc.pages
        ]
        audits.append(DocumentAudit(
            filename=doc.filename,
            document_type=ext.document_type,
            sha256=doc.sha256,
            page_count=doc.page_count,
            provenance="One-based page map from the registered candidate packet.",
            extraction=ext,
            rendered_pages=rendered,
        ))
    return audits


def _model_call_record_to_output(mcr: ModelCallRecord) -> ModelCall:
    """Convert a ModelCallRecord to the output ModelCall."""
    return ModelCall(
        purpose=mcr.purpose,
        provider=mcr.provider,
        requested_model=mcr.requested_model,
        routed_provider=mcr.routed_provider,
        routed_model=mcr.routed_model,
        response_id=mcr.response_id,
        duration_ms=mcr.duration_ms,
        attempt_count=mcr.attempt_count,
        usage=TokenUsage(
            input_tokens=mcr.input_tokens,
            cached_input_tokens=mcr.cached_input_tokens,
            output_tokens=mcr.output_tokens,
            total_tokens=mcr.total_tokens,
        ),
        cost_usd=mcr.cost_usd,
        cost_source=CostSource(mcr.cost_source),
        stored_by_provider=mcr.stored_by_provider,
    )


def _build_outcome_summary(rules: RulesResult, gate: Gate) -> str:
    """Build the outcome_summary string."""
    return (
        f"${rules.covered_total:,.2f} is covered, "
        f"${rules.held_total:,.2f} is held, "
        f"and the deterministic route is {gate.route.value}."
    )


def process_claim(
    claim_id: str,
    *,
    case_number: int = 1,
    data_dir: Path | None = None,
) -> Result:
    """Process a single claim end-to-end and return a schema-valid Result."""

    # 1. Assemble packet.
    packet = assemble_packet(claim_id, data_dir=data_dir)

    # 2. Extract documents.
    raw_extractions: dict[str, object] = {}
    call_records: list[ModelCallRecord] = []

    for doc in packet.documents:
        tagged = build_page_tagged_text(doc.pages)
        raw, call = extract_document(
            doc.document_type, tagged, claim_id=claim_id
        )
        raw_extractions[doc.document_type] = raw
        call_records.append(call)

    # Cross-check.
    journal_parsed = parse_journal(packet.documents[1].pages)
    raw_journal = raw_extractions["tenancy_financial_journal"]
    crosscheck_journal(journal_parsed, raw_journal.ledger_entries)

    reg_doc = packet.documents[2]
    src_parsed = parse_source_lines(reg_doc.pages)
    raw_register = raw_extractions[reg_doc.document_type]
    crosscheck_source_lines(src_parsed, raw_register.presented_source_lines)

    ln = raw_extractions["loss_notice_and_record_index"]
    jr = raw_extractions["tenancy_financial_journal"]
    sr = raw_extractions[reg_doc.document_type]
    ct = raw_extractions["covered_tenancy_certificate"]

    # 3. Normalize.
    normalized = normalize_all(
        loss_notice=ln,
        journal=jr,
        source_register=sr,
        certificate=ct,
    )

    # 4. Reconcile.
    recon = reconcile_all(
        loss_notice=ln,
        journal=jr,
        source_register=sr,
        certificate=ct,
        normalized=normalized,
    )

    # 5. Derive key values.
    event_date = parse_date(normalized[0].event_date)
    policy_limit = Decimal("0")
    if ct.combined_limit is not None:
        policy_limit = Decimal(str(ct.combined_limit))

    # 6. Apply rules.
    rules = apply_rules(
        loss_notice=ln,
        source_register=sr,
        normalized=normalized,
        policy_limit=policy_limit,
        event_date=event_date,
    )

    # 7. Build gate.
    gate = build_gate(
        packet=packet,
        recon=recon,
        rules=rules,
        claim_id=claim_id,
    )

    # 8. Determine disposition.
    disposition = determine_disposition_from_rules(gate, rules)

    # 9. Build decision lines.
    decision_lines = [_to_decision_line(ls) for ls in rules.lines]

    # 10. Assemble result.
    return Result(
        run_id=f"run-{uuid.uuid4().hex[:12]}",
        case_number=case_number,
        claim_id=claim_id,
        claim_type="occupancy_exit_protection",
        policy_form="OEP-2027-SYN",
        completed_at=datetime.now(timezone.utc),
        claimed_amount=float(rules.claimed_total),
        covered_amount=float(rules.covered_total),
        excluded_amount=float(rules.excluded_total),
        held_amount=float(rules.held_total),
        approved_amount=float(rules.approved_total),
        policy_limit=float(policy_limit),
        disposition=disposition,
        outcome_summary=_build_outcome_summary(rules, gate),
        decision_lines=decision_lines,
        math_audit=_build_math_audit(rules, policy_limit),
        gate=gate,
        source_conflicts=recon.all_conflicts,
        documents=_build_document_audits(packet, normalized),
        policy_audit=_build_policy_audit(),
        retrieved_policy=_build_retrieved_policy(decision_lines),
        model_calls=[_model_call_record_to_output(m) for m in call_records],
        tool_calls=[],
        warnings=rules.warnings + recon.warnings,
        writeback_preview=_build_writeback(
            claim_id, case_number, rules, gate, policy_limit, decision_lines,
        ),
    )
