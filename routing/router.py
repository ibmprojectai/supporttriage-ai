"""Routing — deterministic auto-tag and queue assignment.

Maps a classified Ticket to a support queue and tag set based on category,
priority, confidence scores, and critical error codes.

Rules:
  - If confidence_classify or confidence_extract is below CONFIDENCE_THRESHOLD,
    route to 'queue-human-review' and set requires_human_review = True.
  - Critical priority or data-loss category always escalates.
  - severity_impact score is calculated from priority and error code severity.
"""

from __future__ import annotations

from models import Ticket

# Tickets below this confidence threshold go to human review
CONFIDENCE_THRESHOLD = 0.75

# ── Queue mapping ──────────────────────────────────────────────────────────────
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

# Priority → numeric weight for severity_impact calculation
_PRIORITY_WEIGHT: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

# Error code prefixes considered critical for severity scoring
_CRITICAL_ERROR_PREFIXES = ("500", "ERR-5")


def _severity_impact(ticket: Ticket) -> float:
    """Return a 0.0–10.0 severity impact score.

    Score = priority_weight * 2  +  1 point per critical error code (capped at 2).
    """
    priority = ticket.priority.lower() if ticket.priority else "medium"
    weight = _PRIORITY_WEIGHT.get(priority, 2)
    critical_codes = sum(
        1 for code in ticket.error_codes
        if any(code.startswith(p) for p in _CRITICAL_ERROR_PREFIXES)
    )
    return min(10.0, weight * 2.0 + min(critical_codes, 2))


def route(ticket: Ticket) -> dict:
    """Return routing metadata for *ticket*.

    Returns a dict with keys:
      queue                — name of the target support queue
      tags                 — list of string tags to apply
      escalate             — True if ticket should bypass normal queue
      requires_human_review — True if confidence scores are below threshold
      severity_impact      — float 0.0–10.0 severity score
    """
    category = ticket.category.lower() if ticket.category else "other"
    priority = ticket.priority.lower() if ticket.priority else "medium"

    # ── Confidence check — route low-confidence tickets to human review ────────
    if ticket.classify_confidence < CONFIDENCE_THRESHOLD:
        ticket.requires_human_review = True
        print(
            f"[router] Low confidence (classify={ticket.classify_confidence:.2f}) "
            "— routing to human review."
        )
        return {
            "queue": "human-review",
            "tags": ["low-confidence", "needs-human"],
            "escalate": True,
            "requires_human_review": True,
            "severity_impact": _severity_impact(ticket),
        }

    # ── Normal routing ─────────────────────────────────────────────────────────
    queue = _CATEGORY_QUEUE.get(category, _CATEGORY_QUEUE["other"])
    tags = list(_CATEGORY_TAGS.get(category, ["general"]))
    tags.append(f"priority-{priority}")

    escalate = priority == "critical" or category == "data-loss"

    return {
        "queue": queue,
        "tags": tags,
        "escalate": escalate,
        "requires_human_review": False,
        "severity_impact": _severity_impact(ticket),
    }
