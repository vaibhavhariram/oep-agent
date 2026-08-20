# OEP-27-4706 — Reasoning

**Route**: auto_approve · **Gate**: 100/90 · **STP**: eligible
**Approved**: $1,030 of $3,401 claimed · **Limit**: $2,980 (does not bind)

This claim is dominated by service-life depreciation. Four of five lines
involve scheduled components under OEP-4.2 and OEP-3.6. The remaining service
calculation is: gross cost × (remaining whole months / scheduled months),
rounded half-up to cents.

---

## L0 — Floor finish restoration · $960 → $144 covered / $816 excluded

Floor finish is a 120-month scheduled component (OEP-3.6). First use date is
2018-10-09. The elapsed time to the event date is 102 whole months. Remaining
= 120 − 102 = 18 months. Eligible value = $960 × 18/120 = $144.00. The $816
reduction is excluded as the consumed portion of the component's service life
— the amount is "outside a supported interval" under OEP-3.2 when read
alongside OEP-4.2's remaining-service formula.

## L1 — Window treatment replacement · $504 → $63 covered / $441 excluded

Window treatment is a 96-month scheduled component (OEP-3.6). First use date
is 2020-04-09. Elapsed = 84 whole months. Remaining = 96 − 84 = 12 months.
Eligible value = $504 × 12/96 = $63.00.

## L2 — Electrical labor · $715 → $715 covered

Labor charges for restoration work are not subject to the service-life schedule.
OEP-3.6 schedules only physical components (floor finish, countertop panel,
window treatment, carpet, etc.). Electrical labor is a service cost, not a
depreciable component. Under OEP-2.3, it qualifies as "reasonable restoration
of direct physical change" supported by an acceptable work record. No reduction
applies.

## L3 — Countertop panel replacement · $1,080 → $108 covered / $972 excluded

Countertop panel is a 120-month scheduled component (OEP-3.6). First use date
is 2018-04-09. Elapsed = 108 whole months. Remaining = 120 − 108 = 12 months.
Eligible value = $1,080 × 12/120 = $108.00.

## L4 — Standard turnover cleaning · $142 → excluded

OEP-3.2 explicitly excludes "standard turnover." This is ordinary turnover
cleaning, not restoration of direct physical change. Excluded in full.

## Routing

No held amount. All gate checks pass. Covered total ($1,030) is well below the
limit ($2,980). Gate score 100/90 → auto_approve, STP-eligible.
