# Evaluation Scorecard

Generated: 2026-08-21T00:27:48Z

Golden reference claims: 10 of 10 (3 supplied ground truth, 7 candidate-authored)

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
| **FALSE AUTO-APPROVES** | N/A (no valid outputs) | 0 |
| Route accuracy | 0/10 (supplied: 0/3) | 10/10 (supplied: 3/3) |
| Per-line status accuracy | N/A (N/A) (supplied: N/A) | 42/43 (97.7%) (supplied: 13/13) |
| Line monetary exact match | N/A (N/A) (supplied: N/A) | 43/43 (100.0%) (supplied: 13/13) |
| Case monetary exact match | N/A (N/A) (supplied: N/A) | 10/10 (100.0%) (supplied: 3/3) |
| Total abs $ deviation (line) | $0 | $0.0 |
| Total abs $ deviation (case) | $0 | $0.0 |
| Invalid citations | N/A (no valid outputs) | 0/72 |
| Schema valid claims | 0/10 | 10/10 |
| Cost per claim (avg) | $0.036100 | $0.018977 |
| Total cost | $0.361001 | $0.189769 |
| Latency per claim (avg) | 59,356ms | 14,778ms |
| Total latency | 593,566ms | 147,785ms |

## Per-Claim Overview

| Claim | Golden | B Schema | F Schema | B Route | F Route | G Route | F Status Acc | F Line $ Match |
|-------|--------|----------|----------|---------|---------|---------|-------------|----------------|
| OEP-27-9062 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 5/5 | 5/5 |
| OEP-27-9548 | yes | FAIL | pass | N/A | partial_approve_with_hold | partial_approve_with_hold | 4/4 | 4/4 |
| OEP-27-1087 | yes | FAIL | pass | N/A | human_review | human_review | 4/4 | 4/4 |
| OEP-27-2849 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 3/3 | 3/3 |
| OEP-27-8150 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 5/5 | 5/5 |
| OEP-27-4706 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 5/5 | 5/5 |
| OEP-27-6795 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 4/5 | 5/5 |
| OEP-27-2146 | yes | FAIL | pass | N/A | auto_approve | auto_approve | 4/4 | 4/4 |
| OEP-27-4358 | yes | FAIL | pass | N/A | partial_approve_with_hold | partial_approve_with_hold | 3/3 | 3/3 |
| OEP-27-5804 | yes | FAIL | pass | N/A | partial_approve_with_hold | partial_approve_with_hold | 5/5 | 5/5 |

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

### OEP-27-2146

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Patio-door glazing replacement | covered | covered | yes | $916.0 | $916.0 | $0.0 |
| 1 | Kitchen cabinet-face restoration | covered | covered | yes | $842.0 | $842.0 | $0.0 |
| 2 | Entry floor restoration | covered | covered | yes | $652.0 | $652.0 | $0.0 |
| 3 | Processing charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-2849

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Prior occupancy balance | covered | covered | yes | $1380.0 | $1380.0 | $0.0 |
| 1 | Reletting interval — 21 days at $73.00 p | partially_covered | partially_covered | yes | $949.0 | $949.0 | $0.0 |
| 2 | Vendor scheduling charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-4358

- **Golden route:** partial_approve_with_hold
- **Final route:** partial_approve_with_hold MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Completed kitchen and wall restoration | covered | covered | yes | $2385.0 | $2385.0 | $0.0 |
| 1 | Additional cabinet supplement | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 2 | Reopening processing charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-4706

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Kitchen floor finish replacement | partially_covered | partially_covered | yes | $144.0 | $144.0 | $0.0 |
| 1 | Window blind rail and hardware | partially_covered | partially_covered | yes | $63.0 | $63.0 | $0.0 |
| 2 | Kitchen GFCI receptacle restoration | covered | covered | yes | $715.0 | $715.0 | $0.0 |
| 3 | Countertop edge panel replacement | partially_covered | partially_covered | yes | $108.0 | $108.0 | $0.0 |
| 4 | Standard turnover cleaning | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-5804

- **Golden route:** partial_approve_with_hold
- **Final route:** partial_approve_with_hold MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Drywall and finish restoration | covered | covered | yes | $1163.0 | $1163.0 | $0.0 |
| 1 | Reletting interval — 7 days at $61.00 pe | covered | covered | yes | $427.0 | $427.0 | $0.0 |
| 2 | Entry floor finish replacement | partially_covered | partially_covered | yes | $405.0 | $405.0 | $0.0 |
| 3 | Isolation valve replacement | needs_review | needs_review | yes | $0.0 | $0.0 | $0.0 |
| 4 | Administrative charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-6795

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Primary wall and trim restoration | covered | partially_covered | **NO** | $1261.0 | $1261.0 | $0.0 |
| 1 | Reletting interval — 11 days at $69.00 p | covered | covered | yes | $759.0 | $759.0 | $0.0 |
| 2 | Primary wall and trim restoration | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |
| 3 | Posted restoration supplement | covered | covered | yes | $536.0 | $536.0 | $0.0 |
| 4 | Late amendment charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

### OEP-27-8150

- **Golden route:** auto_approve
- **Final route:** auto_approve MATCH
- **Baseline route:** N/A (no valid result)
- **Case amounts exact:** yes (deviation: $0.0)

| Line | Description | Golden Status | Final Status | Match | Golden Approved | Final Approved | $ Dev |
|------|-------------|--------------|-------------|-------|----------------|----------------|-------|
| 0 | Bedroom carpet replacement | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |
| 1 | Living-room blind track replacement | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |
| 2 | Hard-wired smoke alarm restoration | covered | covered | yes | $606.0 | $606.0 | $0.0 |
| 3 | Entry door closer replacement | partially_covered | partially_covered | yes | $352.0 | $352.0 | $0.0 |
| 4 | Closeout handling charge | excluded | excluded | yes | $0.0 | $0.0 | $0.0 |

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
