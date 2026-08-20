# OEP-27-2146 — Reasoning

**Route**: auto_approve · **Gate**: 100/90 · **STP**: eligible
**Approved**: $2,410 of $2,955 claimed · **Limit**: $2,410 (cap binds)

This claim demonstrates the policy-limit cap applied greedily in source order
across multiple covered lines, with no held amounts.

---

## L0 — Patio-door glazing replacement · $916 → covered, approved $916

Glazing replacement is not on the OEP-3.6 service-life schedule (the schedule
lists floor finish, countertop panel, vanity, cabinet front, window treatment,
appliance panel, carpet, and door closer — glazing is not among them).
The work is supported by evidence per OEP-3.4, and qualifies as premises
restoration under OEP-2.3. No service-life reduction. Full amount covered.

Greedy cap: $2,410 remaining → approved $916. Remaining cap budget: $1,494.

## L1 — Kitchen cabinet-face restoration · $842 → covered, approved $842

This is cabinet LABOR — the restoration of cabinet faces, not the replacement
of the cabinet-front material component. The distinction matters: OEP-3.6
assigns 120 months to "cabinet front" (the physical panel/surface), but labor
to restore existing cabinet faces is not a scheduled component replacement.
It is restoration work under OEP-2.3, supported by an acceptable work record.
No service-life reduction applies.

Greedy cap: $1,494 remaining → approved $842. Remaining cap budget: $652.

## L2 — Entry floor restoration · $1,094 → covered, approved $652

Entry floor restoration is labor for direct physical change under OEP-2.3. The
full $1,094 is covered (this is restoration work, not a floor-finish component
replacement that would trigger the 120-month schedule). Evidence is sufficient.

Greedy cap: $652 remaining → approved $652. The cap binds on this line:
$1,094 covered but only $652 approved. Remaining cap budget: $0.

## L3 — Processing charge · $103 → excluded

OEP-3.2 excludes "administrative charges." Excluded in full.

## Routing and cap mechanics

The cap binds: total covered ($2,852) exceeds the limit ($2,410). The greedy
allocation in source order results in: L0 gets $916, L1 gets $842, L2 gets
$652 (capped from $1,094). Total approved = $916 + $842 + $652 = $2,410 =
limit.

No held amount. All gate checks pass. Gate score 100/90 → auto_approve,
STP-eligible. Despite the cap binding, routing is auto_approve because the
cap is a standard arithmetic step (OEP-2.4), not an evidence deficiency.
