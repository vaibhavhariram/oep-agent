# OEP-27-5804 — Reasoning

**Route**: partial_approve_with_hold · **Gate**: 90/90 · **STP**: not eligible
**Approved**: $1,995 of $3,297 claimed · **Limit**: $2,640 (does not bind)

One line is held for missing evidence, which drops the gate to 90 (the
unresolved_evidence check fails) and forces the route to
partial_approve_with_hold.

---

## L0 — Drywall and finish restoration · $1,163 → covered

Drywall restoration is labor for direct physical change, supported by a paid
record. Under OEP-2.3, it qualifies as premises restoration with evidence per
OEP-3.4. Drywall work is not a scheduled component on OEP-3.6's list — no
service-life reduction applies. Full amount covered.

## L1 — Reletting interval · $427 → covered

The claim presents 7 days at $61/day. Under OEP-2.2, the gap runs from the
day after possession return until the earliest of: ready cutoff, replacement
occupancy, or 30th calendar day. The ready cutoff is 09/19, which equals the
gap end date — no trimming. All 7 days are supported. Covered = 7 × $61 =
$427.

## L2 — Entry floor finish replacement · $648 → $405 covered / $243 excluded

Floor finish is a 120-month scheduled component (OEP-3.6). First use date is
2023-12-12. Elapsed = 45 whole months. Remaining = 120 − 45 = 75 months.
Eligible value = $648 × 75/120 = $405.00. The $243 consumed portion is
excluded per OEP-4.2.

## L3 — Isolation valve replacement · $958 → held

No supporting record (paid record or executed work order) is supplied for this
line. OEP-3.4 requires "a paid record or executed work order that itemizes
completed work and cost." Without one, the line is unresolved. The amount is
held pending evidence review.

## L4 — Administrative charge · $101 → excluded

OEP-3.2 excludes "administrative charges." Excluded in full.

## Routing

The unresolved_evidence gate check fails because L3 ($958) is a material held
amount. The four hard-fail checks (source_integrity, reconciliation,
policy_support, amount_safety) all pass, so there is no hard gate failure.
Score = 90/90 (passes threshold, but held amount prevents auto-approval).
Route is partial_approve_with_hold: the $1,995 covered portion is approved,
while the $958 held amount requires human review.
