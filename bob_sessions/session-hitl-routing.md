# IBM Bob Session Log — HITL Routing Engine

**Date:** 2026-07-04
**Task:** Rebuild the routing layer with production-grade Human-in-the-Loop (HITL) confidence thresholds

**Files Modified:**
- `routing/router.py`
- `models.py`
- `ui/review_app.py`

**Key Changes:**

- Raised confidence threshold from `0.75` → `0.85` (`AUTO_ROUTE_THRESHOLD`) to reflect a stricter production standard for autonomous routing
- Implemented three-tier deterministic routing logic with clear priority ordering:
  1. **Escalated** — `priority == "critical"` OR `category == "data-loss"` → bypasses confidence check entirely, routed to queue immediately with `escalate=True`
  2. **Human-Review** — `confidence ≤ 0.85` → ticket is **held** in the HITL queue, NOT dispatched to any queue automatically; `requires_human_review = True`, `ticket.status = "human-review"`
  3. **Auto-Routed** — `confidence > 0.85` AND non-critical → dispatched to the correct category queue with `ticket.status = "auto-routed"`
- Added `status` key to routing metadata dict so the UI and downstream systems can read the routing decision without re-evaluating confidence
- Added `ERR-9` prefix to `_CRITICAL_ERROR_PREFIXES` (alongside `500` and `ERR-5`) to catch data-loss error codes in severity scoring
- Added `CONFIDENCE_THRESHOLD` alias pointing to `AUTO_ROUTE_THRESHOLD` for backward compatibility with existing tests
- Added `status: str = "untriaged"` field to `Ticket` dataclass (values: `"untriaged"`, `"auto-routed"`, `"human-review"`, `"escalated"`, `"approved"`)
- Router now mutates `ticket.status` in-place so the UI can reflect the current state without extra computation
- UI HITL tab filters `processed` results by `r.get("status") == "human-review"` and `t.status != "approved"`, removing tickets from the queue after agent approval
- Agent approval flow: queue selector dropdown → editable draft → **✅ Approve & Route** button updates `ticket.status = "approved"` and `r["queue"]` in-place, appends a `[HITL APPROVED]` entry to the system log, then calls `st.rerun()`
- Confidence gauge in the dashboard now renders a visible red threshold line at the 85% mark so judges can immediately see how many tickets crossed the bar

**Outcome:** The router now enforces a strict separation between autonomous routing and human-supervised routing, with critical tickets always escalated regardless of confidence score.
