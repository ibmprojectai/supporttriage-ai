"""Web form ticket submission via SMTP.

Functions
---------
submit_web_ticket(...)
    Build and send a formatted support ticket email via SMTP_SSL.
    Returns (True, "OK") on success or (False, error_message) on failure.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage


def submit_web_ticket(
    sender_name: str,
    sender_email: str,
    subject: str,
    body: str,
    product: str,
    priority: str,
    account: str,
    dest_email: str,
    smtp_user: str,
    smtp_pass: str,
    smtp_server: str = "smtp.gmail.com",
) -> tuple[bool, str]:
    """Send a support ticket email via SMTP_SSL and return (success, message).

    Parameters
    ----------
    sender_name   : Customer's full name.
    sender_email  : Customer's email address (used as Reply-To).
    subject       : Short issue summary (will be prefixed with [SUPPORT-TICKET]).
    body          : Full issue description.
    product       : Product name selected in the form.
    priority      : Priority level selected in the form.
    account       : Optional account ID string (may be empty).
    dest_email    : Destination inbox address (SUPPORT_EMAIL or GMAIL_USER).
    smtp_user     : SMTP login username (Gmail address).
    smtp_pass     : SMTP App Password.
    smtp_server   : SMTP server host (default: smtp.gmail.com).

    Returns
    -------
    (True, "OK") on success.
    (False, error_string) on any failure.
    """
    email_body = (
        "New support ticket submitted via Web Form\n"
        "==========================================\n"
        "From: {name} <{email}>\n"
        "Product: {product}\n"
        "Priority: {priority}\n"
        "Account: {account}\n"
        "\n"
        "Issue Description:\n"
        "{body}\n"
        "\n"
        "--\n"
        "Submitted via SupportTriage AI Web Form"
    ).format(
        name=sender_name,
        email=sender_email,
        product=product,
        priority=priority,
        account=account or "Not provided",
        body=body,
    )

    msg = EmailMessage()
    msg["Subject"] = "[SUPPORT-TICKET] {}".format(subject)
    msg["From"] = smtp_user
    msg["To"] = dest_email
    msg["Reply-To"] = sender_email
    msg.set_content(email_body)

    try:
        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "OK"
    except Exception as exc:
        return False, str(exc)
