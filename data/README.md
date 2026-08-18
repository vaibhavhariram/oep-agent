# Alderquill Occupancy Exit Protection Trial

Build an agent that evaluates synthetic occupancy-exit protection submissions against the supplied master policy.

## Task

Each case represents a move-out claim submitted by a property operator. The agent must review the claim documents, reconcile facts and financial entries, apply the policy, calculate supported amounts, identify unresolved evidence, and recommend a safe next action with citations and an auditable rationale.

The goal is not only to reach the correct outcome. The system should make clear what evidence it used, what it could not determine, and why its result is reliable enough to automate or should be escalated for review.

## Package contents

- `policy/` — governing master-policy DOCX.
- `claims/` — ten visible cases, each containing four DOCX records.
- `examples/` — expected outputs for three labeled cases.
- `agent_requirements.md` — required agent behavior and safety boundaries.
- `dataset_index.json` — visible case inventory, document paths, sizes, and hashes.
- `output_schema.json` — required machine-readable output format.

## Dataset structure

The ten visible cases include three labeled examples and seven unlabeled development cases. Use the examples to understand the expected output and use the development cases to build, test, and evaluate your approach.

After submission, the same system may be run unchanged on ten additional held-out cases. Those cases follow the same policy, agent requirements, document roles, and output schema. They are retained to evaluate whether the system generalizes beyond the visible packets, so do not hard-code case identifiers, amounts, phrases, or outcomes.

## Build

Provide a CLI or API command that runs one visible case and another that runs all ten visible cases. Results must validate against `output_schema.json`. A frontend is not required.

Use at least one model-based component. Monetary calculations and routing safeguards must be implemented and verified deterministically.

## Submit

- Working source code and fresh-clone setup instructions.
- Commands to run one case and all visible cases.
- Schema-valid outputs for all ten visible cases.
- Deterministic tests for extraction, reconciliation, policy rules, arithmetic, verification, and routing.
- A baseline and final approach evaluated on the same candidate-authored evaluation set.
- Failure-path evidence.
- Architecture, tradeoff, error-analysis, latency, cost, and model/tool notes.

Clearly identify anything incomplete or mocked.

## Safety

All supplied data are synthetic. Do not use real credentials or connect to claim, banking, payment, or customer systems. The system must not perform an external write or initiate payment.
