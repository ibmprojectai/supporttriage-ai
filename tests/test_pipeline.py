"""Real proof test suite for supporttriage-ai.

Every test exercises actual production logic — no trivial assertions.
Tests verify:
  - regex boundaries, not just "tag present"
  - exact arithmetic from _severity_impact
  - LLM response parsing in classify/extract (mocked model returns real-looking text)
  - _repair_json stripping of markdown fences and leading prose
  - router confidence boundary at exactly 0.75 (boundary value analysis)
  - tag list contents, not just queue name
  - Ticket field isolation (mutable default_factory)
  - extract JSON-parse fallback path when model returns garbage
  - classify response parsing with messy/extra whitespace
  - account auto-extraction by ACC regex in stub mode
  - redact idempotency and ordering (CC before PHONE to avoid overlap)
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from guardrails.pii_redactor import redact
from models import Ticket
from routing.router import CONFIDENCE_THRESHOLD, route


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _make_model(response: str) -> MagicMock:
    """Return a mock model whose generate_text() returns *response*."""
    m = MagicMock()
    m.generate_text.return_value = response
    return m


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — PII Redactor: real boundary & content tests (15 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestPIIRedactor:

    # --- emails ---

    def test_email_replaced_with_exact_placeholder(self):
        result = redact("Mail me: alice@example.com please")
        assert result == "Mail me: [EMAIL] please"

    def test_multiple_emails_all_replaced(self):
        result = redact("From a@x.com to b@y.org cc c@z.net")
        assert result.count("[EMAIL]") == 3
        assert "@" not in result

    def test_email_at_start_of_string(self):
        result = redact("user@domain.io is the sender")
        assert result.startswith("[EMAIL]")

    def test_email_not_over_redacted(self):
        # Non-email text around the address must survive unchanged
        result = redact("Hello, please email support@corp.com for help.")
        assert "Hello, please email" in result
        assert "for help." in result

    def test_plain_text_unchanged_by_email_redactor(self):
        text = "No PII in this sentence at all."
        assert redact(text) == text

    # --- phones ---

    def test_phone_dashes_replaced(self):
        result = redact("Call 415-555-0198 now")
        assert "[PHONE]" in result
        assert "555-0198" not in result

    def test_phone_parentheses_format_replaced(self):
        result = redact("Ring (800) 555 1234 anytime")
        assert "[PHONE]" in result
        assert "800" not in result

    def test_phone_dot_separator_replaced(self):
        result = redact("Fax: 212.555.6789")
        assert "[PHONE]" in result
        assert "212.555.6789" not in result

    # --- credit cards ---

    def test_cc_16_digit_spaced_replaced(self):
        result = redact("Card: 4111 1111 1111 1111")
        assert "[CC]" in result
        assert "4111" not in result

    def test_cc_16_digit_continuous_replaced(self):
        result = redact("Visa 4111111111111111 on file")
        assert "[CC]" in result
        assert "4111111111111111" not in result

    def test_cc_replaced_before_phone_no_overlap(self):
        # A 16-digit number must become [CC], not [PHONE]
        result = redact("4111111111111111")
        assert "[CC]" in result
        assert "[PHONE]" not in result

    # --- combined / ordering ---

    def test_email_and_phone_both_redacted(self):
        result = redact("Email me at x@y.com or call 415-555-0100")
        assert "[EMAIL]" in result
        assert "[PHONE]" in result
        assert "@" not in result

    def test_redact_is_idempotent(self):
        # Running redact twice on already-redacted text must not double-replace
        once = redact("user@corp.com and 415-555-0100")
        twice = redact(once)
        assert once == twice

    def test_empty_string_unchanged(self):
        assert redact("") == ""

    def test_redact_preserves_surrounding_words(self):
        result = redact("Account ACC-00123 flagged — email admin@corp.com immediately.")
        assert "Account" in result
        assert "flagged" in result
        assert "immediately." in result
        assert "[EMAIL]" in result


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — _severity_impact arithmetic (8 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestSeverityImpact:
    """Import and test _severity_impact directly — it's pure arithmetic."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from routing.router import _severity_impact
        self._severity_impact = _severity_impact

    def test_low_priority_no_errors(self):
        t = Ticket(priority="low", error_codes=[])
        assert self._severity_impact(t) == 2.0   # 1*2 + 0

    def test_medium_priority_no_errors(self):
        t = Ticket(priority="medium", error_codes=[])
        assert self._severity_impact(t) == 4.0   # 2*2 + 0

    def test_high_priority_no_errors(self):
        t = Ticket(priority="high", error_codes=[])
        assert self._severity_impact(t) == 6.0   # 3*2 + 0

    def test_critical_priority_no_errors(self):
        t = Ticket(priority="critical", error_codes=[])
        assert self._severity_impact(t) == 8.0   # 4*2 + 0

    def test_critical_one_critical_error_code(self):
        t = Ticket(priority="critical", error_codes=["ERR-5001"])
        assert self._severity_impact(t) == 9.0   # 4*2 + 1

    def test_critical_two_critical_error_codes(self):
        t = Ticket(priority="critical", error_codes=["ERR-5001", "ERR-5002"])
        assert self._severity_impact(t) == 10.0  # 4*2 + 2 (capped)

    def test_three_critical_codes_capped_at_10(self):
        t = Ticket(priority="critical", error_codes=["ERR-5001", "ERR-5002", "ERR-5003"])
        assert self._severity_impact(t) == 10.0  # capped at 10

    def test_non_critical_error_codes_ignored(self):
        t = Ticket(priority="high", error_codes=["ERR-1001", "ERR-2000"])
        assert self._severity_impact(t) == 6.0   # non-critical codes add nothing


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — Router: boundary value analysis & tag content (10 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestRouter:

    def test_confidence_at_threshold_does_not_trigger_human_review(self):
        # exactly 0.75 must NOT go to human-review
        t = Ticket(category="billing", priority="medium",
                   classify_confidence=CONFIDENCE_THRESHOLD)
        result = route(t)
        assert result["queue"] != "human-review"
        assert result["requires_human_review"] is False

    def test_confidence_just_below_threshold_triggers_human_review(self):
        t = Ticket(category="billing", priority="medium",
                   classify_confidence=CONFIDENCE_THRESHOLD - 0.01)
        result = route(t)
        assert result["queue"] == "human-review"
        assert result["requires_human_review"] is True

    def test_auth_tags_contain_login_and_password(self):
        t = Ticket(category="authentication", priority="high", classify_confidence=1.0)
        result = route(t)
        assert "login" in result["tags"]
        assert "password" in result["tags"]

    def test_priority_tag_appended_to_tags(self):
        t = Ticket(category="billing", priority="medium", classify_confidence=1.0)
        result = route(t)
        assert "priority-medium" in result["tags"]

    def test_human_review_tags_are_correct(self):
        t = Ticket(category="other", priority="low", classify_confidence=0.5)
        result = route(t)
        assert "low-confidence" in result["tags"]
        assert "needs-human" in result["tags"]

    def test_data_loss_tags_include_escalate(self):
        t = Ticket(category="data-loss", priority="high", classify_confidence=1.0)
        result = route(t)
        assert "escalate" in result["tags"]

    def test_unknown_category_falls_back_to_general_queue(self):
        t = Ticket(category="xyz-unknown", priority="low", classify_confidence=1.0)
        result = route(t)
        assert result["queue"] == "queue-general"

    def test_route_sets_requires_human_review_on_ticket_object(self):
        t = Ticket(category="billing", priority="medium", classify_confidence=0.4)
        route(t)
        assert t.requires_human_review is True  # side-effect on ticket

    def test_severity_impact_in_result_is_float(self):
        t = Ticket(category="authentication", priority="high", classify_confidence=1.0)
        result = route(t)
        assert isinstance(result["severity_impact"], float)

    def test_severity_impact_in_human_review_path_is_correct(self):
        # severity_impact should still be calculated even in human-review path
        t = Ticket(category="authentication", priority="critical",
                   classify_confidence=0.4, error_codes=[])
        result = route(t)
        assert result["queue"] == "human-review"
        assert result["severity_impact"] == 8.0  # critical=4*2


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — Ticket dataclass: field isolation & type correctness (8 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestTicketModel:

    def test_error_codes_isolated_between_instances(self):
        t1, t2 = Ticket(), Ticket()
        t1.error_codes.append("ERR-001")
        assert t2.error_codes == []

    def test_symptoms_isolated_between_instances(self):
        t1, t2 = Ticket(), Ticket()
        t1.symptoms.append("crash on login")
        assert t2.symptoms == []

    def test_thread_isolated_between_instances(self):
        t1, t2 = Ticket(), Ticket()
        t1.thread.append("message one")
        assert t2.thread == []

    def test_confidence_defaults_are_floats(self):
        t = Ticket()
        assert isinstance(t.confidence_classify, float)
        assert isinstance(t.confidence_extract, float)
        assert isinstance(t.classify_confidence, float)

    def test_requires_human_review_default_false(self):
        assert Ticket().requires_human_review is False

    def test_partial_construction_valid(self):
        # All fields have defaults — partial construction must not raise
        t = Ticket(id="T-001", subject="Test subject")
        assert t.id == "T-001"
        assert t.body == ""
        assert t.category == ""

    def test_repr_truncates_long_body(self):
        t = Ticket(body="x" * 100)
        r = repr(t)
        assert "…" in r  # body is elided

    def test_repr_does_not_truncate_short_body(self):
        t = Ticket(body="short")
        r = repr(t)
        assert "…" not in r


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — _repair_json: real parsing logic (7 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestRepairJson:
    """Test _repair_json directly — it's called on every live LLM response."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from pipeline.extract import _repair_json
        self._repair_json = _repair_json

    def test_plain_json_unchanged(self):
        s = '{"error_codes": [], "account": "ACC-001"}'
        assert self._repair_json(s) == s

    def test_strips_json_fences(self):
        s = '```json\n{"error_codes": []}\n```'
        result = self._repair_json(s)
        assert result == '{"error_codes": []}'

    def test_strips_plain_fences(self):
        s = '```\n{"a": 1}\n```'
        result = self._repair_json(s)
        assert result == '{"a": 1}'

    def test_strips_leading_prose(self):
        s = 'Sure! Here is the JSON:\n{"error_codes": ["ERR-1"]}'
        result = self._repair_json(s)
        assert result.startswith("{")

    def test_result_is_valid_json(self):
        s = '```json\n{"error_codes": ["ERR-404"], "confidence": 0.9}\n```'
        result = self._repair_json(s)
        parsed = json.loads(result)
        assert parsed["error_codes"] == ["ERR-404"]

    def test_handles_object_with_content_attr(self):
        # Simulates an AIMessage — must not crash, must return str
        class FakeAIMessage:
            content = '{"error_codes": []}'
        result = self._repair_json(FakeAIMessage())
        assert isinstance(result, str)
        assert "{" in result

    def test_non_string_non_message_coerced_to_str(self):
        # Any random object must be safely coerced
        result = self._repair_json(42)
        assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — classify: live response parsing via mock model (7 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyLiveResponseParsing:
    """
    Mock model returns real-looking LLM text.
    Tests verify that the regex parsing in classify() correctly extracts
    category, priority, and confidence from various realistic response formats.
    """

    def _run(self, response_text: str, subject: str = "Test", body: str = "Test body"):
        from pipeline.classify import classify
        ticket = Ticket(subject=subject, body=body)
        model = _make_model(response_text)
        with patch("pipeline.classify.get_model", return_value=model):
            return asyncio.run(classify(ticket))

    def test_parses_clean_three_line_response(self):
        t = self._run("CATEGORY: billing\nPRIORITY: high\nCONFIDENCE: 0.92")
        assert t.category == "billing"
        assert t.priority == "high"
        assert t.confidence_classify == pytest.approx(0.92)

    def test_parses_response_with_extra_whitespace(self):
        t = self._run("CATEGORY:   performance  \nPRIORITY:   critical  \nCONFIDENCE: 0.88")
        assert t.category == "performance"
        assert t.priority == "critical"

    def test_category_lowercased(self):
        t = self._run("CATEGORY: Authentication\nPRIORITY: High\nCONFIDENCE: 0.80")
        assert t.category == "authentication"
        assert t.priority == "high"

    def test_missing_confidence_defaults_to_0_5(self):
        t = self._run("CATEGORY: billing\nPRIORITY: medium")
        assert t.confidence_classify == 0.5

    def test_missing_category_defaults_to_other(self):
        t = self._run("PRIORITY: high\nCONFIDENCE: 0.75")
        assert t.category == "other"

    def test_missing_priority_defaults_to_medium(self):
        t = self._run("CATEGORY: billing\nCONFIDENCE: 0.80")
        assert t.priority == "medium"

    def test_confidence_and_classify_confidence_both_set(self):
        t = self._run("CATEGORY: billing\nPRIORITY: low\nCONFIDENCE: 0.66")
        assert t.confidence_classify == pytest.approx(0.66)
        assert t.classify_confidence == pytest.approx(0.66)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — extract: live JSON parsing + fallback path via mock model (9 tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractLiveResponseParsing:
    """
    Mock model returns real-looking JSON (or garbage for fallback tests).
    Verifies that extract() correctly parses LLM JSON output and
    falls back to regex when the JSON is invalid.
    """

    def _run(self, response_text: str, body: str = "Ticket body", account: str = ""):
        from pipeline.extract import extract
        ticket = Ticket(body=body, account=account)
        model = _make_model(response_text)
        with patch("pipeline.extract.get_model", return_value=model):
            return asyncio.run(extract(ticket))

    def test_parses_error_codes_from_json(self):
        payload = json.dumps({"error_codes": ["ERR-1001", "ERR-2002"],
                               "account": "", "product": "",
                               "symptoms": [], "confidence": 0.9})
        t = self._run(payload)
        assert t.error_codes == ["ERR-1001", "ERR-2002"]

    def test_parses_symptoms_from_json(self):
        payload = json.dumps({"error_codes": [],
                               "account": "", "product": "",
                               "symptoms": ["login fails", "timeout on dashboard"],
                               "confidence": 0.85})
        t = self._run(payload)
        assert "login fails" in t.symptoms
        assert "timeout on dashboard" in t.symptoms

    def test_parses_confidence_from_json(self):
        payload = json.dumps({"error_codes": [], "account": "", "product": "",
                               "symptoms": [], "confidence": 0.77})
        t = self._run(payload)
        assert t.confidence_extract == pytest.approx(0.77)

    def test_account_not_overwritten_if_already_set(self):
        payload = json.dumps({"error_codes": [], "account": "ACC-FROM-LLM",
                               "product": "", "symptoms": [], "confidence": 0.8})
        t = self._run(payload, account="ACC-EXISTING")
        assert t.account == "ACC-EXISTING"  # pre-set account must not be overwritten

    def test_product_set_from_json(self):
        payload = json.dumps({"error_codes": [], "account": "",
                               "product": "CloudSync Pro",
                               "symptoms": [], "confidence": 0.8})
        t = self._run(payload)
        assert t.product == "CloudSync Pro"

    def test_json_in_markdown_fence_parsed_correctly(self):
        payload = ('```json\n' +
                   json.dumps({"error_codes": ["ERR-999"], "account": "",
                                "product": "", "symptoms": [], "confidence": 0.7}) +
                   '\n```')
        t = self._run(payload)
        assert t.error_codes == ["ERR-999"]

    def test_garbage_response_falls_back_to_regex(self):
        # When LLM returns non-JSON, extract() must fall back to body regex
        t = self._run("Sorry, I cannot help with that.",
                      body="System threw ERR-4040 and ERR-5050 repeatedly.")
        assert "ERR-4040" in t.error_codes
        assert "ERR-5050" in t.error_codes
        assert t.confidence_extract == 0.0

    def test_stub_mode_extracts_account_from_body(self):
        from pipeline.extract import extract
        ticket = Ticket(body="Account ACC-00982 is locked out. Error ERR-3030.")
        with patch("pipeline.extract.get_model", return_value=None):
            result = asyncio.run(extract(ticket))
        assert result.account == "ACC-00982"

    def test_stub_mode_does_not_overwrite_existing_account(self):
        from pipeline.extract import extract
        ticket = Ticket(body="See ACC-99999 in body", account="ACC-PRESET")
        with patch("pipeline.extract.get_model", return_value=None):
            result = asyncio.run(extract(ticket))
        assert result.account == "ACC-PRESET"
