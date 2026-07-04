# Enterprise Upgrade Plan — Phase 1: Rendering Fix + Channel Wiring

## Top-Level Overview

Two quick-win tracks before the full enterprise model rebuild:

1. **Rendering fix** — eliminate all raw HTML leaking from `st.markdown()` triple-quoted f-strings with embedded newlines. Root cause confirmed: Streamlit's markdown renderer treats newlines inside a `st.markdown()` call as paragraph breaks, fragmenting the HTML. The fix is to convert every affected block to a single-line concatenated string with `.format()` (no embedded newlines, no f-string).

2. **Channel wiring verification** — confirm Telegram polling, Gmail IMAP, and the web form each work end-to-end, and patch any gaps (IMAP not marking emails read, Telegram tickets missing product/account defaults, web form smoke test).

---

## Sub-Task 1 — Fix All Multiline st.markdown() HTML Blocks

**Intent:** Every `st.markdown(f"""...""", unsafe_allow_html=True)` call that has embedded newlines in the HTML string is a potential rendering bug. Replace them all with single-line string concatenation + `.format()` so the HTML is always one unbroken string.

**Affected locations in `ui/review_app.py`** (confirmed by code search):
| Line | Block | Currently broken? |
|---|---|---|
| 594 | Inbox ticket card | ✅ Yes — user-reported |
| 292 | Sidebar channel status | Possibly |
| 329 | Sidebar queue stats | Possibly |
| 719 | Dashboard confidence gauge | Possibly |
| 769 | Outage critical banner | Possibly |
| 782 | Outage warning banner | Possibly |

**Expected Outcomes:**
- Inbox cards render as clean styled cards with no raw HTML text visible
- All other dashboard blocks (gauge, outage banners, sidebar) render correctly
- No `</div>` or attribute strings visible on screen

**Todo List:**
1. In `ui/review_app.py`, convert the inbox ticket card (line 594) triple-quoted f-string to a single-line `.format()` string
2. Convert the sidebar channel status block (line 292) the same way
3. Convert the sidebar queue stats block (line 329) the same way
4. Convert the dashboard confidence gauge block (line 719) the same way
5. Convert the outage critical banner (line 769) the same way
6. Convert the outage warning banner (line 782) the same way
7. Run `pytest tests/ -q` — must still be 64/64

**Relevant Context:**
- Pattern to use: build the HTML as a Python string concatenation (no newlines in the string value) then call `st.markdown(html_string, unsafe_allow_html=True)`
- The HITL card (line 865) already uses concatenated f-strings — use that as the reference pattern
- All user-supplied fields must still be `_html.escape()`d before injection (already done)
- Use `.format()` not f-strings to stay Python 3.14 safe (no escaped quotes inside expressions)

**Status:** `[ ] pending`

---

## Sub-Task 2 — Verify and Patch Telegram Wiring

**Intent:** Confirm the Telegram fetch button works end-to-end. Patch two known gaps: Telegram tickets arrive with no `product` or `account` set (empty strings), and the channel label in the card correctly identifies them.

**Known gaps from code research:**
- `fetch_telegram_updates()` sets only: `id`, `sender`, `subject`, `body`, `channel="telegram"`, `status="untriaged"` — `product` and `account` remain `""`
- This is fine for triage (the LLM classifies without product), but the HITL card's AI Reasoning table will show empty product

**Expected Outcomes:**
- Telegram fetch button works when a valid token is saved in Settings
- Telegram tickets appear in the inbox with correct channel colour and icon
- After triage, Telegram tickets route correctly through classify → extract → summarize → draft

**Todo List:**
1. Manually test: go to ⚙️ Settings → enter a valid Telegram bot token → Save & Test → should show `✅ Connected to @botname`
2. Send a test message to the bot
3. Go to 📥 Inbox → click "✈️ Fetch Telegram" → ticket should appear
4. Click "Run AI Triage" → ticket should process without error
5. If any error surfaces, patch it

**Relevant Context:**
- `intake/channels.py` `fetch_telegram_updates()` — lines 38–121
- Telegram API call: `https://api.telegram.org/bot{token}/getUpdates`
- The `_REQUESTS_AVAILABLE` guard means if `requests` isn't installed, polling silently returns `[]` — `requirements.txt` already has `requests>=2.28`

**Status:** `[ ] pending`

---

## Sub-Task 3 — Verify and Patch Gmail IMAP Wiring

**Intent:** Confirm Gmail fetch works end-to-end. Fix the known gap: emails are fetched but never marked as read, so clicking "Fetch Gmail" repeatedly will keep re-importing the same emails.

**Known gaps from code research:**
- `fetch_unread_emails()` does NOT call `mail.store()` to mark fetched emails as `\Seen` — every fetch returns the same unread emails again
- IMAP search is filtered to `(UNSEEN SUBJECT "[SUPPORT-TICKET]")` so only web-form tickets come through (correct)

**Expected Outcomes:**
- Gmail fetch works when valid credentials are saved
- Fetched emails are marked as read in Gmail so they don't re-appear on next fetch
- If no `[SUPPORT-TICKET]` emails exist, `st.info("No unread emails found.")` shows correctly

**Todo List:**
1. In `intake/channels.py` `fetch_unread_emails()`, after fetching each message add `mail.store(mid, '+FLAGS', '\\Seen')` to mark it read
2. Run `pytest tests/ -q` — 64/64
3. Manually test with a real Gmail account (send a `[SUPPORT-TICKET]` email from another address, then fetch)

**Relevant Context:**
- `intake/channels.py` lines 128–199
- The IMAP search at line 151: `'(UNSEEN SUBJECT "[SUPPORT-TICKET]")'`
- `mail.store(mid, '+FLAGS', '\\Seen')` must be called while the mailbox is still selected, before `mail.logout()`

**Status:** `[ ] pending`

---

## Sub-Task 4 — Smoke Test Web Form End-to-End

**Intent:** Verify the customer web form (`ui/web_form.py`) submits correctly in both demo mode (no credentials) and live mode (GMAIL_USER + GMAIL_APP_PASSWORD set).

**Known gaps from code research:**
- `ui/web_form.py` correctly calls `st.set_page_config` first — no crash risk
- Demo mode path: if no email credentials, shows success card without sending — correct
- Live mode: sends via `smtplib.SMTP_SSL("smtp.gmail.com", 465)` — correct

**Expected Outcomes:**
- `streamlit run ui/web_form.py --server.port 8502` launches without error
- Submitting with empty required fields shows the error message
- Submitting in demo mode shows the green success card
- (If credentials available) Submitting in live mode sends an email with subject `[SUPPORT-TICKET] ...`

**Todo List:**
1. Launch `streamlit run ui/web_form.py --server.port 8502` locally
2. Test empty-field validation — should show `st.error("Please fill in all required fields...")`
3. Test demo mode submit (no `.env` credentials) — should show success card
4. Click "Submit Another Request" — should reset to blank form
5. If any issue found, patch it

**Relevant Context:**
- `ui/web_form.py` — the standalone customer portal
- `intake/web_form.py` — `submit_web_ticket()` SMTP function
- Demo mode trigger: `dest = _os.getenv("SUPPORT_EMAIL", _os.getenv("GMAIL_USER", ""))` — if both empty, skips email send and shows success

**Status:** `[ ] pending`

---

## Sub-Task 5 — Commit, Push, Update Session Log

**Intent:** Land all fixes in a single clean commit, update the session log with Task 32 entry and commit hash.

**Todo List:**
1. Run `pytest tests/ -q` — confirm 64/64
2. `git add ui/review_app.py intake/channels.py`
3. `git commit -m "Fix all multiline HTML st.markdown blocks + mark IMAP emails read after fetch"`
4. `git push origin main`
5. Update `bob_sessions/session-2026-07-04.html` with Task 32 entry + real commit hash
6. Push the log update

**Status:** `[ ] pending`
