"""Claim packet assembly.

Given a claim id, verifies the manifest, extracts pages from each
document, and returns a structured ``ClaimPacket``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from oep import config
from oep.ingest import docx_pages, manifest
from oep.ingest.docx_pages import PageData

# Mapping from the filename stem (stripped of leading digit + underscore)
# to the canonical document_type enum value used in the output schema.
_DOC_TYPE_PATTERN = re.compile(r"^\d+_(.+)\.docx$", re.IGNORECASE)

_VALID_DOC_TYPES = frozenset({
    "loss_notice_and_record_index",
    "tenancy_financial_journal",
    "restoration_cost_register",
    "premises_condition_log",
    "covered_tenancy_certificate",
})


@dataclass
class DocumentPacket:
    """One document within a claim packet."""

    filename: str
    document_type: str
    sha256: str
    page_count: int
    provenance: str
    pages: list[PageData]


@dataclass
class ClaimPacket:
    """A verified, page-extracted claim packet."""

    claim_id: str
    label: str
    documents: list[DocumentPacket]


def infer_document_type(filename: str) -> str:
    """Derive the canonical document_type from a document filename.

    Example: ``"3_Restoration_Cost_Register.docx"`` → ``"restoration_cost_register"``
    """
    m = _DOC_TYPE_PATTERN.match(filename)
    if m is None:
        raise ValueError(f"Cannot infer document type from filename: {filename!r}")
    doc_type = m.group(1).lower()
    if doc_type not in _VALID_DOC_TYPES:
        raise ValueError(
            f"Unrecognised document type {doc_type!r} from filename {filename!r}"
        )
    return doc_type


def assemble_packet(
    claim_id: str,
    data_dir: Path | None = None,
) -> ClaimPacket:
    """Verify and assemble a complete claim packet.

    Parameters
    ----------
    claim_id:
        Claim identifier (e.g. ``"OEP-27-1087"``).
    data_dir:
        Root data directory.  Defaults to ``config.DATA_DIR``.

    Returns
    -------
    ClaimPacket
        The verified packet with per-page extracted text.
    """
    data_dir = data_dir or config.DATA_DIR

    claim = manifest.verify_claim_packet(claim_id, data_dir=data_dir)

    documents: list[DocumentPacket] = []
    for filename in claim["documents"]:
        doc_path = data_dir / "claims" / claim_id / filename
        doc_type = infer_document_type(filename)
        sha256 = manifest.compute_sha256(doc_path)
        pages = docx_pages.extract_pages(doc_path, filename)

        documents.append(
            DocumentPacket(
                filename=filename,
                document_type=doc_type,
                sha256=sha256,
                page_count=len(pages),
                provenance="One-based page map from the registered candidate packet.",
                pages=pages,
            )
        )

    return ClaimPacket(
        claim_id=claim_id,
        label=claim.get("label", "unknown"),
        documents=documents,
    )
