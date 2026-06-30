"""Pipeline stage 4 — draft a reply to a support ticket using RAG.

Retrieves relevant knowledge-base snippets from ChromaDB and uses them as grounding
context for the Granite LLM to compose a helpful, accurate draft reply.
Sets ticket.draft_reply.
"""

from __future__ import annotations

from chromadb import Collection
from langchain_core.prompts import PromptTemplate

from models import Ticket
from rag.store import retrieve
from watsonx_config import get_llm

_PROMPT = PromptTemplate(
    input_variables=["context", "summary", "category", "priority"],
    template="""You are a senior technical support agent. Using the knowledge-base context
below, write a professional, empathetic reply to a support ticket.

Knowledge-base context:
{context}

Ticket summary:
{summary}

Category: {category} | Priority: {priority}

Guidelines:
- Greet the customer and acknowledge the issue.
- Provide clear troubleshooting steps drawn from the context above.
- Set an expectation for next steps or escalation if needed.
- Keep the reply under 200 words.
- Do not include any PII.

Draft reply:""",
)


def draft_reply(ticket: Ticket, collection: Collection) -> Ticket:
    """Generate a draft reply for *ticket* using RAG context from *collection*.

    Retrieves the top-3 KB snippets most relevant to the ticket summary, then
    asks Granite to compose a grounded reply.  Falls back to a placeholder string
    when credentials are absent.
    """
    llm = get_llm()

    # Always retrieve context so we can show it in stub mode too
    snippets = retrieve(collection, query=ticket.summary or ticket.subject, n_results=3)
    context_text = "\n---\n".join(snippets) if snippets else "(no knowledge-base context available)"

    if llm is None:
        print("[draft] STUB MODE — watsonx credentials not found.")
        ticket.draft_reply = (
            "[STUB] Draft reply not available — configure WATSONX_* env vars to enable LLM generation.\n\n"
            f"RAG context retrieved ({len(snippets)} snippet(s)):\n{context_text}"
        )
        return ticket

    chain = _PROMPT | llm
    response: str = chain.invoke(
        {
            "context": context_text,
            "summary": ticket.summary,
            "category": ticket.category,
            "priority": ticket.priority,
        }
    )
    ticket.draft_reply = response.strip()
    return ticket
