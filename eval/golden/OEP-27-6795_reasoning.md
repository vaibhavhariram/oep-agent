# OEP-27-6795 — Reasoning

**Route**: auto_approve · **Gate**: 100/90 · **STP**: eligible
**Approved**: $2,556 of $5,292 claimed · **Limit**: $3,190 (does not bind)

This claim has two complicating factors: a duplicate line and a post-closeout
recovery. Both require careful application of OEP-3.2's "removed once, not
twice" rule.

---

## L0 — Primary wall and trim restoration · $1,944 → $1,261 covered / $683 excluded

The restoration is supported by a paid record and qualifies under OEP-2.3.
Before the recovery adjustment, the full $1,944 would be covered.

However, the journal records a $683 post-closeout recovery. Under OEP-2.1 and
OEP-4.1, recoveries are "applied once." This $683 must be subtracted from the
covered total. The golden follows the documented convention of greedy
attribution in source order: the recovery is applied against L0 first,
reducing its covered amount from $1,944 to $1,261 and producing $683 of
excluded amount on this line.

**Important caveat**: The policy does not specify which line a recovery offsets.
The line-level attribution of the recovery (L0 vs. spreading across multiple
lines) is a convention choice. The case-level totals (covered $2,556, excluded
$2,736) are firm. The per-line split of the recovery should be scored as
convention, not ground truth. An implementation that attributes the recovery
to a different line but reaches the same case totals is not wrong — it merely
follows a different convention.

## L1 — Reletting interval · $759 → $759 covered

The claim presents 11 days at $69/day. Under OEP-2.2, the gap runs from the
day after possession return until the earliest of: ready cutoff, replacement
occupancy, or 30th calendar day. The ready cutoff date is 06/24, which equals
the gap end date — no trimming is needed. All 11 claimed days are supported.
Covered = 11 × $69 = $759.

## L2 — Primary wall and trim restoration (duplicate) · $1,944 → excluded

This line is identical to L0 in description and amount. The journal has already
reversed it (credit entry). OEP-3.2 excludes "duplicate entries" and specifies
"A duplicate or recovery is removed once, not twice." The duplicate is removed
once — the full $1,944 is excluded.

Note the interaction with L0's recovery: the duplicate exclusion and the
recovery are separate adjustments. The duplicate removes the second
presentation of the charge. The recovery offsets part of the first
presentation. They do not compound — each is applied once, per OEP-3.2's rule.

## L3 — Posted restoration supplement · $536 → $536 covered

A supplemental restoration charge supported by a posted record. Qualifies
under OEP-2.3 with evidence per OEP-3.4. No service-life schedule applies to
this item (it is labor/supplemental work, not a listed scheduled component).
Full amount covered.

## L4 — Late amendment charge · $109 → excluded

An administrative fee. OEP-3.2 excludes "administrative charges." Excluded in
full.

## Routing

No held amount. All gate checks pass. Covered total ($2,556) is below the
limit ($3,190). Gate score 100/90 → auto_approve, STP-eligible.
