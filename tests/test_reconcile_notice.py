"""Tests for Check 6 — Notice deadline (OEP-5.1)."""

from __future__ import annotations

from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.normalize import normalize_all
from oep.reconcile._notice import check_notice_deadline


def _normalize(*, possession_returned, statement_date):
    ln = RawLossNotice(
        claim_id="OEP-27-0001",
        possession_returned=possession_returned,
        statement_date=statement_date,
    )
    j = RawFinancialJournal()
    sr = RawSourceRegister(document_title="Restoration Cost Register")
    cert = RawCertificate(certificate_period_raw="2027-01-01 through 2027-12-31")
    return normalize_all(loss_notice=ln, journal=j, source_register=sr, certificate=cert)


def test_within_deadline():
    normalized = _normalize(
        possession_returned="01/01/2027",
        statement_date="03/01/2027",  # 59 days
    )
    result = check_notice_deadline(normalized)
    assert result.passed
    assert result.conflicts == []


def test_exactly_105_days():
    normalized = _normalize(
        possession_returned="01/01/2027",
        statement_date="04/16/2027",  # exactly 105 days
    )
    result = check_notice_deadline(normalized)
    assert result.passed


def test_over_105_days():
    normalized = _normalize(
        possession_returned="01/01/2027",
        statement_date="04/17/2027",  # 106 days
    )
    result = check_notice_deadline(normalized)
    assert not result.passed
    assert result.conflicts[0].field == "notice_deadline"
    assert "106 days" in result.conflicts[0].resolution


def test_missing_statement_date():
    normalized = _normalize(
        possession_returned="01/01/2027",
        statement_date=None,
    )
    result = check_notice_deadline(normalized)
    assert result.passed
    assert any("statement_date" in w for w in result.warnings)


def test_missing_event_date():
    normalized = _normalize(
        possession_returned=None,
        statement_date="04/01/2027",
    )
    result = check_notice_deadline(normalized)
    assert result.passed
    assert any("event_date" in w for w in result.warnings)
