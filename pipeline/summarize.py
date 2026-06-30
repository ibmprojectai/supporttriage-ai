"""Pipeline stage 3 — summarize a support ticket.

Sets ticket.summary to a concise 2–3 sentence condensation of the full ticket thread.

Live mode:  calls IBM Granite via the native ibm-watsonx-ai ModelInference SDK.
Stub mode:  returns a templated summary when credentials are absent.
"""

from __future__ import annotations

from models import Ticket
from watsonx_config import get_model

_SYSTEM = (
    "You are a support-ticket summariser. "
    "Write a concise 2-3 sentence summary of the issue. "
    "Include the product name, the reported error, and the customer's current situation. "
    "Do not include any personal data such as names, emails, or phone numbers. "
    "Respond with only the summary — no preamble."
)


def _build_prompt(ticket: Ticket) -> str:
    thread_text = (
        "\n".join(f"  - {msg}" for msg in ticket.thread)
        if ticket.thread
        else "  (no thread)"
    )
    return (
        f"Subject: {ticket.subject}\n"
        f"Body:\n{ticket.body}\n\n"
        f"Thread:\n{thread_text}\n\n"
        "Summarise this ticket."
    )


def summarize(ticket: Ticket) -> Ticket:
    """Summarise *ticket*, setting ``summary``.

    Uses IBM Granite (ibm/granite-3-8b-instruct) via the ibm-watsonx-ai SDK.
    Falls back to a templated stub summary when credentials are absent.
    """
    model = get_model()

    if model is None:
        print("[summarize] STUB MODE — generating templated summary.")
        ticket.summary = (
            f"Customer reports inability to log in to {ticket.product or 'the product'} "
            f"after a password reset, receiving error code(s) "
            f"{', '.join(ticket.error_codes) if ticket.error_codes else 'unknown'}. "
            f"Account {ticket.account or 'unknown'} is affected and the issue is blocking "
            "the customer's team. Multiple browsers have been tried without success."
        )
        return ticket

    prompt = f"{_SYSTEM}\n\n{_build_prompt(ticket)}"
    response: str = model.generate_text(prompt=prompt)
    ticket.summary = response.strip()

    print(f"[summarize] summary={ticket.summary[:80]!r} …")
    return ticket
