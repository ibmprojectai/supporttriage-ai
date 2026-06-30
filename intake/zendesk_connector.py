"""Zendesk email connector stub.

Production usage: replace the body of fetch_ticket() with a real Zendesk REST call.
The stub path returns a fully populated mock Ticket so the pipeline can run without
any credentials.
"""

from __future__ import annotations

from models import Ticket


def fetch_ticket(ticket_id: str) -> Ticket:
    """Return a Ticket for the given Zendesk ticket ID.

    In stub mode every ID resolves to the same mock ticket.
    TODO: replace stub body with real Zendesk API call:
        GET https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json
    """
    # ── Stub / mock ────────────────────────────────────────────────────────────
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
