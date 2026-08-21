# Adversarial Test Suite

Tests that each gate check is falsifiable and that failures block `auto_approve`.

Every test asserts **both** that the targeted check fails **and** that
`gate.route != Route.auto_approve`.

## Test inventory

| File | Case | Targeted check | What it proves |
|------|------|----------------|----------------|
| `test_source_integrity.py` | Missing registered file | `source_integrity` | `MissingFileError` raised on absent file |
| `test_source_integrity.py` | Extra unregistered file | `source_integrity` | `ExtraFileError` raised on rogue file |
| `test_source_integrity.py` | SHA-256 mismatch | `source_integrity` | `HashMismatchError` raised on corrupted file |
| `test_source_integrity.py` | Unreadable/zero-page doc | `source_integrity` | Gate check fails and blocks auto_approve |
| `test_reconciliation.py` | Identifier disagreement | `reconciliation` | Conflict carries provenance from both documents |
| `test_reconciliation.py` | Limit disagreement | `reconciliation` | Limit conflict blocks auto_approve |
| `test_amount_safety.py` | Line invariant break | `amount_safety` | claimed != covered + excluded + held detected |
| `test_amount_safety.py` | Case total break | `amount_safety` | Tampered case totals detected |
| `test_policy_support.py` | Absent clause_id | `policy_support` | Unknown rule_id fails the check |
| `test_policy_support.py` | Wrong source_page (xfail) | `policy_support` | **Gap found**: page not verified (see below) |
| `test_coverage_window.py` | Event outside cert period | `reconciliation` | Coverage conflict produced and blocks approval |
| `test_notice_deadline.py` | Statement > 105 days | `reconciliation` | Notice deadline conflict blocks approval |
| `test_failure_path.py` | Extraction fails mid-claim | (end-to-end) | Completed work preserved, nothing fabricated |

## Falsifiability findings

**Checks shown falsifiable**: `source_integrity`, `reconciliation`,
`amount_safety`, `policy_support` (clause_id existence only).

**Known gap**: `_check_policy_support` verifies that `rule_id` resolves to a
clause in `CLAUSE_BY_ID`, but does **not** verify `source_page` correctness.
A citation with a valid `clause_id` and an incorrect `source_page` will pass
the check.  This is documented as `test_wrong_source_page` (xfail) and in
`KNOWN_LIMITATIONS.md`.  The gap does not affect safety — invalid page numbers
are caught by the eval harness's `_validate_citations()` — but it means the
gate alone cannot detect page-level citation errors.

## Failure path coverage

The failure-path test mocks `extract_document` to fail on the third document.
It verifies that the exception propagates (nothing silently swallowed), no
partial `Result` is fabricated, and no external write occurs.
