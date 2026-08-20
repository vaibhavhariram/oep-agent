"""Internal types and constants for the policy rules engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from oep.models.output import Citation, RuleTraceStep

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

# -------------------------------------------------------------------
# Exclusion table (OEP-3.2): categories excluded in Stage 2
# -------------------------------------------------------------------

EXCLUDED_CATEGORIES: frozenset[str] = frozenset({
    "operator_fee",
    "ordinary_upkeep",
    "upgrade",
    "duplicate",
})

EXCLUSION_RATIONALE: dict[str, str] = {
    "operator_fee": "Administrative charges are excluded.",
    "ordinary_upkeep": "Routine turnover is excluded.",
    "upgrade": "The elective uplift is excluded.",
    "duplicate": "Duplicate source entry is excluded.",
}

# -------------------------------------------------------------------
# Component service schedule (OEP-3.6): exact match, case-insensitive
# -------------------------------------------------------------------

COMPONENT_SCHEDULE: dict[str, int] = {
    "floor finish": 120,
    "carpet": 84,
    "window treatment": 96,
    "countertop panel": 120,
    "countertop": 120,
    "vanity": 120,
    "cabinet front": 120,
    "appliance panel": 96,
    "door closer": 72,
}

# -------------------------------------------------------------------
# Rule-ID by classification (for the final "applied" trace step)
# -------------------------------------------------------------------

RULE_ID_BY_CATEGORY: dict[str, str] = {
    "occupancy_balance": "OEP-2.1",
    "reletting_gap": "OEP-2.2",
    "unit_restoration": "OEP-2.3",
}

# -------------------------------------------------------------------
# Citation by category (for DecisionLine.citations)
# -------------------------------------------------------------------

CITATIONS: dict[str, Citation] = {
    "OEP-2.1": Citation(
        clause_id="OEP-2.1",
        heading="Part A \u2014 occupancy balance",
        source_page=2,
        quote="Part A includes a scheduled occupancy amount remaining at possession return after attributable payments, concessions, reversals, credits, and recoveries are applied once.",
    ),
    "OEP-2.2": Citation(
        clause_id="OEP-2.2",
        heading="Part A \u2014 reletting gap",
        source_page=2,
        quote="Part A includes the rounded daily occupancy value for supported days beginning after possession return and ending at the earliest ready cutoff, replacement occupancy, or thirtieth calendar day after return.",
    ),
    "OEP-2.3": Citation(
        clause_id="OEP-2.3",
        heading="Part B \u2014 premises restoration",
        source_page=2,
        quote="Part B includes reasonable restoration of direct physical change beyond normal aging or ordinary turnover when an acceptable completed-work record separately states the work and charge.",
    ),
    "OEP-3.2": Citation(
        clause_id="OEP-3.2",
        heading="Excluded amounts",
        source_page=3,
        quote="Administrative charges, ordinary upkeep, standard turnover, household-owned property, elective upgrades, duplicate entries, and amounts outside a supported interval are excluded. A duplicate or recovery is removed once, not twice.",
    ),
    "OEP-3.3": Citation(
        clause_id="OEP-3.3",
        heading="Journal evidence",
        source_page=3,
        quote="An occupancy balance or gap requires a tenancy journal identifying the tenancy, scheduled charge, debits, credits, reversals, and recoveries through closeout; an unexplained aggregate or code is unresolved.",
    ),
    "OEP-3.4": Citation(
        clause_id="OEP-3.4",
        heading="Restoration evidence",
        source_page=3,
        quote="A restoration line requires a paid record or executed work order that itemizes completed work and cost. An estimate, missing record, unclear record, or unsupported specialized cleaning need is unresolved.",
    ),
    "OEP-4.1": Citation(
        clause_id="OEP-4.1",
        heading="Ordered calculation",
        source_page=4,
        quote="Reconcile sources, classify lines, remove exclusions and duplicates, preserve unsupported values, apply service and interval boundaries, apply credits and recoveries once, sum eligible values, and finally apply the certificate limit.",
    ),
    "OEP-4.2": Citation(
        clause_id="OEP-4.2",
        heading="Remaining service",
        source_page=4,
        quote="For a scheduled component, eligible service value equals gross cost multiplied by remaining whole months divided by scheduled months, rounded half up to cents; an expired component has no remaining service value.",
    ),
}

CITATIONS_BY_CATEGORY: dict[str, list[Citation]] = {
    "occupancy_balance": [CITATIONS["OEP-2.1"], CITATIONS["OEP-3.3"]],
    "reletting_gap": [CITATIONS["OEP-2.2"], CITATIONS["OEP-3.3"], CITATIONS["OEP-4.1"]],
    "unit_restoration": [CITATIONS["OEP-2.3"], CITATIONS["OEP-3.4"]],
}

# -------------------------------------------------------------------
# Component name parser
# -------------------------------------------------------------------

_COMPONENT_RE = re.compile(r"Component:\s*(.+?)(?:\s*;\s*|$)")
_SERVICE_START_RE = re.compile(r"Service start:\s*(\S+)")


def parse_component(service_life_fact: str | None) -> str | None:
    """Extract component name from a service_life_fact string."""
    if not service_life_fact:
        return None
    m = _COMPONENT_RE.search(service_life_fact)
    return m.group(1).strip() if m else None


def parse_service_start(service_life_fact: str | None) -> str | None:
    """Extract service-start date string from a service_life_fact string."""
    if not service_life_fact:
        return None
    m = _SERVICE_START_RE.search(service_life_fact)
    return m.group(1).strip() if m else None


# -------------------------------------------------------------------
# LineState — mutable per-line working state
# -------------------------------------------------------------------

@dataclass
class LineState:
    """Mutable working state for one submitted line through the rules pipeline."""

    source_index: int
    description: str
    source_page: int
    amount: Decimal           # original gross = claimed, NEVER mutated
    category: str             # source_classification
    documentation_status: str
    reference: str | None
    evidence: str             # "Line N: desc — $X,XXX.XX"
    component: str | None     # parsed from service_life_fact
    service_start: date | None
    gap_start: date | None
    gap_end: date | None
    stated_rate: Decimal | None
    source_document: str

    # Amounts — mutated by stages
    covered: Decimal = ZERO
    excluded: Decimal = ZERO
    held: Decimal = ZERO
    approved: Decimal = ZERO

    rule_trace: list[RuleTraceStep] = field(default_factory=list)
    rationale: str = ""
    status: str = "covered"

    def evidence_anchor(self) -> str:
        """Evidence anchor for this line."""
        return f"{self.source_document}:page:{self.source_page}:line:{self.source_index + 1}"

    def check_invariant(self) -> None:
        """Assert claimed == covered + excluded + held."""
        total = self.covered + self.excluded + self.held
        assert total == self.amount, (
            f"Line {self.source_index}: invariant broken: "
            f"claimed={self.amount} != covered={self.covered} + "
            f"excluded={self.excluded} + held={self.held} (sum={total})"
        )


@dataclass
class RulesResult:
    """Aggregate result from all rules stages."""

    lines: list[LineState]
    warnings: list[str] = field(default_factory=list)
    claimed_total: Decimal = ZERO
    covered_total: Decimal = ZERO
    excluded_total: Decimal = ZERO
    held_total: Decimal = ZERO
    approved_total: Decimal = ZERO
