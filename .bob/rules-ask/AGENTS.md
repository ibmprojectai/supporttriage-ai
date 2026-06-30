# Ask Mode — Documentation Context (Non-Obvious)

- **`rag/` is not in the original project spec** but is required by `pipeline/draft.py`. It was added to isolate ChromaDB logic.
- **`app.py` is both the CLI entry point and the import target for `ui/review_app.py`.** The Streamlit UI re-uses the same module calls rather than duplicating pipeline logic.
- **`.env.example` is the authoritative list of env vars.** There are exactly five: `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID`, `WATSONX_MODEL_ID`, `CHROMA_PERSIST_DIR`.
- **Stub mode output is intentionally visible** — every skipped LLM stage prints a `[STAGE] STUB MODE` warning to stdout so developers know which stages ran live vs. fallback.
- **The mock ticket in `intake/zendesk_connector.py` deliberately contains PII** (email, phone, credit card number) so the PII redactor can be visually verified during development.
