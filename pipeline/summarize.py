"""Pipeline stage 3 — summarize a support ticket.

Sets ticket.summary to a concise 2–3 sentence condensation of the full ticket thread.

Live mode:  calls the local Ollama model via watsonx_config.get_model().
Stub mode:  returns a templated summary when Ollama is unreachable.
"""

from __future__ import annotations

import asyncio
import logging
import time

from models import Ticket
from watsonx_config import get_model

log = logging.getLogger(__name__)

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


async def summarize(ticket: Ticket) -> Ticket:
    """Summarise *ticket*, setting ``summary``."""
    model = get_model()

    if model is None:
        log.warning("[summarize] STUB MODE — Ollama unreachable. Generating templated summary.")
        print("[summarize] STUB MODE — generating templated summary.")
        ticket.summary = (
            f"Customer reports inability to log in to {ticket.product or 'the product'} "
            f"after a password reset, receiving error code(s) "
            f"{', '.join(ticket.error_codes) if ticket.error_codes else 'unknown'}. "
            f"Account {ticket.account or 'unknown'} is affected and the issue is blocking "
            "the customer's team. Multiple browsers have been tried without success."
        )
        return ticket

    t0 = time.perf_counter()
    prompt = f"{_SYSTEM}\n\n{_build_prompt(ticket)}"
    response: str = await asyncio.to_thread(model.generate_text, prompt)
    elapsed = time.perf_counter() - t0

    ticket.summary = response.strip()
    log.info("[summarize] length=%d chars elapsed=%.2fs", len(ticket.summary), elapsed)
    print(f"[summarize] summary={ticket.summary[:80]!r} …")
    return ticket
