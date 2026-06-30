# Plan Mode — Architectural Constraints (Non-Obvious)

- **PII redaction is a mandatory pre-processing step, not a pipeline stage.** It runs in `app.py` before the pipeline chain. Any future pipeline stage added between intake and classify must also receive redacted text — enforce this in `app.py`, not inside the stages.
- **`get_llm()` must remain a factory function that returns `None` on failure** (not raises). All pipeline callers depend on this contract for safe stub-mode operation.
- **The Ticket dataclass uses field ownership as an implicit interface.** Each stage reads upstream fields and writes only its own. Violating this (e.g. classify overwriting `error_codes`) breaks the extract stage's enrichment logic.
- **ChromaDB collection is created once and passed into `draft_reply()`** — it is not created inside the function. If redesigning the pipeline, keep the collection as a dependency injection parameter so tests can substitute a mock collection.
- **Routing is a pure function with no side effects.** Any queuing/ticketing system integration belongs in `app.py` after `route()` returns, not inside `routing/router.py`.
- **The Streamlit UI is intentionally read-only** with respect to the pipeline — it calls the same functions as `app.py` but does not modify the Ticket after the pipeline runs. The edited draft exists only in Streamlit session state.
