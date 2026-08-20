"""Tests for Stage 5 — Reletting gap boundary (OEP-2.2).

Acceptance values verified against the specification.
"""

from datetime import date
from decimal import Decimal

import pytest

from oep.extraction.schemas import RawFactualObservation
from oep.rules._stage5_gap import parse_ready_cutoff, run_stage5
from oep.rules._types import ZERO, LineState

D = Decimal


def _gap_line(amount, gap_start, gap_end, rate):
    return LineState(
        source_index=0, description="Gap", source_page=1,
        amount=D(amount), category="reletting_gap",
        documentation_status="sufficient", reference=None,
        evidence="Line 1: Gap", component=None, service_start=None,
        gap_start=gap_start, gap_end=gap_end, stated_rate=D(rate),
        source_document="3_Restoration_Cost_Register.docx",
        covered=D(amount), excluded=ZERO, held=ZERO, approved=ZERO,
    )


def _obs(cutoff_str):
    return [
        RawFactualObservation(
            observation="Ready or replacement cutoff",
            recorded_fact=cutoff_str,
            source_page=2,
        ),
    ]


def test_parse_ready_cutoff():
    obs = _obs("02/05/2027")
    assert parse_ready_cutoff(obs) == date(2027, 2, 5)


def test_parse_ready_cutoff_not_stated():
    obs = [RawFactualObservation(
        observation="Ready or replacement cutoff",
        recorded_fact="Not stated",
        source_page=2,
    )]
    assert parse_ready_cutoff(obs) is None


# -------------------------------------------------------------------
# Acceptance: OEP-27-2849 — gap trimmed
# -------------------------------------------------------------------

def test_2849_gap_trimmed():
    """possession 01/23, gap 01/24..02/13 (21d@$73=$1533), cutoff 02/05.
    Supported = 13d = $949, excluded = 8d = $584.
    """
    ls = _gap_line("1533.00", date(2027, 1, 24), date(2027, 2, 13), "73.00")
    run_stage5([ls], event_date=date(2027, 1, 23), factual_observations=_obs("02/05/2027"))
    assert ls.covered == D("949.00")
    assert ls.excluded == D("584.00")
    assert ls.status == "partially_covered"
    # Invariant
    assert ls.amount == ls.covered + ls.excluded + ls.held


# -------------------------------------------------------------------
# Acceptance: no-trim cases
# -------------------------------------------------------------------

def test_5804_no_trim():
    """7 days @ $61, cutoff=gap end → $427 covered."""
    ls = _gap_line("427.00", date(2027, 9, 13), date(2027, 9, 19), "61.00")
    run_stage5([ls], event_date=date(2027, 9, 12), factual_observations=_obs("09/19/2027"))
    assert ls.covered == D("427.00")
    assert ls.excluded == ZERO


def test_6795_no_trim():
    """11 days @ $69, cutoff=gap end → $759 covered."""
    ls = _gap_line("759.00", date(2027, 6, 14), date(2027, 6, 24), "69.00")
    run_stage5([ls], event_date=date(2027, 6, 13), factual_observations=_obs("06/24/2027"))
    assert ls.covered == D("759.00")
    assert ls.excluded == ZERO


def test_9062_no_trim():
    """4 days @ $103, cutoff=gap end → $412 covered."""
    ls = _gap_line("412.00", date(2027, 2, 5), date(2027, 2, 8), "103.00")
    run_stage5([ls], event_date=date(2027, 2, 4), factual_observations=_obs("02/08/2027"))
    assert ls.covered == D("412.00")
    assert ls.excluded == ZERO


# -------------------------------------------------------------------
# 30-day cap
# -------------------------------------------------------------------

def test_thirty_day_cap():
    """If no ready cutoff stated, 30-day cap applies."""
    ls = _gap_line("3650.00", date(2027, 2, 1), date(2027, 3, 20), "100.00")
    run_stage5([ls], event_date=date(2027, 1, 31), factual_observations=[])
    # 30 days from 01/31 → 03/02; gap starts 02/01, cutoff 03/02
    # Supported = 02/01..03/02 = 30 days = $3000
    assert ls.covered == D("3000.00")
    assert ls.excluded == D("650.00")
    assert ls.status == "partially_covered"


# -------------------------------------------------------------------
# Non-gap lines unaffected
# -------------------------------------------------------------------

def test_non_gap_line_skipped():
    ls = LineState(
        source_index=0, description="Wall repair", source_page=1,
        amount=D("1000.00"), category="unit_restoration",
        documentation_status="sufficient", reference=None,
        evidence="Line 1: Wall repair", component=None, service_start=None,
        gap_start=None, gap_end=None, stated_rate=None,
        source_document="3_Restoration_Cost_Register.docx",
        covered=D("1000.00"), excluded=ZERO, held=ZERO, approved=ZERO,
    )
    run_stage5([ls], event_date=date(2027, 1, 23), factual_observations=[])
    assert ls.covered == D("1000.00")
