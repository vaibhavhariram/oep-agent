"""Integration tests for the reconciliation module.

Runs reconciliation on real claim data using the deterministic
table parser (no LLM calls).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oep.extraction.normalize import normalize_all
from oep.reconcile import reconcile_all

# Reuse the deterministic raw-extraction builder from the diff harness.
from tests.test_extraction_diff import _build_raw_from_parser


# ------------------------------------------------------------------
# All 10 claims: reconciliation must not raise
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id", [
    "OEP-27-1087",
    "OEP-27-2146",
    "OEP-27-2849",
    "OEP-27-4358",
    "OEP-27-4706",
    "OEP-27-5804",
    "OEP-27-6795",
    "OEP-27-8150",
    "OEP-27-9062",
    "OEP-27-9548",
])
def test_reconcile_no_raise(data_dir: Path, claim_id: str) -> None:
    raw = _build_raw_from_parser(claim_id, data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )
    result = reconcile_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
        normalized=normalized,
    )
    # Structured result — must not raise.
    assert result is not None
    assert isinstance(result.checks, list)
    assert len(result.checks) == 6


# ------------------------------------------------------------------
# Three labeled examples: zero material conflicts
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id", [
    "OEP-27-1087",
    "OEP-27-9062",
    "OEP-27-9548",
])
def test_labeled_examples_zero_conflicts(data_dir: Path, claim_id: str) -> None:
    raw = _build_raw_from_parser(claim_id, data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )
    result = reconcile_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
        normalized=normalized,
    )
    assert result.all_conflicts == [], (
        f"{claim_id} should have zero conflicts but got:\n"
        + "\n".join(
            f"  {c.field}: {[v.value for v in c.values]}"
            for c in result.all_conflicts
        )
    )


# ------------------------------------------------------------------
# OEP-27-6795: zero totals-chain conflicts (credits case)
# ------------------------------------------------------------------


def test_oep_27_6795_totals_chain_zero_conflicts(data_dir: Path) -> None:
    """OEP-27-6795 has a $1,944 reversal and $683 recovery.

    claimed_total=$5,292, ending_balance=$2,665.  All three totals-chain
    comparisons (3a, 3b, 3c) must pass.
    """
    raw = _build_raw_from_parser("OEP-27-6795", data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )
    result = reconcile_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
        normalized=normalized,
    )
    totals_check = next(c for c in result.checks if c.check_id == "totals_chain")
    assert totals_check.passed, (
        f"OEP-27-6795 totals_chain should pass but got conflicts:\n"
        + "\n".join(
            f"  {c.field}: {[v.value for v in c.values]}"
            for c in totals_check.conflicts
        )
    )
