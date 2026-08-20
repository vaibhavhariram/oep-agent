"""Tests for Stage 1 — Classification."""

from oep.extraction.normalize import CATEGORY_MAP


def test_seven_categories_mapped():
    """All seven visible source categories produce correct classifications."""
    expected = {
        "occupancy balance": "occupancy_balance",
        "premises restoration": "unit_restoration",
        "reletting gap": "reletting_gap",
        "upgrade or elective improvement": "upgrade",
        "fee or service charge": "operator_fee",
        "routine turnover": "ordinary_upkeep",
        "duplicate source entry": "duplicate",
    }
    for raw, classification in expected.items():
        assert CATEGORY_MAP[raw] == classification, f"{raw!r} should map to {classification!r}"


def test_case_insensitive_lookup():
    """CATEGORY_MAP keys are lowercase; lookup must normalize."""
    assert CATEGORY_MAP.get("routine turnover") == "ordinary_upkeep"
