"""Extraction prompt for Document 4 — Covered Tenancy Certificate.

Layout (4 pages):
  Page 1:  Certificate Schedule table (Policy number, Policy form, Tenancy
           reference, Covered household, Housing operator, Property and unit,
           Covered premises, Certificate period, Monthly occupancy charge,
           Combined protection limit, Certificate deductible).
  Page 2:  Protection Election — Selected parts table (Part, Selection,
           Certificate description), Limit application text.
  Page 3:  Certificate Statements — Household statements table,
           Operator statements table.
  Page 4:  Execution Record — Household execution, Operator execution,
           Certificate administration table.

Populates limit_mentions and the protection period.
No claim_id field — the claim id does not appear on this document.
"""

PROMPT = """\
You are extracting the **Covered Tenancy Certificate**.

This is the formal protection-election document. It records the policy
details, selected coverage parts, limit, household and operator statements,
and execution signatures.

The claim id does NOT appear on this document. There is no `claim_id` field.
The packet supplies the claim id separately.

Extract the following JSON object from the page-tagged text below.

{{
  "policy_number":          "string or null",
  "policy_form":            "string or null",
  "agreement_id":           "string or null",
  "participant_name":       "string or null",
  "operator":               "string or null",
  "property_and_unit":      "string or null",
  "protected_location":     "string or null",
  "certificate_period_raw": "string or null",
  "monthly_charge":         "number or null",
  "combined_limit":         "number or null",
  "deductible":             "number or null",

  "selected_parts": [
    {{"part": "string", "selection": "string", "description": "string", "source_page": "int"}}
  ],
  "limit_application_text": "string or null",

  "household_statements": [
    {{"statement": "string", "response": "string", "source_page": "int"}}
  ],
  "operator_statements": [
    {{"statement": "string", "response": "string", "source_page": "int"}}
  ],
  "executions": [
    {{"party": "string", "printed_name": "string", "signature_record": "string",
     "execution_date": "string", "source_page": "int"}}
  ],
  "issuing_carrier":        "string or null",
  "program":                "string or null",
  "master_form":            "string or null",
  "warnings":               ["string"]
}}

FIELD MAPPING:
- `policy_number`          ← "Policy number" row in Certificate Schedule
- `policy_form`            ← "Policy form" row
- `agreement_id`           ← "Tenancy reference" row
- `participant_name`       ← "Covered household" row
- `operator`               ← "Housing operator" row
- `property_and_unit`      ← "Property and unit" row — verbatim
- `protected_location`     ← "Covered premises" row — verbatim
- `certificate_period_raw` ← "Certificate period" row — the WHOLE printed string,
                              unsplit (e.g. "09/28/2026 through 09/27/2027").
                              Splitting into start/end happens downstream.
- `monthly_charge`         ← "Monthly occupancy charge" row
- `combined_limit`         ← "Combined protection limit" row
- `deductible`             ← "Certificate deductible" row

- `selected_parts`         ← the Selected parts table on page 2. Record
                              `selection` verbatim ("Selected" / "Not selected" /
                              whatever is printed). A part that is not selected
                              changes coverage downstream.
- `limit_application_text` ← the paragraph under "Limit application" on page 2,
                              verbatim

- `household_statements`   ← every row in the Household statements table (page 3)
- `operator_statements`    ← every row in the Operator statements table (page 3)

- `executions`             ← both the Household execution and Operator execution
                              from page 4, as entries in one array:
    - `party`            ← "Household" or "Operator"
    - `printed_name`     ← "Printed name" cell or "Authorized representative" cell
    - `signature_record` ← "Electronic signature record" cell — verbatim
    - `execution_date`   ← "Execution date" cell — verbatim date string

- `issuing_carrier`        ← from Certificate administration table (page 4)
- `program`                ← from Certificate administration table (page 4)
- `master_form`            ← from Certificate administration table (page 4)

RULES SPECIFIC TO THIS DOCUMENT:
- This document is 4 pages. `source_page` must reflect the real page of each
  item: Schedule p1, Protection Election p2, Statements p3, Execution Record p4.
- There is NO `claim_id` field. The claim id does not appear on this document.
  Do not invent one.
- `certificate_period_raw` must be the WHOLE string unsplit.
- `selected_parts`: preserve the full Part label including the em-dash
  (e.g. "Part A \u2014 Occupancy balance and reletting gap").
- `executions` combines household and operator executions into a single array.
  Use `party` to distinguish ("Household" vs "Operator").

DOCUMENT TEXT:
{pages}\
"""
