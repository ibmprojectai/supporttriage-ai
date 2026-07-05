"""ChromaDB wrapper — initialise, seed, and query the knowledge-base vector store.

All ChromaDB interaction is isolated here so pipeline modules stay decoupled from
the underlying store implementation.

Each KB document is stored with metadata so pipeline/draft.py can filter retrieval
by ticket category and product, reducing hallucination from irrelevant snippets.
"""

from __future__ import annotations

import os

import chromadb
from chromadb import Collection

_COLLECTION_NAME = "support_kb"

# ── Knowledge base seed documents ─────────────────────────────────────────────
# Each entry: (id, document_text, metadata_dict)
_SEED_DOCS: list[tuple[str, str, dict]] = [
    # HTTP / API errors
    (
        "kb-001",
        "403 Forbidden error: check that the user has the correct permissions for the "
        "resource they are trying to access. Verify their role in the admin console under "
        "Settings → Users → Roles. If the role looks correct, check for IP allowlist "
        "restrictions or organisation-level access policies.",
        {"category": "authentication", "product": ""},
    ),
    (
        "kb-002",
        "401 Unauthorized error: the request is missing valid authentication credentials. "
        "Ask the user to log out completely, clear browser cookies and cache, then log back "
        "in. If using an API key, verify it has not expired in the Developer Portal.",
        {"category": "authentication", "product": ""},
    ),
    (
        "kb-003",
        "500 Internal Server Error: this is a server-side issue. Collect the request ID "
        "from the error response header (X-Request-ID) and escalate to the platform team "
        "with the timestamp and account ID. Do not ask the user to retry more than twice.",
        {"category": "performance", "product": ""},
    ),
    (
        "kb-004",
        "429 Too Many Requests: the account has exceeded its API rate limit. "
        "Standard rate limit is 100 requests/minute on the Free plan and 1000/minute on Pro. "
        "Advise the user to implement exponential backoff or upgrade their plan.",
        {"category": "performance", "product": ""},
    ),
    # Auth / login
    (
        "kb-005",
        "ERR-4021 indicates an expired session token. Ask the user to clear browser "
        "cookies, log out completely, and attempt a fresh login. If the issue persists "
        "after a full cache clear, escalate to Tier-2 authentication team.",
        {"category": "authentication", "product": "DataPilot Pro"},
    ),
    (
        "kb-006",
        "Password reset emails can be delayed up to 15 minutes due to spam-filter "
        "queuing. Advise the user to check their junk/spam folder and whitelist "
        "noreply@datapilot.example.com. If not received after 30 minutes, trigger a "
        "manual reset from the admin console.",
        {"category": "authentication", "product": "DataPilot Pro"},
    ),
    (
        "kb-007",
        "DataPilot Pro accounts are locked after 5 consecutive failed login attempts. "
        "An admin can unlock the account via Account Management Console → Users → "
        "Unlock Account. Self-service unlock is available after a 30-minute cooldown.",
        {"category": "authentication", "product": "DataPilot Pro"},
    ),
    # Billing
    (
        "kb-008",
        "Billing cycles are 30 days from the subscription start date, not from the "
        "calendar month. Invoices are generated on day 1 of each cycle and are due within "
        "14 days. Customers can view all invoices under Account → Billing → Invoice History.",
        {"category": "billing", "product": ""},
    ),
    (
        "kb-009",
        "Refund policy: refunds are available within 7 days of a charge for annual plans "
        "and within 48 hours for monthly plans. To process a refund, go to the billing "
        "portal, select the invoice, and click 'Request Refund'. Escalate to billing team "
        "if the refund window has passed.",
        {"category": "billing", "product": ""},
    ),
    (
        "kb-010",
        "For billing-related access issues on ACC-series accounts, verify that the "
        "subscription is active in the billing portal before troubleshooting auth errors. "
        "A lapsed subscription will cause 403 errors on all API endpoints.",
        {"category": "billing", "product": ""},
    ),
    # SLA / escalation
    (
        "kb-011",
        "Standard SLA: P1 (critical) = 1-hour response, P2 (high) = 4-hour response, "
        "P3 (medium) = 1 business day, P4 (low) = 3 business days. "
        "Escalate to P1 if more than 5 users on the same account are affected simultaneously.",
        {"category": "other", "product": ""},
    ),
    (
        "kb-012",
        "Data loss or corruption issues are always treated as P1 regardless of the number "
        "of users affected. Immediately page the on-call data engineering team and open a "
        "war-room bridge. Do not attempt to resolve data issues without engineering present.",
        {"category": "data-loss", "product": ""},
    ),
]


def init_store(persist_dir: str | None = None) -> Collection:
    """Create (or reopen) a persistent ChromaDB collection and seed it with metadata.

    Args:
        persist_dir: Path for ChromaDB storage. Reads ``CHROMA_PERSIST_DIR`` env var;
                     falls back to ``.chromadb``.
    """
    if persist_dir is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", ".chromadb")

    try:
        client = chromadb.PersistentClient(path=persist_dir)
    except Exception as exc:
        print(
            f"[rag/store] PersistentClient failed ({exc}); "
            "falling back to in-memory store."
        )
        client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    # Always upsert so edits to _SEED_DOCS are reflected on next run
    ids = [d[0] for d in _SEED_DOCS]
    docs = [d[1] for d in _SEED_DOCS]
    metadatas = [d[2] for d in _SEED_DOCS]
    add_documents(collection, docs, ids, metadatas)

    if collection.count() <= len(_SEED_DOCS):
        print(
            f"[rag/store] Collection '{_COLLECTION_NAME}' ready "
            f"({len(ids)} KB documents)."
        )

    return collection


def add_documents(
    collection: Collection,
    docs: list[str],
    ids: list[str],
    metadatas: list[dict] | None = None,
) -> None:
    """Upsert *docs* into *collection* with given *ids* and optional *metadatas*."""
    kwargs: dict = {"documents": docs, "ids": ids}
    if metadatas is not None:
        kwargs["metadatas"] = metadatas
    collection.upsert(**kwargs)


def retrieve(
    collection: Collection,
    query: str,
    n_results: int = 3,
    where: dict | None = None,
) -> list[str]:
    """Return the top *n_results* KB snippets most relevant to *query*.

    Args:
        where: Optional ChromaDB metadata filter (e.g. ``{"category": "billing"}``).
               Ignored if the collection has fewer documents than n_results.
    """
    if collection.count() == 0:
        return []

    kwargs: dict = {
        "query_texts": [query],
        "n_results": min(n_results, collection.count()),
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)
    return results["documents"][0] if results["documents"] else []
