# OEP-27-8150 — Reasoning

**Route**: auto_approve · **Gate**: 100/90 · **STP**: eligible
**Approved**: $958 of $2,726 claimed · **Limit**: $3,265 (does not bind)

Two of five lines are fully expired under the service-life schedule.
One line is partially depreciated. The claim illustrates the "expired component
has no remaining service value" rule from OEP-4.2.

---

## L0 — Carpet replacement · $1,075 → excluded (expired)

Carpet is on an 84-month schedule (OEP-3.6). First use date is 2019-03-27.
Elapsed time to the event date: 96 whole months. Since 96 > 84, the component
is expired. OEP-4.2: "an expired component has no remaining service value."
The entire $1,075 is excluded.

## L1 — Window treatment replacement · $438 → excluded (expired)

Window treatment is on a 96-month schedule (OEP-3.6). First use date is
2018-03-27. Elapsed time: 108 whole months. Since 108 > 96, the component is
expired. No remaining service value under OEP-4.2. The full $438 is excluded.

## L2 — Life-safety work · $606 → covered

Life-safety work is labor for premises restoration, not a scheduled physical
component. The OEP-3.6 schedule lists only specific components (floor finish,
countertop panel, vanity, cabinet front, window treatment, appliance panel,
carpet, door closer). Life-safety work does not appear on this list and
receives no service-life reduction. Under OEP-2.3, it is "reasonable
restoration of direct physical change" supported by evidence. Full amount
covered.

## L3 — Door closer replacement · $528 → $352 covered / $176 excluded

Door closer is on a 72-month schedule (OEP-3.6). First use date is 2025-03-27.
Elapsed = 24 whole months. Remaining = 72 − 24 = 48 months.
Eligible value = $528 × 48/72 = $352.00. The $176 consumed portion is
excluded per OEP-4.2.

## L4 — Closeout handling charge · $79 → excluded

An administrative fee. OEP-3.2 excludes "administrative charges." Excluded in
full.

## Routing

No held amount. All gate checks pass. Covered total ($958) is well below the
limit ($3,265). Gate score 100/90 → auto_approve, STP-eligible.
