"""Extraction prompt for Document 3 — Source Register.

Covers BOTH document types that appear in position 3:
  - Restoration Cost Register
  - Premises Condition Log

Both share an identical two-page layout:
  Page 1:  Header metadata table, then "Presented source lines" table
           (Line | Source description | Source category | Gross amount).
  Page 2:  "Source Record Register" table
           (Line | Record status | Record reference | Service-life, interval, or condition fact).
           "Factual observations" table
           (Observation | Recorded fact).
"""

PROMPT = """\
You are extracting a **source register** (either Restoration Cost Register
or Premises Condition Log — both have the same layout).

This document contains the line-by-line itemization of the claim and the
per-line evidence status.

Extract the following JSON object from the page-tagged text below.

{{
  "document_title":       "string — the title line, e.g. 'Restoration Cost Register' or 'Premises Condition Log'",
  "claim_id":             "string — from the Claim ID field",
  "agreement_id":         "string — from the Tenancy ID field",
  "policy_number":        "string — from the Policy number field",
  "policy_form":          "string — from the Policy form field",
  "participant_name":     "string — from the Covered household field",
  "operator_name":        "string — from the Operator field",
  "property_name":        "string — from the Property field",
  "unit":                 "string — from the Unit field",
  "property_address":     "string — from the Property address field",
  "monthly_charge":       "number — from the Monthly charge field",
  "selected_limit":       "number — from the Selected limit field",
  "possession_returned":  "string — verbatim date from the Possession returned field",

  "source_lines": [
    {{
      "line_number":        "integer — from the Line column (1-based)",
      "description":        "string — verbatim text from the Source description column",
      "category":           "string — verbatim text from the Source category column",
      "gross_amount":       "number — from the Gross amount column",
      "source_page":        "integer — page where this line appears (typically 1)"
    }}
  ],

  "record_register": [
    {{
      "line_number":        "integer — matches the line_number in source_lines",
      "record_status":      "string — verbatim text from the Record status column",
      "record_reference":   "string — verbatim text from the Record reference column (including 'None stated')",
      "service_life_note":  "string — verbatim text from the Service-life, interval, or condition fact column",
      "source_page":        "integer — page where this row appears (typically 2)"
    }}
  ],

  "factual_observations": [
    {{
      "observation":        "string — from the Observation column",
      "recorded_fact":      "string — verbatim text from the Recorded fact column",
      "source_page":        "integer — page where this row appears"
    }}
  ],

  "warnings": ["array of strings — any issues found"]
}}

RULES SPECIFIC TO THIS DOCUMENT:
- There are two tables that share line numbers: "Presented source lines" (page 1)
  and "Source Record Register" (page 2). Extract both and keep them as separate
  arrays. They are joined by `line_number` during normalization.
- The `description` field must be copied verbatim, preserving em-dashes, spacing,
  and any embedded rate or day-count text
  (e.g. "Reletting interval — 4 days at $103.00 per day").
- The `category` field must be copied verbatim from the Source category column
  (e.g. "Occupancy balance", "Premises restoration", "Reletting gap",
  "Upgrade or elective improvement", "Fee or service charge").
  Do NOT normalize or map these values.
- The `record_status` field must be copied verbatim from the Record status column
  (e.g. "Supported by tenancy journal", "Paid record supplied",
  "Executed work order supplied", "Record not applicable",
  "No record supplied", "Estimate supplied").
  Do NOT normalize these values.
- The `record_reference` field: copy the exact text, including "None stated"
  when that appears. Do NOT convert "None stated" to null.
- The `service_life_note` field: copy the full text verbatim. This may contain
  component names, service start dates, gap date ranges with rates, or
  "No additional service-life or interval fact stated".
- Factual observations always include "Possession return" and
  "Ready or replacement cutoff" (which may be "Not stated") and
  "Condition evidence".

DOCUMENT TEXT:
{pages}\
"""
