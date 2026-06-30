"""Shared Ticket data model — the single contract passed between all pipeline modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Ticket:
    # ── Set by intake ──────────────────────────────────────────────────────────
    id: str = ""
    sender: str = ""
    subject: str = ""
    body: str = ""
    thread: list[str] = field(default_factory=list)
    account: str = ""
    product: str = ""

    # ── Set by pipeline/extract ────────────────────────────────────────────────
    error_codes: list[str] = field(default_factory=list)

    # ── Set by pipeline/classify ───────────────────────────────────────────────
    category: str = ""
    priority: str = ""

    # ── Set by pipeline/summarize ──────────────────────────────────────────────
    summary: str = ""

    # ── Set by pipeline/draft ──────────────────────────────────────────────────
    draft_reply: str = ""

    def __repr__(self) -> str:  # elide body for readability in logs
        body_preview = (self.body[:60] + "…") if len(self.body) > 60 else self.body
        return (
            f"Ticket(id={self.id!r}, sender={self.sender!r}, subject={self.subject!r}, "
            f"body={body_preview!r}, account={self.account!r}, product={self.product!r}, "
            f"error_codes={self.error_codes!r}, category={self.category!r}, "
            f"priority={self.priority!r}, summary={self.summary!r})"
        )
