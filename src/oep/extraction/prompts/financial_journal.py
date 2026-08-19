"""Extraction prompt for Document 2 — Tenancy Financial Journal.

Layout (1 page):
  Header line: "Activity snapshot · <date>"
  Metadata row: Claim ID | Tenancy ID | Unit | Household
  Ledger table columns:
      Date | Journal description | Debit | Credit / recovery | Running balance
  Footer disclaimer.
"""

PROMPT = """\
You are extracting the **Tenancy Financial Journal**.

This document is an accounting-source snapshot showing every debit, credit,
recovery, and reversal through the closeout date. It is always a single page.

Extract the following JSON object from the page-tagged text below.

{{
  "claim_id":         "string — from the Claim ID cell",
  "agreement_id":     "string — from the Tenancy ID cell",
  "unit":             "string — from the Unit cell",
  "participant_name": "string — from the Household cell",
  "statement_date":   "string — verbatim date from the 'Activity snapshot' header line",

  "ledger_entries": [
    {{
      "entry_date":       "string — verbatim date from the Date column",
      "description":      "string — verbatim text from the Journal description column",
      "debit":            "number | null — amount from the Debit column, or null if the cell is '—' or empty",
      "credit":           "number | null — amount from the Credit / recovery column, or null if '—' or empty",
      "running_balance":  "number — from the Running balance column",
      "source_page":      "integer — always 1 for this document type"
    }}
  ],

  "warnings": ["array of strings — any issues found"]
}}

RULES SPECIFIC TO THIS DOCUMENT:
- Every row in the ledger table becomes one entry in `ledger_entries`.
- Preserve the EXACT order of rows as they appear in the table.
- A dash character "—" in the Debit or Credit column means null (no amount),
  NOT zero. Only return a number when an actual dollar figure is printed.
- The `description` field must be copied verbatim, including em-dashes and
  spacing (e.g. "Reletting interval — 4 days at $103.00 per day").
- Do not skip, merge, or reorder any ledger rows.

DOCUMENT TEXT:
{pages}\
"""
