"""Extraction prompts — one per document type, plus the shared system preamble.

Design principle: the model reads, code normalizes.  The LLM emits only what
is literally printed on the page — verbatim strings, raw dates, raw status
text.  Deterministic code then maps category_hint → source_classification,
record status → documentation_status, and MM/DD/YYYY → ISO.

Prompt registry
---------------
Each prompt module exports a ``PROMPT`` string containing the user-turn
instructions for that document type.  The shared system preamble is in
``system_preamble.SYSTEM``.

Usage::

    from oep.extraction.prompts import system_preamble, loss_notice
    messages = [
        {"role": "system", "content": system_preamble.SYSTEM},
        {"role": "user",   "content": loss_notice.PROMPT.format(pages=tagged_text)},
    ]
"""

from oep.extraction.prompts import (
    certificate,
    financial_journal,
    loss_notice,
    source_register,
    system_preamble,
)

PROMPT_BY_DOC_TYPE: dict[str, str] = {
    "loss_notice_and_record_index": loss_notice.PROMPT,
    "tenancy_financial_journal": financial_journal.PROMPT,
    "restoration_cost_register": source_register.PROMPT,
    "premises_condition_log": source_register.PROMPT,
    "covered_tenancy_certificate": certificate.PROMPT,
}
