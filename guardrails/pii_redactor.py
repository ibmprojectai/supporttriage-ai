"""PII redactor — strips personal data from ticket text before LLM calls.

Applies a regex pass for the most common PII patterns.
TODO: add an LLM-based fallback for harder PII not caught by regex (e.g. names,
      partial addresses).  Hook goes at the bottom of redact() where marked.
"""

from __future__ import annotations

import re

# ── Regex patterns ─────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Matches common US/international phone formats: 415-555-0198, (415) 555 0198, +1 415 555 0198
_PHONE_RE = re.compile(
    r"(\+?1[\s\-.]?)?"           # optional country code
    r"(\(?\d{3}\)?[\s\-.]?)"     # area code
    r"\d{3}[\s\-.]?\d{4}"        # number
)

# 13–19 digit sequences that look like card numbers (with optional separators)
_CC_RE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")


def redact(text: str) -> str:
    """Return *text* with PII replaced by labelled placeholders.

    Replacement markers:
      [EMAIL]  — email addresses
      [PHONE]  — phone numbers
      [CC]     — credit / debit card numbers
    """
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _CC_RE.sub("[CC]", text)      # run CC before PHONE to avoid partial overlaps
    text = _PHONE_RE.sub("[PHONE]", text)

    # TODO: LLM-fallback hook — call an LLM here for residual PII (names, addresses, etc.)
    # Example:
    #   llm = get_llm()
    #   if llm:
    #       text = llm_pii_fallback(llm, text)

    return text
