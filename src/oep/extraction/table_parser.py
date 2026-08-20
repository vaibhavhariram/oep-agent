"""Deterministic table parser for journal and source register documents.

Reads the same page-split text that the LLM receives, parses the
pipe-separated tables, and returns structured data.  This is a
CROSS-CHECK against the LLM extraction — compare field by field and
emit extraction-integrity warnings on disagreement.  Do not silently
prefer one source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from oep.ingest.docx_pages import PageData


# ===================================================================
# Parsed table row types
# ===================================================================

@dataclass
class ParsedLedgerRow:
    entry_date: str
    description: str
    debit_amount: float
    credit_amount: float
    running_balance: float
    source_page: int


@dataclass
class ParsedSourceLine:
    line_number: int
    description: str
    source_category: str
    gross_amount: float
    source_page: int


@dataclass
class ParsedRecordRegisterRow:
    line_number: int
    record_status: str
    record_reference: str | None
    service_life_fact: str | None
    source_page: int


# ===================================================================
# Money parsing helper
# ===================================================================

_MONEY_RE = re.compile(r"^\$?([\d,]+(?:\.\d+)?)$")


def _parse_money(raw: str) -> float | None:
    """Parse a dollar string like '$1,725.00' into a float.  Returns None for '—' or blanks."""
    s = raw.strip()
    if not s or s == "\u2014" or s == "—" or s == "-":
        return None
    m = _MONEY_RE.match(s)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _split_pipe_row(line: str) -> list[str]:
    """Split a pipe-separated row into trimmed cells."""
    return [cell.strip() for cell in line.split("|")]


# ===================================================================
# Journal parser
# ===================================================================

def parse_journal(pages: list[PageData]) -> list[ParsedLedgerRow]:
    """Parse the Tenancy Financial Journal from rendered page text.

    Expects a single page with pipe-separated ledger rows following the
    header row ``Date | Journal description | Debit | Credit / recovery | Running balance``.
    """
    rows: list[ParsedLedgerRow] = []
    if not pages:
        return rows

    text = pages[0].extracted_text
    lines = text.split("\n")
    in_table = False

    for line in lines:
        if "|" not in line:
            if in_table:
                break  # End of table.
            continue

        cells = _split_pipe_row(line)

        # Detect header row.
        if any("journal description" in c.lower() for c in cells):
            in_table = True
            continue

        if not in_table:
            continue

        if len(cells) < 5:
            continue

        date_str = cells[0]
        description = cells[1]
        debit = _parse_money(cells[2])
        credit = _parse_money(cells[3])
        balance = _parse_money(cells[4])

        # Skip if it doesn't look like a data row (e.g. header metadata).
        if balance is None:
            continue

        rows.append(ParsedLedgerRow(
            entry_date=date_str,
            description=description,
            debit_amount=debit if debit is not None else 0.0,
            credit_amount=credit if credit is not None else 0.0,
            running_balance=balance,
            source_page=pages[0].page_number,
        ))

    return rows


# ===================================================================
# Source register parser (Cost Register / Condition Log)
# ===================================================================

def parse_source_lines(pages: list[PageData]) -> list[ParsedSourceLine]:
    """Parse the 'Presented source lines' table from page 1."""
    rows: list[ParsedSourceLine] = []
    if not pages:
        return rows

    text = pages[0].extracted_text
    lines = text.split("\n")
    in_table = False

    for line in lines:
        if "|" not in line:
            if in_table:
                break
            continue

        cells = _split_pipe_row(line)

        # Detect header row.
        if any("source description" in c.lower() for c in cells):
            in_table = True
            continue

        if not in_table:
            continue

        if len(cells) < 4:
            continue

        try:
            line_num = int(cells[0])
        except ValueError:
            continue

        amount = _parse_money(cells[3])
        if amount is None:
            continue

        rows.append(ParsedSourceLine(
            line_number=line_num,
            description=cells[1],
            source_category=cells[2],
            gross_amount=amount,
            source_page=pages[0].page_number,
        ))

    return rows


def parse_record_register(pages: list[PageData]) -> list[ParsedRecordRegisterRow]:
    """Parse the 'Source Record Register' table from page 2."""
    rows: list[ParsedRecordRegisterRow] = []
    if len(pages) < 2:
        return rows

    text = pages[1].extracted_text
    lines = text.split("\n")
    in_table = False

    for line in lines:
        if "|" not in line:
            if in_table:
                break
            continue

        cells = _split_pipe_row(line)

        # Detect header row.
        if any("record status" in c.lower() for c in cells):
            in_table = True
            continue

        if not in_table:
            continue

        if len(cells) < 4:
            continue

        try:
            line_num = int(cells[0])
        except ValueError:
            continue

        ref = cells[2] if cells[2].lower() != "none stated" else None
        fact = cells[3] if len(cells) > 3 else None

        rows.append(ParsedRecordRegisterRow(
            line_number=line_num,
            record_status=cells[1],
            record_reference=ref,
            service_life_fact=fact,
            source_page=pages[1].page_number,
        ))

    return rows


# ===================================================================
# Cross-check: compare parser output vs LLM extraction
# ===================================================================

def crosscheck_journal(
    parsed: list[ParsedLedgerRow],
    llm_entries: list,
) -> list[str]:
    """Compare deterministic journal parse against LLM extraction.

    Returns a list of extraction-integrity warnings.  Empty = agreement.
    """
    warnings: list[str] = []

    if len(parsed) != len(llm_entries):
        warnings.append(
            f"Journal row count mismatch: parser found {len(parsed)}, "
            f"LLM returned {len(llm_entries)}"
        )
        return warnings

    for i, (p, l) in enumerate(zip(parsed, llm_entries)):
        row_id = f"journal row {i + 1}"
        if p.description != l.description:
            warnings.append(
                f"{row_id} description: parser={p.description!r}, "
                f"LLM={l.description!r}"
            )
        if abs(p.debit_amount - l.debit_amount) > 0.005:
            warnings.append(
                f"{row_id} debit: parser={p.debit_amount}, LLM={l.debit_amount}"
            )
        if abs(p.credit_amount - l.credit_amount) > 0.005:
            warnings.append(
                f"{row_id} credit: parser={p.credit_amount}, LLM={l.credit_amount}"
            )
        if abs(p.running_balance - l.running_balance) > 0.005:
            warnings.append(
                f"{row_id} balance: parser={p.running_balance}, LLM={l.running_balance}"
            )

    return warnings


def crosscheck_source_lines(
    parsed: list[ParsedSourceLine],
    llm_lines: list,
) -> list[str]:
    """Compare deterministic source-line parse against LLM extraction.

    Returns a list of extraction-integrity warnings.  Empty = agreement.
    """
    warnings: list[str] = []

    if len(parsed) != len(llm_lines):
        warnings.append(
            f"Source-line count mismatch: parser found {len(parsed)}, "
            f"LLM returned {len(llm_lines)}"
        )
        return warnings

    for i, (p, l) in enumerate(zip(parsed, llm_lines)):
        row_id = f"source line {p.line_number}"
        if p.description != l.description:
            warnings.append(
                f"{row_id} description: parser={p.description!r}, "
                f"LLM={l.description!r}"
            )
        if abs(p.gross_amount - l.gross_amount) > 0.005:
            warnings.append(
                f"{row_id} amount: parser={p.gross_amount}, LLM={l.gross_amount}"
            )
        if p.source_category != l.source_category:
            warnings.append(
                f"{row_id} category: parser={p.source_category!r}, "
                f"LLM={l.source_category!r}"
            )

    return warnings


# ===================================================================
# Factual observations parser
# ===================================================================

@dataclass
class ParsedFactualObservation:
    observation: str
    recorded_fact: str
    source_page: int


def parse_factual_observations(pages: list[PageData]) -> list[ParsedFactualObservation]:
    """Parse the 'Factual observations' table from the last page of a register."""
    rows: list[ParsedFactualObservation] = []
    if not pages:
        return rows

    # Observations are on the last page (page 2 for most registers).
    text = pages[-1].extracted_text
    lines = text.split("\n")
    in_table = False

    for line in lines:
        if "|" not in line:
            if in_table:
                break
            continue

        cells = _split_pipe_row(line)

        # Detect header row.
        if any("observation" in c.lower() for c in cells) and any(
            "recorded fact" in c.lower() or "fact" in c.lower() for c in cells
        ):
            in_table = True
            continue

        if not in_table:
            continue

        if len(cells) < 2 or not cells[0] or not cells[1]:
            continue

        rows.append(ParsedFactualObservation(
            observation=cells[0],
            recorded_fact=cells[1],
            source_page=pages[-1].page_number,
        ))

    return rows
