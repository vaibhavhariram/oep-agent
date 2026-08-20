"""Shared builders for adversarial gate-check tests.

Every helper constructs a *valid* baseline object.  Individual tests
mutate exactly one aspect to trigger a specific check failure.
"""

from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from oep.gate import build_gate
from oep.ingest.packet import ClaimPacket, DocumentPacket
from oep.models.output import (
    ConflictValue,
    DocumentExtraction,
    DocumentType,
    EvidenceItem,
    ResolutionStatus,
    Route,
    SourceConflict,
    SourceFact,
)
from oep.reconcile._types import ReconciliationResult
from oep.rules._types import ZERO, LineState, RulesResult

D = Decimal

# ── Packet builders ──────────────────────────────────────────────

def make_packet(claim_id: str = "OEP-27-0001", *, num_docs: int = 4, page_count: int = 1) -> ClaimPacket:
    """Return a ClaimPacket that passes source_integrity."""
    return ClaimPacket(
        claim_id=claim_id,
        label="adversarial",
        documents=[
            DocumentPacket(
                filename=f"{i}_doc.docx",
                document_type="test",
                sha256="a" * 64,
                page_count=page_count,
                provenance="adversarial test",
                pages=[],
            )
            for i in range(1, num_docs + 1)
        ],
    )


# ── Reconciliation builders ─────────────────────────────────────

def make_conflict(
    field: str,
    val1: str,
    val2: str,
    doc1: str = "1_Loss_Notice_and_Record_Index.docx",
    doc2: str = "4_Covered_Tenancy_Certificate.docx",
) -> SourceConflict:
    """Build a SourceConflict with two-sided provenance."""
    return SourceConflict(
        field=field,
        values=[
            ConflictValue(value=val1, source_document=doc1, source_page=1, evidence=f"{field}: {val1}"),
            ConflictValue(value=val2, source_document=doc2, source_page=1, evidence=f"{field}: {val2}"),
        ],
        evidence=[
            EvidenceItem(root=f"{doc1}:page:1"),
            EvidenceItem(root=f"{doc2}:page:1"),
        ],
        resolution=f"Adversarial mutation: {field} disagrees across documents",
        resolution_status=ResolutionStatus.unresolved,
    )


def make_recon(conflicts: list[SourceConflict] | None = None) -> ReconciliationResult:
    """Return a ReconciliationResult — clean by default."""
    return ReconciliationResult(
        checks=[],
        all_conflicts=conflicts or [],
        warnings=[],
    )


# ── Rules / line builders ───────────────────────────────────────

def make_line(
    covered: str = "1000.00",
    excluded: str = "0.00",
    held: str = "0.00",
    *,
    rule_ids: list[str] | None = None,
) -> LineState:
    """Return a LineState whose invariant holds (amount == covered + excluded + held)."""
    from oep.models.output import EvidenceItem as EI, Outcome, RuleTraceStep

    c, e, h = D(covered), D(excluded), D(held)
    amount = c + e + h

    trace = []
    for rid in (rule_ids or ["OEP-4.1"]):
        trace.append(RuleTraceStep(
            rule_id=rid,
            detail="adversarial trace step",
            input_amount=float(amount),
            adjustment_amount=0.0,
            output_amount=float(c),
            outcome=Outcome.applied,
            evidence=[EI(root="adversarial evidence")],
        ))

    return LineState(
        source_index=0,
        description="Adversarial test line",
        source_page=1,
        amount=amount,
        category="unit_restoration",
        documentation_status="sufficient",
        reference=None,
        evidence="Line 1: Adversarial — $1,000.00",
        component=None,
        service_start=None,
        gap_start=None,
        gap_end=None,
        stated_rate=None,
        source_document="3_doc.docx",
        covered=c,
        excluded=e,
        held=h,
        approved=ZERO,
        rule_trace=trace,
    )


def make_rules(lines: list[LineState] | None = None) -> RulesResult:
    """Return a RulesResult with auto-summed totals."""
    lines = lines if lines is not None else [make_line()]
    return RulesResult(
        lines=lines,
        claimed_total=sum(ln.amount for ln in lines),
        covered_total=sum(ln.covered for ln in lines),
        excluded_total=sum(ln.excluded for ln in lines),
        held_total=sum(ln.held for ln in lines),
        approved_total=ZERO,
    )


# ── DocumentExtraction builder (for reconciliation sub-checks) ──

def make_doc_extraction(**overrides) -> DocumentExtraction:
    """Return a minimal valid DocumentExtraction.

    Pass keyword overrides for any date/identifier field, e.g.
    ``make_doc_extraction(event_date="2024-06-15")``.
    """
    defaults = dict(
        document_type=DocumentType.loss_notice_and_record_index,
        claim_id="OEP-27-0001",
        agreement_id="AGR-001",
        claim_type="occupancy_exit_protection",
        participant_name="Test Participant",
        policy_form="OEP-2027-SYN",
        protected_location="Unit 101",
        event_date="2024-06-15",
        statement_date="2024-07-01",
        protection_start="2024-01-01",
        protection_end="2024-12-31",
        claimed_total=1000.00,
        ending_balance=None,
        facts=[SourceFact(field="claim_id", value="OEP-27-0001", source_page=1, evidence="adversarial")],
        submitted_lines=[],
        ledger_entries=[],
        evidence_assertions=[],
        checklist_items=[],
        limit_mentions=[],
        warnings=[],
    )
    defaults.update(overrides)
    return DocumentExtraction(**defaults)


# ── File-level helpers (for source_integrity ingest tests) ───────

REFERENCE_CLAIM = "OEP-27-1087"

@pytest.fixture()
def data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def copy_claim_to_tmp(tmp_path: Path, data_dir: Path, claim_id: str = REFERENCE_CLAIM) -> Path:
    """Copy a real claim's files + a minimal dataset_index.json to tmp_path.

    Returns tmp_path (usable as data_dir for assemble_packet).
    """
    src_claim_dir = data_dir / "claims" / claim_id
    dst_claim_dir = tmp_path / "claims" / claim_id
    shutil.copytree(src_claim_dir, dst_claim_dir)

    # Read the real index to get correct sha256 values.
    real_index = json.loads((data_dir / "dataset_index.json").read_text())

    # Filter to only this claim's files.
    prefix = f"claims/{claim_id}/"
    claim_files = [f for f in real_index["files"] if f["path"].startswith(prefix)]

    # Find the claim entry.
    claim_entry = None
    for c in real_index["claims"]:
        if c["claim_id"] == claim_id:
            claim_entry = dict(c)
            break

    mini_index = {
        "schema_version": 1,
        "policy_form": "OEP-2027-SYN",
        "claim_count": 1,
        "documents_per_claim": 4,
        "files": claim_files,
        "claims": [claim_entry],
    }
    (tmp_path / "dataset_index.json").write_text(json.dumps(mini_index, indent=2))
    return tmp_path


# ── Gate assertion helpers ───────────────────────────────────────

def get_check(gate, check_id: str):
    """Return the Check with the given id from a Gate."""
    for c in gate.checks:
        if c.id == check_id:
            return c
    raise KeyError(f"No check with id={check_id!r}")


def assert_check_fails_and_blocks(gate, check_id: str):
    """Assert the named check failed AND route is not auto_approve."""
    check = get_check(gate, check_id)
    assert not check.passed, f"{check_id} should have failed but passed"
    assert gate.route != Route.auto_approve, (
        f"Route should not be auto_approve when {check_id} fails, "
        f"got {gate.route.value}"
    )
