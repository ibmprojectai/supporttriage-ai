"""Pipeline stage 1 — classify a support ticket.

Sets ticket.category and ticket.priority using an IBM Granite LLM chain.
Falls back to stub values when watsonx credentials are absent.
"""

from __future__ import annotations

import re

from langchain_core.prompts import PromptTemplate

from models import Ticket
from watsonx_config import get_llm

_PROMPT = PromptTemplate(
    input_variables=["subject", "body"],
    template="""You are a support-ticket classifier. Given the ticket below, respond with
exactly two lines in this format:
CATEGORY: <one of: authentication, billing, performance, data-loss, feature-request, other>
PRIORITY: <one of: critical, high, medium, low>

Subject: {subject}
Body: {body}

Respond with only the two lines above — no extra text.""",
)


def classify(ticket: Ticket) -> Ticket:
    """Classify *ticket*, setting ``category`` and ``priority``.

    Uses the Granite foundation model via WatsonxLLM.  If credentials are absent,
    returns the ticket unchanged (stub mode) after printing a warning.
    """
    llm = get_llm()
    if llm is None:
        print(
            "[classify] STUB MODE — watsonx credentials not found. "
            "Setting placeholder category/priority."
        )
        ticket.category = "authentication"
        ticket.priority = "high"
        return ticket

    chain = _PROMPT | llm
    response: str = chain.invoke({"subject": ticket.subject, "body": ticket.body})

    category_match = re.search(r"CATEGORY:\s*(.+)", response, re.IGNORECASE)
    priority_match = re.search(r"PRIORITY:\s*(.+)", response, re.IGNORECASE)

    ticket.category = category_match.group(1).strip().lower() if category_match else "other"
    ticket.priority = priority_match.group(1).strip().lower() if priority_match else "medium"

    return ticket
