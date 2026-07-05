"""Routing — HITL-aware queue assignment for the multi-channel ops center.

Rules (production HITL thresholds):
  - Auto-Routed:    confidence >= 0.85 AND priority != "critical"
  - Human-Review:   confidence < 0.85  (held — NOT sent to a queue automatically)
  - Escalated:      (priority == "critical" OR category == "data-loss") AND confidence >= 0.85

severity_impact score is calculated from priority (0–10 scale).
"""

from __future__ import annotations

from models import Ticket

# ── Thresholds ─────────────────────────────────────────────────────────────────
AUTO_ROUTE_THRESHOLD = 0.85   # confidence must exceed this to auto-route
CONFIDENCE_THRESHOLD = AUTO_ROUTE_THRESHOLD  # kept as alias for backward compat

# ── Queue mapping ──────────────────────────────────────────────────────────────
_CATEGORY_QUEUE: dict[str, str] = {
    "authentication": "queue-auth",
    "billing":        "queue-billing",
    "performance":    "queue-performance",
    "data-loss":      "queue-data-loss",
    "feature-request":"queue-product",
    "other":          "queue-general",
}

# Tags applied per category
_CATEGORY_TAGS: dict[str, list[str]] = {
    "authentication":  ["login", "auth", "password"],
    "billing":         ["billing", "payment", "subscription"],
    "performance":     ["performance", "slow", "latency"],
    "data-loss":       ["data-loss", "critical", "escalate"],
    "feature-request": ["feature-request", "product-feedback"],
    "other":           ["general"],
}

# Priority → numeric weight for severity_impact
_PRIORITY_WEIGHT: dict[str, int] = {
    "critical": 4,
    "high":     3,
    "medium":   2,
    "low":      1,
}

# Priority → priority_score 1–5 (business scale shown in UI)
_PRIORITY_SCORE: dict[str, int] = {
    "critical": 5,
    "high":     4,
    "medium":   3,
    "low":      2,
}

# Error code prefixes treated as critical for severity scoring
_CRITICAL_ERROR_PREFIXES = ("500", "ERR-5", "ERR-9")


def _severity_impact(ticket: Ticket) -> float:
    """Return a 0.0–10.0 severity impact score.

    Score = priority_weight * 2  +  1 point per critical error code (capped at 2).
    """
    priority = (ticket.priority or "medium").lower()
    weight = _PRIORITY_WEIGHT.get(priority, 2)
    critical_codes = sum(
        1 for code in ticket.error_codes
        if any(code.startswith(p) for p in _CRITICAL_ERROR_PREFIXES)
    )
    return min(10.0, weight * 2.0 + min(critical_codes, 2))


def route(ticket: Ticket) -> dict:
    """Apply HITL routing rules to *ticket* and return a routing metadata dict.

    Returns
    -------
    dict with keys:
      queue                 — target support queue name
      tags                  — list of string tags
      escalate              — True for critical / data-loss tickets
      requires_human_review — True when confidence <= AUTO_ROUTE_THRESHOLD
      severity_impact       — float 0.0–10.0
      status                — one of "auto-routed" | "human-review" | "escalated"
    """
    category = (ticket.category or "other").lower()
    priority = (ticket.priority or "medium").lower()
    conf     = ticket.classify_confidence

    sev   = _severity_impact(ticket)
    pscore = _PRIORITY_SCORE.get(priority, 3)
    # bump score by 1 (max 5) when severity is high due to critical error codes
    if sev >= 8 and pscore < 5:
        pscore += 1
    ticket.priority_score = pscore

    # ── 1. Escalation: critical priority or data-loss category (only when confident) ──
    if (priority == "critical" or category == "data-loss") and conf >= AUTO_ROUTE_THRESHOLD:
        ticket.requires_human_review = False
        ticket.status = "escalated"
        queue = _CATEGORY_QUEUE.get(category, _CATEGORY_QUEUE["other"])
        tags  = list(_CATEGORY_TAGS.get(category, ["general"]))
        tags.append(f"priority-{priority}")
        tags.append("escalated")
        print(
            f"[router] ESCALATED — {ticket.id} "
            f"(priority={priority}, category={category}, score={pscore})"
        )
        return {
            "queue":                queue,
            "tags":                 tags,
            "escalate":             True,
            "requires_human_review": False,
            "severity_impact":      sev,
            "priority_score":       pscore,
            "status":               "escalated",
        }

    # ── 2. Human review: confidence below threshold ──────────────────────────
    if conf < AUTO_ROUTE_THRESHOLD:
        ticket.requires_human_review = True
        ticket.status = "human-review"
        print(
            f"[router] HUMAN-REVIEW — {ticket.id} "
            f"(confidence={conf:.2f} <= {AUTO_ROUTE_THRESHOLD}, score={pscore})"
        )
        return {
            "queue":                "human-review",
            "tags":                 ["low-confidence", "needs-human"],
            "escalate":             False,
            "requires_human_review": True,
            "severity_impact":      sev,
            "priority_score":       pscore,
            "status":               "human-review",
        }

    # ── 3. Auto-route: high confidence, non-critical ──────────────────────────
    ticket.requires_human_review = False
    ticket.status = "auto-routed"
    queue = _CATEGORY_QUEUE.get(category, _CATEGORY_QUEUE["other"])
    tags  = list(_CATEGORY_TAGS.get(category, ["general"]))
    tags.append(f"priority-{priority}")
    print(
        f"[router] AUTO-ROUTED — {ticket.id} "
        f"(confidence={conf:.2f}, queue={queue}, score={pscore})"
    )
    return {
        "queue":                queue,
        "tags":                 tags,
        "escalate":             False,
        "requires_human_review": False,
        "severity_impact":      sev,
        "priority_score":       pscore,
        "status":               "auto-routed",
    }
