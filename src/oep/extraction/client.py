"""Model client wrapper for document extraction.

Handles: temperature 0, JSON output, Pydantic validation, one repair retry
that feeds back the validator error, then fail loudly.  Every call is logged
into a ``ModelCallRecord`` for later inclusion in the output's ``model_calls``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from decimal import Decimal

import anthropic
from pydantic import BaseModel, ValidationError

from oep.config import DEFAULT_MODEL, DEFAULT_PROVIDER
from oep.extraction.prompts import PROMPT_BY_DOC_TYPE, system_preamble
from oep.extraction.schemas import RAW_SCHEMA_BY_DOC_TYPE


# ---------------------------------------------------------------------------
# Model call record — maps to the output schema's ModelCall
# ---------------------------------------------------------------------------

@dataclass
class ModelCallRecord:
    """One LLM call, ready to be converted to output.ModelCall."""

    purpose: str
    provider: str
    requested_model: str
    routed_provider: str
    routed_model: str
    response_id: str | None
    duration_ms: int
    attempt_count: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None
    cost_source: str  # "provider" | "estimated" | "not_available"
    stored_by_provider: bool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_document(
    document_type: str,
    page_tagged_text: str,
    *,
    model: str = DEFAULT_MODEL,
    claim_id: str = "",
) -> tuple[BaseModel, ModelCallRecord]:
    """Run LLM extraction for a single document.

    Parameters
    ----------
    document_type:
        One of the five document type keys.
    page_tagged_text:
        The ``<<<PAGE N>>>`` tagged text from ``docx_pages``.
    model:
        Model identifier to request.
    claim_id:
        For logging purposes only.

    Returns
    -------
    (parsed_model, call_record)
        The Pydantic-validated raw extraction and the call metadata.

    Raises
    ------
    ExtractionError
        After one repair retry still fails validation.
    """
    prompt_template = PROMPT_BY_DOC_TYPE[document_type]
    schema_cls = RAW_SCHEMA_BY_DOC_TYPE[document_type]
    user_content = prompt_template.format(pages=page_tagged_text)

    client = anthropic.Anthropic()
    attempt_count = 0
    total_input = 0
    total_cached = 0
    total_output = 0
    total_duration_ms = 0
    response_id: str | None = None
    last_error: Exception | None = None

    for attempt in range(2):  # at most 2 attempts (initial + 1 repair)
        attempt_count += 1

        messages: list[dict] = [{"role": "user", "content": user_content}]

        # On retry, append the validation error as feedback.
        if attempt == 1 and last_error is not None:
            messages.append({
                "role": "assistant",
                "content": _last_response_text,
            })
            messages.append({
                "role": "user",
                "content": (
                    f"Your JSON failed Pydantic validation:\n\n"
                    f"{last_error}\n\n"
                    f"Fix the errors and return only the corrected JSON object."
                ),
            })

        t0 = time.monotonic()
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            system=system_preamble.SYSTEM,
            messages=messages,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        total_duration_ms += elapsed_ms

        # Accumulate token usage.
        usage = response.usage
        total_input += usage.input_tokens
        total_cached += getattr(usage, "cache_read_input_tokens", 0)
        total_output += usage.output_tokens
        response_id = response.id

        # Extract text from response.
        _last_response_text = response.content[0].text
        raw_text = _last_response_text.strip()

        # Strip markdown fences if model wrapped output.
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last fence lines.
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw_text = "\n".join(lines)

        try:
            data = json.loads(raw_text)
            result = schema_cls.model_validate(data)
            break
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            if attempt == 1:
                raise ExtractionError(
                    f"Extraction failed for {document_type} ({claim_id}) "
                    f"after {attempt_count} attempts: {exc}"
                ) from exc

    call_record = ModelCallRecord(
        purpose=f"extract_{document_type}",
        provider=DEFAULT_PROVIDER,
        requested_model=model,
        routed_provider=DEFAULT_PROVIDER,
        routed_model=getattr(response, "model", model),
        response_id=response_id,
        duration_ms=total_duration_ms,
        attempt_count=attempt_count,
        input_tokens=total_input,
        cached_input_tokens=total_cached,
        output_tokens=total_output,
        total_tokens=total_input + total_output,
        cost_usd=None,
        cost_source="not_available",
        stored_by_provider=True,
    )

    return result, call_record  # type: ignore[possibly-undefined]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """Extraction failed after retry."""


def build_page_tagged_text(pages: list) -> str:
    """Convert a list of PageData objects to <<<PAGE N>>> tagged text."""
    parts = []
    for page in pages:
        parts.append(f"<<<PAGE {page.page_number}>>>")
        parts.append(page.extracted_text)
        parts.append("")
    return "\n".join(parts)
