"""Extraction prompt for Document 2 — Tenancy Financial Journal.

Layout (1 page):
  Subtitle: "Activity snapshot · <date>"
  Metadata row: Claim ID | Tenancy ID | Unit | Household
  Ledger table columns:
      Date | Journal description | Debit | Credit / recovery | Running balance
  Footer disclaimer.

Populates ledger_entries.
"""

PROMPT = """\
You are extracting the **Tenancy Financial Journal**.

This document is an accounting-source snapshot showing every debit, credit,
recovery, and reversal through the closeout date. It is always a single page.

Extract the following JSON object from the page-tagged text below.

{{
  "claim_id":           "string or null",
  "agreement_id":       "string or null",
  "unit":               "string or null",
  "participant_name":   "string or null",
  "snapshot_date":      "string or null",
  "ledger_entries": [
    {{
      "entry_date":       "string",
      "description":      "string",
      "debit_amount":     "number",
      "credit_amount":    "number",
      "running_balance":  "number",
      "source_page":      "int"
    }}
  ],
  "warnings":           ["string"]
}}

FIELD MAPPING:
- `claim_id`         ← "Claim ID" cell in the header row
- `agreement_id`     ← "Tenancy ID" cell in the header row
- `unit`             ← "Unit" cell in the header row
- `participant_name` ← "Household" cell in the header row
- `snapshot_date`    ← the date in the subtitle line (e.g. "Activity snapshot ·
                        June 07, 2027" → return "June 07, 2027")
- `ledger_entries`   ← one entry per row in the ledger table:
    - `entry_date`     ← literal date from the Date column (e.g. "06/07/2027")
    - `description`    ← verbatim text from the Journal description column,
                         including em-dashes and spacing
    - `debit_amount`   ← amount from the Debit column. An em-dash "—" or blank
                         means zero — return 0.0, never null.
    - `credit_amount`  ← amount from the Credit / recovery column. An em-dash
                         "—" or blank means zero — return 0.0, never null.
    - `running_balance`← from the Running balance column
    - `source_page`    ← always 1 for this document type

RULES SPECIFIC TO THIS DOCUMENT:
- Preserve row ORDER exactly as printed. Order is load-bearing downstream.
- An em-dash "—" in Debit or Credit means zero. Return 0.0, never null.
- Do NOT compute or correct `running_balance`. Copy what is printed, even if
  it does not add up — a mismatch is a finding for later stages, not an error
  to fix.
- Include every row, including reversals, credits, recoveries, and adjustments.
- Do not skip, merge, or reorder any ledger rows.

DOCUMENT TEXT:
{pages}\
"""
