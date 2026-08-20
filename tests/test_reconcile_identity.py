"""Tests for Check 1 — Identifier chain."""

from __future__ import annotations

from oep.extraction.schemas import (
    RawCertificate,
    RawFinancialJournal,
    RawLossNotice,
    RawSourceRegister,
)
from oep.reconcile._identity import check_identifier_chain


def _make_raw(
    *,
    ln_claim="OEP-27-0001",
    ln_agreement="T-100",
    ln_participant="Doe",
    ln_location="123 Main St",
    ln_policy="OEP-2027-SYN",
    j_claim="OEP-27-0001",
    j_agreement="T-100",
    j_participant="Doe",
    sr_claim="OEP-27-0001",
    sr_agreement="T-100",
    sr_participant="Doe",
    sr_location="123 Main St",
    sr_policy="OEP-2027-SYN",
    cert_agreement="T-100",
    cert_participant="Doe",
    cert_location="123 Main St",
    cert_policy="OEP-2027-SYN",
):
    ln = RawLossNotice(
        claim_id=ln_claim,
        agreement_id=ln_agreement,
        participant_name=ln_participant,
        protected_location=ln_location,
        policy_form=ln_policy,
    )
    j = RawFinancialJournal(
        claim_id=j_claim,
        agreement_id=j_agreement,
        participant_name=j_participant,
    )
    sr = RawSourceRegister(
        document_title="Restoration Cost Register",
        claim_id=sr_claim,
        agreement_id=sr_agreement,
        participant_name=sr_participant,
        protected_location=sr_location,
        policy_form=sr_policy,
    )
    cert = RawCertificate(
        agreement_id=cert_agreement,
        participant_name=cert_participant,
        protected_location=cert_location,
        policy_form=cert_policy,
    )
    return ln, j, sr, cert


def test_all_identifiers_match():
    result = check_identifier_chain(*_make_raw())
    assert result.passed
    assert result.conflicts == []


def test_agreement_id_mismatch():
    result = check_identifier_chain(*_make_raw(cert_agreement="T-999"))
    assert not result.passed
    assert len(result.conflicts) == 1
    assert result.conflicts[0].field == "agreement_id"


def test_participant_name_mismatch():
    result = check_identifier_chain(*_make_raw(sr_participant="Smith"))
    assert not result.passed
    assert result.conflicts[0].field == "participant_name"


def test_claim_id_mismatch():
    result = check_identifier_chain(*_make_raw(j_claim="OEP-27-9999"))
    assert not result.passed
    assert result.conflicts[0].field == "claim_id"


def test_certificate_missing_claim_id_not_a_conflict():
    """Certificate has no claim_id — that absence is expected."""
    result = check_identifier_chain(*_make_raw())
    # Certificate never contributes a claim_id, so no conflict.
    claim_conflicts = [c for c in result.conflicts if c.field == "claim_id"]
    assert claim_conflicts == []


def test_case_insensitive_match():
    """Differences in casing should not trigger a conflict."""
    result = check_identifier_chain(
        *_make_raw(
            ln_participant="John Doe",
            j_participant="john doe",
            sr_participant="JOHN DOE",
            cert_participant="John doe",
        )
    )
    assert result.passed


def test_multiple_fields_disagree():
    """Multiple fields can disagree simultaneously."""
    result = check_identifier_chain(
        *_make_raw(cert_agreement="T-999", sr_policy="DIFFERENT")
    )
    assert not result.passed
    fields = {c.field for c in result.conflicts}
    assert "agreement_id" in fields
    assert "policy_form" in fields


def test_none_values_ignored():
    """None values should not count as a distinct value."""
    result = check_identifier_chain(
        *_make_raw(j_claim=None, sr_claim=None)
    )
    # Only Loss Notice states claim_id — single value, no conflict.
    assert result.passed
