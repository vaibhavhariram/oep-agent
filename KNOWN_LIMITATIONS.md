# Known Limitations

## case_number

`case_number` is a required field in the output schema but does not appear in any
source document and is not derivable from the dataset index.  The CLI defaults it
to `1` for single-claim runs and to the 1-based loop index for `run-all`.  In
production it would come from the claims system.

## Upgrade separable-base path unexercised

OEP-3.2 allows a separable base amount for upgrade lines (exclude only the
elective uplift, cover the base).  No visible case states a separable base, so
only the full-line exclusion path is exercised.

## OEP-2.2 replacement-occupancy boundary not implemented

OEP-2.2 lists "replacement occupancy" as a third gap-end boundary alongside
the ready cutoff and the 30-day cap.  No visible case states a replacement
occupancy date, so this boundary is not implemented.

## Recovery attribution greedy in source order

When an unattributed recovery must be allocated to specific lines, the rules
engine uses greedy allocation in `source_index` order.  This is deterministic
but arbitrary; the choice is recorded in `rule_trace`.

## Exact-match harness excludes free-text rationale and detail

The integration test harness (`test_assembly_integration.py`) skips `rationale`
and `detail` fields when diffing against labeled examples, because these are
free-text strings whose exact wording may shift without affecting correctness.

## test_exact_match uses private `_strip_none_artifacts`

`test_exact_match_labeled_example` in `test_assembly_integration.py` imports the
private `_strip_none_artifacts` helper because it constructs a raw dict (not a
full `Result` object) for comparison against labeled examples.  Refactoring it to
build a `Result` and use the public `result_to_dict()` would risk breaking the
single most important test in the suite for a cosmetic gain.  The second call
site (in `test_schema_valid`) was migrated to `result_to_dict()`.

## Policy support check does not verify source_page

The gate's `_check_policy_support` verifies that each `rule_id` in the rule
trace resolves to a known clause in `CLAUSE_BY_ID`, but does not compare the
citation's `source_page` against the clause store's authoritative page number.
A citation with the correct clause_id but wrong source_page will pass the check.
This is documented as an xfail in
`eval/adversarial/test_policy_support.py::test_wrong_source_page`.

## completed_at is real processing time

`completed_at` records the wall-clock time when `process_claim` finishes, not a
synthetic or deterministic timestamp.  This is intentional: it provides a genuine
processing-time signal for cost and latency analysis.
