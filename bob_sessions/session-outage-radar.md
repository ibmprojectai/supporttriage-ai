# IBM Bob Session Log — Outage Radar

**Date:** 2026-07-04
**Task:** Build the cross-channel Outage Radar — real-time systemic failure detection from symptom clustering

**Files Modified:**
- `pipeline/extract.py`
- `intake/channels.py`
- `routing/router.py`
- `ui/review_app.py`

**Key Changes:**

- `pipeline/extract.py` — LLM prompt instructs Granite to return a `symptoms` array alongside `error_codes`; symptoms are short, normalised phrases like `"ERR-5001"`, `"dashboard timeout"`, `"SSO loop"`, `"cascade delete"` — designed to be deduplicated across tickets
- `intake/channels.py` — `generate_background_volume(15)` seeds the inbox with tickets that deliberately share symptoms across channels:
  - `BG-E001` (email): `symptoms=["ERR-5001", "dashboard timeout"]`
  - `BG-E005` (email): `symptoms=["ERR-5001", "API timeout", "dashboard timeout"]`
  - `BG-W001` (web): `symptoms=["ERR-5001", "dashboard timeout"]`
  - `BG-TG001` (telegram): `symptoms=["ERR-5001", "dashboard timeout"]`
  - Result: 4 tickets across 3 channels share `"ERR-5001"` — guaranteed outage trigger
- Outage Radar logic in `ui/review_app.py`:
  - After triage, builds `symptom_tickets: dict[str, list[Ticket]]` by iterating all processed tickets
  - `Counter` over all symptoms ranks by frequency
  - **≥ 3 tickets** with the same symptom → `🚨 SYSTEMIC OUTAGE DETECTED` banner rendered in dark red (`#3d0f0f` bg, `#fa4d56` border) with:
    - Count of affected tickets
    - Exact symptom string in bold
    - Affected channels listed with their colour-coded icons (e.g. `📧 EMAIL + 🌐 WEB + ✈️ TELEGRAM`)
    - List of affected ticket IDs as inline code chips
    - `⚡ Immediate action required` call-to-action
  - **== 2 tickets** → `⚠️ Pattern emerging` amber warning with channel info
  - **0 matches** → `✅ No outage patterns detected` green success
- Symptom deduplication within a single ticket: `set()` is applied before adding to the cross-ticket map so one ticket with repeated symptoms doesn't inflate the count
- Outage Radar is rendered in the **📊 Business Impact & Metrics** tab immediately after the confidence gauge, making it the first thing judges see after triage runs
- `routing/router.py` — `_CRITICAL_ERROR_PREFIXES` updated to include `"ERR-9"` so data-loss error codes also contribute to `severity_impact` scoring

**Outcome:** The Outage Radar automatically surfaces a `🚨 SYSTEMIC OUTAGE DETECTED` alert the moment three or more tickets across any combination of channels report the same symptom, turning reactive support into proactive incident detection.
