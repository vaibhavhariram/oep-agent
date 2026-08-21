# Architecture

## Pipeline overview

```
Ingest → Extraction → Normalization → Reconciliation → Rules → Gate → Assembly
```

Each stage produces a typed intermediate object. The pipeline processes one
claim at a time; `run-all` loops over the ten visible claims sequentially.

### 1. Ingest (`oep.ingest`)

Reads the manifest (`dataset_index.json`), verifies SHA-256 hashes, rejects
missing files, extra files, and path-traversal attempts, then extracts
page-aware text from each DOCX using lxml.

**Decision: page-break parsing over footers.** DOCX footers carry
`PAGE`/`NUMPAGES` field codes that extract as "Page 1 of 1" on a four-page
document — they report the *field value at save time*, not the actual page
count. Splitting on `<w:br w:type="page"/>` elements in `word/document.xml` is
reliable.

### 2. Extraction (`oep.extraction`)

Four LLM calls per claim (one per document type), all to
`claude-haiku-4-5-20251001` at temperature 0 with JSON output. Each call
returns a typed Pydantic model (`RawLossNotice`, `RawFinancialJournal`,
`RawSourceRegister`, `RawCertificate`).

**Decision: the model reads, code decides.** The LLM extracts structured data
from natural-language documents. All policy logic, category mapping, amount
calculation, and routing is deterministic code. This keeps the LLM's role
narrow (structured extraction) and makes the adjudication fully auditable.

### 3. Table parser cross-check (`oep.extraction.table_parser`)

A deterministic regex parser independently extracts journal entries and source
lines from the pipe-delimited tables in the DOCX text. The parser's output is
compared field-by-field against the LLM extraction; disagreements are logged as
warnings.

**Decision: cross-check, not fallback.** The parser validates the LLM's output
rather than replacing it. If the LLM and parser disagree, both values are
preserved and the warning is surfaced — the system does not silently pick one.

### 4. Normalization (`oep.extraction.normalize`)

Maps verbatim source values to schema enum values via lookup tables:
`CATEGORY_MAP` (7 source categories → 7 classifications) and
`RECORD_STATUS_MAP` (10 status strings → 5 documentation statuses). Parses
dates, builds evidence strings, and assembles the shared header block.

**Decision: mapping tables as data, not conditionals.** Adding a new category
or status is a one-line table entry, not a code change. Unknown values fall
through to `"unclassified"` or `"unclear"` with a warning, never silently.

### 5. Reconciliation (`oep.reconcile`)

Six cross-document checks: identifier chain, limit agreement, totals chain,
journal-register alignment, coverage window (OEP-1.2), and notice deadline
(OEP-5.1). Each check produces a list of `SourceConflict` objects with
two-sided provenance.

**Decision: conflicts preserved, not resolved.** Per OEP-3.5, material
conflicts are recorded and forwarded to human review rather than resolved by
the system. A conflict causes the reconciliation gate check to fail, routing
to `human_review`.

### 6. Rules engine (`oep.rules`, 7 stages)

The seven stages map exactly onto OEP-4.1's seven ordered operations:

| Stage | OEP-4.1 operation | Module |
|-------|-------------------|--------|
| 1 | Classify lines | `_stage1_classify` |
| 2 | Remove exclusions and duplicates | `_stage2_exclude` |
| 3 | Preserve unsupported values | `_stage3_hold` |
| 4 | Apply service and interval boundaries | `_stage4_value` |
| 5 | Apply gap boundaries | `_stage5_gap` |
| 6 | Apply credits and recoveries once | `_stage6_credits` |
| 7 | Apply the certificate limit | `_stage7_cap` |

Each stage mutates `LineState` objects in place and appends `RuleTraceStep`
entries. The line invariant (`amount == covered + excluded + held`) is
maintained after every stage.

**Decision: exclusions and the OEP-3.6 service schedule as data.**
`EXCLUDED_CATEGORIES` is a frozenset; `COMPONENT_SCHEDULE` is a dict mapping
component names to months. The rules engine references these tables rather than
encoding policy in conditionals.

**Decision: Decimal with ROUND_HALF_UP throughout.** All financial calculations
use `decimal.Decimal` with `ROUND_HALF_UP` to cents. This matches the policy's
"rounded half up to cents" language and avoids float drift.

### 7. Gate (`oep.gate`)

Five deterministic checks with weights summing to 100:

| Check | Weight | Hard fail | What it verifies |
|-------|--------|-----------|------------------|
| source_integrity | 20% | Yes | All registered files present, SHA-256 verified, pages processed |
| reconciliation | 25% | Yes | No material cross-document conflicts |
| policy_support | 20% | Yes | Every rule_id resolves to a known clause |
| amount_safety | 25% | Yes | Line and case invariants hold |
| unresolved_evidence | 10% | No | No held amount remains |

Routing: `auto_approve` requires score 100, no hard failure, and zero held
amount. Any hard failure → `human_review`. Held amount with covered amount →
`partial_approve_with_hold`.

### 8. Assembly (`oep.assembly`)

Constructs the full `Result` object (25 required fields), validates against
`output_schema.json`, and serializes to JSON.

**Decision: generated Pydantic models plus jsonschema as the authoritative
validator.** `output.py` was generated from `output_schema.json` (35 classes,
all `extra=forbid`). The JSON Schema is the single source of truth; the
Pydantic models enforce it at runtime and the schema validator confirms it on
output.

## Evaluation harness (`oep.eval`)

Compares the pipeline against two baselines (A: full schema single-call, B:
reduced schema single-call) and a golden reference set (3 supplied ground truth
+ 7 candidate-authored). Reports payment accuracy, route accuracy, per-line
status accuracy, monetary exactness, citation validity, and schema validity.
All accuracy metrics are reported both overall (/10) and supplied-only (/3).
