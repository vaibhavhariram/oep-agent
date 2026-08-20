# OEP-27-4358 — Reasoning

**Route**: partial_approve_with_hold · **Gate**: 90/90 · **STP**: not eligible
**Approved**: $2,385 of $4,390 claimed · **Limit**: $2,385 (cap binds)

This claim demonstrates the policy-limit cap applied greedily in source order,
combined with a held line for missing evidence.

---

## L0 — Completed kitchen and wall restoration · $2,546 → covered, approved $2,385

The restoration is supported by a completed-work record and qualifies under
OEP-2.3 with evidence per OEP-3.4. The full $2,546 is covered — the line
item itself is legitimate and fully evidenced.

However, OEP-2.4 provides that "eligible Part A and Part B values share the
single certificate limit, which is applied after line-level classification
and valuation." The policy limit is $2,385. Since L0 is the first covered
line in source order, the greedy cap allocates min($2,546, $2,385) = $2,385
to this line. The remaining $161 of covered amount ($2,546 − $2,385) is the
portion that exceeds the cap but is still correctly classified as "covered"
— the cap operates on approval, not on coverage classification.

## L1 — Additional cabinet supplement · $1,738 → held

No supporting record is supplied. OEP-3.4 requires "a paid record or executed
work order that itemizes completed work and cost." Without one, this amount is
unresolved and held pending human review. Even if this line were resolved and
covered, the cap is already exhausted by L0 — the approved amount would
remain $0 for this line regardless.

## L2 — Reopening processing charge · $106 → excluded

OEP-3.2 excludes "administrative charges." A reopening processing charge is
an operator-imposed administrative fee. Excluded in full.

## Routing and cap mechanics

The cap binds: covered amount ($2,546) exceeds the policy limit ($2,385).
The approved amount equals the limit exactly. The greedy allocation in source
order means L0 absorbs the full cap budget; any subsequent covered lines
would receive $0 of approved amount.

The held L1 ($1,738) causes the unresolved_evidence gate check to fail.
Gate score = 90/90. Route = partial_approve_with_hold. STP is not eligible
because of the unresolved material amount.
