# supporttriage-ai

An AI-powered support ticket triage tool built with **IBM Granite** (via watsonx.ai), **LangChain**, **ChromaDB**, and **Streamlit**.

---

## What it does

Automatically triages incoming support tickets through a 4-stage AI pipeline:

1. **Intake** — fetches ticket from Zendesk (stub mode included)
2. **Guardrails** — redacts PII (emails, phone numbers, credit cards) before any LLM call
3. **Classify** — detects category (authentication, billing, performance…) and priority (critical → low)
4. **Extract** — pulls error codes and enriches account/product fields
5. **Summarize** — condenses the full ticket thread into 2–3 sentences
6. **Draft Reply** — generates a grounded reply using RAG (ChromaDB knowledge base)
7. **Route** — assigns the ticket to the correct support queue with tags

Results are surfaced in a **Streamlit agent-review UI** where a human agent can edit the draft before approving.

---

## Architecture

```
intake/zendesk_connector.py     →  Ticket
guardrails/pii_redactor.py      →  redact PII
pipeline/classify.py            →  category + priority
pipeline/extract.py             →  error_codes + account/product
pipeline/summarize.py           →  summary
pipeline/draft.py               →  draft_reply  (RAG via ChromaDB)
routing/router.py               →  queue + tags + escalate flag
ui/review_app.py                →  Streamlit agent review UI
watsonx_config.py               →  shared IBM Granite LLM factory
```

---

## Stack

| Component | Technology |
|---|---|
| LLM | IBM Granite 3 (`ibm/granite-3-3-8b-instruct`) via watsonx.ai |
| Orchestration | LangChain |
| Vector store | ChromaDB (local, file-backed) |
| UI | Streamlit |
| Data model | Python dataclasses |

---

## Quick start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in your watsonx.ai credentials in .env
```

### 3. Run the pipeline (stub mode — no credentials needed)
```bash
python app.py
```

### 4. Launch the Streamlit review UI
```bash
streamlit run ui/review_app.py
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `WATSONX_API_KEY` | Yes (live mode) | — | IBM Cloud API key |
| `WATSONX_URL` | Yes (live mode) | — | watsonx.ai endpoint |
| `WATSONX_PROJECT_ID` | Yes (live mode) | — | watsonx.ai project GUID |
| `WATSONX_MODEL_ID` | No | `ibm/granite-3-3-8b-instruct` | Foundation model ID |
| `CHROMA_PERSIST_DIR` | No | `.chromadb` | ChromaDB storage path |

> **Stub mode:** if `WATSONX_*` credentials are absent, every LLM stage degrades gracefully — the pipeline still runs end-to-end using regex fallbacks and templated strings.

---

## Project structure

```
supporttriage-ai/
├── models.py                   # Ticket dataclass (shared contract)
├── watsonx_config.py           # Shared IBM Granite LLM factory
├── app.py                      # Orchestration entry point
├── requirements.txt
├── .env.example                # Environment variable template
├── intake/
│   └── zendesk_connector.py    # Zendesk email connector stub
├── pipeline/
│   ├── classify.py             # LLM: category + priority
│   ├── extract.py              # LLM: error codes + enrichment
│   ├── summarize.py            # LLM: ticket summary
│   └── draft.py                # LLM + RAG: draft reply
├── rag/
│   └── store.py                # ChromaDB wrapper
├── routing/
│   └── router.py               # Auto-tag + queue assignment
├── guardrails/
│   └── pii_redactor.py         # PII redaction
└── ui/
    └── review_app.py           # Streamlit agent review UI
```

---

## Ticket data model

| Field | Type | Set by |
|---|---|---|
| `id`, `sender`, `subject`, `body`, `thread`, `account`, `product` | `str` / `list` | intake |
| `error_codes` | `list[str]` | extract |
| `category`, `priority` | `str` | classify |
| `summary` | `str` | summarize |
| `draft_reply` | `str` | draft |

---

## License

MIT
