"""Pipeline stage 4 — draft a grounded reply using RAG + IBM Granite.

Retrieves the top-3 semantically relevant KB snippets from ChromaDB, then
calls IBM Granite to compose a professional reply grounded in that context.
Sets ticket.draft_reply.

Live mode:  calls IBM Granite via the native ibm-watsonx-ai ModelInference SDK.
Stub mode:  returns a placeholder string that includes the retrieved RAG context
            so the grounding pipeline is still visible without credentials.
"""

from __future__ import annotations

from chromadb import Collection

from models import Ticket
from rag.store import retrieve
from watsonx_config import get_model

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
    "Respond with only the reply — no preamble or meta-commentary."
)


def _build_prompt(context: str, ticket: Ticket) -> str:
    return (
        f"Knowledge-base context:\n{context}\n\n"
        f"Ticket summary: {ticket.summary}\n"
        f"Category: {ticket.category} | Priority: {ticket.priority}\n\n"
        "Draft reply:"
    )


def draft_reply(ticket: Ticket, collection: Collection) -> Ticket:
    """Generate a RAG-grounded draft reply for *ticket*.

    Step 1 — retrieve: query ChromaDB with the ticket summary to get the
             top-3 most relevant KB snippets.
    Step 2 — ground:   pass the snippets + ticket context to Granite and
             generate a draft reply.

    Falls back to a labelled placeholder (that still shows retrieved context)
    when watsonx credentials are absent.
    """
    # ── Step 1: retrieve context from ChromaDB ─────────────────────────────
    query = ticket.summary or ticket.subject
    snippets = retrieve(collection, query=query, n_results=3)

    if snippets:
        context_text = "\n---\n".join(
            f"[KB snippet {i + 1}]\n{s}" for i, s in enumerate(snippets)
        )
    else:
        context_text = "(no relevant knowledge-base context found)"

    print(f"[draft] Retrieved {len(snippets)} KB snippet(s) for grounding.")

    # ── Step 2: generate reply ─────────────────────────────────────────────
    model = get_model()

    if model is None:
        print("[draft] STUB MODE — watsonx credentials not found.")
        ticket.draft_reply = (
            "[STUB] Draft reply not available — configure WATSONX_* env vars "
            "to enable Granite LLM generation.\n\n"
            f"RAG context that would be used ({len(snippets)} snippet(s)):\n"
            f"{context_text}"
        )
        return ticket

    prompt = f"{_SYSTEM}\n\n{_build_prompt(context_text, ticket)}"
    response: str = model.generate_text(prompt=prompt)
    ticket.draft_reply = response.strip()

    print(f"[draft] draft_reply={ticket.draft_reply[:80]!r} …")
    return ticket
