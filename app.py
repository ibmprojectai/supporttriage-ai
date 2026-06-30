"""supporttriage-ai — orchestration entry point.

Drives a mock ticket end-to-end through the full pipeline:
  1. Intake       — fetch ticket (Zendesk stub)
  2. Guardrails   — PII redaction
  3. Classify     — category + priority
  4. Extract      — error codes + account/product enrichment
  5. Summarize    — 2–3 sentence summary
  6. Draft        — RAG-grounded reply via ChromaDB + Granite
  7. Route        — auto-tag + queue assignment
  8. Print        — structured output

Run:
    python app.py

Works in stub mode (no .env required) — LLM stages degrade gracefully.
"""

from __future__ import annotations

import pprint
import sys

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


def run_pipeline(ticket_id: str = "mock") -> None:
    print("=" * 60)
    print("  supporttriage-ai — end-to-end triage pipeline")
    print("=" * 60)

    # ── 1. Intake ──────────────────────────────────────────────────
    print("\n[1/7] Fetching ticket …")
    ticket = fetch_ticket(ticket_id)
    print(f"      id={ticket.id!r}  subject={ticket.subject!r}")

    # ── 2. PII Redaction ───────────────────────────────────────────
    print("\n[2/7] Redacting PII …")
    ticket.body = redact(ticket.body)
    ticket.thread = [redact(msg) for msg in ticket.thread]
    print("      PII redaction complete.")

    # ── 3. Classify ────────────────────────────────────────────────
    print("\n[3/7] Classifying ticket …")
    ticket = classify(ticket)
    print(f"      category={ticket.category!r}  priority={ticket.priority!r}")

    # ── 4. Extract ─────────────────────────────────────────────────
    print("\n[4/7] Extracting fields …")
    ticket = extract(ticket)
    print(f"      error_codes={ticket.error_codes!r}  account={ticket.account!r}")

    # ── 5. Summarize ───────────────────────────────────────────────
    print("\n[5/7] Summarising ticket …")
    ticket = summarize(ticket)
    print(f"      summary={ticket.summary[:80]!r} …")

    # ── 6. Draft reply (RAG) ───────────────────────────────────────
    print("\n[6/7] Drafting reply (RAG) …")
    collection = init_store()
    ticket = draft_reply(ticket, collection)
    print(f"      draft_reply={ticket.draft_reply[:80]!r} …")

    # ── 7. Route ───────────────────────────────────────────────────
    print("\n[7/7] Routing ticket …")
    routing = route(ticket)
    print(f"      queue={routing['queue']!r}  escalate={routing['escalate']}")

    # ── Final summary ──────────────────────────────────────────────
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
        "category": ticket.category,
        "priority": ticket.priority,
        "summary": ticket.summary,
        "draft_reply": ticket.draft_reply,
        "routing": routing,
    }
    pprint.pprint(fields, width=80, sort_dicts=False)
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
