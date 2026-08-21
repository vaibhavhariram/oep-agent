# OEP Claims Agent

Claims-adjudication agent for the Alderquill OEP-2027-SYN occupancy-exit protection policy. Reads four-document claim packets, extracts facts with page-level provenance, and (when complete) applies policy rules deterministically.

## Setup from a fresh clone

```bash
git clone <repo-url>
cd kairos-work-trial

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11+.

### Environment variables

Copy `.env.example` to `.env` and fill in your key:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key for LLM extraction |
| `OEP_MODEL` | `claude-haiku-4-5-20251001` | Model used for document extraction |
| `OEP_DATA_DIR` | `./data` | Path to the dataset directory |

LLM extraction uses the Anthropic API (provider: Anthropic, model determined by `OEP_MODEL`).

## CLI commands

```bash
# Verify a claim packet (manifest integrity, sha256, page counts)
oep verify-packet OEP-27-1087

# Extract and display per-page text with evidence anchors
oep pages OEP-27-1087

# Show a single document (1-based index)
oep pages OEP-27-1087 --doc 4

# Process a single claim end-to-end
oep run OEP-27-1087

# Override the case number (required schema field, defaults to 1)
oep run OEP-27-1087 --case-number 3

# Process all ten visible claims (case_number = run index 1..10)
oep run-all
```

> **Note:** `case_number` is a required schema field that does not appear in any
> source document.  It defaults to `1` for single runs and the 1-based loop index
> for `run-all`.  In production it would come from the claims system.
> See `KNOWN_LIMITATIONS.md` for additional caveats.

## Tests

```bash
pytest tests/ eval/ -v
```

231 tests (230 passed, 1 xfailed) covering:
- **Manifest verification**: all 10 claims pass; 6 failure modes
- **Page extraction**: correct page counts, evidence anchors
- **Model round-trip and schema validation**: all 3 labeled examples
- **Normalization**: category mapping, status mapping, date parsing
- **Reconciliation**: identity, limits, totals, coverage window, notice deadline
- **Rules engine**: 7 stages with per-stage unit tests and integration tests
- **Gate invariants**: 5 checks, weights, routing logic across all 10 claims
- **Assembly integration**: exact-match against labeled examples, schema validation
- **Adversarial**: 13 tests targeting all 5 gate checks (see `eval/adversarial/README.md`)

## Regenerate models

If `data/output_schema.json` changes:

```bash
make generate-models
```

## Project structure

```
src/oep/
  config.py                 # data paths (configurable via OEP_DATA_DIR)
  cli.py                    # typer CLI
  models/
    output.py               # generated Pydantic v2 models (do not hand-edit)
    wrappers.py             # helpers, extra=forbid enforcement, schema validation
  ingest/
    errors.py               # typed exceptions
    manifest.py             # dataset_index.json verification
    docx_pages.py           # page-aware docx extraction (lxml, not footers)
    packet.py               # claim packet assembly
tests/
data/                       # trial dataset (read-only, sha256-verified)
```

## Current status

All four days complete:
- [x] Ingestion: manifest verification, page-aware docx extraction, packet assembly
- [x] Extraction: 4 LLM calls per claim, table parser cross-check, normalization
- [x] Rules engine: 7 stages (classify, exclude, hold, value, gap, credits, cap)
- [x] Gate: 5 weighted checks, routing, disposition
- [x] Assembly: full Result with 25 fields, schema validation
- [x] Evaluation: baselines, golden set (10 claims), scorecard
- [x] Adversarial tests: 13 tests across 7 files targeting all gate checks

## Data

10 visible claims (3 labeled examples, 7 development). All data is synthetic. See `data/agent_requirements.md` for full specifications and `data/README.md` for package contents.
