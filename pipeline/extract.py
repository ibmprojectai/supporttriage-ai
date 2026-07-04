"""Pipeline stage 2 — extract structured fields from a support ticket.

Sets ticket.error_codes, ticket.symptoms, ticket.confidence_extract, and
enriches ticket.account / ticket.product when missing.

Live mode:  calls the model via get_model() — works with OpenRouter or Ollama.
Stub mode:  regex-based extraction when no model is available.
"""

from __future__ import annotations

import json
import logging
import re
import time

from models import Ticket
from watsonx_config import get_model

log = logging.getLogger(__name__)

_PROMPT = (
    "You are a support-ticket data extractor. Analyse the ticket body below and "
    "respond with a JSON object containing exactly these keys:\n"
    '  "error_codes": list of error code strings (e.g. ["ERR-4021"]), empty list if none\n'
    '  "account":     account identifier string (e.g. "ACC-00982"), empty string if not found\n'
    '  "product":     product name string, empty string if not found\n'
    '  "symptoms":    list of short symptom strings describing observed behaviours\n'
    '  "confidence":  float 0.0-1.0 — your confidence in the extracted fields\n\n'
    "Ticket body:\n{body}\n\n"
    "Respond with only the JSON object — no explanation, no markdown fences."
)

# Fallback regex for stub mode
_ERR_RE = re.compile(r"\bERR-\d+\b")
_ACC_RE = re.compile(r"\bACC-\d+\b")


def _repair_json(raw: str) -> str:
    """Strip markdown fences and common LLM JSON noise. Expects a plain str."""
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    brace = clean.find("{")
    if brace > 0:
        clean = clean[brace:]
    return clean


async def extract(ticket: Ticket) -> Ticket:
    """Extract error codes, symptoms, and enrich account/product on *ticket*."""
    import asyncio

    model = get_model()

    if model is None:
        log.warning("[extract] STUB MODE — no model available. Using regex fallback.")
        print("[extract] STUB MODE — using regex fallback for extraction.")
        ticket.error_codes = _ERR_RE.findall(ticket.body)
        if not ticket.account:
            match = _ACC_RE.search(ticket.body)
            ticket.account = match.group(0) if match else ""
        ticket.symptoms = []
        ticket.confidence_extract = 0.0
        return ticket

    prompt = _PROMPT.format(body=ticket.body)

    t0 = time.perf_counter()
    # generate_text() is synchronous — run in thread so we don't block the event loop
    response: str = await asyncio.to_thread(model.generate_text, prompt)
    elapsed = time.perf_counter() - t0

    # response is guaranteed str — generate_text() always returns str
    try:
        clean = _repair_json(response)
        data: dict = json.loads(clean)

        ticket.error_codes = data.get("error_codes") or []
        if not ticket.account:
            ticket.account = data.get("account") or ""
        if not ticket.product:
            ticket.product = data.get("product") or ""
        ticket.symptoms = data.get("symptoms") or []
        try:
            ticket.confidence_extract = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            ticket.confidence_extract = 0.5

    except json.JSONDecodeError:
        log.error(
            "[extract] JSON parse failed — falling back to regex. raw=%r", response,
        )
        print(f"[extract] JSON parse failed — falling back to regex. Response: {response!r}")
        ticket.error_codes = _ERR_RE.findall(ticket.body)
        ticket.symptoms = []
        ticket.confidence_extract = 0.0

    log.info(
        "[extract] error_codes=%r symptoms=%r confidence=%.2f elapsed=%.2fs",
        ticket.error_codes, ticket.symptoms, ticket.confidence_extract, elapsed,
    )
    return ticket
