# scaffold-plan.md

## Overview

Scaffold `supporttriage-ai` — a Python AI support-ticket triage tool — from a blank workspace.
The project receives support tickets (via a Zendesk email connector stub), runs them through a
four-stage LLM pipeline (classify → extract → summarize → draft), routes them to queues, applies
PII redaction guardrails, and surfaces the result in a Streamlit agent-review UI.

The LLM backend is `ibm-watsonx-ai` using **IBM Granite 3** as the default foundation model
(`ibm/granite-3-3-8b-instruct`). The model ID is configurable via `WATSONX_MODEL_ID` env var.
A shared `watsonx_config.py` module constructs the `WatsonxLLM` instance used by all four
pipeline stages. RAG context is retrieved from a local ChromaDB vector store. `langchain`
provides chain orchestration across all pipeline stages. `app.py` is the single orchestration
entry point that wires all modules together and drives a mock ticket end-to-end.

---

## Data Model

A single `Ticket` dataclass (defined in `models.py` at the project root) is the shared contract
passed between every module:

| Field | Type | Set by |
|---|---|---|
| `id` | str | intake |
| `sender` | str | intake |
| `subject` | str | intake |
| `body` | str | intake |
| `thread` | list[str] | intake |
| `account` | str | intake |
| `product` | str | intake |
| `error_codes` | list[str] | extract |
| `category` | str | classify |
| `priority` | str | classify |
| `summary` | str | summarize |
| `draft_reply` | str | draft |

---

## Directory Layout (target state)

```
supporttriage-ai/
├── models.py                   # Ticket dataclass
├── watsonx_config.py           # Shared WatsonxLLM factory (model id, creds from env)
├── app.py                      # Orchestration entry point
├── requirements.txt
├── .env.example                # Template showing required env vars
├── intake/
│   ├── __init__.py
│   └── zendesk_connector.py    # Zendesk email connector stub
├── pipeline/
│   ├── __init__.py
│   ├── classify.py             # LLM: sets category + priority
│   ├── extract.py              # LLM: sets error_codes + account/product enrichment
│   ├── summarize.py            # LLM: sets summary
│   └── draft.py                # LLM + RAG: sets draft_reply
├── routing/
│   ├── __init__.py
│   └── router.py               # Auto-tag + queue assignment
├── guardrails/
│   ├── __init__.py
│   └── pii_redactor.py         # PII redaction (regex + LLM fallback stub)
├── ui/
│   ├── __init__.py
│   └── review_app.py           # Streamlit agent-review interface
└── rag/
    ├── __init__.py
    └── store.py                # ChromaDB wrapper (index + retrieve)
```

> `rag/` is a support module used by `pipeline/draft.py`. It is not listed in the original spec
> but is required to isolate ChromaDB logic cleanly.

---

## Sub-Tasks

### Sub-Task 1 — Project boilerplate and data model
**Status:** `[ ] pending`

**Intent:** Lay the foundation: directory tree, `requirements.txt`, and the `Ticket` dataclass
that every subsequent module imports.

**Expected Outcomes:**
- All directories and `__init__.py` files exist.
- `requirements.txt` lists `langchain`, `langchain-ibm`, `ibm-watsonx-ai`, `chromadb`,
  `streamlit`, `pydantic`, `python-dotenv`.
- `models.py` defines `Ticket` as a `dataclasses.dataclass` with all 12 fields, sensible
  defaults (empty string / empty list), and a `__repr__` that elides `body` for readability.

**Todo List:**
1. Create all package directories with `__init__.py` stubs: `intake/`, `pipeline/`, `routing/`,
   `guardrails/`, `ui/`, `rag/`.
2. Write `requirements.txt` with pinned-but-flexible versions (e.g. `langchain>=0.2`).
3. Write `models.py` with the `Ticket` dataclass.

**Relevant Context:** No existing files — pure greenfield.

---

### Sub-Task 2 — Intake: Zendesk email connector stub
**Status:** `[ ] pending`

**Intent:** Provide a realistic-looking connector that production code can swap for a real
Zendesk API call. The stub returns a hardcoded mock `Ticket` so the rest of the pipeline can
run without credentials.

**Expected Outcomes:**
- `intake/zendesk_connector.py` exposes `fetch_ticket(ticket_id: str) -> Ticket`.
- When `ticket_id == "mock"` (or any ID in stub mode), returns a fully populated mock `Ticket`
  with realistic sample data (sender, subject, body, thread, account, product).
- A `TODO` comment marks where the real Zendesk REST call would go.

**Relevant Context:** `models.py` → `Ticket`.

---

### Sub-Task 3 — Guardrails: PII redactor
**Status:** `[ ] pending`

**Intent:** Redact PII from ticket text before it reaches the LLM, ensuring no customer
personal data is sent to the model. Implemented as a pure-Python regex pass (emails, phone
numbers, credit card patterns) with a stub hook for an LLM-based fallback.

**Expected Outcomes:**
- `guardrails/pii_redactor.py` exposes `redact(text: str) -> str`.
- Replaces emails → `[EMAIL]`, phone numbers → `[PHONE]`, credit-card-like numbers → `[CC]`.
- A `TODO` comment marks the LLM-fallback hook.
- `app.py` calls `redact()` on `ticket.body` and each `ticket.thread` entry before the
  pipeline runs.

**Relevant Context:** No LLM dependency — pure stdlib `re`.

---

### Sub-Task 4 — RAG store (ChromaDB wrapper)
**Status:** `[ ] pending`

**Intent:** Isolate all ChromaDB logic in one place so pipeline steps can retrieve relevant
knowledge-base snippets without knowing the underlying store.

**Expected Outcomes:**
- `rag/store.py` exposes:
  - `init_store(persist_dir: str = ".chromadb") -> chromadb.Collection`
  - `add_documents(collection, docs: list[str], ids: list[str]) -> None`
  - `retrieve(collection, query: str, n_results: int = 3) -> list[str]`
- On first call `init_store` seeds the collection with 3–5 hardcoded KB snippets so the
  draft stage has something to retrieve during mock runs.
- Uses `chromadb.PersistentClient` so state survives across runs.

**Relevant Context:** Used by `pipeline/draft.py` (Sub-Task 6).

---

### Sub-Task 5 — Shared watsonx config + Pipeline: classify and extract
**Status:** `[ ] pending`

**Intent:** Implement the shared `watsonx_config.py` module (Granite default, configurable model
ID) AND the first two LLM pipeline stages. Each stage imports `get_llm()` — it does NOT read
credentials directly.

**Expected Outcomes:**
- `watsonx_config.py` at project root exposes `get_llm() -> WatsonxLLM | None`.
  - Reads `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID` from env via `python-dotenv`.
  - Reads `WATSONX_MODEL_ID`; defaults to `"ibm/granite-3-3-8b-instruct"` when unset.
  - Returns `None` (does not raise) when any required credential is absent.
- `.env.example` documents all five env vars with placeholder values:
  `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID`, `WATSONX_MODEL_ID`, `CHROMA_PERSIST_DIR`.
- `pipeline/classify.py` exposes `classify(ticket: Ticket) -> Ticket`.
  - Calls `get_llm()`; if `None`, prints a stub-mode warning and returns ticket unchanged.
  - Sends `subject + body` via a `PromptTemplate` chain; parses `category` and `priority` from response.
- `pipeline/extract.py` exposes `extract(ticket: Ticket) -> Ticket`.
  - Calls `get_llm()`; same stub-mode fallback.
  - Sends `body`; parses `error_codes` list and enriches `account`/`product` if currently empty.
- Both use `langchain.prompts.PromptTemplate`. Neither reads env vars directly.

**Relevant Context:** `models.py` → `Ticket`; `watsonx_config.py` → `get_llm`; `.env` (not committed).

---

### Sub-Task 6 — Pipeline: summarize and draft
**Status:** `[ ] pending`

**Intent:** Implement the last two LLM pipeline stages. `summarize` condenses the ticket;
`draft` generates a reply grounded by RAG context retrieved from ChromaDB.

**Expected Outcomes:**
- `pipeline/summarize.py` exposes `summarize(ticket: Ticket) -> Ticket`.
  - Calls `get_llm()`; stub-mode fallback returns ticket unchanged with placeholder summary.
  - Sends thread + body to the LLM; sets `ticket.summary` (2–3 sentence condensation).
- `pipeline/draft.py` exposes `draft_reply(ticket: Ticket, collection) -> Ticket`.
  - Calls `get_llm()`; stub-mode fallback sets a `"[STUB] Draft reply not available"` placeholder.
  - Retrieves top-3 KB snippets from ChromaDB using `ticket.summary` as the query.
  - Constructs a RAG prompt: `[context snippets] + [summary] → draft reply`.
  - Sets `ticket.draft_reply`.
- Both import `get_llm` from `watsonx_config` — do NOT duplicate credential reading.

**Relevant Context:** `rag/store.py` → `retrieve`; `models.py` → `Ticket`; `watsonx_config.py` → `get_llm`.

---

### Sub-Task 7 — Routing: auto-tag and queue assignment
**Status:** `[ ] pending`

**Intent:** Map a classified ticket to a support queue and attach tags, without any LLM call —
this is deterministic business logic driven by `ticket.category` and `ticket.priority`.

**Expected Outcomes:**
- `routing/router.py` exposes `route(ticket: Ticket) -> dict`.
- Returns a dict: `{"queue": str, "tags": list[str], "escalate": bool}`.
- Priority `"critical"` always sets `escalate=True`.
- Category → queue mapping is a simple dict constant at the top of the file (easy to extend).

**Relevant Context:** `models.py` → `Ticket`; no LLM dependency.

---

### Sub-Task 8 — Orchestration entry point (`app.py`)
**Status:** `[ ] pending`

**Intent:** Wire all modules together into a single runnable script that drives a mock ticket
end-to-end and prints a structured summary.

**Expected Outcomes:**
- `app.py` performs this sequence:
  1. `fetch_ticket("mock")` → `Ticket`
  2. Redact PII from `body` and each `thread` entry
  3. `classify(ticket)` → sets `category`, `priority`
  4. `extract(ticket)` → sets `error_codes`
  5. `summarize(ticket)` → sets `summary`
  6. `init_store()` + `draft_reply(ticket, collection)` → sets `draft_reply`
  7. `route(ticket)` → routing dict
  8. Print all `Ticket` fields and routing result
- Running `python app.py` completes without error even with no `.env` (stub/mock mode).

**Relevant Context:** All modules above; `rag/store.py` seeded in Sub-Task 4.

---

### Sub-Task 9 — Streamlit agent-review UI
**Status:** `[ ] pending`

**Intent:** Give a human support agent a simple browser UI to inspect and approve/edit the
AI-generated triage output before it is sent.

**Expected Outcomes:**
- `ui/review_app.py` is a self-contained Streamlit app.
- On load it imports `app.py`'s pipeline logic (or re-uses the same module calls) and runs
  the mock ticket through the pipeline.
- Displays: `category`, `priority`, `error_codes`, `summary`, `draft_reply`, routing info.
- `draft_reply` is shown in an editable `st.text_area` so an agent can revise before
  "approving" (approve button just prints to console in stub mode).
- Run with `streamlit run ui/review_app.py`.

**Relevant Context:** All prior modules; no new LLM calls needed — reuses pipeline output.

---

### Sub-Task 10 — AGENTS.md
**Status:** `[ ] pending`

**Intent:** Document the non-obvious project conventions for future AI assistants.

**Expected Outcomes:**
- `AGENTS.md` at project root covers: run commands, stub-mode behaviour, env vars, Ticket
  field ownership, the `rag/` module not being in the original spec but required, and
  the PII redaction ordering constraint (must run before any LLM call).
- Mode-specific files at `.bob/rules-agent/AGENTS.md`, `.bob/rules-ask/AGENTS.md`,
  `.bob/rules-plan/AGENTS.md`.

---
