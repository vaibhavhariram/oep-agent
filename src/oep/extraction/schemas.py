"""Pydantic v2 models for the RAW LLM extraction output.

These are *intermediate* models — they mirror what the prompts ask the model
to return (verbatim strings, raw dates, raw category text).  They are
**separate** from the generated ``output.py`` models, which represent the
final normalised schema.

The normalization layer (``normalize.py``) converts these into the
``DocumentExtraction`` objects that ``output_schema.json`` requires.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# §1  Loss Notice and Record Index
# ---------------------------------------------------------------------------

class PresentedAmount(_Strict):
    source_register: str
    gross_amount: float
    source_page: int


class RecordIndexEntry(_Strict):
    registered_record: str
    packet_status: str
    factual_scope: str
    source_page: int


class RawLossNotice(_Strict):
    claim_id: str | None = None
    policy_number: str | None = None
    agreement_id: str | None = None
    policy_form: str | None = None
    participant_name: str | None = None
    operator: str | None = None
    property_name: str | None = None
    unit: str | None = None
    protected_location: str | None = None
    monthly_charge: float | None = None
    possession_returned: str | None = None
    selected_limit: float | None = None
    tenancy_start: str | None = None
    report_date: str | None = None
    statement_date: str | None = None
    event_narrative: str | None = None
    presented_amounts: list[PresentedAmount] = []
    total_presented: float | None = None
    record_index: list[RecordIndexEntry] = []
    prepared_by: str | None = None
    certification_date: str | None = None
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# §2  Tenancy Financial Journal
# ---------------------------------------------------------------------------

class RawLedgerEntry(_Strict):
    entry_date: str
    description: str
    debit_amount: float
    credit_amount: float
    running_balance: float
    source_page: int


class RawFinancialJournal(_Strict):
    claim_id: str | None = None
    agreement_id: str | None = None
    unit: str | None = None
    participant_name: str | None = None
    snapshot_date: str | None = None
    ledger_entries: list[RawLedgerEntry] = []
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# §3  Restoration Cost Register / Premises Condition Log
# ---------------------------------------------------------------------------

class RawSourceLine(_Strict):
    line_number: int
    description: str
    source_category: str
    gross_amount: float
    source_page: int


class RawRecordRegisterEntry(_Strict):
    line_number: int
    record_status: str
    record_reference: str | None = None
    service_life_fact: str | None = None
    source_page: int


class RawFactualObservation(_Strict):
    observation: str
    recorded_fact: str
    source_page: int


class RawSourceRegister(_Strict):
    document_title: str
    claim_id: str | None = None
    policy_number: str | None = None
    agreement_id: str | None = None
    policy_form: str | None = None
    participant_name: str | None = None
    operator: str | None = None
    property_name: str | None = None
    unit: str | None = None
    protected_location: str | None = None
    monthly_charge: float | None = None
    possession_returned: str | None = None
    selected_limit: float | None = None
    presented_source_lines: list[RawSourceLine] = []
    source_record_register: list[RawRecordRegisterEntry] = []
    factual_observations: list[RawFactualObservation] = []
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# §4  Covered Tenancy Certificate
# ---------------------------------------------------------------------------

class RawSelectedPart(_Strict):
    part: str
    selection: str
    description: str
    source_page: int


class RawStatement(_Strict):
    statement: str
    response: str
    source_page: int


class RawExecution(_Strict):
    party: str
    printed_name: str
    signature_record: str
    execution_date: str
    source_page: int


class RawCertificate(_Strict):
    policy_number: str | None = None
    policy_form: str | None = None
    agreement_id: str | None = None
    participant_name: str | None = None
    operator: str | None = None
    property_and_unit: str | None = None
    protected_location: str | None = None
    certificate_period_raw: str | None = None
    monthly_charge: float | None = None
    combined_limit: float | None = None
    deductible: float | None = None
    selected_parts: list[RawSelectedPart] = []
    limit_application_text: str | None = None
    household_statements: list[RawStatement] = []
    operator_statements: list[RawStatement] = []
    executions: list[RawExecution] = []
    issuing_carrier: str | None = None
    program: str | None = None
    master_form: str | None = None
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Registry: document_type → raw schema class
# ---------------------------------------------------------------------------

RAW_SCHEMA_BY_DOC_TYPE: dict[str, type[BaseModel]] = {
    "loss_notice_and_record_index": RawLossNotice,
    "tenancy_financial_journal": RawFinancialJournal,
    "restoration_cost_register": RawSourceRegister,
    "premises_condition_log": RawSourceRegister,
    "covered_tenancy_certificate": RawCertificate,
}
