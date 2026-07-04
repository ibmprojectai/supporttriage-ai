"""Unit tests for supporttriage-ai pipeline, routing, guardrails, and models."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from guardrails.pii_redactor import redact
from models import Ticket
from routing.router import route


# ══════════════════════════════════════════════════════════════════════════════
# guardrails/pii_redactor.py — 3 tests
# ══════════════════════════════════════════════════════════════════════════════

def test_redact_email():
    result = redact("Contact us at support@example.com for help.")
    assert "[EMAIL]" in result
    assert "support@example.com" not in result


def test_redact_phone():
    result = redact("Call me at 415-555-0198 anytime.")
    assert "[PHONE]" in result
    assert "415-555-0198" not in result


def test_redact_credit_card():
    result = redact("My card number is 4111 1111 1111 1111 thanks.")
    assert "[CC]" in result
    assert "4111 1111 1111 1111" not in result


# ══════════════════════════════════════════════════════════════════════════════
# routing/router.py — 3 tests
# ══════════════════════════════════════════════════════════════════════════════

def test_route_critical_priority_escalates():
    ticket = Ticket(
        category="authentication",
        priority="critical",
        classify_confidence=0.95,
    )
    result = route(ticket)
    assert result["escalate"] is True


def test_route_low_confidence_goes_to_human_review():
    ticket = Ticket(
        category="billing",
        priority="medium",
        classify_confidence=0.60,  # below CONFIDENCE_THRESHOLD of 0.75
    )
    result = route(ticket)
    assert result["queue"] == "human-review"
    assert result["requires_human_review"] is True
    assert ticket.requires_human_review is True


def test_route_data_loss_escalates():
    ticket = Ticket(
        category="data-loss",
        priority="high",
        classify_confidence=0.90,
    )
    result = route(ticket)
    assert result["escalate"] is True
    assert result["queue"] == "queue-data-loss"


# ══════════════════════════════════════════════════════════════════════════════
# models.py — 2 tests
# ══════════════════════════════════════════════════════════════════════════════

def test_ticket_default_fields():
    ticket = Ticket()
    assert ticket.id == ""
    assert ticket.sender == ""
    assert ticket.subject == ""
    assert ticket.body == ""
    assert ticket.category == ""
    assert ticket.priority == ""
    assert ticket.summary == ""
    assert ticket.draft_reply == ""
    assert ticket.requires_human_review is False


def test_ticket_default_list_fields_are_independent():
    """Each Ticket instance must get its own list — not shared via mutable default."""
    t1 = Ticket()
    t2 = Ticket()
    t1.error_codes.append("ERR-001")
    assert t2.error_codes == []
    t1.thread.append("hello")
    assert t2.thread == []
    t1.symptoms.append("slow login")
    assert t2.symptoms == []


# ══════════════════════════════════════════════════════════════════════════════
# pipeline/classify.py — 2 tests (stub mode, model=None)
# ══════════════════════════════════════════════════════════════════════════════

def test_classify_stub_sets_category():
    """classify() in stub mode must set category='authentication'."""
    from pipeline.classify import classify

    ticket = Ticket(subject="Login broken", body="I cannot log in.")
    with patch("pipeline.classify.get_model", return_value=None):
        result = asyncio.run(classify(ticket))

    assert result.category == "authentication"


def test_classify_stub_sets_confidence():
    """classify() in stub mode must set confidence_classify=0.5."""
    from pipeline.classify import classify

    ticket = Ticket(subject="Login broken", body="I cannot log in.")
    with patch("pipeline.classify.get_model", return_value=None):
        result = asyncio.run(classify(ticket))

    assert result.confidence_classify == 0.5
    assert result.classify_confidence == 0.5
