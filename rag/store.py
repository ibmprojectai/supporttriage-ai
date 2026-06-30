"""ChromaDB wrapper — initialise, seed, and query the knowledge-base vector store.

All ChromaDB interaction is isolated here so pipeline modules stay decoupled from the
underlying store implementation.
"""

from __future__ import annotations

import os

import chromadb
from chromadb import Collection

_COLLECTION_NAME = "support_kb"

# Seed documents used during stub/dev runs so draft_reply has context to retrieve.
_SEED_DOCS = [
    (
        "kb-001",
        "ERR-4021 indicates an expired session token. Ask the user to clear browser "
        "cookies, log out completely, and attempt a fresh login. If the issue persists "
        "after a full cache clear, escalate to Tier-2 authentication team.",
    ),
    (
        "kb-002",
        "Password reset emails can be delayed up to 15 minutes due to spam-filter "
        "queuing. Advise the user to check their junk/spam folder and whitelist "
        "noreply@datapilot.example.com.",
    ),
    (
        "kb-003",
        "DataPilot Pro accounts locked after 5 failed login attempts. An admin can "
        "unlock via the Account Management Console → Users → Unlock Account. "
        "Self-service unlock is available after a 30-minute cooldown.",
    ),
    (
        "kb-004",
        "For billing-related access issues on ACC-series accounts, verify that the "
        "subscription is active in the billing portal before troubleshooting auth errors.",
    ),
    (
        "kb-005",
        "Standard SLA for login/authentication issues is P2 (4-hour response). "
        "Escalate to P1 if more than 5 users on the same account are affected.",
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
        print(f"[rag/store] Seeded collection '{_COLLECTION_NAME}' with {len(ids)} KB documents.")

    return collection


def add_documents(collection: Collection, docs: list[str], ids: list[str]) -> None:
    """Upsert *docs* into *collection* with the given *ids*."""
    collection.upsert(documents=docs, ids=ids)


def retrieve(collection: Collection, query: str, n_results: int = 3) -> list[str]:
    """Return the top *n_results* KB snippets most relevant to *query*."""
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    return results["documents"][0] if results["documents"] else []
