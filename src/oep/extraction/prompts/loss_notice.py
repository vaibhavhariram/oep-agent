"""Extraction prompt for Document 1 — Loss Notice and Record Index.

Layout (2 pages):
  Page 1:  Header metadata table (Claim ID, Policy number, Tenancy ID,
           Covered household, Property, Address, Unit, Monthly charge,
           Selected limit, Possession returned).
           Reported event table (Tenancy start, Report date, Closeout
           statement date, Event narrative).
           Amount presented table (Source register, Gross amount, TOTAL).
  Page 2:  Record Index table (Registered record, Packet status, Factual scope).
           Reporting certification (Preparer, Role, Contact, Certification date).
"""

PROMPT = """\
You are extracting the **Loss Notice and Record Index**.

This document is the administrative cover sheet for the claim. It contains
high-level metadata, the reported event, the gross amount presented, and
an index of which records are included in the packet.

Extract the following JSON object from the page-tagged text below.

{{
  "claim_id":           "string — from the Claim ID field",
  "agreement_id":       "string — from the Tenancy ID field",
  "policy_number":      "string — from the Policy number field",
  "policy_form":        "string — from the Policy form field",
  "participant_name":   "string — from the Covered household field",
  "operator_name":      "string — from the Operator field",
  "property_name":      "string — from the Property field",
  "unit":               "string — from the Unit field",
  "property_address":   "string — from the Property address field",
  "monthly_charge":     "number — from the Monthly charge field",
  "selected_limit":     "number — from the Selected limit field",
  "possession_returned":"string — verbatim date from the Possession returned field",

  "tenancy_start":      "string — verbatim date from the Tenancy start row",
  "report_date":        "string — verbatim date from the Report date row",
  "closeout_statement_date": "string — verbatim date from the Closeout statement date row",
  "event_narrative":    "string — verbatim text of the Event narrative",

  "amount_presented": [
    {{
      "source_register": "string — name of the source register",
      "gross_amount":    "number"
    }}
  ],
  "total_presented":    "number — the TOTAL PRESENTED figure",

  "record_index": [
    {{
      "registered_record": "string — document name",
      "packet_status":     "string — e.g. Included, See source register",
      "factual_scope":     "string — verbatim scope description",
      "source_page":       "integer — page where this row appears"
    }}
  ],

  "certification_date": "string | null — verbatim date from reporting certification",
  "preparer_name":      "string | null — preparer name and affiliation",

  "warnings": ["array of strings — any issues found"]
}}

DOCUMENT TEXT:
{pages}\
"""
