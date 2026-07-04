"""Multi-channel intake — Telegram polling, Gmail IMAP, and background volume generator.

Functions
---------
fetch_telegram_updates(bot_token, last_update_id)
    Poll Telegram Bot API for new messages and return them as Ticket objects.

fetch_unread_emails(user, app_password)
    Connect to Gmail via IMAP and return unread messages as Ticket objects.
    Returns an empty list if credentials are not provided.

generate_background_volume(count=15)
    Simulate a realistic support queue with a mix of email/web/telegram tickets.
    Always includes at least 3 tickets with symptom "ERR-5001" for Outage Radar.
"""

from __future__ import annotations

import email as email_lib
import imaplib
import uuid
from typing import Any

from models import Ticket

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# A. Telegram Bot Polling
# ══════════════════════════════════════════════════════════════════════════════

def fetch_telegram_updates(
    bot_token: str,
    last_update_id: int = 0,
) -> tuple[list[Ticket], int]:
    """Poll the Telegram Bot API for new messages.

    Parameters
    ----------
    bot_token : str
        Your Telegram bot token (from @BotFather).
    last_update_id : int
        The last update_id that was already processed.
        Pass 0 to fetch all pending updates.

    Returns
    -------
    tickets : list[Ticket]
        New tickets parsed from Telegram messages.
    new_last_id : int
        The latest update_id seen (pass back on the next call).
    """
    if not _REQUESTS_AVAILABLE:
        print("[channels/telegram] 'requests' not installed — cannot poll Telegram.")
        return [], last_update_id

    if not bot_token or not bot_token.strip():
        return [], last_update_id

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params: dict[str, Any] = {"timeout": 5, "allowed_updates": ["message"]}
    if last_update_id > 0:
        params["offset"] = last_update_id + 1

    try:
        resp = _requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[channels/telegram] API error: {exc}")
        return [], last_update_id

    if not data.get("ok"):
        print(f"[channels/telegram] Telegram returned ok=false: {data}")
        return [], last_update_id

    tickets: list[Ticket] = []
    new_last_id = last_update_id

    for update in data.get("result", []):
        update_id: int = update.get("update_id", 0)
        new_last_id = max(new_last_id, update_id)

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue

        text: str = msg.get("text") or msg.get("caption") or ""
        if not text.strip():
            continue

        chat = msg.get("chat", {})
        from_user = msg.get("from", {})
        sender_name = (
            from_user.get("username")
            or f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()
            or str(chat.get("id", "unknown"))
        )

        # Use first line as subject, rest as body
        lines = text.strip().splitlines()
        subject = lines[0][:120] if lines else "(no subject)"
        body = text.strip()

        ticket = Ticket(
            id=f"TG-{update_id}",
            sender=f"@{sender_name}" if from_user.get("username") else sender_name,
            subject=subject,
            body=body,
            channel="telegram",
            status="untriaged",
        )
        tickets.append(ticket)

    return tickets, new_last_id


# ══════════════════════════════════════════════════════════════════════════════
# B. Gmail IMAP
# ══════════════════════════════════════════════════════════════════════════════

def fetch_unread_emails(
    user: str = "",
    app_password: str = "",
    max_emails: int = 20,
) -> list[Ticket]:
    """Fetch unread emails from Gmail via IMAP and return them as Ticket objects.

    Uses Gmail's IMAP endpoint (imap.gmail.com:993).
    Requires an App Password (not the account password) when 2FA is enabled.

    Returns an empty list if credentials are not provided.
    """
    if not user or not app_password:
        return []

    tickets: list[Ticket] = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(user, app_password)
        mail.select("INBOX")

        _, msg_ids_raw = mail.search(None, "UNSEEN")
        msg_ids = (msg_ids_raw[0] or b"").split()
        # Most recent first, cap at max_emails
        msg_ids = msg_ids[::-1][:max_emails]

        for i, mid in enumerate(msg_ids):
            _, data = mail.fetch(mid, "(RFC822)")
            raw = data[0]
            if not isinstance(raw, tuple):
                continue

            parsed = email_lib.message_from_bytes(raw[1])
            subject = parsed.get("Subject", "(no subject)")
            sender = parsed.get("From", "unknown@unknown.com")

            # Extract plain-text body
            body = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(
                                part.get_content_charset() or "utf-8", errors="replace"
                            )
                            break
            else:
                payload = parsed.get_payload(decode=True)
                if payload:
                    body = payload.decode(
                        parsed.get_content_charset() or "utf-8", errors="replace"
                    )

            ticket = Ticket(
                id=f"GM-{i+1:04d}",
                sender=sender,
                subject=subject[:200],
                body=body[:4000],
                channel="email",
                status="untriaged",
            )
            tickets.append(ticket)

        mail.logout()

    except Exception as exc:
        print(f"[channels/gmail] IMAP error: {exc}")

    return tickets


# ══════════════════════════════════════════════════════════════════════════════
# C. Background Volume Generator
# ══════════════════════════════════════════════════════════════════════════════

_EMAIL_TICKETS = [
    Ticket(
        id="BG-E001",
        channel="email",
        sender="james.wilson@techcorp.com",
        subject="Dashboard completely unresponsive — ERR-5001 on every load",
        body=(
            "Hi Support,\n\n"
            "Since Monday our analytics dashboard returns ERR-5001 on every load attempt. "
            "We have tested across five machines and two office networks. "
            "This is blocking our weekly reporting cycle — please treat as high priority.\n\n"
            "Account ACC-10021, DataPilot Pro.\n\nJames Wilson"
        ),
        account="ACC-10021",
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["ERR-5001", "dashboard timeout"],
    ),
    Ticket(
        id="BG-E002",
        channel="email",
        sender="sarah.okonkwo@globalfinance.io",
        subject="SSO redirect loop ERR-4022 — 40 users locked out",
        body=(
            "Dear Support,\n\n"
            "After your 2.6 update all 40 users are stuck in an SSO redirect loop showing "
            "ERR-4022. Our IdP config is unchanged. We need escalation to engineering.\n\n"
            "Account ACC-10155, CloudSync Enterprise.\n\nSarah Okonkwo, Head of IT"
        ),
        account="ACC-10155",
        product="CloudSync Enterprise",
        error_codes=["ERR-4022"],
        symptoms=["SSO loop", "SAML redirect failure"],
    ),
    Ticket(
        id="BG-E003",
        channel="email",
        sender="marcus.lee@retailgroup.com",
        subject="Invoice INV-9021 overcharge by $480",
        body=(
            "Hello,\n\n"
            "Invoice INV-9021 shows $1,680 but our contract is $1,200/month — an overcharge "
            "of $480. No service change was communicated. Please issue a corrected invoice "
            "within 48 hours.\n\nAccount ACC-10310, DataPilot Business.\n\nMarcus Lee"
        ),
        account="ACC-10310",
        product="DataPilot Business",
        error_codes=[],
        symptoms=[],
    ),
    Ticket(
        id="BG-E004",
        channel="email",
        sender="priya.sharma@startupco.dev",
        subject="CRITICAL — cascade delete destroyed 6 months of records (ERR-9001)",
        body=(
            "URGENT — critical data loss.\n\n"
            "Cleanup job at 02:00 triggered ERR-9001 cascade delete. Six months of "
            "transaction records are gone from production. Operations halted. "
            "Need emergency recovery.\n\nAccount ACC-10501, DataPilot Enterprise.\n\nPriya Sharma, CTO"
        ),
        account="ACC-10501",
        product="DataPilot Enterprise",
        error_codes=["ERR-9001"],
        symptoms=["cascade delete", "data loss"],
    ),
    Ticket(
        id="BG-E005",
        channel="email",
        sender="tom.baker@agencyworks.net",
        subject="API /v2/export timing out — ERR-5001 — pipeline broken",
        body=(
            "Hi,\n\n"
            "All calls to /api/v2/export return ERR-5001 after 30s since yesterday. "
            "Nightly sync failed two consecutive nights. SLA breach imminent.\n\n"
            "Account ACC-10420, CloudSync API.\n\nTom Baker"
        ),
        account="ACC-10420",
        product="CloudSync API",
        error_codes=["ERR-5001"],
        symptoms=["ERR-5001", "API timeout", "dashboard timeout"],
    ),
    Ticket(
        id="BG-E006",
        channel="email",
        sender="linda.cho@mediafirm.co",
        subject="Refund still not received after 4 weeks",
        body=(
            "Hello Support,\n\n"
            "Downgraded from Enterprise to Business a month ago and was promised a $520 "
            "refund within 7 days. It is now week 4 and nothing received. "
            "Third ticket on this same issue.\n\nAccount ACC-10788.\n\nLinda Cho"
        ),
        account="ACC-10788",
        product="CloudSync Enterprise",
        error_codes=[],
        symptoms=[],
    ),
    Ticket(
        id="BG-E007",
        channel="email",
        sender="alex.novak@research.edu",
        subject="Feature request: scheduled exports with email delivery",
        body=(
            "Hi,\n\nOur team exports reports manually every Monday. Scheduled exports "
            "with email delivery to a distribution list would save us hours monthly. "
            "Happy to beta test.\n\nAccount ACC-10920, CloudSync Research.\n\nAlex Novak"
        ),
        account="ACC-10920",
        product="CloudSync Research",
        error_codes=[],
        symptoms=[],
    ),
]

_WEB_TICKETS = [
    Ticket(
        id="BG-W001",
        channel="web",
        sender="chat_session_4821",
        subject="Dashboard loading ERR-5001",
        body=(
            "Hey the dashboard keeps showing ERR-5001 and won't load. "
            "Been like this for two days. Other people in my team have the same problem."
        ),
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["ERR-5001", "dashboard timeout"],
    ),
    Ticket(
        id="BG-W002",
        channel="web",
        sender="chat_session_5503",
        subject="All my data from last month is gone",
        body=(
            "Hello? I logged in this morning and all my reports from last month are missing. "
            "I didn't delete anything. Please help urgently."
        ),
        product="DataPilot Pro",
        error_codes=[],
        symptoms=["missing data"],
    ),
    Ticket(
        id="BG-W003",
        channel="web",
        sender="chat_session_6112",
        subject="Cant login — says invalid credentials",
        body=(
            "hi i cant login. it says invalid credentials but im sure my password is right. "
            "tried resetting it twice. still blocked."
        ),
        product="DataPilot Starter",
        error_codes=[],
        symptoms=[],
    ),
    Ticket(
        id="BG-W004",
        channel="web",
        sender="contact_form_7034",
        subject="Wrong charge on account",
        body=(
            "Hi, I think I'm being charged the wrong amount. "
            "My bill says $240 but I thought the plan was $200/month. "
            "Can someone check please?"
        ),
        product="DataPilot Business",
        error_codes=[],
        symptoms=[],
    ),
    Ticket(
        id="BG-W005",
        channel="web",
        sender="contact_form_8891",
        subject="Export button does nothing",
        body=(
            "The export button doesn't work. Click it and nothing happens. "
            "Tried on Chrome and Edge. Been broken for a few hours."
        ),
        product="CloudSync API",
        error_codes=[],
        symptoms=[],
    ),
]

_TELEGRAM_TICKETS = [
    Ticket(
        id="BG-TG001",
        channel="telegram",
        sender="@frustrated_dev_99",
        subject="@DataPilot your API is DOWN again!! ERR-5001 #outage",
        body=(
            "@DataPilot your API is DOWN again!! ERR-5001 on every call. "
            "dashboard timeout too. third time this month. fix this NOW!! #outage"
        ),
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["ERR-5001", "dashboard timeout"],
    ),
    Ticket(
        id="BG-TG002",
        channel="telegram",
        sender="@angrySaaS_user",
        subject="dashboard broken 3 days — paying $1200/month for this??",
        body=(
            "why is my @DataPilot dashboard still broken after 3 days?? "
            "keeps timing out every time i load reports. "
            "paying $1200/month for THIS?? #fail"
        ),
        product="DataPilot Pro",
        error_codes=[],
        symptoms=["dashboard timeout"],
    ),
    Ticket(
        id="BG-TG003",
        channel="telegram",
        sender="@devops_rage",
        subject="SSO broken since 2.6 update — 40 people cant work",
        body=(
            "@DataPilot your 2.6 update broke SSO completely. "
            "ERR-4022 every login. 40 people in my org cant work. "
            "NO response in 6 hours. #incident"
        ),
        product="CloudSync Enterprise",
        error_codes=["ERR-4022"],
        symptoms=["SSO loop"],
    ),
]

# Full base pool in display order: emails first, then web, then telegram
_ALL_BACKGROUND: list[Ticket] = _EMAIL_TICKETS + _WEB_TICKETS + _TELEGRAM_TICKETS


def generate_background_volume(count: int = 15) -> list[Ticket]:
    """Return *count* realistic untriaged tickets for background queue simulation.

    The pool guarantees at least 3 tickets share the symptom "ERR-5001" so the
    Outage Radar will fire.  If count <= 15 the first *count* items are returned.
    """
    pool = _ALL_BACKGROUND
    if count <= len(pool):
        return [_clone(t) for t in pool[:count]]
    result: list[Ticket] = []
    while len(result) < count:
        result.extend(_clone(t) for t in pool)
    return result[:count]


def _clone(t: Ticket) -> Ticket:
    """Return a fresh copy with status reset to 'untriaged'."""
    import copy
    c = copy.deepcopy(t)
    c.status = "untriaged"
    return c
