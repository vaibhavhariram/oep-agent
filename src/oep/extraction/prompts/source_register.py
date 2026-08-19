"""Extraction prompt for Document 3 — Source Register.

Covers BOTH document types that appear in position 3:
  - Restoration Cost Register
  - Premises Condition Log

Structurally identical — only the title differs.
  Page 1:  Identity header + "Presented source lines" table
           (Line | Source description | Source category | Gross amount).
  Page 2:  "Source Record Register" table
           (Line | Record status | Record reference | Service-life, interval,
           or condition fact).
           "Factual observations" table
           (Observation | Recorded fact).

Populates submitted_lines.
"""

PROMPT = """\
You are extracting a **source register** (either Restoration Cost Register
or Premises Condition Log — both have the same layout).

This document contains the line-by-line itemization of the claim and the
per-line evidence status.

Extract the following JSON object from the page-tagged text below.

{{
  "document_title":       "string",
  "claim_id":             "string or null",
  "policy_number":        "string or null",
  "agreement_id":         "string or null",
  "policy_form":          "string or null",
  "participant_name":     "string or null",
  "operator":             "string or null",
  "property_name":        "string or null",
  "unit":                 "string or null",
  "protected_location":   "string or null",
  "monthly_charge":       "number or null",
  "possession_returned":  "string or null",
  "selected_limit":       "number or null",

  "presented_source_lines": [
    {{
      "line_number":    "int",
      "description":    "string",
      "source_category":"string",
      "gross_amount":   "number",
      "source_page":    "int"
    }}
  ],

  "source_record_register": [
    {{
      "line_number":      "int",
      "record_status":    "string",
      "record_reference": "string or null",
      "service_life_fact":"string or null",
      "source_page":      "int"
    }}
  ],

  "factual_observations": [
    {{"observation": "string", "recorded_fact": "string", "source_page": "int"}}
  ],

  "warnings":             ["string"]
}}

FIELD MAPPING:
- `document_title`      ← the title line printed at the top of the document,
                           exactly as it appears (e.g. "Restoration Cost Register"
                           or "Premises Condition Log")
- `claim_id`            ← "Claim ID" field
- `policy_number`       ← "Policy number" field
- `agreement_id`        ← "Tenancy ID" field
- `policy_form`         ← "Policy form" field
- `participant_name`    ← "Covered household" field
- `operator`            ← "Operator" field
- `property_name`       ← "Property" field
- `unit`                ← "Unit" field
- `protected_location`  ← "Property address" field
- `monthly_charge`      ← "Monthly charge" field
- `possession_returned` ← "Possession returned" field — literal date string
- `selected_limit`      ← "Selected limit" field

PRESENTED SOURCE LINES (page 1 table):
- `line_number`     ← "Line" column (1-based, as printed)
- `description`     ← "Source description" column — verbatim, preserving
                       em-dashes and embedded rates (e.g. "Reletting interval
                       \u2014 4 days at $103.00 per day")
- `source_category` ← "Source category" column — verbatim, e.g. "Occupancy
                       balance", "Premises restoration", "Reletting gap",
                       "Upgrade or elective improvement", "Fee or service charge".
                       Do NOT normalize or map these values.
- `gross_amount`    ← "Gross amount" column
- `source_page`     ← must be the actual page (typically 1)

SOURCE RECORD REGISTER (page 2 table):
- `line_number`      ← matches the line_number in presented_source_lines
- `record_status`    ← "Record status" column — copy VERBATIM. Do not normalize.
                        Real observed values include:
                          "No supporting record supplied"
                          "Estimate only \u2014 work unfinished"
                          "Paid record or executed work order supplied"
                          "Paid record supplied"
                          "Executed work order supplied"
                          "Record not applicable"
                          "Supported by tenancy journal"
                        Other wordings may appear — copy whatever is printed.
- `record_reference` ← "Record reference" column. Return null when the cell
                        reads "None stated". Otherwise copy verbatim
                        (e.g. "AQ-INV-4103", "AQ-WO-4107", "TJF-4103-A").
- `service_life_fact`← "Service-life, interval, or condition fact" column.
                        Copy the whole cell verbatim; do not parse it. May state
                        a component (e.g. "Component: cabinet labor"), a
                        service start date, gap date ranges with rates, or
                        "No additional service-life or interval fact stated".
                        Return null only if the cell is blank.
- `source_page`      ← must be the actual page (typically 2)

FACTUAL OBSERVATIONS (page 2 table):
- `observation`   ← "Observation" column
- `recorded_fact` ← "Recorded fact" column — verbatim
- `source_page`   ← must be the actual page (typically 2)

RULES SPECIFIC TO THIS DOCUMENT:
- The two line-item tables live on DIFFERENT PAGES. `presented_source_lines`
  is page 1; `source_record_register` and `factual_observations` are page 2.
  Set `source_page` per item accordingly — do not assume page 1 for everything.
- Join the tables ONLY by `line_number`. Never re-order or re-match by
  description or amount.
- If a line number appears in one table but not the other, still emit it in
  the table where it appears, and add a `warnings` entry.

DOCUMENT TEXT:
{pages}\
"""
