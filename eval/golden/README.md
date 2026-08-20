# Golden Dataset — eval/golden/

Reference answer set for evaluating OEP-2027-SYN claim determinations.

## Claim inventory

| Claim ID | Source | Route | Cap binds? | Lines |
|-----------|--------|-------|-----------|-------|
| OEP-27-1087 | Supplied example | human_review | No | 4 |
| OEP-27-9062 | Supplied example | auto_approve | Yes | 5 |
| OEP-27-9548 | Supplied example | partial_approve_with_hold | Yes | 4 |
| OEP-27-2849 | Candidate-authored | auto_approve | No | 3 |
| OEP-27-4706 | Candidate-authored | auto_approve | No | 5 |
| OEP-27-6795 | Candidate-authored | auto_approve | No | 5 |
| OEP-27-8150 | Candidate-authored | auto_approve | No | 5 |
| OEP-27-5804 | Candidate-authored | partial_approve_with_hold | No | 5 |
| OEP-27-4358 | Candidate-authored | partial_approve_with_hold | Yes | 3 |
| OEP-27-2146 | Candidate-authored | auto_approve | Yes | 4 |

## Provenance

### Supplied examples (3 claims)

OEP-27-1087, OEP-27-9062, and OEP-27-9548 are **ground truth** copied
verbatim from `data/examples/*_expected.json`. These files were provided as
part of the problem specification. Their golden status carries no risk of
circular validation — they were not produced by the system under test.

The golden files for these three claims contain the full output schema
(documents, policy audit, gate checks, rule traces, etc.) because the
supplied examples include this detail.

### Candidate-authored (7 claims)

OEP-27-2849, OEP-27-4706, OEP-27-6795, OEP-27-8150, OEP-27-5804,
OEP-27-4358, and OEP-27-2146 were authored by the candidate by reading the
policy text (OEP-2027-SYN) and the source claim documents independently.
Values were not produced by running the system pipeline (`oep run`), importing
from `src/oep/rules`, or copying from `outputs/`.

These golden files use the **reduced schema** (see `golden_schema.json`):
claim-level totals, routing, gate score, and per-line classification with
five amounts. Fields outside this schema are out of scope for scoring.

Each candidate-authored claim has a corresponding `*_reasoning.md` file
explaining why each line lands where it does, with policy clause citations.

## Risk statement

Candidate-authored goldens carry the inherent risk that a misreading of the
policy would be reproduced in both the system implementation and its own
evaluation set. If the candidate misinterprets a policy clause — for example,
applying the service-life formula incorrectly, or mis-classifying a line item
— the system may implement the same misinterpretation and "pass" the eval
despite being wrong.

The supplied examples mitigate this partially: they establish ground truth for
three representative claim patterns (full hold/escalation, full auto-approve,
and partial approve with hold). The candidate-authored claims extend coverage
to patterns not represented in the examples (service-life depreciation, gap
trimming, duplicate handling, recovery attribution, cap binding, expired
components).

### Specific known ambiguity

**OEP-27-6795 recovery attribution**: A $683 post-closeout recovery must be
applied once (OEP-4.1). The policy does not specify which line the recovery
offsets. The golden follows a greedy-in-source-order convention, attributing
the recovery to L0. An implementation that attributes it differently but
reaches the same case totals (covered $2,556, excluded $2,736) should not be
penalized. Score case totals as firm; treat line-level recovery attribution
as convention.

## Scoring scope

The reduced golden schema (`golden_schema.json`) defines the fields that
matter for evaluation:

- **Case level**: claim_id, policy_limit, claimed/covered/excluded/held/approved
  amounts, disposition, route, gate_score
- **Line level**: source_index, description, category, status,
  claimed/covered/excluded/held/approved amounts

Everything else (document extraction, policy audit, rule traces, citations,
writeback preview, etc.) is out of scope for golden-set scoring.

## File manifest

```
eval/golden/
├── README.md                          ← this file
├── golden_schema.json                 ← reduced schema for scoring
├── OEP-27-1087_golden.json            ← supplied example (full schema)
├── OEP-27-9062_golden.json            ← supplied example (full schema)
├── OEP-27-9548_golden.json            ← supplied example (full schema)
├── OEP-27-2849_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-2849_reasoning.md
├── OEP-27-4706_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-4706_reasoning.md
├── OEP-27-6795_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-6795_reasoning.md
├── OEP-27-8150_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-8150_reasoning.md
├── OEP-27-5804_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-5804_reasoning.md
├── OEP-27-4358_golden.json            ← candidate-authored (reduced schema)
├── OEP-27-4358_reasoning.md
├── OEP-27-2146_golden.json            ← candidate-authored (reduced schema)
└── OEP-27-2146_reasoning.md
```
