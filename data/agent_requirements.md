# Agent Requirements

Choose your own architecture, frameworks, models, storage, verification checks, weights, thresholds, and routing method. Final results must validate against `output_schema.json`.

## Inputs

Process one explicit case at a time using:

1. Loss Notice and Record Index
2. Tenancy Financial Journal
3. Restoration Cost Register or Premises Condition Log
4. Covered Tenancy Certificate
5. Master policy form `OEP-2027-SYN`

Reject an unknown case, missing or extra registered file, unreadable input, or unsafe path. Process every page and preserve source filename, one-based page number, and evidence for each material fact and decision.

## Reconciliation

Reconcile:

- case, agreement, participant, location, and policy identifiers;
- occupancy, exit, statement, and protection dates;
- selected policy limit;
- each submitted line, amount, category, and evidence status;
- charges, payments, credits, recoveries, reversals, and ending balance;
- missing evidence and material conflicts.

Preserve conflicting source values and their provenance. Do not resolve a conflict without support from a governing rule or stronger source.

## Policy and decisions

Ground every material conclusion in the supplied policy. Citations must include the clause or heading, source page, and a supported excerpt or anchor.

Assign each submitted line one status:

- `covered`
- `partially_covered`
- `excluded`
- `needs_review`

For each line, report the submitted, covered, excluded, held, and approved amounts; rationale; source evidence; policy citations; and deterministic rule trace.

Calculate monetary outcomes in code using decimal `ROUND_HALF_UP`. Case totals must reconcile with line results.

## Verification and routing

Recommend one route:

- `auto_approve`
- `partial_approve_with_hold`
- `human_review`

Design and test a deterministic verification method covering packet completeness, identity and financial reconciliation, policy support, arithmetic, conflicts, and unresolved evidence.

Missing, contradictory, ambiguous, unsupported, or unverified material evidence must not auto-approve. Explain every unresolved issue and routing decision.

## Output

Provide commands to run one visible case and all ten visible cases. Results must validate against `output_schema.json`.

Make the following reviewable:

- source inventory and page-level provenance;
- policy citations;
- conflicts and unresolved issues;
- line decisions and arithmetic;
- verification checks and route rationale;
- model/tool usage, retries, latency, tokens, and cost when available;
- evidence that no external write or payment occurred.

A frontend is not required. Details may be split between schema-valid output, logs, traces, and other structured artifacts.

## Failure and safety

Test missing or corrupt inputs, document-processing or model failures, malformed outputs, arithmetic failures, timeouts, and retries. Failures must remain visible, preserve valid completed work, avoid fabricating later work, and perform no external action.

Do not use real credentials or call a real claim, customer, carrier, banking, or payment system.
