"""Extraction prompt for Document 1 — Loss Notice and Record Index.

Layout (2 pages):
  Page 1:  Identity header table (Claim ID, Policy number, Tenancy ID,
           Covered household, Operator, Property, Unit, Property address,
           Monthly charge, Selected limit, Possession returned).
           "Reported event" table (Tenancy start, Report date, Closeout
           statement date, Event narrative).
           "Amount presented" table (Source register, Gross amount, TOTAL).
  Page 2:  "Record Index" table (Registered record, Packet status, Factual scope).
           "Reporting certification" (Preparer, Role, Contact, Certification date).

Populates limit_mentions and document-level record availability.
"""

PROMPT = """\
You are extracting the **Loss Notice and Record Index**.

This document is the administrative cover sheet for the claim. It contains
high-level metadata, the reported event, the gross amount presented, and
an index of which records are included in the packet.

Extract the following JSON object from the page-tagged text below.

{{
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
  "tenancy_start":        "string or null",
  "report_date":          "string or null",
  "statement_date":       "string or null",
  "event_narrative":      "string or null",
  "presented_amounts": [
    {{"source_register": "string", "gross_amount": "number", "source_page": "int"}}
  ],
  "total_presented":      "number or null",
  "record_index": [
    {{"registered_record": "string", "packet_status": "string",
     "factual_scope": "string", "source_page": "int"}}
  ],
  "prepared_by":          "string or null",
  "certification_date":   "string or null",
  "warnings":             ["string"]
}}

FIELD MAPPING:
- `claim_id`           ← "Claim ID" field
- `policy_number`      ← "Policy number" field
- `agreement_id`       ← "Tenancy ID" field
- `policy_form`        ← "Policy form" field
- `participant_name`   ← "Covered household" field
- `operator`           ← "Operator" field
- `property_name`      ← "Property" field
- `unit`               ← "Unit" field
- `protected_location` ← "Property address" field — the full address line,
                          including unit only if the address line itself includes it
- `monthly_charge`     ← "Monthly charge" field
- `possession_returned`← "Possession returned" field — literal date string
- `selected_limit`     ← "Selected limit" field
- `tenancy_start`      ← "Tenancy start" row in Reported event
- `report_date`        ← "Report date" row in Reported event
- `statement_date`     ← "Closeout statement date" row in Reported event
- `event_narrative`    ← "Event narrative" row in Reported event
- `presented_amounts`  ← each row in the "Amount presented" table (NOT the total)
- `total_presented`    ← the "TOTAL PRESENTED" figure
- `record_index`       ← the table on page 2 listing which RECORD TYPES are in
                          the packet. Copy `registered_record` and `packet_status`
                          verbatim — e.g. "Premises condition evidence" / "Not
                          included". Do not interpret them.
- `prepared_by`        ← preparer name and affiliation from Reporting certification
- `certification_date` ← verbatim date from Reporting certification

DOCUMENT TEXT:
{pages}\
"""
