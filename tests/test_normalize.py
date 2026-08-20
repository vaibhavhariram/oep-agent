"""Tests for the deterministic normalization layer.

Covers: mapping tables, date serialization, evidence string grammars,
and unknown-value fallback with warnings.
"""

from __future__ import annotations

from datetime import date

import pytest

from oep.extraction.normalize import (
    CATEGORY_MAP,
    RECORD_STATUS_MAP,
    _parse_gap_facts,
    date_to_iso,
    date_to_mmddyyyy,
    evidence_fact,
    evidence_ledger_entry,
    evidence_limit_mention,
    evidence_submitted_line,
    map_documentation_status,
    map_source_classification,
    parse_date,
)


# ===================================================================
# source_category → source_classification
# ===================================================================


class TestCategoryMapping:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Occupancy balance", "occupancy_balance"),
            ("Premises restoration", "unit_restoration"),
            ("Reletting gap", "reletting_gap"),
            ("Upgrade or elective improvement", "upgrade"),
            ("Fee or service charge", "operator_fee"),
        ],
    )
    def test_known_categories(self, raw: str, expected: str) -> None:
        warnings: list[str] = []
        assert map_source_classification(raw, warnings) == expected
        assert warnings == []

    def test_case_insensitive(self) -> None:
        warnings: list[str] = []
        assert map_source_classification("OCCUPANCY BALANCE", warnings) == "occupancy_balance"
        assert warnings == []

    def test_unknown_category_fallback(self) -> None:
        warnings: list[str] = []
        result = map_source_classification("Something unexpected", warnings)
        assert result == "unclassified"
        assert len(warnings) == 1
        assert "Unknown source_category" in warnings[0]


# ===================================================================
# record_status → documentation_status
# ===================================================================


class TestDocumentationStatusMapping:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("No supporting record supplied", "missing"),
            ("No record supplied", "missing"),
            ("Estimate only \u2014 work unfinished", "estimate_only"),
            ("Paid record or executed work order supplied", "sufficient"),
            ("Paid record supplied", "sufficient"),
            ("Executed work order supplied", "sufficient"),
            ("Supported by tenancy journal", "sufficient"),
            ("Record not applicable", "not_applicable"),
        ],
    )
    def test_known_statuses(self, raw: str, expected: str) -> None:
        warnings: list[str] = []
        assert map_documentation_status(raw, warnings) == expected
        assert warnings == []

    def test_case_insensitive(self) -> None:
        warnings: list[str] = []
        assert map_documentation_status("PAID RECORD SUPPLIED", warnings) == "sufficient"
        assert warnings == []

    def test_unknown_status_fallback(self) -> None:
        warnings: list[str] = []
        result = map_documentation_status("Some new status text", warnings)
        assert result == "unclear"
        assert len(warnings) == 1
        assert "Unknown record_status" in warnings[0]


# ===================================================================
# Date handling
# ===================================================================


class TestDateParsing:
    def test_mmddyyyy(self) -> None:
        assert parse_date("02/04/2027") == date(2027, 2, 4)

    def test_iso(self) -> None:
        assert parse_date("2027-02-04") == date(2027, 2, 4)

    def test_long_format(self) -> None:
        assert parse_date("February 10, 2027") == date(2027, 2, 10)

    def test_none(self) -> None:
        assert parse_date(None) is None

    def test_empty(self) -> None:
        assert parse_date("") is None


class TestDateSerialization:
    def test_iso_format(self) -> None:
        """Document-level fields serialize as ISO YYYY-MM-DD."""
        d = date(2027, 2, 4)
        assert date_to_iso(d) == "2027-02-04"

    def test_mmddyyyy_format(self) -> None:
        """Ledger entry_date serializes as MM/DD/YYYY."""
        d = date(2027, 2, 10)
        assert date_to_mmddyyyy(d) == "02/10/2027"

    def test_none_serialization(self) -> None:
        assert date_to_iso(None) is None
        assert date_to_mmddyyyy(None) is None


# ===================================================================
# Evidence string grammars
# ===================================================================


class TestEvidenceStrings:
    def test_submitted_line(self) -> None:
        result = evidence_submitted_line(
            1, "Outstanding occupancy installment", 1725.0
        )
        assert result == "Line 1: Outstanding occupancy installment \u2014 $1,725.00"

    def test_ledger_entry(self) -> None:
        result = evidence_ledger_entry(
            "Outstanding occupancy installment", 1725.0, 0.0
        )
        assert result == "Outstanding occupancy installment: debit $1,725.00, credit $0.00"

    def test_limit_mention(self) -> None:
        result = evidence_limit_mention("Combined protection limit", 2675.0)
        assert result == "Combined protection limit $2,675.00"

    def test_fact(self) -> None:
        result = evidence_fact("OEP-27-9062")
        assert result == "Claim ID OEP-27-9062"


# ===================================================================
# Evidence strings against real values from labeled examples
# ===================================================================


class TestEvidenceAgainstExamples:
    """Verify evidence grammars produce exactly the strings in the examples."""

    def test_submitted_line_9062_line1(self) -> None:
        expected = "Line 1: Outstanding occupancy installment \u2014 $1,725.00"
        assert evidence_submitted_line(1, "Outstanding occupancy installment", 1725.0) == expected

    def test_submitted_line_9062_line3(self) -> None:
        expected = "Line 3: Reletting interval \u2014 4 days at $103.00 per day \u2014 $412.00"
        assert evidence_submitted_line(
            3, "Reletting interval \u2014 4 days at $103.00 per day", 412.0
        ) == expected

    def test_ledger_entry_9062(self) -> None:
        expected = "Outstanding occupancy installment: debit $1,725.00, credit $0.00"
        assert evidence_ledger_entry("Outstanding occupancy installment", 1725.0, 0.0) == expected

    def test_limit_mention_9062(self) -> None:
        expected = "Combined protection limit $2,675.00"
        assert evidence_limit_mention("Combined protection limit", 2675.0) == expected

    def test_fact_9062(self) -> None:
        expected = "Claim ID OEP-27-9062"
        assert evidence_fact("OEP-27-9062") == expected


# ===================================================================
# Gap-fact date parsing (_parse_gap_facts)
# ===================================================================


class TestGapFactDateFormats:
    def test_iso_dates(self) -> None:
        fact = "Gap: 2027-01-24 \u2013 2027-02-13 at $73.00/day"
        result = _parse_gap_facts(fact)
        assert result["protected_period_start"] == "2027-01-24"
        assert result["protected_period_end"] == "2027-02-13"
        assert result["stated_rate"] == 73.0

    def test_mmddyyyy_dates(self) -> None:
        fact = "Gap: 01/24/2027 \u2013 02/13/2027 at $73.00/day"
        result = _parse_gap_facts(fact)
        assert result["protected_period_start"] == "2027-01-24"
        assert result["protected_period_end"] == "2027-02-13"
        assert result["stated_rate"] == 73.0
