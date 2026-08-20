"""Baseline adjudicator: one model call per claim, no rules engine.

Input: all four documents' page-tagged text + full policy text + output_schema.
Output: complete Result JSON (no retry on schema failure, recorded as-is).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from pydantic import ValidationError

from oep import config
from oep.extraction.client import ModelCallRecord, build_page_tagged_text
from oep.ingest.docx_pages import extract_pages
from oep.ingest.packet import assemble_packet
from oep.models.output import Result
from oep.models.wrappers import validate_against_schema


@dataclass
class BaselineResult:
    """Result from baseline adjudication."""
    claim_id: str
    result: dict | None  # JSON result, or None if validation failed
    validation_errors: list[str]  # Empty if valid; otherwise schema errors
    model_call: ModelCallRecord
    success: bool  # True if result is valid; False if schema validation failed


def _build_policy_text(policy_docx_path: Path) -> str:
    """Extract all text from the policy DOCX."""
    pages = extract_pages(policy_docx_path)
    parts = []
    for page in pages:
        parts.append(f"<<<PAGE {page.page_number}>>>")
        parts.append(page.extracted_text)
    return "\n".join(parts)


def _extract_result_json(response_text: str) -> dict | None:
    """Extract JSON from model response, handling markdown fences."""
    raw_text = response_text.strip()

    # Strip markdown fences if model wrapped output.
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove first and last fence lines.
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def baseline_adjudicate(
    claim_id: str,
    *,
    data_dir: Path | None = None,
) -> BaselineResult:
    """Adjudicate a claim using a single model call.

    Parameters
    ----------
    claim_id:
        The claim ID (e.g., "OEP-27-9062").
    data_dir:
        Override for data directory. Defaults to config.DATA_DIR.

    Returns
    -------
    BaselineResult
        The result JSON (if schema-valid) and model call metadata.
        Validation failures are recorded but NOT retried.
    """
    data_dir = data_dir or config.DATA_DIR

    # Assemble packet and extract documents.
    packet = assemble_packet(claim_id, data_dir=data_dir)

    # Build page-tagged text for each document.
    doc_sections = []
    for doc in packet.documents:
        tagged = build_page_tagged_text(doc.pages)
        doc_sections.append(f"=== {doc.document_type} ===\n{tagged}")

    docs_text = "\n\n".join(doc_sections)

    # Extract policy text.
    policy_text = _build_policy_text(config.POLICY_DOCX_PATH)

    # Build prompt with full policy and documents.
    prompt = f"""You are a deterministic claims adjudication assistant. Analyze the provided claim documents and policy to produce a complete Result JSON object.

The Result object must have:
- claim_id, claim_type, policy_form, completed_at
- claimed_amount, covered_amount, excluded_amount, held_amount, approved_amount, policy_limit
- disposition (approved/escalated), outcome_summary
- decision_lines (with source_index, claimed_amount, covered_amount, excluded_amount, held_amount, approved_amount, category, status, rationale, citations, rule_trace)
- documents (4 entries with document_type, extraction, rendered_pages)
- math_audit, gate (with route, score, checks, threshold)
- source_conflicts, policy_audit, retrieved_policy
- model_calls, tool_calls, warnings, writeback_preview
- case_number=1, run_id (unique)

CLAIM DOCUMENTS:
{docs_text}

POLICY (OEP-2027-SYN):
{policy_text}

Output ONLY valid JSON — no markdown, no explanation, no extra text.
"""

    # Make model call.
    client = anthropic.Anthropic()
    t0 = time.monotonic()
    response = client.messages.create(
        model=config.DEFAULT_MODEL,
        max_tokens=8192,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Parse response.
    response_text = response.content[0].text
    result_dict = _extract_result_json(response_text)

    # Validate against schema.
    validation_errors: list[str] = []
    if result_dict is None:
        validation_errors = ["Failed to extract JSON from model response"]
    else:
        # Wrap in "results" array and validate.
        wrapped = {"results": [result_dict]}
        validation_errors = validate_against_schema(wrapped)

    # Build model call record.
    usage = response.usage
    model_call = ModelCallRecord(
        purpose="baseline_adjudicate",
        provider=config.DEFAULT_PROVIDER,
        requested_model=config.DEFAULT_MODEL,
        routed_provider=config.DEFAULT_PROVIDER,
        routed_model=getattr(response, "model", config.DEFAULT_MODEL),
        response_id=response.id,
        duration_ms=elapsed_ms,
        attempt_count=1,
        input_tokens=usage.input_tokens,
        cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0),
        output_tokens=usage.output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
        cost_usd=None,
        cost_source="not_available",
        stored_by_provider=True,
    )

    success = len(validation_errors) == 0

    return BaselineResult(
        claim_id=claim_id,
        result=result_dict if success else None,
        validation_errors=validation_errors,
        model_call=model_call,
        success=success,
    )


@dataclass
class BaselineBResult:
    """Result from baseline-b adjudication."""
    claim_id: str
    result: dict | None  # Reduced JSON result, or None if validation failed
    validation_errors: list[str]  # Empty if valid; otherwise schema errors
    model_call: ModelCallRecord
    success: bool  # True if result is valid; False if schema validation failed


def baseline_b_adjudicate(
    claim_id: str,
    *,
    data_dir: Path | None = None,
) -> BaselineBResult:
    """Adjudicate a claim using a single model call, reduced output schema.

    Focus: decision quality (lines, amounts, route, disposition) only.
    No structural overhead (documents, policy_audit, etc.).

    Parameters
    ----------
    claim_id:
        The claim ID (e.g., "OEP-27-9062").
    data_dir:
        Override for data directory. Defaults to config.DATA_DIR.

    Returns
    -------
    BaselineBResult
        Reduced result JSON (if valid) and model call metadata.
    """
    data_dir = data_dir or config.DATA_DIR

    # Assemble packet and extract documents.
    packet = assemble_packet(claim_id, data_dir=data_dir)

    # Build page-tagged text for each document.
    doc_sections = []
    for doc in packet.documents:
        tagged = build_page_tagged_text(doc.pages)
        doc_sections.append(f"=== {doc.document_type} ===\n{tagged}")

    docs_text = "\n\n".join(doc_sections)

    # Extract policy text.
    policy_text = _build_policy_text(config.POLICY_DOCX_PATH)

    # Reduced schema definition (adjudication core only).
    reduced_schema = {
        "type": "object",
        "properties": {
            "claim_id": {"type": "string", "pattern": "^OEP-27-[0-9]{4}$"},
            "policy_limit": {"type": "number", "minimum": 0},
            "disposition": {"type": "string", "enum": ["approved", "escalated"]},
            "route": {"type": "string", "enum": ["auto_approve", "partial_approve_with_hold", "human_review"]},
            "claimed_total": {"type": "number", "minimum": 0},
            "covered_total": {"type": "number", "minimum": 0},
            "excluded_total": {"type": "number", "minimum": 0},
            "held_total": {"type": "number", "minimum": 0},
            "approved_total": {"type": "number", "minimum": 0},
            "decision_lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_index": {"type": "integer", "minimum": 0},
                        "description": {"type": "string"},
                        "category": {"type": "string"},
                        "status": {"type": "string", "enum": ["covered", "partially_covered", "excluded", "needs_review"]},
                        "claimed_amount": {"type": "number", "minimum": 0},
                        "covered_amount": {"type": "number", "minimum": 0},
                        "excluded_amount": {"type": "number", "minimum": 0},
                        "held_amount": {"type": "number", "minimum": 0},
                        "approved_amount": {"type": "number", "minimum": 0},
                    },
                    "required": ["source_index", "description", "category", "status",
                                "claimed_amount", "covered_amount", "excluded_amount",
                                "held_amount", "approved_amount"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["claim_id", "policy_limit", "disposition", "route",
                    "claimed_total", "covered_total", "excluded_total", "held_total",
                    "approved_total", "decision_lines"],
        "additionalProperties": False,
    }

    # Build prompt.
    prompt = f"""You are a claims adjudication system. Analyze the claim documents and policy to produce an adjudication JSON.

TASK:
For each line in the submitted register, determine:
- category (occupancy_balance, reletting_gap, unit_restoration, operator_fee, ordinary_upkeep, upgrade, duplicate, or other)
- status (covered, partially_covered, excluded, needs_review)
- claimed_amount (original), covered_amount, excluded_amount, held_amount, approved_amount

POLICY REFERENCE (OEP-2027-SYN):
{policy_text}

CLAIM DOCUMENTS:
{docs_text}

OUTPUT:
A JSON object with:
- claim_id, policy_limit, disposition (approved/escalated), route (auto_approve/partial_approve_with_hold/human_review)
- claimed_total, covered_total, excluded_total, held_total, approved_total
- decision_lines array: each with source_index, description, category, status, all five amounts

Examples of line categorization and status:
- "Outstanding occupancy" → occupancy_balance, covered (if documented)
- "Administrative charge" → operator_fee, excluded
- "Premises restoration" → unit_restoration, covered (if documented) or needs_review (if insufficient evidence)
- "Elective upgrade" → upgrade, excluded
- "Duplicate entry" → duplicate, excluded

Disposition:
- approved: all amounts can be approved (covered > 0, held == 0)
- escalated: material evidence is unresolved (held > 0, needs_review items present)

Route:
- auto_approve: high confidence, no conflicts, all amounts safe
- partial_approve_with_hold: some amounts covered, some held for review
- human_review: insufficient data, conflicts, or escalation required

Apply OEP-2027-SYN policy logic:
- Exclude administrative charges, duplicate entries, elective upgrades, routine upkeep
- Hold restoration items lacking adequate work orders or records
- Apply component service-life reduction for claimed components past expiration
- Trim reletting gap to earliest of: ready cutoff (if stated), 30 days after possession return
- Apply certificate policy limit as hard cap on approved_total

Output ONLY the JSON object — no markdown, no explanation.
"""

    # Make model call.
    client = anthropic.Anthropic()
    t0 = time.monotonic()
    response = client.messages.create(
        model=config.DEFAULT_MODEL,
        max_tokens=4096,  # Ample for reduced schema
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    # Parse response.
    response_text = response.content[0].text
    result_dict = _extract_result_json(response_text)

    # Validate against reduced schema.
    validation_errors: list[str] = []
    if result_dict is None:
        validation_errors = ["Failed to extract JSON from model response"]
    else:
        # Simple schema validation (no external validator needed).
        from jsonschema import Draft202012Validator

        validator = Draft202012Validator(reduced_schema)
        validation_errors = [str(e.message) for e in validator.iter_errors(result_dict)]

    # Build model call record.
    usage = response.usage
    model_call = ModelCallRecord(
        purpose="baseline_b_adjudicate",
        provider=config.DEFAULT_PROVIDER,
        requested_model=config.DEFAULT_MODEL,
        routed_provider=config.DEFAULT_PROVIDER,
        routed_model=getattr(response, "model", config.DEFAULT_MODEL),
        response_id=response.id,
        duration_ms=elapsed_ms,
        attempt_count=1,
        input_tokens=usage.input_tokens,
        cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0),
        output_tokens=usage.output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
        cost_usd=None,
        cost_source="not_available",
        stored_by_provider=True,
    )

    success = len(validation_errors) == 0

    return BaselineBResult(
        claim_id=claim_id,
        result=result_dict if success else None,
        validation_errors=validation_errors,
        model_call=model_call,
        success=success,
    )
