# Time Log - OEP Claims Agent Trial

## 2026-08-18 (Day 1 - Kickoff)

| Date | Start | Stop | Duration | What |
|------|-------|------|----------|------|
| 2026-08-18 | 00:03 | ~00:20 | 17 min | Setup: Initialize repo, extract data folder, create .gitignore, TIME_LOG.md, first commits |
| 2026-08-18 | 00:20 | ~01:15 | 55 min | Day 1 build: pyproject.toml, generated Pydantic models, manifest verification, page-aware docx extraction, packet assembly, CLI, 21 tests (all green), README |

**Day 1 deliverables completed:**
- Project skeleton with pyproject.toml, config, package structure
- Generated Pydantic v2 models from output_schema.json (35 classes, all extra=forbid)
- Manifest verification with 6 typed error classes
- Page-aware docx extraction (lxml, splits on w:br page breaks, not footers)
- Claim packet assembly with sha256, page counts, doc type inference
- CLI: verify-packet, pages, run/run-all stubs
- 21 tests: manifest (happy + 6 failures), page extraction (6), models (round-trip, schema, extra=forbid)
- README with fresh-clone setup and CLI usage

## 2026-08-18 (Day 2 - Extraction + Normalization)

| Date | Start | Stop | Duration | What |
|------|-------|------|----------|------|
| 2026-08-18 | 20:45 | ~22:45 | ~2 hr | Day 2 build: extraction prompts (all 4 doc types), raw Pydantic schemas, model client with retry, deterministic normalization layer, table parser cross-check, CLI extract command, 47 new tests (68 total, all green) |

**Day 2 deliverables completed:**
- Extraction prompts for all 4 document types (§0-4), verified against real layouts
- Raw extraction Pydantic schemas (intermediate, separate from output.py)
- Model client: temp=0, JSON output, Pydantic validation, 1 repair retry, ModelCallRecord logging
- Deterministic normalization: category→classification (5), status→documentation_status (9), dual date serialization, 4 evidence string grammars, shared header block, gap/service-life parsing
- Table parser cross-check: journal and source register parsed deterministically, compared field-by-field against LLM output
- CLI `oep extract` command with cross-check and normalization
- Structural diff harness: all 3 labeled examples match normalized output exactly
- 68 tests total, all green

## 2026-08-19 (Day 3 — Reconciliation, rules engine, gate, end-to-end)

| Date | Duration | What |
|------|----------|------|
| 2026-08-19 | ~1.0 hr | Daily sync; dev-case analysis — read all seven unlabeled registers and journals, identified planted behaviors (depreciation, gap trimming, duplicate-with-reversal) |
| 2026-08-19 | ~1.5 hr | Reconciliation module: six cross-document checks, typed conflicts, 51 tests. Caught and corrected a totals check that passed on all labeled cases but breaks on any claim with credits |
| 2026-08-19 | ~2.5 hr | Rules engine: seven stages mapped to OEP-4.1. Hand-derived depreciation, gap-boundary, and cap-allocation values from the policy to use as acceptance tests |
| 2026-08-19 | ~1.5 hr | Gate, routing, end-to-end assembly; clause store; schema validation before output; 216 tests green |
| 2026-08-19 | ~0.5 hr | Review, self-audit, commits |

**Day 3 total: ~7.0 hr**

## 2026-08-20 (Day 4 — Evaluation, adversarial testing, audit, submission)

| Date | Duration | What |
|------|----------|------|
| 2026-08-20 | ~1.0 hr | Daily sync; planning the evaluation phase |
| 2026-08-20 | ~1.5 hr | Two baseline variants (full schema and reduced decision core), run across all ten claims; failure-mode analysis |
| 2026-08-20 | ~2.0 hr | Golden dataset: hand-adjudicated seven unlabeled claims against the policy, wrote per-claim reasoning documents citing clauses |
| 2026-08-20 | ~1.0 hr | Eval harness and scorecard; payment-accuracy metrics; divergence analysis with per-case verdicts |
| 2026-08-20 | ~1.0 hr | Adversarial gate-check suite |
| 2026-08-20 | ~1.0 hr | Full repository audit, remediation, artifact regeneration |
| 2026-08-20 | ~1.0 hr | Write-ups, disclosure, fresh-clone verification, submission |

**Day 4 total: ~8.5 hr**

---

## Total: 20.0 hours (capped)

Actual time worked exceeded the cap. Logged at 20 hours per the trial terms.

This log includes work that does not appear in commit history: reading the
policy and claim documents, hand-deriving expected values from the clauses,
reviewing implementation plans before execution, the daily syncs, and the
final audit pass. Earlier entries for Days 1 and 2 recorded only
commit-adjacent time and understate the actual hours.
