"""supporttriage-ai — orchestration entry point.

Drives a mock ticket end-to-end through the full pipeline:
  1. Intake       — fetch ticket (Zendesk stub)
  2. Guardrails   — PII redaction
  3. Classify     — category + priority + confidence
  4. Extract      — error codes + symptoms + confidence
  5. Summarize    — 2–3 sentence summary
  6. Draft        — RAG-grounded reply (metadata-filtered ChromaDB + LLM)
  7. Route        — auto-tag + queue assignment + human-review fallback

Run:
    python app.py

Works in stub mode (no Ollama required) — LLM stages degrade gracefully.
"""

from __future__ import annotations

import asyncio
import logging
import pprint
import sys
import time

# Ensure UTF-8 output on Windows terminals that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from guardrails.pii_redactor import redact
from intake.zendesk_connector import fetch_ticket
from pipeline.classify import classify
from pipeline.draft import draft_reply
from pipeline.extract import extract
from pipeline.summarize import summarize
from rag.store import init_store
from routing.router import route

# ── Structured logging setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


async def run_pipeline_async(ticket_id: str = "mock") -> None:
    t_start = time.perf_counter()

    print("=" * 60)
    print("  supporttriage-ai — end-to-end triage pipeline")
    print("=" * 60)

    # ── 1. Intake ──────────────────────────────────────────────────
    print("\n[1/7] Fetching ticket …")
    ticket = await asyncio.to_thread(fetch_ticket, ticket_id)
    log.info("[intake] id=%r subject=%r", ticket.id, ticket.subject)
    print(f"      id={ticket.id!r}  subject={ticket.subject!r}")

    # ── 2. PII Redaction ───────────────────────────────────────────
    print("\n[2/7] Redacting PII …")
    ticket.body = redact(ticket.body)
    ticket.thread = [redact(msg) for msg in ticket.thread]
    log.info("[pii] redaction complete")
    print("      PII redaction complete.")

    # ── 3. Classify ────────────────────────────────────────────────
    print("\n[3/7] Classifying ticket …")
    ticket = await classify(ticket)
    print(
        f"      category={ticket.category!r}  priority={ticket.priority!r}"
        f"  confidence={ticket.confidence_classify:.2f}"
    )

    # ── 4. Extract ─────────────────────────────────────────────────
    print("\n[4/7] Extracting fields …")
    ticket = await extract(ticket)
    print(
        f"      error_codes={ticket.error_codes!r}  account={ticket.account!r}"
        f"  symptoms={ticket.symptoms!r}"
    )

    # ── 5. Summarize ───────────────────────────────────────────────
    print("\n[5/7] Summarising ticket …")
    ticket = await summarize(ticket)
    print(f"      summary={ticket.summary[:80]!r} …")

    # ── 6. Draft reply (RAG) ───────────────────────────────────────
    print("\n[6/7] Drafting reply (RAG) …")
    collection = await asyncio.to_thread(init_store)
    ticket = await draft_reply(ticket, collection)
    print(f"      draft_reply={ticket.draft_reply[:80]!r} …")

    # ── 7. Route ───────────────────────────────────────────────────
    print("\n[7/7] Routing ticket …")
    routing = route(ticket)
    log.info(
        "[route] queue=%r escalate=%s human_review=%s severity=%.1f",
        routing["queue"], routing["escalate"],
        routing["requires_human_review"], routing["severity_impact"],
    )
    print(
        f"      queue={routing['queue']!r}  escalate={routing['escalate']}"
        f"  human_review={routing['requires_human_review']}"
        f"  severity_impact={routing['severity_impact']:.1f}"
    )

    # ── Final summary ──────────────────────────────────────────────
    elapsed = time.perf_counter() - t_start
    print("\n" + "=" * 60)
    print("  TRIAGE RESULT")
    print("=" * 60)

    fields = {
        "id": ticket.id,
        "sender": ticket.sender,
        "subject": ticket.subject,
        "account": ticket.account,
        "product": ticket.product,
        "error_codes": ticket.error_codes,
        "symptoms": ticket.symptoms,
        "category": ticket.category,
        "priority": ticket.priority,
        "confidence_classify": round(ticket.confidence_classify, 2),
        "confidence_extract": round(ticket.confidence_extract, 2),
        "summary": ticket.summary,
        "draft_reply": ticket.draft_reply,
        "routing": routing,
    }
    pprint.pprint(fields, width=80, sort_dicts=False)
    print("=" * 60)
    log.info("[pipeline] completed in %.2fs", elapsed)


if __name__ == "__main__":
    asyncio.run(run_pipeline_async())
