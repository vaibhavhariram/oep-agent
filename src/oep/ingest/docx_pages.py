"""Page-aware .docx text extraction using lxml.

CRITICAL — footer trap
-----------------------
Document footers contain PAGE / NUMPAGES field codes that always render as
"Page 1 of 1" regardless of actual page count.  Do NOT use footers for
page numbering.  Real page boundaries come from explicit page-break elements
in ``word/document.xml``: ``<w:br w:type="page"/>``.

Evidence anchor formats
-----------------------
Two distinct anchor formats exist in the output schema:

1. **Page-level** (used in ``rendered_pages.evidence_anchor``):
       ``<filename>:page:<N>``
   Example: ``3_Restoration_Cost_Register.docx:page:1``

2. **Line-level** (used in ``rule_trace`` evidence):
       ``<filename>:page:<N>:line:<M>``
   where ``M`` is the 1-based ordinal of the SUBMITTED LINE within that
   source document (``source_index + 1``) — NOT a physical text row.
   This module does **not** implement physical text-line numbering.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass
class PageData:
    """One extracted page from a .docx document."""

    page_number: int
    extracted_text: str
    evidence_anchor: str


def extract_pages(docx_path: Path, filename: str | None = None) -> list[PageData]:
    """Extract per-page text from a .docx file.

    Pages are delimited by ``<w:br w:type="page"/>`` elements.

    Parameters
    ----------
    docx_path:
        Path to the ``.docx`` file.
    filename:
        Filename to use in evidence anchors.  Defaults to
        ``docx_path.name``.

    Returns
    -------
    list[PageData]
        One entry per page, 1-based page numbers.
    """
    filename = filename or docx_path.name

    with zipfile.ZipFile(docx_path) as zf:
        xml_bytes = zf.read("word/document.xml")

    root = etree.fromstring(xml_bytes)
    body = root.find(".//w:body", _NS)
    if body is None:
        return []

    pages: list[PageData] = []
    current_blocks: list[str] = []
    page_num = 1

    for child in body:
        tag = etree.QName(child.tag).localname

        # Skip the final section properties element.
        if tag == "sectPr":
            continue

        has_page_break = bool(
            child.findall('.//w:br[@w:type="page"]', _NS)
        )

        if has_page_break:
            # Flush the current page.
            pages.append(_make_page(page_num, current_blocks, filename))
            current_blocks = []
            page_num += 1
        else:
            text = _extract_element(child, tag)
            if text:
                current_blocks.append(text)

    # Flush the final page.
    if current_blocks:
        pages.append(_make_page(page_num, current_blocks, filename))

    return pages


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_page(
    page_number: int,
    blocks: list[str],
    filename: str,
) -> PageData:
    return PageData(
        page_number=page_number,
        extracted_text="\n".join(blocks),
        evidence_anchor=f"{filename}:page:{page_number}",
    )


def _extract_element(element: etree._Element, tag: str) -> str:
    """Return readable text for a body-level element."""
    if tag == "tbl":
        return _extract_table(element)
    # Assume paragraph.
    return _extract_paragraph(element)


def _extract_paragraph(p: etree._Element) -> str:
    """Join all w:t text nodes in a paragraph."""
    parts = [t.text for t in p.findall(".//w:t", _NS) if t.text]
    return " ".join(parts).strip()


def _extract_table(tbl: etree._Element) -> str:
    """Render a table as pipe-separated rows."""
    rows: list[str] = []
    for tr in tbl.findall(".//w:tr", _NS):
        cells: list[str] = []
        for tc in tr.findall("w:tc", _NS):
            parts = [t.text for t in tc.findall(".//w:t", _NS) if t.text]
            cells.append(" ".join(parts).strip())
        rows.append(" | ".join(cells))
    return "\n".join(rows)
