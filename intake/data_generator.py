"""Multi-channel inbox generator.

Returns a realistic mix of untriaged support tickets from three channels:
  - Email   (formal, longer, include account IDs and error codes)
  - Twitter (short, angry, informal, @mentions, hashtags)
  - Chat    (vague, short, conversational)

Critical: 4 tickets across channels all reference ERR-5001 / dashboard timeout
so the Outage Radar can detect the pattern.

Usage:
    from intake.data_generator import generate_inbox
    tickets = generate_inbox(20)
"""

from __future__ import annotations

import random
from models import Ticket

__all__ = ["generate_inbox"]

# ── Base ticket pool (always included, 20 tickets) ────────────────────────────

_BASE_TICKETS: list[Ticket] = [

    # ── EMAIL (7) ─────────────────────────────────────────────────────────────

    Ticket(
        id="T-E001",
        channel="email",
        sender="james.wilson@techcorp.com",
        subject="Cannot access dashboard — ERR-5001 timeout since Monday",
        body=(
            "Hi Support,\n\n"
            "Since Monday morning our entire analytics dashboard has been returning "
            "ERR-5001 (request timeout) on every load attempt. Before this week it "
            "loaded consistently in under 3 seconds. We have verified the issue "
            "across five separate machines and two different office networks.\n\n"
            "This is blocking our weekly reporting cycle which is due on Friday. "
            "Our account is ACC-10021, product DataPilot Pro. "
            "Please treat this as high priority.\n\nRegards,\nJames Wilson"
        ),
        account="ACC-10021",
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["dashboard timeout", "ERR-5001"],
    ),

    Ticket(
        id="T-E002",
        channel="email",
        sender="sarah.okonkwo@globalfinance.io",
        subject="SSO login redirect loop — ERR-4022 — 40 users affected",
        body=(
            "Dear Support Team,\n\n"
            "Following the 2.6 platform update deployed yesterday, all 40 users at "
            "Global Finance are experiencing an SSO redirect loop. The browser shows "
            "ERR-4022 after returning from our SAML identity provider. "
            "We have confirmed that our IdP configuration has not changed.\n\n"
            "This is a Severity-1 incident for us — we cannot access the platform at "
            "all. Account ACC-10155, CloudSync Enterprise. "
            "We need escalation to your senior engineering team immediately.\n\n"
            "Sarah Okonkwo, Head of IT"
        ),
        account="ACC-10155",
        product="CloudSync Enterprise",
        error_codes=["ERR-4022"],
        symptoms=["SSO loop", "SAML redirect failure"],
    ),

    Ticket(
        id="T-E003",
        channel="email",
        sender="marcus.lee@retailgroup.com",
        subject="Incorrect invoice — overcharged $480 on INV-9021",
        body=(
            "Hello,\n\n"
            "I am writing regarding invoice INV-9021 dated last month. "
            "Our contract specifies $1,200 per month for the Business tier, "
            "but we have been billed $1,680 — an overcharge of $480.\n\n"
            "No change in service level was communicated prior to this invoice. "
            "I have attached our signed contract for reference. "
            "Please issue a corrected invoice and credit note within 48 hours "
            "as this is affecting our accounts payable close. Account ACC-10310.\n\n"
            "Marcus Lee, Finance Manager"
        ),
        account="ACC-10310",
        product="DataPilot Business",
        error_codes=[],
    ),

    Ticket(
        id="T-E004",
        channel="email",
        sender="priya.sharma@startupco.dev",
        subject="CRITICAL: 6 months of customer records deleted — ERR-9001",
        body=(
            "URGENT — This is a critical data loss incident.\n\n"
            "The scheduled cleanup job that ran at 02:00 this morning triggered "
            "an unexpected cascade delete (ERR-9001). Six months of customer "
            "transaction records have been removed from our production database.\n\n"
            "We have halted all operations and need emergency data recovery support "
            "immediately. Our compliance team is already involved. "
            "Account ACC-10501, DataPilot Enterprise.\n\nPriya Sharma, CTO"
        ),
        account="ACC-10501",
        product="DataPilot Enterprise",
        error_codes=["ERR-9001"],
        symptoms=["cascade delete", "data loss"],
    ),

    Ticket(
        id="T-E005",
        channel="email",
        sender="tom.baker@agencyworks.net",
        subject="API /v2/export endpoint timing out — ERR-5001 — pipeline broken",
        body=(
            "Hi,\n\n"
            "Our automated data pipeline hits /api/v2/export every 15 minutes. "
            "Since yesterday all calls return ERR-5001 after 30 seconds. "
            "Our nightly sync has now failed for two consecutive nights and "
            "our downstream BI tools are showing stale data.\n\n"
            "Account ACC-10420, CloudSync API. This needs immediate attention "
            "as we have SLA commitments to our own clients.\n\nTom Baker"
        ),
        account="ACC-10420",
        product="CloudSync API",
        error_codes=["ERR-5001"],
        symptoms=["dashboard timeout", "ERR-5001", "API timeout"],
    ),

    Ticket(
        id="T-E006",
        channel="email",
        sender="linda.cho@mediafirm.co",
        subject="Refund not received — downgraded 4 weeks ago",
        body=(
            "Hello Support,\n\n"
            "I downgraded from Enterprise to Business on the 1st of last month "
            "and was told a pro-rated refund of $520 would be issued within 5–7 days. "
            "It has been four weeks and nothing has appeared on my statement.\n\n"
            "I have opened two previous tickets (#8012 and #8145) with no resolution. "
            "This is unacceptable. Account ACC-10788, CloudSync Enterprise.\n\n"
            "Linda Cho"
        ),
        account="ACC-10788",
        product="CloudSync Enterprise",
        error_codes=[],
    ),

    Ticket(
        id="T-E007",
        channel="email",
        sender="alex.novak@research.edu",
        subject="Feature request: scheduled exports and email delivery",
        body=(
            "Hi,\n\n"
            "Our research team exports reports manually every Monday morning. "
            "It would save us significant time if the platform supported scheduled "
            "exports with automatic email delivery to a distribution list.\n\n"
            "We would also love a CSV preview before download. "
            "Happy to join a beta if this is on your roadmap. "
            "Account ACC-10920, CloudSync Research.\n\nAlex Novak"
        ),
        account="ACC-10920",
        product="CloudSync Research",
        error_codes=[],
    ),

    # ── TWITTER (7) ───────────────────────────────────────────────────────────

    Ticket(
        id="T-TW001",
        channel="twitter",
        sender="@frustrated_dev_99",
        subject="@DataPilot your API is DOWN again!! ERR-5001 #outage",
        body=(
            "@DataPilot your API is DOWN again!! ERR-5001 on every single call. "
            "dashboard timeout too. third time this month. "
            "my entire pipeline is broken. fix this NOW!! #outage #datapilot"
        ),
        account="",
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["dashboard timeout", "ERR-5001"],
    ),

    Ticket(
        id="T-TW002",
        channel="twitter",
        sender="@angrySaaS_user",
        subject="why is my dashboard broken for 3 days now??",
        body=(
            "why is my @DataPilot dashboard still broken after 3 days?? "
            "keeps timing out every time i try to load reports. "
            "paying $1200/month for THIS?? #fail #support"
        ),
        account="",
        product="DataPilot Pro",
        error_codes=[],
        symptoms=["dashboard timeout"],
    ),

    Ticket(
        id="T-TW003",
        channel="twitter",
        sender="@cloudsync_victim",
        subject="@DataPilot charged me TWICE this month wtf",
        body=(
            "just checked my bank statement and @DataPilot charged me TWICE this month. "
            "this is literally fraud. DMing now but also posting publicly "
            "so others know. #billing #scam"
        ),
        account="",
        product="CloudSync Enterprise",
        error_codes=[],
    ),

    Ticket(
        id="T-TW004",
        channel="twitter",
        sender="@devops_rage",
        subject="@DataPilot SSO is completely broken since your update",
        body=(
            "@DataPilot your 2.6 update broke our entire SSO. "
            "ERR-4022 on every login attempt. 40 people in my company cant work. "
            "when is this being fixed?? no response from support in 6 hours #incident"
        ),
        account="",
        product="CloudSync Enterprise",
        error_codes=["ERR-4022"],
        symptoms=["SSO loop"],
    ),

    Ticket(
        id="T-TW005",
        channel="twitter",
        sender="@pmgirl_tweets",
        subject="@DataPilot seriously where is my refund",
        body=(
            "@DataPilot i downgraded my plan 5 weeks ago and STILL no refund. "
            "opened 3 tickets. nobody responds. "
            "is this company even real anymore?? #noreply"
        ),
        account="",
        product="DataPilot Business",
        error_codes=[],
    ),

    Ticket(
        id="T-TW006",
        channel="twitter",
        sender="@startup_founder_zara",
        subject="@DataPilot data export produced corrupted file AGAIN",
        body=(
            "hey @DataPilot our bulk export job just corrupted 20k records AGAIN. "
            "this is the second time. "
            "email fields are all NULL. what is going on with your platform??"
        ),
        account="",
        product="CloudSync Enterprise",
        error_codes=["ERR-9002"],
        symptoms=["data corruption", "null fields"],
    ),

    Ticket(
        id="T-TW007",
        channel="twitter",
        sender="@techbro_dan",
        subject="@DataPilot any ETA on dark mode? asking for the 100th time",
        body=(
            "@DataPilot any ETA on dark mode?? "
            "been asking for this for literally a year. "
            "my eyes hurt every evening session. please just ship it 🙏"
        ),
        account="",
        product="DataPilot Pro",
        error_codes=[],
    ),

    # ── CHAT (6) ──────────────────────────────────────────────────────────────

    Ticket(
        id="T-CH001",
        channel="chat",
        sender="chat_session_4821",
        subject="hi i cant login",
        body=(
            "hi i cant login to my account. "
            "it just says invalid credentials but im sure my password is right. "
            "i tried resetting it twice already"
        ),
        account="",
        product="DataPilot Starter",
        error_codes=[],
    ),

    Ticket(
        id="T-CH002",
        channel="chat",
        sender="chat_session_5503",
        subject="help my data is gone",
        body=(
            "hello? my data is gone. "
            "i logged in this morning and all my reports from last month are missing. "
            "i didnt delete anything i swear. please help"
        ),
        account="",
        product="DataPilot Pro",
        error_codes=[],
        symptoms=["missing data"],
    ),

    Ticket(
        id="T-CH003",
        channel="chat",
        sender="chat_session_6112",
        subject="dashboard super slow today",
        body=(
            "hey the dashboard is super slow today. "
            "like way slower than normal. "
            "is there an outage or something? ERR-5001 keeps popping up"
        ),
        account="",
        product="DataPilot Pro",
        error_codes=["ERR-5001"],
        symptoms=["dashboard timeout", "ERR-5001"],
    ),

    Ticket(
        id="T-CH004",
        channel="chat",
        sender="chat_session_7034",
        subject="how do i add team members",
        body=(
            "hi how do i add team members to my workspace? "
            "i looked in settings but cant find the option. "
            "we just signed up today"
        ),
        account="",
        product="DataPilot Starter",
        error_codes=[],
    ),

    Ticket(
        id="T-CH005",
        channel="chat",
        sender="chat_session_7891",
        subject="wrong amount on my bill",
        body=(
            "hi i think im being charged the wrong amount. "
            "my bill says $240 but i thought it was supposed to be $200. "
            "can someone check please"
        ),
        account="",
        product="DataPilot Business",
        error_codes=[],
    ),

    Ticket(
        id="T-CH006",
        channel="chat",
        sender="chat_session_8204",
        subject="export not working",
        body=(
            "hey my export is not working. "
            "i click the export button and nothing happens. "
            "its been like this for a few hours now"
        ),
        account="",
        product="CloudSync API",
        error_codes=[],
    ),
]


def generate_inbox(count: int = 20) -> list[Ticket]:
    """Return *count* untriaged Ticket objects from the multi-channel inbox pool.

    The base pool has exactly 20 tickets (7 email + 7 twitter + 6 chat).
    If count <= 20 the first *count* tickets are returned.
    If count > 20 tickets are cycled/repeated to fill the requested size.
    """
    pool = _BASE_TICKETS
    if count <= len(pool):
        return list(pool[:count])
    # cycle if caller requests more than the pool
    result = []
    while len(result) < count:
        result.extend(pool)
    return result[:count]
