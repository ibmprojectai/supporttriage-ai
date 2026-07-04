# supporttriage-ai — Agentic Incident Command Center

An AI-powered support ticket triage system built with **IBM Granite** (via Ollama), **LangChain**, **ChromaDB**, and **Streamlit**. Submitted to the **IBM AI Builders Challenge — July 2026** under the Wildcard theme: *Build Intelligent Systems for the Future of Work*.

---

## What it does

Most support triage tools just classify and route tickets. `supporttriage-ai` goes further — it measures its own confidence, detects emerging outages across ticket clusters, and grounds every reply in a verified knowledge base.

The system runs incoming support tickets through a 7-stage async AI pipeline:

1. **Intake** — fetches ticket from Zendesk (stub mode included)
2. **Guardrails** — redacts PII (emails, phones, card numbers) before any LLM call
3. **Classify** — detects category and priority, outputs a confidence score (0.0–1.0)
4. **Extract** — pulls error codes, symptoms, and enriches account/product fields
5. **Summarize** — condenses the full ticket thread into 2–3 sentences
6. **Draft Reply** — generates a grounded reply using metadata-filtered RAG (ChromaDB)
7. **Route** — assigns ticket to the correct queue; low-confidence tickets are automatically escalated to human review

Results are surfaced in a **Streamlit dashboard** with two views: an executive overview (confidence metrics, ticket volume by category, outage alerts) and a per-ticket agent review screen.

---

## Key Innovations

| Feature | Description |
|---|---|
| **Confidence Scoring** | Granite outputs a 0.0–1.0 confidence score per classification. Tickets below 0.75 are routed to `human-review` automatically. |
| **Symptom Extraction** | The extract stage pulls specific symptoms (e.g., "session expires immediately") enabling outage pattern detection. |
| **Metadata-Filtered RAG** | ChromaDB retrieval is filtered by `category` and `product` to ensure grounded, hallucination-resistant replies. |
| **Async Pipeline** | All pipeline stages are `async def` using `asyncio.to_thread` and LangChain `ainvoke` for production-grade scalability. |
| **Severity Scoring** | Router calculates a 0.0–10.0 severity impact score from priority and critical error codes. |

---

## Architecture

```
intake/zendesk_connector.py     →  Ticket
guardrails/pii_redactor.py      →  redact PII
pipeline/classify.py            →  category + priority + confidence_classify
pipeline/extract.py             →  error_codes + symptoms + confidence_extract
pipeline/summarize.py           →  summary
pipeline/draft.py               →  draft_reply (metadata-filtered RAG via ChromaDB)
routing/router.py               →  queue + tags + escalate + requires_human_review + severity_impact
ui/review_app.py                →  Streamlit dashboard (📊 Dashboard + 🎫 Ticket Review)
watsonx_config.py               →  shared Ollama Granite LLM factory
```

---

## Stack

| Component | Technology |
|---|---|
| LLM | IBM Granite 3.1 8B via Ollama (local) |
| Orchestration | LangChain (async) |
| Vector store | ChromaDB (metadata-filtered) |
| UI | Streamlit (two-tab dashboard) |
| Data model | Python dataclasses |
| AI Development Partner | IBM Bob |

---

## Quick Start

### 1. Install Ollama

Download from **https://ollama.com/download** and install.

### 2. Pull the Granite model

```bash
ollama pull granite3.1:8b
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the pipeline

```bash
python app.py
```

### 5. Launch the Streamlit dashboard

```bash
streamlit run ui/review_app.py
```

---

## Stub / Offline Mode

If Ollama is not running, every LLM stage degrades gracefully — the pipeline still runs end-to-end using regex fallbacks and templated strings. Confidence defaults to `0.5`, which correctly triggers the human-review escalation path. `python app.py` works with zero configuration.

---

## IBM AI Builders Challenge — July 2026

**Theme:** Wildcard — Build Intelligent Systems for the Future of Work

This project demonstrates how IBM Bob and IBM Granite can transform reactive support ticket triage into a proactive, agentic incident management system. IBM Bob was used as the primary development partner throughout the build — architecting the confidence scoring system, async pipeline refactor, metadata-driven RAG improvements, and executive dashboard UI.

See `/bob_sessions/` for the exported IBM Bob session reports.

---

## License

MIT
