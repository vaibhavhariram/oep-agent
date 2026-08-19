"""Extraction prompt for Document 4 — Covered Tenancy Certificate.

Layout (4 pages):
  Page 1:  Certificate Schedule table (Policy number, Policy form, Tenancy
           reference, Covered household, Housing operator, Property and unit,
           Covered premises, Certificate period, Monthly occupancy charge,
           Combined protection limit, Certificate deductible).
  Page 2:  Protection Election — Selected parts table (Part A, Part B),
           Limit application text, No independent grant text.
  Page 3:  Certificate Statements — Household statements table,
           Operator statements table.
  Page 4:  Execution Record — Household execution table, Operator execution
           table, Certificate administration table.
"""

PROMPT = """\
You are extracting the **Covered Tenancy Certificate**.

This is the formal protection-election document. It records the policy
details, selected coverage parts, limit, household and operator statements,
and execution signatures.

Extract the following JSON object from the page-tagged text below.

{{
  "policy_number":          "string — from the Policy number row",
  "policy_form":            "string — from the Policy form row",
  "agreement_id":           "string — from the Tenancy reference row",
  "participant_name":       "string — from the Covered household row",
  "operator_name":          "string — from the Housing operator row",
  "property_and_unit":      "string — verbatim from the Property and unit row",
  "covered_premises":       "string — verbatim from the Covered premises row",
  "certificate_period":     "string — verbatim from the Certificate period row (e.g. '04/14/2026 through 04/13/2027')",
  "monthly_occupancy_charge": "number — from the Monthly occupancy charge row",
  "combined_protection_limit": "number — from the Combined protection limit row",
  "certificate_deductible": "number — from the Certificate deductible row",

  "selected_parts": [
    {{
      "part":               "string — verbatim part label (e.g. 'Part A — Occupancy balance and reletting gap')",
      "selection":          "string — e.g. 'Selected' or 'Not selected'",
      "description":        "string — verbatim certificate description",
      "source_page":        "integer — page where this row appears"
    }}
  ],

  "household_statements": [
    {{
      "statement":          "string — verbatim statement text",
      "response":           "string — e.g. 'Acknowledged'",
      "source_page":        "integer"
    }}
  ],

  "operator_statements": [
    {{
      "statement":          "string — verbatim statement text",
      "response":           "string — e.g. 'Confirmed'",
      "source_page":        "integer"
    }}
  ],

  "household_execution": {{
    "printed_name":         "string — from the Printed name cell",
    "execution_date":       "string — verbatim date from the Execution date cell",
    "source_page":          "integer"
  }},

  "operator_execution": {{
    "representative_name":  "string — from the Authorized representative cell",
    "execution_date":       "string — verbatim date from the Execution date cell",
    "source_page":          "integer"
  }},

  "administration": [
    {{
      "field":              "string — from the Administrative field column",
      "value":              "string — from the Recorded value column",
      "source_page":        "integer"
    }}
  ],

  "warnings": ["array of strings — any issues found"]
}}

RULES SPECIFIC TO THIS DOCUMENT:
- The Certificate period contains two dates separated by "through".
  Return the full string verbatim (e.g. "04/14/2026 through 04/13/2027").
  Do NOT split it into separate fields.
- For `selected_parts`, preserve the full Part label including the em-dash and
  description (e.g. "Part A — Occupancy balance and reletting gap").
- The household and operator statement arrays must include EVERY row from
  their respective tables, in order.
- The `household_execution` and `operator_execution` objects capture the
  signature record. Include the printed name / authorized representative
  and the execution date.
- The `administration` array captures the Certificate administration table
  on page 4 (issuing carrier, certificate ID, effective/expiry dates, etc.).

DOCUMENT TEXT:
{pages}\
"""
