"""Pipeline stage 1 — classify a support ticket.

Sets ticket.category and ticket.priority.

Live mode:  calls IBM Granite via the native ibm-watsonx-ai ModelInference SDK.
Stub mode:  sets deterministic placeholder values when credentials are absent.
"""

from __future__ import annotations

import re

from models import Ticket
from watsonx_config import get_model

_SYSTEM = (
    "You are a support-ticket classifier. "
    "Respond with exactly two lines and nothing else:\n"
    "CATEGORY: <one of: authentication, billing, performance, data-loss, feature-request, other>\n"
    "PRIORITY: <one of: critical, high, medium, low>"
)


def _build_prompt(ticket: Ticket) -> str:
    return (
        f"Subject: {ticket.subject}\n"
        f"Body:\n{ticket.body}\n\n"
        "Classify this ticket."
    )


def classify(ticket: Ticket) -> Ticket:
    """Classify *ticket*, setting ``category`` and ``priority``.

    Uses IBM Granite (ibm/granite-3-8b-instruct) via the ibm-watsonx-ai SDK.
    Falls back to stub values when credentials are absent.
    """
    model = get_model()

    if model is None:
        print(
            "[classify] STUB MODE — watsonx credentials not found. "
            "Setting placeholder category/priority."
        )
        ticket.category = "authentication"
        ticket.priority = "high"
        return ticket

    prompt = f"{_SYSTEM}\n\n{_build_prompt(ticket)}"
    response: str = model.generate_text(prompt=prompt)

    category_match = re.search(r"CATEGORY:\s*(.+)", response, re.IGNORECASE)
    priority_match = re.search(r"PRIORITY:\s*(.+)", response, re.IGNORECASE)

    ticket.category = (
        category_match.group(1).strip().lower() if category_match else "other"
    )
    ticket.priority = (
        priority_match.group(1).strip().lower() if priority_match else "medium"
    )

    print(f"[classify] category={ticket.category!r}  priority={ticket.priority!r}")
    return ticket
