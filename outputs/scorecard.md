# Evaluation Scorecard

Generated: 2026-08-20T21:07:48Z

Golden reference claims: OEP-27-1087, OEP-27-9062, OEP-27-9548 (3 of 10)

## Payment Accuracy

Scored against 10 golden references.

| Metric | Baseline A | Baseline B | Final Pipeline |
|--------|-----------|-----------|----------------|
| **Approved amount exact match** | N/A (no valid outputs) | N/A (no valid outputs) | **10/10** |
| Approved amount total absolute error | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Approved amount overpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Approved amount underpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Covered amount exact match | N/A (no valid outputs) | N/A (no valid outputs) | 10/10 |
| Covered amount total absolute error | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Covered amount overpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Covered amount underpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Excluded amount exact match | N/A (no valid outputs) | N/A (no valid outputs) | 10/10 |
| Excluded amount total absolute error | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Excluded amount overpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Excluded amount underpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Held amount exact match | N/A (no valid outputs) | N/A (no valid outputs) | 10/10 |
| Held amount total absolute error | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Held amount overpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Held amount underpayment | N/A (no valid outputs) | N/A (no valid outputs) | $0.00 |
| Line-level approved amt exact match | N/A (no valid outputs) | N/A (no valid outputs) | 43/43 |

## Summary

| Metric | Baseline | Final Pipeline |
|--------|----------|----------------|
| **FALSE AUTO-APPROVES** | 0 | 0 |
| Route accuracy | 0/3 | 3/3 |
| Per-line status accuracy | N/A (N/A) | 13/13 (100.0%) |
| Line monetary exact match | N/A (N/A) | 13/13 (100.0%) |
| Case monetary exact match | N/A (N/A) | 3/3 (100.0%) |
| Total abs $ deviation (line) | $0 | $0.0 |
| Total abs $ deviation (case) | $0 | $0.0 |
| Invalid citations | 0/0 | 0/72 |
| Schema valid claims | 0/10 | 10/10 |
| Cost per claim (avg) | $0.033012 | $0.018977 |
| Total cost | $0.330122 | $0.189769 |
| Latency per claim (avg) | 51,417ms | 14,883ms |
| Total latency | 514,172ms | 148,834ms |

## Per-Claim Overview

| Claim | Golden | B Schema | F Schema | B Route | F Route | G Route | F Status Acc | F Line $ Match |
|-------|--------|----------|----------|---------|---------|---------|-------------|----------------|
| OEP-27-9062 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 5/5 | 5/5 |
| OEP-27-9548 | yes | FAIL | pass | N/A | partial_approve_with_hold | partial_approve_with_hold | 4/4 | 4/4 |
| OEP-27-1087 | yes | FAIL | pass | N/A | human_review | human_review | 4/4 | 4/4 |
| OEP-27-2849 | no | FAIL | pass | N/A | auto_approve | - | - | - |
| OEP-27-8150 | no | FAIL | pass | N/A | auto_approve | - | - | - |
| OEP-27-4706 | no | FAIL | pass | N/A | auto_approve | - | - | - |
| OEP-27-6795 | no | FAIL | pass | N/A | auto_approve | - | - | - |
| OEP-27-2146 | no | FAIL | pass | N/A | auto_approve | - | - | - |
| OEP-27-4358 | no | FAIL | pass | N/A | partial_approve_with_hold | - | - | - |
| OEP-27-5804 | no | FAIL | pass | N/A | partial_approve_with_hold | - | - | - |

## Per-Claim Detail (Golden Divergences)

### OEP-27-1087

- **Golden route:** human_review
- **Final route:** human_review MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Living-room wall restoration | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 1 | Kitchen cabinet repair | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 2 | Specialized odor treatment | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 3 | Administrative reopening fee | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-9062

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Outstanding occupancy installment | covered | covered | yes | $1725.0 | $1725.0 | $0.0 |
| 1 | Entry door slab and frame restoration | covered | covered | yes | $950.0 | $950.0 | $0.0 |
| 2 | Reletting interval — 4 days at $103.00 p | covered | covered | yes | $0.0 | $0.0 | $0.0 |
| 3 | Premium cleaning package uplift | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |
| 4 | Account closure fee | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-9548

- **Golden route:** partial_approve_with_hold
- **Final route:** partial_approve_with_hold MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Ceiling board and finish restoration | covered | covered | yes | $1837.0 | $1837.0 | $0.0 |
| 1 | Entry floor tile restoration | covered | covered | yes | $453.0 | $453.0 | $0.0 |
| 2 | Range control module replacement | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 3 | Document handling fee | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |
