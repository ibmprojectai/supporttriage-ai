"""Pipeline stage 3 — summarize a support ticket.

Sets ticket.summary to a concise 2–3 sentence condensation of the full ticket thread.
Falls back to a templated stub summary when watsonx credentials are absent.
"""

from __future__ import annotations

from langchain_core.prompts import PromptTemplate

from models import Ticket
from watsonx_config import get_llm

_PROMPT = PromptTemplate(
    input_variables=["subject", "body", "thread"],
    template="""You are a support-ticket summariser. Write a concise 2–3 sentence summary
of the issue described below. Include the product, the reported error, and the customer's
current situation. Do not include personal data.

Subject: {subject}
Body: {body}
Thread:
{thread}

Summary:""",
)


def summarize(ticket: Ticket) -> Ticket:
    """Summarise *ticket*, setting ``summary``.

    Uses the Granite foundation model via WatsonxLLM.  Falls back to a templated
    stub summary when credentials are absent.
    """
    llm = get_llm()
    if llm is None:
        print("[summarize] STUB MODE — generating templated summary.")
        ticket.summary = (
            f"Customer reports inability to log in to {ticket.product or 'the product'} "
            f"after a password reset, receiving error code(s) "
            f"{', '.join(ticket.error_codes) if ticket.error_codes else 'unknown'}. "
            f"Account {ticket.account or 'unknown'} is affected and the issue is blocking "
            f"the customer's team. Multiple browsers have been tried without success."
        )
        return ticket

    thread_text = "\n".join(f"- {msg}" for msg in ticket.thread) if ticket.thread else "(no thread)"
    chain = _PROMPT | llm
    response: str = chain.invoke(
        {"subject": ticket.subject, "body": ticket.body, "thread": thread_text}
    )
    ticket.summary = response.strip()
    return ticket
