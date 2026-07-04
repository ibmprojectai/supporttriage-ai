"""Zendesk email connector stub.

Production usage: replace the body of fetch_ticket() with a real Zendesk REST call.
The stub path returns a fully populated mock Ticket so the pipeline can run without
any credentials. Exports: fetch_ticket, fetch_all_tickets.
"""

from __future__ import annotations

from models import Ticket

__all__ = ["fetch_ticket", "fetch_all_tickets"]


def fetch_ticket(ticket_id: str) -> Ticket:
    """Return a Ticket for the given Zendesk ticket ID.

    In stub mode every ID resolves to the same mock ticket.
    TODO: replace stub body with real Zendesk API call:
        GET https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json
    """
    return Ticket(
        id=ticket_id,
        sender="alice.smith@example.com",
        subject="Cannot login after password reset — ERR-4021",
        body=(
            "Hi Support,\n\n"
            "I reset my password yesterday but I still can't log in. "
            "I keep getting error code ERR-4021. "
            "My account number is ACC-00982 and I'm using the DataPilot Pro product. "
            "I've tried three times from different browsers. "
            "Please help — this is blocking my entire team.\n\n"
            "Thanks,\nAlice Smith\n"
            "Phone: 415-555-0198\nCard on file: 4111 1111 1111 1111"
        ),
        thread=[
            "Auto-reply: Your ticket has been received. Reference: ERR-4021.",
            "Agent Bob: Hi Alice, can you confirm your account email address?",
            "Alice: Sure — alice.smith@example.com. Still getting ERR-4021.",
        ],
        account="ACC-00982",
        product="DataPilot Pro",
    )


def fetch_all_tickets() -> list[Ticket]:
    """Return 15 realistic mock support tickets covering all triage categories.

    Ticket breakdown:
      3 × authentication   (T-001, T-002, T-003)
      3 × billing          (T-004, T-005, T-006)
      2 × performance      (T-007, T-008)
      2 × data-loss        (T-009, T-010) — both critical
      2 × feature-request  (T-011, T-012)
      2 × other/general    (T-013, T-014)
      1 × ambiguous        (T-015) — intended to trigger low confidence
    """
    return [
        # ── Authentication (3) ─────────────────────────────────────────────────
        Ticket(
            id="T-001",
            sender="alice.smith@corp.com",
            subject="Cannot login after password reset — ERR-4021",
            body=(
                "I reset my password yesterday but I still cannot log in to the portal. "
                "Every attempt returns ERR-4021 — invalid credentials. "
                "I have confirmed the new password is correct by resetting it twice. "
                "This is blocking my entire team from accessing daily reports. "
                "Account ACC-00982, product DataPilot Pro."
            ),
            account="ACC-00982",
            product="DataPilot Pro",
            error_codes=["ERR-4021"],
        ),
        Ticket(
            id="T-002",
            sender="bob.jones@enterprise.io",
            subject="SSO login loop — ERR-4022 after SAML redirect",
            body=(
                "Our company uses SAML SSO and since the 2.4 update we are stuck in a "
                "login redirect loop. The browser shows ERR-4022 after returning from "
                "our identity provider. All 40 users in our organisation are affected. "
                "We have verified the SSO configuration has not changed on our side. "
                "Account ACC-01155, product CloudSync Enterprise."
            ),
            account="ACC-01155",
            product="CloudSync Enterprise",
            error_codes=["ERR-4022"],
        ),
        Ticket(
            id="T-003",
            sender="carol.white@startup.dev",
            subject="Account locked after 3 failed attempts — need immediate unlock",
            body=(
                "My account has been locked after three failed login attempts this morning. "
                "I was testing a new API integration and accidentally used wrong credentials. "
                "The self-service unlock email never arrived in my inbox or spam folder. "
                "I need access urgently to demo the product to a client in two hours. "
                "Account ACC-02210, product DataPilot Starter."
            ),
            account="ACC-02210",
            product="DataPilot Starter",
            error_codes=[],
        ),

        # ── Billing (3) ────────────────────────────────────────────────────────
        Ticket(
            id="T-004",
            sender="david.lee@company.com",
            subject="Incorrect charge on invoice #INV-8821 — overcharged by $240",
            body=(
                "Our invoice INV-8821 dated last month shows a charge of $1,440 but our "
                "contract specifies $1,200 per month for the Business plan. "
                "We have been overcharged by $240 with no explanation or change in service. "
                "I have attached the contract and the invoice for your reference. "
                "Please issue a corrected invoice and credit note. Account ACC-00310."
            ),
            account="ACC-00310",
            product="DataPilot Business",
            error_codes=[],
        ),
        Ticket(
            id="T-005",
            sender="eva.martin@agency.net",
            subject="Refund not received after downgrade 3 weeks ago",
            body=(
                "I downgraded from the Enterprise to Business plan on the 1st of last month "
                "and was told a pro-rated refund of $380 would be issued within 5–7 days. "
                "It has now been three weeks and the refund has not appeared on my statement. "
                "I have opened two previous tickets about this (refs #7710 and #7834) "
                "with no resolution. Account ACC-00788, product CloudSync Enterprise."
            ),
            account="ACC-00788",
            product="CloudSync Enterprise",
            error_codes=[],
        ),
        Ticket(
            id="T-006",
            sender="frank.chen@logistics.co",
            subject="January invoice missing from billing portal",
            body=(
                "The January invoice is not showing in our billing portal despite the payment "
                "having been successfully processed on January 3rd. "
                "All other months are visible but January shows a blank entry. "
                "We need the invoice for our quarterly audit which is due this Friday. "
                "Account ACC-01902, product DataPilot Pro."
            ),
            account="ACC-01902",
            product="DataPilot Pro",
            error_codes=[],
        ),

        # ── Performance (2) ────────────────────────────────────────────────────
        Ticket(
            id="T-007",
            sender="grace.kim@mediahouse.com",
            subject="Dashboard load time exceeds 45 seconds — unusable since Friday",
            body=(
                "Since last Friday our main analytics dashboard takes over 45 seconds to load. "
                "Before the update it loaded in under 3 seconds. "
                "We have tested on multiple machines and network connections — the issue "
                "persists across all users in our team. "
                "Account ACC-03301, product DataPilot Pro. Browser console shows ERR-5001."
            ),
            account="ACC-03301",
            product="DataPilot Pro",
            error_codes=["ERR-5001"],
        ),
        Ticket(
            id="T-008",
            sender="henry.paul@devshop.io",
            subject="API response times exceeding 30s — integration pipeline broken",
            body=(
                "Our automated data pipeline calls the /api/v2/export endpoint every 15 minutes "
                "and since yesterday all calls are timing out after 30 seconds. "
                "We are seeing ERR-5010 in the API response body. "
                "This has caused our nightly data sync to fail for two consecutive nights. "
                "Account ACC-04420, product CloudSync API."
            ),
            account="ACC-04420",
            product="CloudSync API",
            error_codes=["ERR-5010"],
        ),

        # ── Data-loss (2, both critical) ───────────────────────────────────────
        Ticket(
            id="T-009",
            sender="irene.fox@finance.org",
            subject="CRITICAL: 3 months of transaction records deleted — ERR-9001",
            body=(
                "After running the scheduled data cleanup job last night, three months of "
                "transaction records (October–December) have been permanently deleted from "
                "our production database. The job log shows ERR-9001 — unexpected cascade. "
                "This is a critical compliance issue and we have immediately halted all "
                "operations. We need emergency data recovery. Account ACC-00501."
            ),
            account="ACC-00501",
            product="DataPilot Enterprise",
            error_codes=["ERR-9001"],
        ),
        Ticket(
            id="T-010",
            sender="james.ruiz@retail.com",
            subject="CRITICAL: Bulk export job corrupted 50,000 customer records",
            body=(
                "The bulk export job that ran at 02:00 this morning has returned a corrupted "
                "CSV file. Upon inspection, 50,000 customer records have malformed email fields "
                "and NULL values where data existed yesterday. "
                "We cannot determine if the source data was also affected. "
                "Account ACC-00622, product CloudSync Enterprise. Error: ERR-9002."
            ),
            account="ACC-00622",
            product="CloudSync Enterprise",
            error_codes=["ERR-9002"],
        ),

        # ── Feature requests (2) ───────────────────────────────────────────────
        Ticket(
            id="T-011",
            sender="karen.wood@design.co",
            subject="Feature request: dark mode for the analytics dashboard",
            body=(
                "Our team works late hours and the current bright white dashboard causes "
                "significant eye strain during evening sessions. "
                "We would love to see a dark mode toggle added to the user preferences. "
                "Many of our colleagues have mentioned this as their most-wanted feature. "
                "Account ACC-05001, product DataPilot Pro."
            ),
            account="ACC-05001",
            product="DataPilot Pro",
            error_codes=[],
        ),
        Ticket(
            id="T-012",
            sender="liam.scott@research.edu",
            subject="Feature request: bulk export of filtered reports to CSV/Excel",
            body=(
                "Currently we can only export one report at a time which is very slow "
                "when we need to pull 30+ reports for our monthly research digest. "
                "A bulk export feature with filter options would save us several hours monthly. "
                "We would be happy to beta test this if it is on the roadmap. "
                "Account ACC-05220, product CloudSync Research."
            ),
            account="ACC-05220",
            product="CloudSync Research",
            error_codes=[],
        ),

        # ── Other / General (2) ───────────────────────────────────────────────
        Ticket(
            id="T-013",
            sender="mia.taylor@newco.com",
            subject="Onboarding question — how do I invite team members?",
            body=(
                "We just signed up for DataPilot Starter and I am trying to invite my "
                "three colleagues to the workspace but cannot find the option in settings. "
                "I have looked at the help docs but the screenshots look different from "
                "what I see in my dashboard. "
                "Could you point me to the correct section? Account ACC-06100."
            ),
            account="ACC-06100",
            product="DataPilot Starter",
            error_codes=[],
        ),
        Ticket(
            id="T-014",
            sender="noah.harris@consulting.biz",
            subject="Documentation for webhook setup is outdated",
            body=(
                "The webhook configuration guide in your docs refers to an endpoint "
                "/api/v1/webhooks but that endpoint returns 404 — it appears to have "
                "moved to /api/v2/webhooks in a recent release. "
                "The docs have not been updated and this caused several hours of confusion "
                "for our integration team. Account ACC-06780, product CloudSync API."
            ),
            account="ACC-06780",
            product="CloudSync API",
            error_codes=[],
        ),

        # ── Ambiguous (1) — intended to trigger low confidence ────────────────
        Ticket(
            id="T-015",
            sender="olivia.jones@unknown.org",
            subject="Something is wrong with my account",
            body=(
                "Hi, things are not working properly on my end. "
                "I am not sure what is happening but the system seems off. "
                "Can someone look into this for me? "
                "Account ACC-07001."
            ),
            account="ACC-07001",
            product="",
            error_codes=[],
        ),
    ]
