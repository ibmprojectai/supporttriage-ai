"""Pipeline stage 4 — draft a grounded reply using RAG + local Ollama model.

Retrieves KB snippets from ChromaDB filtered by ticket category and product,
then calls the LLM to compose a professional reply grounded in that context.
Sets ticket.draft_reply.

Live mode:  calls the local Ollama model via watsonx_config.get_model().
Stub mode:  returns a placeholder string that still shows retrieved RAG context.
"""

from __future__ import annotations

import asyncio
import logging
import time

from chromadb import Collection

from models import Ticket
from rag.store import retrieve
from watsonx_config import get_model

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior technical support agent. "
    "Using ONLY the knowledge-base context provided below, write a professional, "
    "empathetic reply to the customer's support ticket. "
    "Follow these rules:\n"
    "1. Greet the customer by name if available, otherwise use 'Hello'.\n"
    "2. Acknowledge the specific issue they reported.\n"
    "3. Provide clear, numbered troubleshooting steps drawn directly from the context.\n"
    "4. State the next step or escalation path.\n"
    "5. Keep the reply under 200 words.\n"
    "6. Do not include any PII (emails, phone numbers, card numbers).\n"
    "7. If the provided context does not contain enough information to answer the query, "
    "say explicitly: 'I need to escalate this to our specialist team for further investigation' "
    "— do NOT invent steps or information not present in the context.\n"
    "Respond with only the reply — no preamble or meta-commentary."
)


def _build_prompt(context: str, ticket: Ticket) -> str:
    return (
        f"Knowledge-base context:\n{context}\n\n"
        f"Ticket summary: {ticket.summary}\n"
        f"Category: {ticket.category} | Priority: {ticket.priority}\n\n"
        "Draft reply:"
    )


async def draft_reply(ticket: Ticket, collection: Collection) -> Ticket:
    """Generate a RAG-grounded draft reply for *ticket*.

    Step 1 — retrieve: query ChromaDB filtered by ticket category + product.
    Step 2 — ground:   pass snippets + ticket context to the LLM.
    """
    # ── Step 1: retrieve context filtered by category and product ──────────────
    query = ticket.summary or ticket.subject
    where_filter: dict | None = None
    if ticket.category:
        where_filter = {"category": ticket.category}

    snippets = retrieve(
        collection,
        query=query,
        n_results=3,
        where=where_filter,
    )

    # Fallback: if filtered retrieval returns nothing, retry without filter
    if not snippets and where_filter is not None:
        log.info("[draft] Filtered retrieval returned 0 results — retrying without filter.")
        snippets = retrieve(collection, query=query, n_results=3)

    if snippets:
        context_text = "\n---\n".join(
            f"[KB snippet {i + 1}]\n{s}" for i, s in enumerate(snippets)
        )
    else:
        context_text = "(no relevant knowledge-base context found)"

    print(f"[draft] Retrieved {len(snippets)} KB snippet(s) for grounding.")
    log.info("[draft] snippets=%d category_filter=%r", len(snippets), ticket.category)

    # ── Step 2: generate reply ─────────────────────────────────────────────────
    model = get_model()

    if model is None:
        log.warning("[draft] STUB MODE — Ollama unreachable.")
        print("[draft] STUB MODE — Ollama not found.")
        ticket.draft_reply = (
            "[STUB] Draft reply not available — start Ollama and pull a model "
            "to enable LLM generation.\n\n"
            f"RAG context that would be used ({len(snippets)} snippet(s)):\n"
            f"{context_text}"
        )
        return ticket

    t0 = time.perf_counter()
    prompt = f"{_SYSTEM}\n\n{_build_prompt(context_text, ticket)}"
    response: str = await asyncio.to_thread(model.generate_text, prompt)
    elapsed = time.perf_counter() - t0

    ticket.draft_reply = response.strip()
    log.info("[draft] reply_length=%d chars elapsed=%.2fs", len(ticket.draft_reply), elapsed)
    print(f"[draft] draft_reply={ticket.draft_reply[:80]!r} …")
    return ticket
