# Agent Mode — Coding Rules (Non-Obvious)

- **Never read `WATSONX_*` env vars in pipeline modules.** Always `from watsonx_config import get_llm` and check for `None` before building a chain.
- **Default model ID is `ibm/granite-3-3-8b-instruct`.** It lives in `watsonx_config._DEFAULT_MODEL_ID`. Override via `WATSONX_MODEL_ID` env var — do not hardcode model IDs elsewhere.
- **All four pipeline stages must have a stub-mode path** that runs without raising when `get_llm()` returns `None`. Stub output should clearly signal `[STUB]` or `[PLACEHOLDER]`.
- **ChromaDB must be accessed only through `rag/store.py`.** Direct `chromadb` imports in pipeline files are forbidden.
- **`pipeline/extract.py` has a JSON parse fallback** — the Granite model sometimes wraps JSON in markdown fences; the module strips them with regex before `json.loads`.
- **Routing is intentionally LLM-free** — `routing/router.py` uses only dict lookup. Do not add LLM calls there.
- **`ui/review_app.py` inserts the project root into `sys.path`** at the top so it can import project modules when launched via `streamlit run ui/review_app.py` from any directory. Keep this path-fixup line.
- **`rag/store.init_store()` auto-seeds** the ChromaDB collection with 5 KB documents on first call. Do not call `add_documents()` again for the same IDs — ChromaDB `upsert` is idempotent.
