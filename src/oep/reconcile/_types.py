"""Internal result types for the reconciliation module."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from oep.models.output import SourceConflict


class CheckResult(BaseModel):
    """Result of a single reconciliation check."""

    model_config = ConfigDict(extra="forbid")

    check_id: str
    passed: bool
    conflicts: list[SourceConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReconciliationResult(BaseModel):
    """Aggregate result from all reconciliation checks."""

    model_config = ConfigDict(extra="forbid")

    checks: list[CheckResult]
    all_conflicts: list[SourceConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# Canonical filenames for each document role, used to populate
# ConflictValue.source_document.
DOC_FILENAME = {
    "loss_notice": "1_Loss_Notice_and_Record_Index.docx",
    "journal": "2_Tenancy_Financial_Journal.docx",
    "restoration_cost_register": "3_Restoration_Cost_Register.docx",
    "premises_condition_log": "3_Premises_Condition_Log.docx",
    "certificate": "4_Covered_Tenancy_Certificate.docx",
}


def doc3_filename(source_register_title: str) -> str:
    """Return the correct Document 3 filename based on its title."""
    if "condition log" in (source_register_title or "").lower():
        return DOC_FILENAME["premises_condition_log"]
    return DOC_FILENAME["restoration_cost_register"]
