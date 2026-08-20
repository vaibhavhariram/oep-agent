"""Tests for Check 5 — Coverage window (OEP-1.2)."""

from __future__ import annotations

from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.extraction.normalize import normalize_all
from oep.reconcile._coverage import check_coverage_window


def _normalize(*, possession_returned, certificate_period):
    ln = RawLossNotice(claim_id="OEP-27-0001", possession_returned=possession_returned)
    j = RawFinancialJournal()
    sr = RawSourceRegister(document_title="Restoration Cost Register")
    cert = RawCertificate(certificate_period_raw=certificate_period)
    return normalize_all(loss_notice=ln, journal=j, source_register=sr, certificate=cert)


def test_event_within_period():
    normalized = _normalize(
        possession_returned="06/15/2027",
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert result.passed
    assert result.conflicts == []


def test_event_on_start_boundary():
    normalized = _normalize(
        possession_returned="01/01/2027",
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert result.passed


def test_event_on_end_boundary():
    normalized = _normalize(
        possession_returned="12/31/2027",
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert result.passed


def test_event_before_period():
    normalized = _normalize(
        possession_returned="12/31/2026",
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert not result.passed
    assert result.conflicts[0].field == "coverage_window"


def test_event_after_period():
    normalized = _normalize(
        possession_returned="01/01/2028",
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert not result.passed


def test_missing_event_date():
    normalized = _normalize(
        possession_returned=None,
        certificate_period="2027-01-01 through 2027-12-31",
    )
    result = check_coverage_window(normalized)
    assert result.passed  # no conflict, just a warning
    assert any("event_date" in w for w in result.warnings)


def test_missing_certificate_period():
    normalized = _normalize(
        possession_returned="06/15/2027",
        certificate_period=None,
    )
    result = check_coverage_window(normalized)
    assert result.passed
    assert any("Certificate" in w for w in result.warnings)
