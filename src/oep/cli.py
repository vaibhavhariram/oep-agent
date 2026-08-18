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
def run(claim_id: str) -> None:
    """Process a single claim (not yet implemented)."""
    raise NotImplementedError(
        f"'oep run {claim_id}' is not yet implemented — "
        "extraction, rules, and routing come in Day 2+."
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
