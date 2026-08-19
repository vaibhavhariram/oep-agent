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
def run(claim_id: str) -> None:
    """Process a single claim (not yet implemented)."""
    raise NotImplementedError(
        f"'oep run {claim_id}' is not yet implemented — "
        "rules, gate, and routing come in Day 3+."
    )


@app.command()
def run_all() -> None:
    """Process all visible claims (not yet implemented)."""
    raise NotImplementedError(
        "'oep run-all' is not yet implemented — "
        "extraction, rules, and routing come in Day 2+."
    )


if __name__ == "__main__":
    app()
