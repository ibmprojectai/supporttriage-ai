"""Pipeline stage 1 — classify a support ticket.

Sets ticket.category, ticket.priority, and ticket.confidence_classify.

Live mode:  calls the local Ollama model via watsonx_config.get_model().
Stub mode:  sets deterministic placeholder values when Ollama is unreachable.
"""

from __future__ import annotations

import logging
import re
import time

from models import Ticket
from watsonx_config import get_model

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a support-ticket classifier. "
    "Respond with exactly three lines and nothing else:\n"
    "CATEGORY: <one of: authentication, billing, performance, data-loss, feature-request, other>\n"
    "PRIORITY: <one of: critical, high, medium, low>\n"
    "CONFIDENCE: <a float between 0.0 and 1.0 reflecting how certain you are>"
)


def _build_prompt(ticket: Ticket) -> str:
    return (
        f"Subject: {ticket.subject}\n"
        f"Body:\n{ticket.body}\n\n"
        "Classify this ticket."
    )


def classify(ticket: Ticket) -> Ticket:
    """Classify *ticket*, setting ``category``, ``priority``, and ``confidence_classify``."""
    model = get_model()

    if model is None:
        log.warning("[classify] STUB MODE — Ollama unreachable. Using placeholder values.")
        print(
            "[classify] STUB MODE — Ollama not found. "
            "Setting placeholder category/priority."
        )
        ticket.category = "authentication"
        ticket.priority = "high"
        ticket.confidence_classify = 0.5
        ticket.classify_confidence = 0.5
        return ticket

    t0 = time.perf_counter()
    prompt = f"{_SYSTEM}\n\n{_build_prompt(ticket)}"
    response: str = model.generate_text(prompt=prompt)
    elapsed = time.perf_counter() - t0

    category_match = re.search(r"CATEGORY:\s*(.+)", response, re.IGNORECASE)
    priority_match = re.search(r"PRIORITY:\s*(.+)", response, re.IGNORECASE)
    confidence_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", response, re.IGNORECASE)

    ticket.category = (
        category_match.group(1).strip().lower() if category_match else "other"
    )
    ticket.priority = (
        priority_match.group(1).strip().lower() if priority_match else "medium"
    )
    try:
        score = float(confidence_match.group(1)) if confidence_match else 0.5
    except ValueError:
        score = 0.5
    ticket.confidence_classify = score
    ticket.classify_confidence = score

    log.info(
        "[classify] category=%r priority=%r confidence=%.2f elapsed=%.2fs",
        ticket.category, ticket.priority, ticket.confidence_classify, elapsed,
    )
    print(
        f"[classify] category={ticket.category!r}  priority={ticket.priority!r}"
        f"  confidence={ticket.confidence_classify:.2f}"
    )
    return ticket
