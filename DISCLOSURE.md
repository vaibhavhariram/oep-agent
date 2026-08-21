# Disclosure

## Build-time AI usage

Claude Code was used throughout implementation across multiple sessions, with
plan-mode review before execution on the major modules (rules engine, gate,
reconciliation, eval harness, adversarial test suite). Claude Code assisted
with:

- Code generation for all pipeline stages
- Test generation for unit, integration, and adversarial tests
- Golden file authoring (7 candidate-authored goldens with reasoning files)
- Documentation drafting

All generated code was reviewed and modified before committing. The candidate
made all architectural decisions (pipeline structure, gate design, rules
staging, mapping tables, evaluation methodology).

## Runtime AI usage

The agent calls `claude-haiku-4-5-20251001` via the Anthropic API at runtime:

- **Calls per claim**: 4 (one per document type: Loss Notice, Financial
  Journal, Source Register/Condition Log, Certificate)
- **Temperature**: 0 (deterministic extraction)
- **Model**: Configurable via `OEP_MODEL` environment variable
- **No other external services**: No vector databases, no web searches, no
  external APIs beyond the Anthropic API

### Cost estimation

The eval harness reports cost per claim using a local price table, not
API-reported costs:

| Token type | Price per 1M tokens |
|-----------|-------------------|
| Input (uncached) | $0.80 |
| Input (cached) | $0.08 |
| Output | $4.00 |

Source: `src/oep/eval/__init__.py` (`_INPUT_PRICE`, `_OUTPUT_PRICE`,
`_CACHE_PRICE`). The `cost_source` field in model call records reflects
`"local_price_table"`, not API-reported billing.

### Observed costs

- **Pipeline**: ~$0.019 per claim, ~$0.19 total (10 claims)
- **Baseline A**: ~$0.036 per claim, ~$0.36 total
- **Baseline B**: similar to Baseline A

## What is NOT AI-generated at runtime

All of the following are deterministic code with no LLM involvement:

- Category and status mapping tables (`CATEGORY_MAP`, `RECORD_STATUS_MAP`)
- Rules engine logic (7 stages, all table-driven)
- Reconciliation checks (6 cross-document validations)
- Gate checks and routing logic (5 weighted checks)
- Amount calculations (Decimal arithmetic with ROUND_HALF_UP)
- Schema validation (jsonschema against `output_schema.json`)
- Table parser cross-check (regex-based, validates LLM output)
