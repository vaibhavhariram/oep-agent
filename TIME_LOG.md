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
