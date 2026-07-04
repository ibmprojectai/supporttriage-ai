"""Comprehensive parametrized test suite for supporttriage-ai.

Groups:
  1. PII Redactor          — 15 tests
  2. Router category map   — 10 tests
  3. Router escalation     —  8 tests
  4. Ticket defaults       —  5 tests
  5. Classify stub mode    —  6 tests
  6. Extract stub mode     —  6 tests

Total: 50 tests
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from guardrails.pii_redactor import redact
from models import Ticket
from routing.router import route


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — PII Redactor (15 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("text, expected_tag, absent", [
    # Emails (5)
    ("Reach me at alice@example.com thanks",         "[EMAIL]", "alice@example.com"),
    ("Email bob.smith+tag@corp.org for details",     "[EMAIL]", "bob.smith+tag@corp.org"),
    ("From: no-reply@service.io to you",             "[EMAIL]", "no-reply@service.io"),
    ("user123@sub.domain.co.uk is my address",       "[EMAIL]", "user123@sub.domain.co.uk"),
    ("Contact support@help-desk.net immediately",    "[EMAIL]", "support@help-desk.net"),
    # Phone numbers (5)
    ("Call me at 415-555-0198 anytime",              "[PHONE]", "415-555-0198"),
    ("My number is (800) 555 1234 please call",      "[PHONE]", "800"),
    ("Reach us at +1 415 555 0199 for support",      "[PHONE]", "555 0199"),
    ("Phone: 212.555.6789 extension 42",             "[PHONE]", "212.555.6789"),
    ("SMS to 6505550123 for updates",                "[PHONE]", "6505550123"),
    # Credit card numbers (5)
    ("Card: 4111 1111 1111 1111 exp 12/26",          "[CC]", "4111 1111 1111 1111"),
    ("Visa 4111111111111111 on file",                "[CC]", "4111111111111111"),
    ("Mastercard 5500-0000-0000-0004 charged",       "[CC]", "5500-0000-0000-0004"),
    ("Amex 3714 496353 98431 declined",              "[CC]", "3714 496353 98431"),
    ("Card number 6011000990139424 is expired",      "[CC]", "6011000990139424"),
])
def test_pii_redacted(text, expected_tag, absent):
    result = redact(text)
    assert expected_tag in result, f"Expected {expected_tag!r} in output: {result!r}"
    assert absent not in result, f"PII {absent!r} should be redacted but found in: {result!r}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — Router category mapping (10 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("category, priority, expected_queue", [
    ("authentication",  "high",   "queue-auth"),
    ("authentication",  "low",    "queue-auth"),
    ("billing",         "medium", "queue-billing"),
    ("billing",         "high",   "queue-billing"),
    ("performance",     "low",    "queue-performance"),
    ("performance",     "critical","queue-performance"),
    ("data-loss",       "high",   "queue-data-loss"),
    ("data-loss",       "medium", "queue-data-loss"),
    ("feature-request", "low",    "queue-product"),
    ("other",           "medium", "queue-general"),
])
def test_router_category_queue(category, priority, expected_queue):
    ticket = Ticket(
        category=category,
        priority=priority,
        classify_confidence=1.0,  # bypass confidence check
    )
    result = route(ticket)
    assert result["queue"] == expected_queue


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Router escalation logic (8 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("category, priority, confidence, expect_escalate, expect_human", [
    # critical priority always escalates
    ("authentication", "critical", 0.95, True,  False),
    ("billing",        "critical", 0.90, True,  False),
    # data-loss always escalates
    ("data-loss",      "high",     0.95, True,  False),
    ("data-loss",      "medium",   0.85, True,  False),
    # low confidence routes to human-review (escalate=True, requires_human_review=True)
    ("authentication", "medium",   0.50, True,  True),
    ("billing",        "high",     0.70, True,  True),
    # normal cases — no escalation
    ("authentication", "high",     0.90, False, False),
    ("performance",    "medium",   0.80, False, False),
])
def test_router_escalation(category, priority, confidence, expect_escalate, expect_human):
    ticket = Ticket(
        category=category,
        priority=priority,
        classify_confidence=confidence,
    )
    result = route(ticket)
    assert result["escalate"] is expect_escalate
    assert result["requires_human_review"] is expect_human


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Ticket dataclass defaults (5 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("field, expected", [
    ("id",                    ""),
    ("category",              ""),
    ("priority",              ""),
    ("summary",               ""),
    ("requires_human_review", False),
])
def test_ticket_defaults(field, expected):
    ticket = Ticket()
    assert getattr(ticket, field) == expected


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — Classify stub mode (6 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("subject, body", [
    ("Cannot log in",              "I keep getting invalid password errors."),
    ("Login broken after update",  "SSO stopped working yesterday."),
    ("Password reset not working", "Reset email never arrives."),
    ("Access denied to dashboard", "I get 403 forbidden on every page."),
    ("Two-factor auth failing",    "My authenticator code is rejected."),
    ("Account locked out",         "Too many failed attempts, now locked."),
])
def test_classify_stub_category_and_confidence(subject, body):
    from pipeline.classify import classify

    ticket = Ticket(subject=subject, body=body)
    with patch("pipeline.classify.get_model", return_value=None):
        result = asyncio.run(classify(ticket))

    assert result.category == "authentication"
    assert result.priority == "high"
    assert result.confidence_classify == 0.5
    assert result.classify_confidence == 0.5


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — Extract stub mode (6 parametrized tests)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("body, expected_codes", [
    ("We got ERR-1001 when logging in",                   ["ERR-1001"]),
    ("Errors: ERR-2020 and ERR-3030 appeared",            ["ERR-2020", "ERR-3030"]),
    ("Fatal ERR-5000 crash on startup",                   ["ERR-5000"]),
    ("No error codes in this ticket",                     []),
    ("ERR-9999 shown after every save action",            ["ERR-9999"]),
    ("Saw ERR-1111 then ERR-2222 then ERR-3333 in order", ["ERR-1111", "ERR-2222", "ERR-3333"]),
])
def test_extract_stub_error_codes_and_confidence(body, expected_codes):
    from pipeline.extract import extract

    ticket = Ticket(body=body)
    with patch("pipeline.extract.get_model", return_value=None):
        result = asyncio.run(extract(ticket))

    assert result.error_codes == expected_codes
    assert result.confidence_extract == 0.0
    assert result.symptoms == []
