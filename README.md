# supporttriage-ai

An AI-powered support ticket triage tool built with **IBM Granite** (via Ollama, fully local), **LangChain**, **ChromaDB**, and **Streamlit**.

Runs 100% locally — no API key, no account, no internet required after the initial model pull.

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
watsonx_config.py               →  shared Ollama Granite LLM factory
```

---

## Stack

| Component | Technology |
|---|---|
| LLM | IBM Granite 3.1 8B (`granite3.1:8b`) via Ollama (local) |
| Orchestration | LangChain |
| Vector store | ChromaDB (local, file-backed) |
| UI | Streamlit |
| Data model | Python dataclasses |

---

## Quick start

### 1. Install Ollama

Download and install from **https://ollama.com/download** (Windows / Mac / Linux).

Ollama runs as a background service automatically after install.

### 2. Pull the Granite model

```bash
ollama pull granite3.1:8b
```

This downloads ~5 GB once. After that everything runs offline.

> **Fallback:** if `granite3.1:8b` is unavailable, try `ollama pull granite3:8b`
> and set `OLLAMA_MODEL=granite3:8b` in your `.env`.

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure environment

```bash
cp .env.example .env
# Edit .env only if Ollama runs on a non-default host/port
```

No credentials needed — the defaults work out of the box.

### 5. Run the pipeline

```bash
python app.py
```

### 6. Launch the Streamlit review UI

```bash
streamlit run ui/review_app.py
```

---

## Stub / offline mode

If Ollama is not running, every LLM stage degrades gracefully — the pipeline still runs end-to-end using regex fallbacks and templated strings. `python app.py` works with zero config.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `granite3.1:8b` | Model name to use |
| `CHROMA_PERSIST_DIR` | No | `.chromadb` | ChromaDB storage path |

---

## Project structure

```
supporttriage-ai/
├── models.py                   # Ticket dataclass (shared contract)
├── watsonx_config.py           # Shared Ollama Granite LLM factory
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
