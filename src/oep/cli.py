"""OEP Claims Agent CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from oep import config
from oep.ingest import manifest, packet

app = typer.Typer(name="oep", help="OEP Claims Adjudication Agent")


@app.command()
def verify_packet(claim_id: str) -> None:
    """Verify manifest integrity for a claim packet."""
    pkt = packet.assemble_packet(claim_id)
    typer.echo(f"Claim {pkt.claim_id} verified OK  (label: {pkt.label})")
    for doc in pkt.documents:
        typer.echo(
            f"  {doc.filename}  "
            f"sha256={doc.sha256[:16]}…  "
            f"{doc.page_count} page(s)  "
            f"type={doc.document_type}"
        )


@app.command()
def pages(
    claim_id: str,
    doc: int | None = typer.Option(None, help="Show only document N (1-based)"),
) -> None:
    """Extract and display per-page text with evidence anchors."""
    pkt = packet.assemble_packet(claim_id)
    docs = pkt.documents
    if doc is not None:
        if doc < 1 or doc > len(docs):
            typer.echo(f"Error: --doc must be 1–{len(docs)}", err=True)
            raise typer.Exit(1)
        docs = [docs[doc - 1]]

    for d in docs:
        typer.echo(f"\n=== {d.filename} ({d.page_count} page(s)) ===")
        for page in d.pages:
            typer.echo(f"\n--- Page {page.page_number}  [{page.evidence_anchor}] ---")
            typer.echo(page.extracted_text)


@app.command()
def extract(claim_id: str) -> None:
    """Run LLM extraction + normalization for a claim and print results."""
    from oep.extraction.client import build_page_tagged_text, extract_document
    from oep.extraction.normalize import normalize_all
    from oep.extraction.schemas import (
        RawCertificate,
        RawFinancialJournal,
        RawLossNotice,
        RawSourceRegister,
    )
    from oep.extraction.table_parser import (
        crosscheck_journal,
        crosscheck_source_lines,
        parse_journal,
        parse_source_lines,
    )

    pkt = packet.assemble_packet(claim_id)
    raw_extractions = {}
    call_records = []

    for doc in pkt.documents:
        typer.echo(f"Extracting {doc.filename} ...", err=True)
        tagged = build_page_tagged_text(doc.pages)
        raw, call = extract_document(
            doc.document_type, tagged, claim_id=claim_id
        )
        raw_extractions[doc.document_type] = raw
        call_records.append(call)

    # Table-parser cross-check.
    journal_parsed = parse_journal(pkt.documents[1].pages)
    raw_journal = raw_extractions["tenancy_financial_journal"]
    j_warnings = crosscheck_journal(journal_parsed, raw_journal.ledger_entries)
    for w in j_warnings:
        typer.echo(f"  ⚠ journal cross-check: {w}", err=True)

    reg_doc = pkt.documents[2]
    src_parsed = parse_source_lines(reg_doc.pages)
    raw_register = raw_extractions[reg_doc.document_type]
    sl_warnings = crosscheck_source_lines(
        src_parsed, raw_register.presented_source_lines
    )
    for w in sl_warnings:
        typer.echo(f"  ⚠ register cross-check: {w}", err=True)

    # Normalize.
    normalized = normalize_all(
        loss_notice=raw_extractions["loss_notice_and_record_index"],
        journal=raw_extractions["tenancy_financial_journal"],
        source_register=raw_extractions[reg_doc.document_type],
        certificate=raw_extractions["covered_tenancy_certificate"],
    )

    # Print as JSON.
    output = []
    for ext in normalized:
        output.append(ext.model_dump(mode="json"))
    typer.echo(json.dumps(output, indent=2))

    # Summary.
    typer.echo(
        f"\n{len(call_records)} model calls, "
        f"{len(j_warnings)} journal warnings, "
        f"{len(sl_warnings)} register warnings",
        err=True,
    )


@app.command()
def run(
    claim_id: str,
    case_number: int = typer.Option(1, help="Case number (required schema field; defaults to 1)."),
) -> None:
    """Process a single claim end-to-end and write a schema-valid result."""
    from oep.assembly import process_claim, result_to_dict
    from oep.models.wrappers import validate_against_schema

    typer.echo(f"Processing {claim_id} ...", err=True)
    try:
        result = process_claim(claim_id, case_number=case_number)
    except Exception as exc:
        typer.echo(f"Error processing {claim_id}: {exc}", err=True)
        raise typer.Exit(1) from None

    output = result_to_dict(result)
    errors = validate_against_schema(output)
    if errors:
        typer.echo(f"Schema validation failed ({len(errors)} errors):", err=True)
        for e in errors[:10]:
            typer.echo(f"  {e}", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(output, indent=2))
    typer.echo(
        f"\n{claim_id}: {result.disposition.value}, "
        f"route={result.gate.route.value}, "
        f"score={result.gate.score}, "
        f"approved=${result.approved_amount:,.2f}",
        err=True,
    )


@app.command()
def run_all() -> None:
    """Process all ten visible claims."""
    from oep.assembly import process_claim, result_to_dict
    from oep.models.wrappers import validate_against_schema

    idx = json.loads(config.DATASET_INDEX_PATH.read_text())
    claims = idx["claims"]

    results = []
    failures: list[dict] = []
    for i, entry in enumerate(claims, 1):
        cid = entry["claim_id"]
        typer.echo(f"[{i}/{len(claims)}] Processing {cid} ...", err=True)
        try:
            result = process_claim(cid, case_number=i)
            results.append(result)
            typer.echo(
                f"  {result.disposition.value}, "
                f"route={result.gate.route.value}, "
                f"approved=${result.approved_amount:,.2f}",
                err=True,
            )
        except Exception as exc:
            typer.echo(f"  ERROR: {exc}", err=True)
            failures.append({"claim_id": cid, "error": str(exc)})

    if not results and not failures:
        typer.echo("No claims processed.", err=True)
        raise typer.Exit(1)

    output = result_to_dict(results) if results else {"results": []}
    if failures:
        output["failed"] = failures
    errors = validate_against_schema(output)
    if errors:
        typer.echo(f"Schema validation failed ({len(errors)} errors):", err=True)
        for e in errors[:10]:
            typer.echo(f"  {e}", err=True)
        raise typer.Exit(1)

    typer.echo(json.dumps(output, indent=2))
    typer.echo(
        f"\n{len(results)}/{len(claims)} claims succeeded"
        + (f", {len(failures)} failed" if failures else "")
        + ".",
        err=True,
    )


@app.command(name="eval")
def eval_cmd() -> None:
    """Score baseline vs final pipeline against golden references."""
    from oep.eval import build_scorecard

    typer.echo("Building scorecard ...", err=True)
    md, scorecard_json = build_scorecard()

    out_dir = Path(__file__).resolve().parents[2] / "outputs"
    out_dir.mkdir(exist_ok=True)

    md_path = out_dir / "scorecard.md"
    md_path.write_text(md)
    typer.echo(f"Wrote {md_path}", err=True)

    json_path = out_dir / "scorecard.json"
    json_path.write_text(json.dumps(scorecard_json, indent=2) + "\n")
    typer.echo(f"Wrote {json_path}", err=True)

    typer.echo(md)


@app.command()
def baseline(claim_id: str) -> None:
    """Baseline: one model call per claim, no rules engine."""
    from oep.baseline import baseline_adjudicate

    typer.echo(f"Baseline adjudicating {claim_id} ...", err=True)
    try:
        bl_result = baseline_adjudicate(claim_id)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None

    if bl_result.success:
        typer.echo(f"  ✓ valid schema", err=True)
        output = {"results": [bl_result.result]}
    else:
        typer.echo(f"  ✗ schema validation failed ({len(bl_result.validation_errors)} errors)", err=True)
        for e in bl_result.validation_errors[:5]:
            typer.echo(f"    {e}", err=True)
        output = {"results": [bl_result.result] if bl_result.result else []}

    typer.echo(json.dumps(output, indent=2))


@app.command()
def baseline_all() -> None:
    """Baseline all ten visible claims."""
    from oep.baseline import baseline_adjudicate

    idx = json.loads(config.DATASET_INDEX_PATH.read_text())
    claims = idx["claims"]

    results = []
    for i, entry in enumerate(claims, 1):
        cid = entry["claim_id"]
        typer.echo(f"[{i}/{len(claims)}] Baseline {cid} ...", err=True)
        try:
            bl_result = baseline_adjudicate(cid)
            results.append({
                "claim_id": cid,
                "success": bl_result.success,
                "validation_errors": bl_result.validation_errors[:3],  # first 3 errors
                "result": bl_result.result,
                "model_call": {
                    "purpose": bl_result.model_call.purpose,
                    "duration_ms": bl_result.model_call.duration_ms,
                    "input_tokens": bl_result.model_call.input_tokens,
                    "output_tokens": bl_result.model_call.output_tokens,
                    "total_tokens": bl_result.model_call.total_tokens,
                },
            })
            if bl_result.success:
                typer.echo(f"  ✓ valid", err=True)
            else:
                typer.echo(f"  ✗ {len(bl_result.validation_errors)} errors", err=True)
        except Exception as exc:
            typer.echo(f"  ERROR: {exc}", err=True)
            continue

    output = {
        "metadata": {
            "baseline_type": "single_call_no_rules",
            "total_claims": len(claims),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
        },
        "results": results,
    }

    typer.echo(json.dumps(output, indent=2))
    typer.echo(
        f"\nBaseline: {sum(1 for r in results if r['success'])}/{len(claims)} schema-valid.",
        err=True,
    )


@app.command(name="baseline-b")
def baseline_b(claim_id: str) -> None:
    """Baseline B: one call per claim, reduced schema (adjudication core only)."""
    from oep.baseline import baseline_b_adjudicate

    typer.echo(f"Baseline B adjudicating {claim_id} ...", err=True)
    try:
        bl_result = baseline_b_adjudicate(claim_id)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None

    if bl_result.success:
        typer.echo(f"  ✓ valid schema", err=True)
        output = {"result": bl_result.result}
    else:
        typer.echo(f"  ✗ schema validation failed ({len(bl_result.validation_errors)} errors)", err=True)
        for e in bl_result.validation_errors[:5]:
            typer.echo(f"    {e}", err=True)
        output = {"result": bl_result.result, "errors": bl_result.validation_errors}

    typer.echo(json.dumps(output, indent=2))


@app.command(name="baseline-b-all")
def baseline_b_all() -> None:
    """Baseline B all ten visible claims."""
    from oep.baseline import baseline_b_adjudicate

    idx = json.loads(config.DATASET_INDEX_PATH.read_text())
    claims = idx["claims"]

    results = []
    for i, entry in enumerate(claims, 1):
        cid = entry["claim_id"]
        typer.echo(f"[{i}/{len(claims)}] Baseline B {cid} ...", err=True)
        try:
            bl_result = baseline_b_adjudicate(cid)
            results.append({
                "claim_id": cid,
                "success": bl_result.success,
                "validation_errors": bl_result.validation_errors[:3],
                "result": bl_result.result,
                "model_call": {
                    "purpose": bl_result.model_call.purpose,
                    "duration_ms": bl_result.model_call.duration_ms,
                    "input_tokens": bl_result.model_call.input_tokens,
                    "output_tokens": bl_result.model_call.output_tokens,
                    "total_tokens": bl_result.model_call.total_tokens,
                },
            })
            if bl_result.success:
                typer.echo(f"  ✓ valid", err=True)
            else:
                typer.echo(f"  ✗ {len(bl_result.validation_errors)} errors", err=True)
        except Exception as exc:
            typer.echo(f"  ERROR: {exc}", err=True)
            continue

    output = {
        "metadata": {
            "baseline_type": "reduced_schema_adjudication",
            "total_claims": len(claims),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
        },
        "results": results,
    }

    typer.echo(json.dumps(output, indent=2))
    typer.echo(
        f"\nBaseline B: {sum(1 for r in results if r['success'])}/{len(claims)} schema-valid.",
        err=True,
    )


if __name__ == "__main__":
    app()
