"""Tests for Check 2 — Limit agreement."""

from __future__ import annotations

from oep.extraction.schemas import RawCertificate, RawLossNotice
from oep.reconcile._limits import check_limit_agreement


def test_limits_match():
    ln = RawLossNotice(selected_limit=5000.00)
    cert = RawCertificate(combined_limit=5000.00)
    result = check_limit_agreement(ln, cert)
    assert result.passed
    assert result.conflicts == []


def test_limits_disagree():
    ln = RawLossNotice(selected_limit=5000.00)
    cert = RawCertificate(combined_limit=7500.00)
    result = check_limit_agreement(ln, cert)
    assert not result.passed
    assert len(result.conflicts) == 1
    assert result.conflicts[0].field == "selected_limit"
    vals = {v.value for v in result.conflicts[0].values}
    assert "$5,000.00" in vals
    assert "$7,500.00" in vals


def test_loss_notice_limit_missing():
    ln = RawLossNotice(selected_limit=None)
    cert = RawCertificate(combined_limit=5000.00)
    result = check_limit_agreement(ln, cert)
    assert result.passed
    assert any("Loss Notice" in w for w in result.warnings)


def test_certificate_limit_missing():
    ln = RawLossNotice(selected_limit=5000.00)
    cert = RawCertificate(combined_limit=None)
    result = check_limit_agreement(ln, cert)
    assert result.passed
    assert any("Certificate" in w for w in result.warnings)


def test_both_limits_missing():
    ln = RawLossNotice()
    cert = RawCertificate()
    result = check_limit_agreement(ln, cert)
    assert result.passed
    assert len(result.warnings) == 2
