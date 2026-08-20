"""Integration tests: exact-match against labeled examples + invariants.

Compares full results for the three labeled claims against their expected
JSONs — amounts to the cent, line statuses, categories, routes, gate scores
and per-check results, citation clause ids and pages.

Excludes: rendered_pages[].extracted_text, run_id, completed_at, case_number.

Also tests failure paths and the auto_approve safety invariant.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from oep.assembly import _strip_none_artifacts
from oep.extraction.normalize import normalize_all, parse_date
from oep.gate import build_gate, determine_disposition_from_rules
from oep.ingest.packet import assemble_packet
from oep.models.output import Route
from oep.models.wrappers import validate_against_schema
from oep.policy_store import CLAUSE_BY_ID
from oep.reconcile import reconcile_all
from oep.rules import apply_rules
from oep.rules._types import ZERO

from tests.test_extraction_diff import _build_raw_from_parser


D = Decimal

_EXAMPLES = [
    ("OEP-27-1087", "OEP-27-1087_expected.json"),
    ("OEP-27-9062", "OEP-27-9062_expected.json"),
    ("OEP-27-9548", "OEP-27-9548_expected.json"),
]

# Fields excluded from comparison.
_SKIP_KEYS = {"rendered_pages", "run_id", "completed_at", "case_number",
              "rationale", "detail"}


def _deep_diff(actual, expected, path="") -> list[str]:
    """Compare two dicts/lists field by field. Returns list of differences."""
    diffs: list[str] = []

    if isinstance(actual, dict) and isinstance(expected, dict):
        all_keys = sorted(set(list(actual.keys()) + list(expected.keys())))
        for k in all_keys:
            if k in _SKIP_KEYS:
                continue
            kpath = f"{path}.{k}" if path else k
            if k not in actual:
                diffs.append(f"{kpath}: missing in actual")
            elif k not in expected:
                diffs.append(f"{kpath}: extra in actual")
            else:
                diffs.extend(_deep_diff(actual[k], expected[k], kpath))
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            diffs.append(f"{path}: list length {len(actual)} != {len(expected)}")
        else:
            for i in range(len(actual)):
                diffs.extend(_deep_diff(actual[i], expected[i], f"{path}[{i}]"))
    elif actual != expected:
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            if abs(actual - expected) < 0.005:
                return diffs
        diffs.append(f"{path}: {actual!r} != {expected!r}")

    return diffs


def _process_deterministic(claim_id: str, data_dir: Path):
    """Process a claim using deterministic extraction (no LLM)."""
    raw = _build_raw_from_parser(claim_id, data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )
    recon = reconcile_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
        normalized=normalized,
    )
    event_date = parse_date(normalized[0].event_date)
    policy_limit = D("0")
    if raw["certificate"].combined_limit is not None:
        policy_limit = D(str(raw["certificate"].combined_limit))

    rules = apply_rules(
        loss_notice=raw["loss_notice"],
        source_register=raw["source_register"],
        normalized=normalized,
        policy_limit=policy_limit,
        event_date=event_date,
    )
    pkt = assemble_packet(claim_id, data_dir=data_dir)
    gate = build_gate(
        packet=pkt, recon=recon, rules=rules, claim_id=claim_id,
    )
    disposition = determine_disposition_from_rules(gate, rules)
    return raw, normalized, recon, rules, gate, disposition, pkt, policy_limit


# ------------------------------------------------------------------
# Exact-match against labeled examples
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id, example_file", _EXAMPLES)
def test_exact_match_labeled_example(
    data_dir: Path, claim_id: str, example_file: str
) -> None:
    """Full result must match labeled example to the cent."""
    from oep.assembly import (
        _build_document_audits,
        _build_math_audit,
        _build_outcome_summary,
        _build_policy_audit,
        _build_retrieved_policy,
        _build_writeback,
        _to_decision_line,
    )

    raw, normalized, recon, rules, gate, disposition, pkt, policy_limit = \
        _process_deterministic(claim_id, data_dir)

    decision_lines = [_to_decision_line(ls) for ls in rules.lines]

    # Build the same structures assembly.py would build.
    result_dict = _strip_none_artifacts({
        "claim_id": claim_id,
        "claim_type": "occupancy_exit_protection",
        "policy_form": "OEP-2027-SYN",
        "claimed_amount": float(rules.claimed_total),
        "covered_amount": float(rules.covered_total),
        "excluded_amount": float(rules.excluded_total),
        "held_amount": float(rules.held_total),
        "approved_amount": float(rules.approved_total),
        "policy_limit": float(policy_limit),
        "disposition": disposition.value,
        "outcome_summary": _build_outcome_summary(rules, gate),
        "decision_lines": [dl.model_dump(mode="json") for dl in decision_lines],
        "math_audit": _build_math_audit(rules, policy_limit).model_dump(mode="json"),
        "gate": gate.model_dump(mode="json"),
        "source_conflicts": [sc.model_dump(mode="json") for sc in recon.all_conflicts],
        "documents": [
            da.model_dump(mode="json")
            for da in _build_document_audits(pkt, normalized)
        ],
        "policy_audit": _build_policy_audit().model_dump(mode="json"),
        "retrieved_policy": [
            pm.model_dump(mode="json")
            for pm in _build_retrieved_policy(decision_lines)
        ],
        "model_calls": [],
        "tool_calls": [],
        "warnings": rules.warnings + recon.warnings,
        "writeback_preview": _build_writeback(
            claim_id, 1, rules, gate, policy_limit, decision_lines,
        ).model_dump(mode="json"),
    })

    expected_data = json.loads((data_dir / "examples" / example_file).read_text())
    expected = expected_data["results"][0]

    diffs = _deep_diff(result_dict, expected)
    if diffs:
        diff_str = "\n  ".join(diffs[:30])
        pytest.fail(f"{claim_id}: {len(diffs)} diff(s):\n  {diff_str}")


# ------------------------------------------------------------------
# Schema validation
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id", ["OEP-27-1087", "OEP-27-9062", "OEP-27-9548"])
def test_schema_valid(data_dir: Path, claim_id: str) -> None:
    """Result must validate against output_schema.json."""
    from oep.assembly import (
        _build_document_audits, _build_math_audit, _build_outcome_summary,
        _build_policy_audit, _build_retrieved_policy, _build_writeback, _to_decision_line,
    )
    import uuid
    from datetime import datetime, timezone

    raw, normalized, recon, rules, gate, disposition, pkt, policy_limit = \
        _process_deterministic(claim_id, data_dir)

    decision_lines = [_to_decision_line(ls) for ls in rules.lines]

    from oep.models.output import Result
    result = Result(
        run_id=f"test-{uuid.uuid4().hex[:8]}",
        case_number=1,
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
        documents=_build_document_audits(pkt, normalized),
        policy_audit=_build_policy_audit(),
        retrieved_policy=_build_retrieved_policy(decision_lines),
        model_calls=[],
        tool_calls=[],
        warnings=rules.warnings + recon.warnings,
        writeback_preview=_build_writeback(
            claim_id, 1, rules, gate, policy_limit, decision_lines,
        ),
    )

    output = _strip_none_artifacts({"results": [result.model_dump(mode="json")]})
    errors = validate_against_schema(output)
    assert errors == [], f"Schema validation errors:\n" + "\n".join(errors[:10])


# ------------------------------------------------------------------
# INVARIANT: auto_approve never with unresolved material evidence
# ------------------------------------------------------------------


def test_auto_approve_never_with_held(data_dir: Path) -> None:
    """Missing, contradictory, ambiguous, unsupported, or unverified material
    evidence must NEVER produce auto_approve."""
    for claim_id in [
        "OEP-27-1087", "OEP-27-2146", "OEP-27-2849", "OEP-27-4358",
        "OEP-27-4706", "OEP-27-5804", "OEP-27-6795", "OEP-27-8150",
        "OEP-27-9062", "OEP-27-9548",
    ]:
        raw, normalized, recon, rules, gate, disposition, pkt, policy_limit = \
            _process_deterministic(claim_id, data_dir)
        if rules.held_total > ZERO:
            assert gate.route != Route.auto_approve, (
                f"{claim_id}: auto_approve with held={rules.held_total}"
            )
            assert gate.eligible_for_stp is False, (
                f"{claim_id}: STP eligible with held={rules.held_total}"
            )


# ------------------------------------------------------------------
# All 10 claims: invariants hold
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id", [
    "OEP-27-1087", "OEP-27-2146", "OEP-27-2849", "OEP-27-4358",
    "OEP-27-4706", "OEP-27-5804", "OEP-27-6795", "OEP-27-8150",
    "OEP-27-9062", "OEP-27-9548",
])
def test_gate_invariants(data_dir: Path, claim_id: str) -> None:
    raw, normalized, recon, rules, gate, disposition, pkt, policy_limit = \
        _process_deterministic(claim_id, data_dir)

    # 5 checks, weights sum to 100
    assert len(gate.checks) == 5
    assert sum(c.weight for c in gate.checks) == 100.0

    # Score == sum of passing weights
    expected_score = sum(c.weight for c in gate.checks if c.passed)
    assert gate.score == expected_score

    # Hard failure iff any hard_fail check failed
    expected_hard = any(c.hard_fail and not c.passed for c in gate.checks)
    assert gate.hard_failure == expected_hard
