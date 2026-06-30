"""Pipeline stage 2 — extract structured fields from a support ticket.

Sets ticket.error_codes and enriches ticket.account / ticket.product when missing.
Falls back to regex-based extraction in stub mode.
"""

from __future__ import annotations

import json
import re

from langchain_core.prompts import PromptTemplate

from models import Ticket
from watsonx_config import get_llm

_PROMPT = PromptTemplate(
    input_variables=["body"],
    template="""You are a support-ticket data extractor. Analyse the ticket body below and
respond with a JSON object containing exactly these keys:
  "error_codes": list of error code strings (e.g. ["ERR-4021"]), empty list if none
  "account":     account identifier string (e.g. "ACC-00982"), empty string if not found
  "product":     product name string, empty string if not found

Ticket body:
{body}

Respond with only the JSON object — no explanation, no markdown fences.""",
)

# Fallback regex for stub mode
_ERR_RE = re.compile(r"\bERR-\d+\b")
_ACC_RE = re.compile(r"\bACC-\d+\b")


def extract(ticket: Ticket) -> Ticket:
    """Extract error codes and enrich account/product on *ticket*.

    Uses the Granite foundation model via WatsonxLLM.  If credentials are absent,
    falls back to simple regex extraction so the mock flow still demonstrates the
    field population without LLM calls.
    """
    llm = get_llm()
    if llm is None:
        print("[extract] STUB MODE — using regex fallback for extraction.")
        ticket.error_codes = _ERR_RE.findall(ticket.body)
        if not ticket.account:
            match = _ACC_RE.search(ticket.body)
            ticket.account = match.group(0) if match else ""
        return ticket

    chain = _PROMPT | llm
    response: str = chain.invoke({"body": ticket.body})

    try:
        # Strip accidental markdown fences the model may add
        clean = re.sub(r"```(?:json)?", "", response).strip().rstrip("```").strip()
        data: dict = json.loads(clean)
        ticket.error_codes = data.get("error_codes") or []
        if not ticket.account:
            ticket.account = data.get("account") or ""
        if not ticket.product:
            ticket.product = data.get("product") or ""
    except json.JSONDecodeError:
        print(f"[extract] JSON parse failed — falling back to regex. Response was: {response!r}")
        ticket.error_codes = _ERR_RE.findall(ticket.body)

    return ticket
