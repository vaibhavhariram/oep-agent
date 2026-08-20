"""Canonical 16-clause policy store for OEP-2027-SYN.

Source of truth for clause texts, headings, and page numbers.
Clause numbering is NOT document order — OEP-3.6 sits on page 4.
"""

from __future__ import annotations

from oep.models.output import PolicyClause


CLAUSE_STORE: list[PolicyClause] = [
    PolicyClause(
        clause_id="OEP-1.1", heading="Coverage agreement", source_page=1,
        text="The program determines an eligible amount only for a protected residential tenancy and only after every source line has been classified, evidenced, valued, and reconciled under this form.",
        evidence="The program determines an eligible amount only for a protected residential tenancy and only after every source line has been classified, evidenced, valued, and reconciled under this form.",
    ),
    PolicyClause(
        clause_id="OEP-1.2", heading="Covered tenancy", source_page=1,
        text="A covered tenancy is the executed occupancy arrangement identified on the certificate when the possession-return event occurs during the stated certificate period.",
        evidence="A covered tenancy is the executed occupancy arrangement identified on the certificate when the possession-return event occurs during the stated certificate period.",
    ),
    PolicyClause(
        clause_id="OEP-1.3", heading="Defined terms", source_page=1,
        text="Source line means one separately presented charge. Ready cutoff means the earliest supported date on which the premises could accept a replacement household. Unresolved amount means a value that lacks a determinative source fact.",
        evidence="Source line means one separately presented charge. Ready cutoff means the earliest supported date on which the premises could accept a replacement household. Unresolved amount means a value that lacks a determinative source fact.",
    ),
    PolicyClause(
        clause_id="OEP-2.1", heading="Part A \u2014 occupancy balance", source_page=2,
        text="Part A includes a scheduled occupancy amount remaining at possession return after attributable payments, concessions, reversals, credits, and recoveries are applied once.",
        evidence="Part A includes a scheduled occupancy amount remaining at possession return after attributable payments, concessions, reversals, credits, and recoveries are applied once.",
    ),
    PolicyClause(
        clause_id="OEP-2.2", heading="Part A \u2014 reletting gap", source_page=2,
        text="Part A includes the rounded daily occupancy value for supported days beginning after possession return and ending at the earliest ready cutoff, replacement occupancy, or thirtieth calendar day after return.",
        evidence="Part A includes the rounded daily occupancy value for supported days beginning after possession return and ending at the earliest ready cutoff, replacement occupancy, or thirtieth calendar day after return.",
    ),
    PolicyClause(
        clause_id="OEP-2.3", heading="Part B \u2014 premises restoration", source_page=2,
        text="Part B includes reasonable restoration of direct physical change beyond normal aging or ordinary turnover when an acceptable completed-work record separately states the work and charge.",
        evidence="Part B includes reasonable restoration of direct physical change beyond normal aging or ordinary turnover when an acceptable completed-work record separately states the work and charge.",
    ),
    PolicyClause(
        clause_id="OEP-2.4", heading="Combined limit", source_page=2,
        text="Eligible Part A and Part B values share the single certificate limit, which is applied after line-level classification and valuation and never operates as evidence of loss.",
        evidence="Eligible Part A and Part B values share the single certificate limit, which is applied after line-level classification and valuation and never operates as evidence of loss.",
    ),
    PolicyClause(
        clause_id="OEP-3.1", heading="Classification rule", source_page=2,
        text="Each submitted source line must receive one normalized classification. A coded, lump-sum, or otherwise indeterminate line remains unresolved until its nature can be established.",
        evidence="Each submitted source line must receive one normalized classification. A coded, lump-sum, or otherwise indeterminate line remains unresolved until its nature can be established.",
    ),
    PolicyClause(
        clause_id="OEP-3.2", heading="Excluded amounts", source_page=3,
        text="Administrative charges, ordinary upkeep, standard turnover, household-owned property, elective upgrades, duplicate entries, and amounts outside a supported interval are excluded. A duplicate or recovery is removed once, not twice.",
        evidence="Administrative charges, ordinary upkeep, standard turnover, household-owned property, elective upgrades, duplicate entries, and amounts outside a supported interval are excluded. A duplicate or recovery is removed once, not twice.",
    ),
    PolicyClause(
        clause_id="OEP-3.3", heading="Journal evidence", source_page=3,
        text="An occupancy balance or gap requires a tenancy journal identifying the tenancy, scheduled charge, debits, credits, reversals, and recoveries through closeout; an unexplained aggregate or code is unresolved.",
        evidence="An occupancy balance or gap requires a tenancy journal identifying the tenancy, scheduled charge, debits, credits, reversals, and recoveries through closeout; an unexplained aggregate or code is unresolved.",
    ),
    PolicyClause(
        clause_id="OEP-3.4", heading="Restoration evidence", source_page=3,
        text="A restoration line requires a paid record or executed work order that itemizes completed work and cost. An estimate, missing record, unclear record, or unsupported specialized cleaning need is unresolved.",
        evidence="A restoration line requires a paid record or executed work order that itemizes completed work and cost. An estimate, missing record, unclear record, or unsupported specialized cleaning need is unresolved.",
    ),
    PolicyClause(
        clause_id="OEP-3.5", heading="Conflict rule", source_page=3,
        text="A material disagreement among identifiers, dates, amounts, evidence status, or source facts must be retained with provenance; a value-changing disagreement remains unresolved unless a governing source resolves it.",
        evidence="A material disagreement among identifiers, dates, amounts, evidence status, or source facts must be retained with provenance; a value-changing disagreement remains unresolved unless a governing source resolves it.",
    ),
    PolicyClause(
        clause_id="OEP-4.1", heading="Ordered calculation", source_page=4,
        text="Reconcile sources, classify lines, remove exclusions and duplicates, preserve unsupported values, apply service and interval boundaries, apply credits and recoveries once, sum eligible values, and finally apply the certificate limit.",
        evidence="Reconcile sources, classify lines, remove exclusions and duplicates, preserve unsupported values, apply service and interval boundaries, apply credits and recoveries once, sum eligible values, and finally apply the certificate limit.",
    ),
    PolicyClause(
        clause_id="OEP-4.2", heading="Remaining service", source_page=4,
        text="For a scheduled component, eligible service value equals gross cost multiplied by remaining whole months divided by scheduled months, rounded half up to cents; an expired component has no remaining service value.",
        evidence="For a scheduled component, eligible service value equals gross cost multiplied by remaining whole months divided by scheduled months, rounded half up to cents; an expired component has no remaining service value.",
    ),
    PolicyClause(
        clause_id="OEP-3.6", heading="Component service schedule", source_page=4,
        text="The schedule assigns 120 months to floor finish, countertop panel, vanity, and cabinet front; 96 months to window treatment and appliance panel; 84 months to carpet; and 72 months to a door closer.",
        evidence="The schedule assigns 120 months to floor finish, countertop panel, vanity, and cabinet front; 96 months to window treatment and appliance panel; 84 months to carpet; and 72 months to a door closer.",
    ),
    PolicyClause(
        clause_id="OEP-5.1", heading="Notice and determination record", source_page=4,
        text="Notice is due within 105 days after possession return. The determination must retain source-page provenance, citations, line mathematics, unresolved values, verification and routing rationale, and a preview that performs no external write.",
        evidence="Notice is due within 105 days after possession return. The determination must retain source-page provenance, citations, line mathematics, unresolved values, verification and routing rationale, and a preview that performs no external write.",
    ),
]

CLAUSE_BY_ID: dict[str, PolicyClause] = {c.clause_id: c for c in CLAUSE_STORE}
