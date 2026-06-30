# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Stack
Python 3.11+. LLM: `ibm-watsonx-ai` via `langchain-ibm`. Vector store: ChromaDB (local). UI: Streamlit.

## Run commands
```
python app.py                        # full end-to-end pipeline (stub mode, no .env needed)
streamlit run ui/review_app.py       # agent review UI
pip install -r requirements.txt      # install deps
```

## Stub / mock mode
**Every LLM stage degrades gracefully** — `classify`, `extract`, `summarize`, and `draft_reply` all call `get_llm()` from `watsonx_config.py`. When `WATSONX_*` env vars are missing, `get_llm()` returns `None` and each stage falls back silently (regex extraction, templated strings). `python app.py` must work with zero config.

## Env vars
Copy `.env.example` → `.env`. Five vars:
- `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID` — required for live LLM calls
- `WATSONX_MODEL_ID` — defaults to `ibm/granite-3-3-8b-instruct` when unset
- `CHROMA_PERSIST_DIR` — defaults to `.chromadb`

## Critical architectural constraints

**PII redaction must run before any pipeline stage.** `app.py` calls `redact()` on `ticket.body` and all `ticket.thread` entries immediately after intake, before the classify/extract/summarize/draft chain.

**`watsonx_config.py` is the single source of credentials.** Pipeline modules (`classify`, `extract`, `summarize`, `draft`) must `from watsonx_config import get_llm` — they must NOT read `WATSONX_*` env vars directly.

**`rag/` is a required 7th package** not in the original spec. `pipeline/draft.py` depends on `rag.store.retrieve` and `rag.store.init_store`. Do not inline ChromaDB calls into the pipeline.

**`Ticket` is a plain `dataclasses.dataclass`** (not Pydantic). All 12 fields have defaults so partial construction is valid. Field ownership is documented in `models.py` — set fields only in the designated stage.

## Ticket field ownership
| Field | Set by |
|---|---|
| `id`, `sender`, `subject`, `body`, `thread`, `account`, `product` | `intake/zendesk_connector.py` |
| `error_codes` | `pipeline/extract.py` |
| `category`, `priority` | `pipeline/classify.py` |
| `summary` | `pipeline/summarize.py` |
| `draft_reply` | `pipeline/draft.py` |

## Gotchas discovered during install
- **`langchain 1.x` removed `langchain.prompts`** — use `from langchain_core.prompts import PromptTemplate` in all pipeline modules (already corrected in the codebase).
- **Python PATH not set by installer on this machine** — run via full path `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe` or add `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Scripts` to PATH for `streamlit` to work from the terminal.

## Module map
```
watsonx_config.py     get_llm() → WatsonxLLM | None
models.py             Ticket dataclass
intake/               zendesk_connector.fetch_ticket()
guardrails/           pii_redactor.redact()
pipeline/             classify() → extract() → summarize() → draft_reply()
rag/                  store.init_store(), store.retrieve()
routing/              router.route() → {queue, tags, escalate}
ui/                   review_app.py  (streamlit run ui/review_app.py)
app.py                orchestrates all of the above
```
