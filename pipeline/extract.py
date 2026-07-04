"""Pipeline stage 2 — extract structured fields from a support ticket.

Sets ticket.error_codes, ticket.symptoms, ticket.confidence_extract, and
enriches ticket.account / ticket.product when missing.

Live mode:  calls Ollama via LangChain OllamaLLM with strict JSON schema.
Stub mode:  regex-based extraction when Ollama is unreachable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from models import Ticket
from watsonx_config import get_llm

log = logging.getLogger(__name__)

_PROMPT = PromptTemplate(
    input_variables=["body"],
    template="""You are a support-ticket data extractor. Analyse the ticket body below and
respond with a JSON object containing exactly these keys:
  "error_codes": list of error code strings (e.g. ["ERR-4021"]), empty list if none
  "account":     account identifier string (e.g. "ACC-00982"), empty string if not found
  "product":     product name string, empty string if not found
  "symptoms":    list of short symptom strings describing observed behaviours (e.g. ["cannot login", "session expires immediately"])
  "confidence":  float 0.0-1.0 — your confidence in the extracted fields

Ticket body:
{body}

Respond with only the JSON object — no explanation, no markdown fences.""",
)

# Fallback regex for stub mode
_ERR_RE = re.compile(r"\bERR-\d+\b")
_ACC_RE = re.compile(r"\bACC-\d+\b")


def _repair_json(raw: str) -> str:
    """Strip markdown fences and common LLM JSON noise."""
    # Remove ```json ... ``` or ``` ... ```
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    # Strip any leading prose before the first '{'
    brace = clean.find("{")
    if brace > 0:
        clean = clean[brace:]
    return clean


async def extract(ticket: Ticket) -> Ticket:
    """Extract error codes, symptoms, and enrich account/product on *ticket*."""
    llm = get_llm()

    if llm is None:
        log.warning("[extract] STUB MODE — Ollama unreachable. Using regex fallback.")
        print("[extract] STUB MODE — using regex fallback for extraction.")
        ticket.error_codes = _ERR_RE.findall(ticket.body)
        if not ticket.account:
            match = _ACC_RE.search(ticket.body)
            ticket.account = match.group(0) if match else ""
        ticket.symptoms = []
        ticket.confidence_extract = 0.0
        return ticket

    chain = _PROMPT | llm | StrOutputParser()

    t0 = time.perf_counter()
    response: str = await chain.ainvoke({"body": ticket.body})
    elapsed = time.perf_counter() - t0

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
            "[extract] JSON parse failed after repair — falling back to regex. raw=%r",
            response,
        )
        print(f"[extract] JSON parse failed — falling back to regex. Response was: {response!r}")
        ticket.error_codes = _ERR_RE.findall(ticket.body)
        ticket.symptoms = []
        ticket.confidence_extract = 0.0

    log.info(
        "[extract] error_codes=%r symptoms=%r confidence=%.2f elapsed=%.2fs",
        ticket.error_codes, ticket.symptoms, ticket.confidence_extract, elapsed,
    )
    return ticket
