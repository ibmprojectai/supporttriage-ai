"""Routing — deterministic auto-tag and queue assignment.

Maps a classified Ticket to a support queue and tag set based on category and priority.
No LLM call — this is pure business logic that is easy to extend via the constants below.
"""

from __future__ import annotations

from models import Ticket

# ── Queue mapping ──────────────────────────────────────────────────────────────
# Map ticket category → default support queue name.
_CATEGORY_QUEUE: dict[str, str] = {
    "authentication": "queue-auth",
    "billing": "queue-billing",
    "performance": "queue-performance",
    "data-loss": "queue-data-loss",
    "feature-request": "queue-product",
    "other": "queue-general",
}

# Tags applied per category in addition to any priority tag
_CATEGORY_TAGS: dict[str, list[str]] = {
    "authentication": ["login", "auth", "password"],
    "billing": ["billing", "payment", "subscription"],
    "performance": ["performance", "slow", "latency"],
    "data-loss": ["data-loss", "critical", "escalate"],
    "feature-request": ["feature-request", "product-feedback"],
    "other": ["general"],
}


def route(ticket: Ticket) -> dict:
    """Return routing metadata for *ticket*.

    Returns a dict with keys:
      queue     — name of the target support queue
      tags      — list of string tags to apply
      escalate  — True if this ticket should bypass normal queue and escalate immediately
    """
    category = ticket.category.lower() if ticket.category else "other"
    priority = ticket.priority.lower() if ticket.priority else "medium"

    queue = _CATEGORY_QUEUE.get(category, _CATEGORY_QUEUE["other"])
    tags = list(_CATEGORY_TAGS.get(category, ["general"]))
    tags.append(f"priority-{priority}")

    # Critical priority or data-loss category always escalates
    escalate = priority == "critical" or category == "data-loss"

    return {
        "queue": queue,
        "tags": tags,
        "escalate": escalate,
    }
