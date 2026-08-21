# Error Analysis

Analysis of the final system's failure modes, divergences, and known gaps.

## Golden divergences

Three of ten claims diverge between the golden set and the pipeline output.
Full details are in `eval/DIVERGENCE_ANALYSIS.md`.

### 1. OEP-27-4706 — category naming (resolved)

The original golden used `standard_turnover` for L4 ("Standard turnover
cleaning"). The pipeline emits `ordinary_upkeep`, which is the policy's own
classification vocabulary in OEP-3.1. The golden_schema.json originally listed
`standard_turnover` as a category enum value. This was a naming inconsistency
in the candidate-authored golden schema, not a pipeline defect.

**Resolution**: Golden and golden_schema.json corrected to use
`ordinary_upkeep`, matching the policy's terminology. Both reach the same
adjudication outcome (full exclusion under OEP-3.2).

### 2. OEP-27-4706 and OEP-27-8150 — descriptions (resolved)

The golden files used editorial paraphrases (e.g., "Electrical labor" for
"Kitchen GFCI receptacle restoration"). The golden schema defines `description`
as "Item label from the source register." The pipeline preserves the verbatim
source labels.

**Verdict**: PIPELINE CORRECT. Golden descriptions corrected to match the
source register.

### 3. OEP-27-6795 — status and category (policy-silent)

- **L0 status**: Golden says `covered`, pipeline says `partially_covered`. The
  $683 recovery attribution to L0 is convention (acknowledged in the golden
  README). Both are defensible. Case totals are firm and identical.
- **L2 category**: Golden says `unit_restoration` (original nature), pipeline
  says `duplicate` (exclusion reason). Policy does not prescribe which
  classification a duplicate line receives. Both reach full exclusion.
- **L2 description**: Pipeline appends "[DUPLICATE OF LINE 1]". Informational
  annotation, does not affect adjudication.

**Impact**: 42/43 per-line status accuracy (the L0 mismatch). All monetary
values exact. This is the system's single remaining divergence from the golden
set, and it is on a policy-silent field.

## Citation page-validation gap

The gate's `_check_policy_support` verifies that each `rule_id` in the rule
trace resolves to a known clause in `CLAUSE_BY_ID`, but does **not** verify
`source_page` correctness. A citation with a valid clause_id and wrong
source_page will pass the gate check.

This gap is documented in:
- `KNOWN_LIMITATIONS.md`
- `eval/adversarial/test_policy_support.py::test_wrong_source_page` (xfail)

The eval harness's `_validate_citations()` does check page correctness (0/72
invalid citations in the current output), so the gap affects only the gate's
real-time safety check, not the offline evaluation.

## Adversarial suite findings

The adversarial test suite (`eval/adversarial/`) proved the following checks
falsifiable:

| Check | Falsifiable? | Notes |
|-------|-------------|-------|
| source_integrity | Yes | Missing file, extra file, hash mismatch, zero-page doc |
| reconciliation | Yes | Identifier disagreement, limit disagreement, coverage window, notice deadline |
| amount_safety | Yes | Line invariant break, case total break |
| policy_support | Partially | clause_id existence verified; source_page NOT verified (xfail) |
| unresolved_evidence | Yes | (soft check; held > 0 routes to partial_approve, not auto_approve) |

## Candidate-authored golden risk

Seven of ten golden files are candidate-authored. A misread clause would be
reproduced in both the system implementation and its own evaluation set. The
three supplied ground-truth examples (OEP-27-1087, 9062, 9548) mitigate this
partially by establishing correctness on representative patterns:
- Full hold/escalation (1087)
- Full auto-approve with cap (9062)
- Partial approve with hold (9548)

The supplied-only accuracy (3/3 route, 13/13 status, 13/13 monetary) is the
strong claim. The overall 10/10 is self-consistency.

## Where the system is most likely to be wrong on held-out data

1. **Novel source categories**: The CATEGORY_MAP covers 7 verbatim strings. A
   held-out claim with a source category not in the map would fall through to
   `"unclassified"` and be held for review — safe but not ideal.

2. **Complex recovery scenarios**: Recovery attribution is greedy in source
   order. A held-out claim with multiple recoveries or non-trivial attribution
   rules could produce different line-level amounts than intended.

3. **Edge cases in gap calculation**: The 30-day cap and ready-cutoff logic
   have been tested on 4 claims with reletting gaps, but unusual date
   configurations (e.g., gap starting before possession return) are untested.

4. **Document layout variation**: The table parser uses regex on pipe-delimited
   text. A held-out document with different table formatting could produce
   cross-check warnings or fail to parse entirely.
