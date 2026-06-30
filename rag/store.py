"""ChromaDB wrapper — initialise, seed, and query the knowledge-base vector store.

All ChromaDB interaction is isolated here so pipeline modules stay decoupled from the
underlying store implementation.

Knowledge base covers:
  - HTTP error codes (403, 401, 500, 429)
  - Billing (cycles, invoices, refunds)
  - Authentication / login issues
  - Account management
  - SLA / escalation thresholds
"""

from __future__ import annotations

import os

import chromadb
from chromadb import Collection

_COLLECTION_NAME = "support_kb"

# ── Knowledge base seed documents ─────────────────────────────────────────────
_SEED_DOCS = [
    # HTTP / API errors
    (
        "kb-001",
        "403 Forbidden error: check that the user has the correct permissions for the "
        "resource they are trying to access. Verify their role in the admin console under "
        "Settings → Users → Roles. If the role looks correct, check for IP allowlist "
        "restrictions or organisation-level access policies.",
    ),
    (
        "kb-002",
        "401 Unauthorized error: the request is missing valid authentication credentials. "
        "Ask the user to log out completely, clear browser cookies and cache, then log back "
        "in. If using an API key, verify it has not expired in the Developer Portal.",
    ),
    (
        "kb-003",
        "500 Internal Server Error: this is a server-side issue. Collect the request ID "
        "from the error response header (X-Request-ID) and escalate to the platform team "
        "with the timestamp and account ID. Do not ask the user to retry more than twice.",
    ),
    (
        "kb-004",
        "429 Too Many Requests: the account has exceeded its API rate limit. "
        "Standard rate limit is 100 requests/minute on the Free plan and 1000/minute on Pro. "
        "Advise the user to implement exponential backoff or upgrade their plan.",
    ),
    # Auth / login
    (
        "kb-005",
        "ERR-4021 indicates an expired session token. Ask the user to clear browser "
        "cookies, log out completely, and attempt a fresh login. If the issue persists "
        "after a full cache clear, escalate to Tier-2 authentication team.",
    ),
    (
        "kb-006",
        "Password reset emails can be delayed up to 15 minutes due to spam-filter "
        "queuing. Advise the user to check their junk/spam folder and whitelist "
        "noreply@datapilot.example.com. If not received after 30 minutes, trigger a "
        "manual reset from the admin console.",
    ),
    (
        "kb-007",
        "DataPilot Pro accounts are locked after 5 consecutive failed login attempts. "
        "An admin can unlock the account via Account Management Console → Users → "
        "Unlock Account. Self-service unlock is available after a 30-minute cooldown.",
    ),
    # Billing
    (
        "kb-008",
        "Billing cycles are 30 days from the subscription start date, not from the "
        "calendar month. Invoices are generated on day 1 of each cycle and are due within "
        "14 days. Customers can view all invoices under Account → Billing → Invoice History.",
    ),
    (
        "kb-009",
        "Refund policy: refunds are available within 7 days of a charge for annual plans "
        "and within 48 hours for monthly plans. To process a refund, go to the billing "
        "portal, select the invoice, and click 'Request Refund'. Escalate to billing team "
        "if the refund window has passed.",
    ),
    (
        "kb-010",
        "For billing-related access issues on ACC-series accounts, verify that the "
        "subscription is active in the billing portal before troubleshooting auth errors. "
        "A lapsed subscription will cause 403 errors on all API endpoints.",
    ),
    # SLA / escalation
    (
        "kb-011",
        "Standard SLA: P1 (critical) = 1-hour response, P2 (high) = 4-hour response, "
        "P3 (medium) = 1 business day, P4 (low) = 3 business days. "
        "Escalate to P1 if more than 5 users on the same account are affected simultaneously.",
    ),
    (
        "kb-012",
        "Data loss or corruption issues are always treated as P1 regardless of the number "
        "of users affected. Immediately page the on-call data engineering team and open a "
        "war-room bridge. Do not attempt to resolve data issues without engineering present.",
    ),
]


def init_store(persist_dir: str | None = None) -> Collection:
    """Create (or reopen) a persistent ChromaDB collection and seed it if empty.

    Args:
        persist_dir: Path for ChromaDB storage. Reads ``CHROMA_PERSIST_DIR`` env var;
                     falls back to ``.chromadb``.
    """
    if persist_dir is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", ".chromadb")

    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    if collection.count() == 0:
        ids, docs = zip(*_SEED_DOCS)
        add_documents(collection, list(docs), list(ids))
        print(
            f"[rag/store] Seeded collection '{_COLLECTION_NAME}' "
            f"with {len(ids)} KB documents."
        )
    else:
        # Re-upsert every run so edits to _SEED_DOCS are always reflected
        ids, docs = zip(*_SEED_DOCS)
        add_documents(collection, list(docs), list(ids))

    return collection


def add_documents(collection: Collection, docs: list[str], ids: list[str]) -> None:
    """Upsert *docs* into *collection* with the given *ids*."""
    collection.upsert(documents=docs, ids=ids)


def retrieve(collection: Collection, query: str, n_results: int = 3) -> list[str]:
    """Return the top *n_results* KB snippets most semantically relevant to *query*."""
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
    )
    return results["documents"][0] if results["documents"] else []
