"""Integration tests for the policy rules engine.

Runs all 7 stages on real claim data using the deterministic table parser.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from oep.extraction.normalize import normalize_all, parse_date
from oep.rules import apply_rules

from tests.test_extraction_diff import _build_raw_from_parser

D = Decimal


def _run_rules(claim_id: str, data_dir: Path):
    """Build raw + normalized, then apply rules."""
    raw = _build_raw_from_parser(claim_id, data_dir)
    normalized = normalize_all(
        loss_notice=raw["loss_notice"],
        journal=raw["journal"],
        source_register=raw["source_register"],
        certificate=raw["certificate"],
    )
    event_date = parse_date(normalized[0].event_date)
    policy_limit = D("0")
    if normalized[3].limit_mentions:
        policy_limit = D(str(normalized[3].limit_mentions[0].amount))
    elif raw["certificate"].combined_limit is not None:
        policy_limit = D(str(raw["certificate"].combined_limit))

    result = apply_rules(
        loss_notice=raw["loss_notice"],
        source_register=raw["source_register"],
        normalized=normalized,
        policy_limit=policy_limit,
        event_date=event_date,
    )
    return result


# ------------------------------------------------------------------
# All 10 claims: invariants hold, no raise
# ------------------------------------------------------------------


@pytest.mark.parametrize("claim_id", [
    "OEP-27-1087", "OEP-27-2146", "OEP-27-2849", "OEP-27-4358",
    "OEP-27-4706", "OEP-27-5804", "OEP-27-6795", "OEP-27-8150",
    "OEP-27-9062", "OEP-27-9548",
])
def test_invariants_all_claims(data_dir: Path, claim_id: str) -> None:
    result = _run_rules(claim_id, data_dir)

    # Line-level invariant: claimed == covered + excluded + held
    for ls in result.lines:
        assert ls.amount == ls.covered + ls.excluded + ls.held, (
            f"{claim_id} line {ls.source_index}: "
            f"claimed={ls.amount} != covered={ls.covered} + "
            f"excluded={ls.excluded} + held={ls.held}"
        )

    # Case-level invariant: sums match
    assert result.claimed_total == result.covered_total + result.excluded_total + result.held_total

    # Cap invariant: approved == min(covered, limit)
    assert result.approved_total <= result.covered_total
    assert result.approved_total >= D("0")


# ------------------------------------------------------------------
# Labeled examples: exact dollar amounts
# ------------------------------------------------------------------


def test_1087_amounts(data_dir: Path) -> None:
    """OEP-27-1087: all held, fee excluded."""
    r = _run_rules("OEP-27-1087", data_dir)
    assert r.claimed_total == D("3482.00")
    assert r.covered_total == D("0.00")
    assert r.excluded_total == D("124.00")
    assert r.held_total == D("3358.00")
    assert r.approved_total == D("0.00")


def test_9062_amounts(data_dir: Path) -> None:
    """OEP-27-9062: capped at limit."""
    r = _run_rules("OEP-27-9062", data_dir)
    assert r.claimed_total == D("3698.00")
    assert r.covered_total == D("3421.00")
    assert r.excluded_total == D("277.00")
    assert r.held_total == D("0.00")
    assert r.approved_total == D("2675.00")

    # Greedy cap allocation.
    by_idx = {ls.source_index: ls for ls in r.lines}
    assert by_idx[0].approved == D("1725.00")
    assert by_idx[1].approved == D("950.00")
    assert by_idx[2].approved == D("0.00")


def test_9548_amounts(data_dir: Path) -> None:
    """OEP-27-9548: partial hold, capped."""
    r = _run_rules("OEP-27-9548", data_dir)
    assert r.claimed_total == D("4309.00")
    assert r.covered_total == D("2548.00")
    assert r.excluded_total == D("97.00")
    assert r.held_total == D("1664.00")
    assert r.approved_total == D("2290.00")

    by_idx = {ls.source_index: ls for ls in r.lines}
    assert by_idx[0].approved == D("1837.00")
    assert by_idx[1].approved == D("453.00")


# ------------------------------------------------------------------
# OEP-27-6795: duplicate single-removal + recovery
# ------------------------------------------------------------------


def test_6795_credits(data_dir: Path) -> None:
    """OEP-27-6795: $1,944 duplicate removed once, $683 recovery applied once."""
    r = _run_rules("OEP-27-6795", data_dir)
    assert r.claimed_total == D("5292.00")
    assert r.claimed_total == r.covered_total + r.excluded_total + r.held_total


# ------------------------------------------------------------------
# OEP-27-2849: gap trimmed
# ------------------------------------------------------------------


def test_2849_gap_trim(data_dir: Path) -> None:
    """OEP-27-2849: gap 21d@$73, cutoff 02/05, supported 13d=$949, excluded 8d=$584."""
    r = _run_rules("OEP-27-2849", data_dir)
    gap_line = next(ls for ls in r.lines if ls.category == "reletting_gap")
    assert gap_line.covered == D("949.00")
    assert gap_line.excluded == D("584.00")
    assert gap_line.status == "partially_covered"
