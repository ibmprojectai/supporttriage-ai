"""SupportTriage AI — Multi-Channel Agentic Support Operations Center.

Architecture
------------
Sidebar: Live connector inputs (Telegram token, Gmail credentials)
State:   st.session_state.inbox     — untriaged Ticket objects
         st.session_state.processed — list of (Ticket, routing_dict) after triage
         st.session_state.log       — execution log string

View A — Triage Queue (inbox non-empty or processed empty):
  Shows inbox cards → "🚀 Run AI Triage" button → async batch pipeline

View B — Operations Dashboard (after triage, 3 tabs):
  Tab 1: 📊 Business Impact & Metrics  (KPIs, Outage Radar)
  Tab 2: 🧑‍💻 Human-in-the-Loop Queue  (editable drafts, approve button)
  Tab 3: 🟢 Auto-Routed Log           (read-only table)

Launch:
    streamlit run ui/review_app.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SupportTriage AI — Ops Center",
    page_icon="🎫",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
/* Base */
.stApp { background-color: #0f0f0f; color: #e8e8e8; }
section[data-testid="stSidebar"] { background-color: #161616; border-right: 1px solid #2a2a2a; }

/* Typography */
h1, h2, h3, h4 { color: #f4f4f4; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #1a1a1a; border-radius: 8px;
    padding: 4px; gap: 4px; border: 1px solid #2a2a2a; }
.stTabs [data-baseweb="tab"] { color: #8d8d8d; font-size: 0.9rem; font-weight: 500;
    border-radius: 6px; padding: 8px 16px; border: none; background: transparent; }
.stTabs [aria-selected="true"] { background: #0f62fe !important; color: #fff !important; }

/* Metric cards */
[data-testid="metric-container"] { background: #1a1a1a; border: 1px solid #2a2a2a;
    border-radius: 10px; padding: 1rem 1.2rem; }
[data-testid="stMetricLabel"] { color: #8d8d8d !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #f4f4f4 !important; font-size: 1.7rem !important;
    font-weight: 700 !important; }

/* Buttons */
.stButton > button { background: #0f62fe; color: #fff; border: none; border-radius: 6px;
    padding: 0.5rem 1.2rem; font-weight: 600; font-size: 0.9rem; }
.stButton > button:hover { background: #0353e9; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1a1a1a !important; color: #f4f4f4 !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important; }

/* Expanders */
.streamlit-expanderHeader { background: #1a1a1a !important; color: #f4f4f4 !important;
    border-radius: 8px !important; border: 1px solid #2a2a2a !important; }

/* Divider */
hr { border-color: #2a2a2a !important; }

/* Channel badges */
.badge { display:inline-block; padding:2px 9px; border-radius:20px;
    font-size:0.72rem; font-weight:700; margin-right:4px; }
.badge-telegram { background:#229ed9; color:#fff; }
.badge-email    { background:#0043ce; color:#fff; }
.badge-web      { background:#6929c4; color:#fff; }

/* Priority badges */
.badge-critical { background:#fa4d56; color:#fff; }
.badge-high     { background:#f1c21b; color:#161616; }
.badge-medium   { background:#0f62fe; color:#fff; }
.badge-low      { background:#42be65; color:#161616; }

/* Status badges */
.badge-auto-routed   { background:#42be65; color:#161616; }
.badge-human-review  { background:#f1c21b; color:#161616; }
.badge-escalated     { background:#fa4d56; color:#fff; }
.badge-untriaged     { background:#393939; color:#8d8d8d; }

/* Ticket inbox cards */
.inbox-card { background:#1a1a1a; border:1px solid #2a2a2a; border-radius:10px;
    padding:0.85rem 1rem; margin:0.35rem 0; display:flex; gap:0.9rem;
    align-items:flex-start; }
.inbox-card-telegram { border-left: 4px solid #229ed9 !important; }
.inbox-card-email    { border-left: 4px solid #0043ce !important; }
.inbox-card-web      { border-left: 4px solid #6929c4 !important; }

/* Outage banner */
.outage-critical { background:#3d0f0f; border:2px solid #fa4d56;
    border-radius:10px; padding:1.1rem 1.4rem; margin:0.6rem 0; }
.outage-warning  { background:#2d2000; border:2px solid #f1c21b;
    border-radius:10px; padding:0.9rem 1.2rem; margin:0.5rem 0; }

/* Impact banner */
.impact-banner { background:linear-gradient(135deg,#003a8c,#0f62fe);
    padding:1.2rem 1.6rem; border-radius:10px; margin-bottom:1rem;
    border: 1px solid #1a4fff; }

/* Confidence bar */
.conf-track { background:#2a2a2a; border-radius:6px; height:8px;
    width:100%; margin-top:4px; overflow:hidden; }

/* Terminal log */
.terminal { background:#000; color:#42be65; font-family:"IBM Plex Mono",
    "SFMono-Regular", Consolas, monospace; font-size:0.8rem; padding:1.1rem;
    border-radius:8px; white-space:pre-wrap; line-height:1.55;
    border:1px solid #1a3a1a; max-height:480px; overflow-y:auto; }

/* HITL review card */
.hitl-card { background:#1e1a00; border:1px solid #f1c21b44;
    border-left:4px solid #f1c21b; border-radius:8px;
    padding:1rem 1.2rem; margin-bottom:0.8rem; }
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

_CHANNEL_ICON  = {"telegram": "✈️", "email": "📧", "web": "🌐"}
_CHANNEL_COLOR = {"telegram": "#229ed9", "email": "#0043ce", "web": "#6929c4"}
_PRIORITY_COLOR = {
    "critical": "#fa4d56", "high": "#f1c21b",
    "medium": "#0f62fe",   "low":  "#42be65",
}
_STATUS_COLOR = {
    "auto-routed":  "#42be65",
    "human-review": "#f1c21b",
    "escalated":    "#fa4d56",
    "untriaged":    "#8d8d8d",
}


def _conf_bar_html(conf: float, width_px: int = 120) -> str:
    color = "#42be65" if conf > 0.85 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
    filled = int(conf * width_px)
    return (
        f"<div class='conf-track' style='width:{width_px}px'>"
        f"<div style='background:{color};height:8px;width:{filled}px;border-radius:6px'></div>"
        f"</div><small style='color:{color}'>{conf:.0%}</small>"
    )


def _ticket_badges(t) -> str:
    ch   = (t.channel  or "web").lower()
    pri  = (t.priority or "medium").lower()
    stat = (t.status   or "untriaged").lower().replace(" ", "-")
    cat  = (t.category or "unknown").upper()
    return (
        f"<span class='badge badge-{ch}'>{ch.upper()}</span>"
        f"<span class='badge badge-{pri}'>{pri.upper()}</span>"
        f"<span class='badge badge-{stat}'>{stat.upper()}</span>"
        f"<span class='badge' style='background:#2a2a2a;color:#c6c6c6'>{cat}</span>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# State initialisation
# ══════════════════════════════════════════════════════════════════════════════

if "inbox" not in st.session_state:
    from intake.channels import generate_background_volume
    st.session_state.inbox = generate_background_volume(15)

if "processed" not in st.session_state:
    st.session_state.processed: list[tuple] = []   # list of (Ticket, routing_dict)

if "log" not in st.session_state:
    st.session_state.log = ""

if "tg_last_id" not in st.session_state:
    st.session_state.tg_last_id = 0


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar — Live Connectors
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(
        "<h2 style='color:#f4f4f4;font-size:1.1rem;margin-bottom:0.2rem'>"
        "📡 Live Connectors</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Connect real channels to populate the inbox.")
    st.divider()

    # ── Telegram ──────────────────────────────────────────────────────────────
    st.markdown(
        "<span style='color:#229ed9;font-weight:700'>✈️ Telegram Bot</span>",
        unsafe_allow_html=True,
    )
    tg_token = st.text_input(
        "Bot Token",
        type="password",
        placeholder="123456:ABC-DEF…",
        key="tg_token_input",
        label_visibility="collapsed",
    )
    tg_col1, tg_col2 = st.columns([2, 1])
    if tg_col1.button("📥 Fetch Live Messages", use_container_width=True, key="tg_fetch"):
        if not tg_token.strip():
            st.warning("Enter a Telegram Bot Token first.")
        else:
            from intake.channels import fetch_telegram_updates
            with st.spinner("Polling Telegram…"):
                new_tickets, new_last_id = fetch_telegram_updates(
                    tg_token, st.session_state.tg_last_id
                )
            if new_tickets:
                st.session_state.inbox.extend(new_tickets)
                st.session_state.tg_last_id = new_last_id
                st.success(f"✅ {len(new_tickets)} new message(s) added to inbox.")
            else:
                st.info("No new Telegram messages.")

    st.divider()

    # ── Gmail IMAP ────────────────────────────────────────────────────────────
    st.markdown(
        "<span style='color:#0043ce;font-weight:700'>📧 Gmail IMAP</span>",
        unsafe_allow_html=True,
    )
    gmail_user = st.text_input(
        "Gmail address",
        placeholder="you@gmail.com",
        key="gmail_user",
        label_visibility="collapsed",
    )
    gmail_pass = st.text_input(
        "App Password",
        type="password",
        placeholder="App password (not account password)",
        key="gmail_pass",
        label_visibility="collapsed",
    )
    if st.button("📥 Fetch Unread Emails", use_container_width=True, key="gmail_fetch"):
        if not gmail_user.strip() or not gmail_pass.strip():
            st.warning("Enter Gmail address and App Password.")
        else:
            from intake.channels import fetch_unread_emails
            with st.spinner("Reading Gmail IMAP…"):
                new_emails = fetch_unread_emails(gmail_user, gmail_pass)
            if new_emails:
                st.session_state.inbox.extend(new_emails)
                st.success(f"✅ {len(new_emails)} unread email(s) added to inbox.")
            else:
                st.info("No unread emails found.")

    st.divider()

    # ── Reset ─────────────────────────────────────────────────────────────────
    st.markdown(
        "<span style='color:#8d8d8d;font-weight:700'>⚙️ Session</span>",
        unsafe_allow_html=True,
    )
    if st.button("🔄 Reset Everything", use_container_width=True, key="reset_all"):
        from intake.channels import generate_background_volume
        st.session_state.inbox     = generate_background_volume(15)
        st.session_state.processed = []
        st.session_state.log       = ""
        st.session_state.tg_last_id = 0
        st.rerun()

    st.divider()
    inbox_count     = len(st.session_state.inbox)
    processed_count = len(st.session_state.processed)
    st.markdown(
        f"<div style='color:#8d8d8d;font-size:0.82rem'>"
        f"📥 Inbox: <b style='color:#f4f4f4'>{inbox_count}</b> untriaged<br>"
        f"✅ Processed: <b style='color:#f4f4f4'>{processed_count}</b></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Main header
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    "<h1 style='color:#f4f4f4;margin-bottom:0'>🎫 SupportTriage "
    "<span style='color:#0f62fe'>AI</span></h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#8d8d8d;margin-top:0'>Multi-Channel Agentic Support Operations Center "
    "— powered by IBM Granite · Human-in-the-Loop Routing</p>",
    unsafe_allow_html=True,
)
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW A — TRIAGE QUEUE  (inbox has tickets OR nothing processed yet)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.inbox:

    inbox = st.session_state.inbox

    # ── Header + counts ────────────────────────────────────────────────────────
    ch_counts = Counter(t.channel for t in inbox)
    ch_summary = "  ·  ".join(
        "<span style='color:{c}'>{i} {ch}: {n}</span>".format(
            c=_CHANNEL_COLOR.get(ch, "#8d8d8d"),
            i=_CHANNEL_ICON.get(ch, "?"),
            ch=ch.upper(),
            n=n,
        )
        for ch, n in sorted(ch_counts.items())
    )
    st.markdown(
        f"<h3 style='color:#f4f4f4;margin-bottom:0.2rem'>"
        f"📥 Triage Queue — {len(inbox)} Untriaged Tickets</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:#8d8d8d;margin-top:0'>{ch_summary}</p>",
        unsafe_allow_html=True,
    )

    # ── Ticket cards ───────────────────────────────────────────────────────────
    for t in inbox:
        ch    = (t.channel or "web").lower()
        icon  = _CHANNEL_ICON.get(ch, "?")
        color = _CHANNEL_COLOR.get(ch, "#8d8d8d")
        preview = (t.body[:130] + "…") if len(t.body) > 130 else t.body
        errs = (
            "  " + " ".join(
                f"<code style='background:#2a2a2a;padding:1px 5px;border-radius:3px;"
                f"font-size:0.75rem'>{e}</code>"
                for e in t.error_codes
            ) if t.error_codes else ""
        )
        st.markdown(f"""
<div class='inbox-card inbox-card-{ch}'>
  <span style='font-size:1.25rem;flex-shrink:0;padding-top:2px'>{icon}</span>
  <div style='flex:1;min-width:0'>
    <div style='margin-bottom:0.15rem'>
      <span style='color:#8d8d8d;font-size:0.76rem'>
        {t.id} &nbsp;·&nbsp;
        <span style='color:{color};font-weight:700'>{ch.upper()}</span>
        &nbsp;·&nbsp; {t.sender}
      </span>{errs}
    </div>
    <div style='color:#f4f4f4;font-weight:600;margin-bottom:0.2rem;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{t.subject}</div>
    <div style='color:#6d6d6d;font-size:0.82rem'>{preview}</div>
  </div>
  <span class='badge badge-untriaged' style='flex-shrink:0;margin-top:2px'>UNTRIAGED</span>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Triage button ──────────────────────────────────────────────────────────
    if st.button(
        f"🚀 Run AI Triage on {len(inbox)} Ticket(s) — IBM Granite",
        type="primary",
        use_container_width=True,
        key="run_triage",
    ):
        from guardrails.pii_redactor import redact
        from pipeline.classify import classify
        from pipeline.draft import draft_reply
        from pipeline.extract import extract
        from pipeline.summarize import summarize
        from rag.store import init_store
        from routing.router import route

        n = len(inbox)
        progress = st.progress(0, text="Initialising IBM Granite…")
        collection = init_store()
        t_start = time.perf_counter()

        async def _triage_all(tickets):
            async def _one(ticket):
                ticket.body   = redact(ticket.body)
                ticket.thread = [redact(m) for m in ticket.thread]
                ticket = await classify(ticket)
                ticket = await extract(ticket)
                ticket = await summarize(ticket)
                ticket = await draft_reply(ticket, collection)
                r = route(ticket)
                return ticket, r
            return await asyncio.gather(*[_one(t) for t in tickets])

        raw = asyncio.run(_triage_all(list(inbox)))
        elapsed = time.perf_counter() - t_start

        new_results = []
        for i, (t, r) in enumerate(raw):
            new_results.append((t, r))
            progress.progress((i + 1) / n, text=f"Triaged {i+1}/{n}…")

        # Append to processed, clear inbox
        st.session_state.processed.extend(new_results)
        st.session_state.inbox = []

        # Build log
        log_lines = [
            f"[IBM Granite] {n} tickets triaged in {elapsed:.2f}s (async batch)\n"
        ]
        for t, r in new_results:
            status_str = r.get("status", t.status)
            log_lines.append(
                f"  [{t.channel.upper():<9}] {t.id:<10} "
                f"→ {r['queue']:<22} "
                f"| conf={t.classify_confidence:.2f} "
                f"| status={status_str:<12} "
                f"| priority={t.priority or 'unknown'}\n"
            )
        st.session_state.log += "".join(log_lines)

        progress.empty()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW B — OPERATIONS DASHBOARD  (after triage, inbox empty)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.processed and not st.session_state.inbox:

    results = st.session_state.processed

    tab_metrics, tab_hitl, tab_autorouted, tab_logs = st.tabs([
        "📊 Business Impact & Metrics",
        "🧑‍💻 Human-in-the-Loop Queue",
        "🟢 Auto-Routed Log",
        "⚙️ System Logs",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — BUSINESS IMPACT & METRICS
    # ════════════════════════════════════════════════════════════════════════
    with tab_metrics:

        total        = len(results)
        auto_routed  = [p for p in results if p[1].get("status") == "auto-routed"]
        hitl_tickets = [p for p in results if p[1].get("status") == "human-review"]
        escalated    = [p for p in results if p[1].get("status") == "escalated"]
        avg_conf     = sum(t.classify_confidence for t, _ in results) / total
        automation_rate = len(auto_routed) / total

        # ── Impact banner ──────────────────────────────────────────────────
        st.markdown("""<div class='impact-banner'>
<h4 style='color:white;margin:0;font-size:1.05rem'>💡 Real-World Business Impact</h4>
<p style='color:#d0e2ff;margin:0.4rem 0 0 0;font-size:0.9rem'>
Support teams misroute <b style='color:white'>35% of tickets manually</b> — costing
<b style='color:white'>$329,000/year</b> for a 2,000-ticket/month operation.
This system applies HITL routing: only tickets with <b style='color:white'>confidence &gt; 85%</b>
are auto-routed. Everything else is held for human review — eliminating both
misrouting <em>and</em> automation failures simultaneously.
</p>
</div>""", unsafe_allow_html=True)

        # ── KPI metrics ────────────────────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🎫 Processed",      total)
        m2.metric("🤖 Auto-Routed",    f"{len(auto_routed)} ({automation_rate:.0%})")
        m3.metric("🧑‍💻 Human Review", len(hitl_tickets))
        m4.metric("🚨 Escalated",      len(escalated))
        m5.metric("📈 Avg Confidence", f"{avg_conf:.0%}")

        st.divider()

        # ── Confidence gauge ───────────────────────────────────────────────
        conf_color = "#42be65" if avg_conf > 0.85 else "#f1c21b" if avg_conf >= 0.6 else "#fa4d56"
        threshold_pct = 85
        st.markdown(f"""
<div style='background:#1a1a1a;border-radius:12px;padding:1.2rem 1.4rem;
     margin-bottom:1rem;border:1px solid #2a2a2a'>
  <div style='display:flex;justify-content:space-between;margin-bottom:0.5rem'>
    <b style='color:#f4f4f4'>Average Classification Confidence</b>
    <span style='color:{conf_color};font-size:1.25rem;font-weight:700'>{avg_conf:.0%}</span>
  </div>
  <div style='position:relative;background:#2a2a2a;border-radius:6px;height:14px;width:100%'>
    <div style='background:{conf_color};border-radius:6px;height:14px;
         width:{avg_conf*100:.0f}%'></div>
    <div style='position:absolute;top:0;left:{threshold_pct}%;width:2px;height:14px;
         background:#fa4d56;'></div>
  </div>
  <div style='display:flex;justify-content:space-between;margin-top:4px'>
    <small style='color:{conf_color}'>{avg_conf:.0%} average</small>
    <small style='color:#fa4d56'>▲ 85% auto-route threshold</small>
  </div>
</div>""", unsafe_allow_html=True)

        st.divider()

        # ── Outage Radar ───────────────────────────────────────────────────
        st.markdown("## 🚨 Outage Radar")
        st.caption("Symptoms reported across multiple channels. Threshold: 3+ tickets = systemic outage.")

        # Group symptoms → tickets
        symptom_tickets: dict[str, list] = defaultdict(list)
        for t, _ in results:
            for sym in (t.symptoms or []):
                symptom_tickets[sym].append(t)

        outage_found = False
        for symptom, tickets_with_sym in sorted(
            symptom_tickets.items(), key=lambda x: -len(x[1])
        ):
            count = len(tickets_with_sym)
            channels_affected = sorted({t.channel for t in tickets_with_sym})
            channels_str = " + ".join(
                "<span style='color:{col}'>{icon} {ch}</span>".format(
                    col=_CHANNEL_COLOR.get(c, "#8d8d8d"),
                    icon=_CHANNEL_ICON.get(c, ""),
                    ch=c.upper(),
                )
                for c in channels_affected
            )
            if count >= 3:
                outage_found = True
                st.markdown(f"""<div class='outage-critical'>
<div style='font-size:1.05rem;font-weight:700;color:#fa4d56;margin-bottom:0.4rem'>
🚨 SYSTEMIC OUTAGE DETECTED
</div>
<div style='color:#f4f4f4;font-size:0.95rem;margin-bottom:0.3rem'>
<b>{count} users</b> reporting <b>"{symptom}"</b> across {channels_str}
</div>
<div style='color:#8d8d8d;font-size:0.82rem'>
Affected tickets: {", ".join(f"<code style='background:#2a2a2a;padding:1px 5px;border-radius:3px'>{t.id}</code>" for t in tickets_with_sym)}
</div>
<div style='color:#fa4d56;font-size:0.82rem;margin-top:0.4rem;font-weight:600'>
⚡ Immediate action required — escalate to engineering now.
</div>
</div>""", unsafe_allow_html=True)

            elif count == 2:
                st.markdown(f"""<div class='outage-warning'>
<b style='color:#f1c21b'>⚠️ Pattern emerging</b>
&nbsp; <b>{count} tickets</b> reporting <b>"{symptom}"</b> — {channels_str}
&nbsp; <span style='color:#8d8d8d;font-size:0.82rem'>Monitor for further reports.</span>
</div>""", unsafe_allow_html=True)

        if not outage_found and not any(
            len(v) >= 2 for v in symptom_tickets.values()
        ):
            st.success("✅ No outage patterns detected in current processed batch.")

        st.divider()

        # ── Charts ─────────────────────────────────────────────────────────
        col_cat, col_ch = st.columns(2)

        with col_cat:
            st.subheader("📊 Volume by Category")
            cat_counts = Counter(t.category or "other" for t, _ in results)
            st.bar_chart(
                pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
                .sort_values("Tickets", ascending=False)
            )

        with col_ch:
            st.subheader("📡 Volume by Channel")
            ch_bar = Counter(t.channel for t, _ in results)
            st.bar_chart(
                pd.DataFrame.from_dict(ch_bar, orient="index", columns=["Tickets"])
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — HUMAN-IN-THE-LOOP REVIEW QUEUE
    # ════════════════════════════════════════════════════════════════════════
    with tab_hitl:

        hitl_pairs = [
            (i, t, r) for i, (t, r) in enumerate(results)
            if r.get("status") == "human-review" and t.status != "approved"
        ]

        if not hitl_pairs:
            st.success(
                "✅ No tickets awaiting human review. "
                "All low-confidence tickets have been approved or queue is clear."
            )
        else:
            st.markdown(
                f"<h3 style='color:#f1c21b'>"
                f"🧑‍💻 {len(hitl_pairs)} Ticket(s) Awaiting Agent Approval</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='color:#8d8d8d'>"
                "These tickets were held because AI confidence ≤ 85%. "
                "Review the AI reasoning, edit the draft if needed, then approve.</p>",
                unsafe_allow_html=True,
            )

            for idx, t, r in hitl_pairs:
                conf        = t.classify_confidence
                conf_color  = "#42be65" if conf > 0.85 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
                ch_color    = _CHANNEL_COLOR.get(t.channel or "web", "#8d8d8d")
                ch_icon     = _CHANNEL_ICON.get(t.channel or "web", "?")

                with st.expander(
                    f"{ch_icon} {t.id} — {t.subject[:70]}{'…' if len(t.subject)>70 else ''}",
                    expanded=False,
                ):
                    st.markdown(
                        f"<div class='hitl-card'>"
                        f"<div style='margin-bottom:0.5rem'>{_ticket_badges(t)}</div>"
                        f"<div style='display:flex;gap:2rem;flex-wrap:wrap'>"
                        f"<span style='color:#8d8d8d'>Sender: "
                        f"<b style='color:#f4f4f4'>{t.sender}</b></span>"
                        f"<span style='color:#8d8d8d'>Queue held: "
                        f"<b style='color:#f1c21b'>human-review</b></span>"
                        f"<span style='color:#8d8d8d'>Severity: "
                        f"<b style='color:{conf_color}'>{r['severity_impact']:.1f}/10</b></span>"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

                    c1, c2 = st.columns([1, 1])

                    with c1:
                        st.markdown("**🔍 AI Reasoning**")
                        st.markdown(
                            f"| Field | Value |\n|---|---|\n"
                            f"| Category | `{t.category or 'unknown'}` |\n"
                            f"| Priority  | `{t.priority  or 'unknown'}` |\n"
                            f"| Confidence | `{conf:.0%}` |\n"
                            f"| Threshold  | `85%` — below = human review |"
                        )
                        st.markdown(_conf_bar_html(conf, 180), unsafe_allow_html=True)

                        if t.error_codes:
                            st.markdown(
                                "**Error codes:** "
                                + " ".join(f"`{e}`" for e in t.error_codes)
                            )
                        if t.symptoms:
                            st.markdown(
                                "**Symptoms:** "
                                + ", ".join(
                                    f"<span style='background:#2a2a2a;color:#c6c6c6;"
                                    f"padding:1px 7px;border-radius:10px;font-size:0.75rem'>{s}</span>"
                                    for s in t.symptoms
                                ),
                                unsafe_allow_html=True,
                            )
                        st.markdown("**📝 AI Summary**")
                        st.info(t.summary or "_(no summary)_")

                    with c2:
                        st.markdown("**✉️ Draft Reply** _(editable — fix before approving)_")
                        approved_queue = st.selectbox(
                            "Route to queue",
                            options=[
                                "queue-auth", "queue-billing", "queue-performance",
                                "queue-data-loss", "queue-product", "queue-general",
                            ],
                            index=0,
                            key=f"queue_select_{t.id}",
                        )
                        edited_draft = st.text_area(
                            "Draft",
                            value=t.draft_reply or "",
                            height=220,
                            label_visibility="collapsed",
                            key=f"draft_{t.id}",
                        )
                        if st.button(
                            "✅ Approve & Route",
                            key=f"approve_{t.id}",
                            use_container_width=True,
                            type="primary",
                        ):
                            # Update in-place
                            t.draft_reply = edited_draft
                            t.status = "approved"
                            results[idx] = (t, {**r, "queue": approved_queue,
                                                "status": "approved"})
                            st.session_state.processed = results
                            st.session_state.log += (
                                f"  [HITL APPROVED] {t.id} → {approved_queue} "
                                f"by agent\n"
                            )
                            st.success(
                                f"✅ {t.id} approved and routed to `{approved_queue}`."
                            )
                            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — AUTO-ROUTED LOG
    # ════════════════════════════════════════════════════════════════════════
    with tab_autorouted:

        auto_pairs = [(t, r) for t, r in results if r.get("status") == "auto-routed"]

        if not auto_pairs:
            st.info(
                "No tickets were auto-routed yet. "
                "Auto-routing requires confidence > 85% AND non-critical priority."
            )
        else:
            st.markdown(
                f"<h3 style='color:#42be65'>"
                f"🟢 {len(auto_pairs)} Ticket(s) Auto-Routed</h3>",
                unsafe_allow_html=True,
            )
            st.caption(
                "These tickets met the confidence threshold (> 85%) and were "
                "automatically dispatched to their queue without human intervention."
            )

            rows = []
            for t, r in auto_pairs:
                rows.append({
                    "ID":         t.id,
                    "Channel":    (t.channel or "web").upper(),
                    "Subject":    t.subject[:55] + "…" if len(t.subject) > 55 else t.subject,
                    "Category":   (t.category or "—").title(),
                    "Priority":   (t.priority  or "—").title(),
                    "Confidence": f"{t.classify_confidence:.0%}",
                    "Queue":      r["queue"],
                    "Severity":   f"{r['severity_impact']:.1f}",
                })

            df = pd.DataFrame(rows)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                height=min(60 + len(rows) * 35, 500),
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — SYSTEM LOGS
    # ════════════════════════════════════════════════════════════════════════
    with tab_logs:
        st.markdown(
            "<h3 style='color:#f4f4f4'>⚙️ System Execution Log</h3>",
            unsafe_allow_html=True,
        )
        log_text = st.session_state.log or "(no triage runs yet)"
        st.markdown(
            f"<div class='terminal'>{log_text}</div>",
            unsafe_allow_html=True,
        )


# ── Empty state — everything clear ────────────────────────────────────────────
elif not st.session_state.inbox and not st.session_state.processed:
    st.markdown(
        "<div style='text-align:center;padding:4rem 2rem;color:#8d8d8d'>"
        "<div style='font-size:3rem'>📭</div>"
        "<h3 style='color:#f4f4f4'>Inbox is empty</h3>"
        "<p>Use the sidebar to fetch live tickets from Telegram or Gmail,<br>"
        "or click <b>🔄 Reset Everything</b> to reload the demo queue.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#2a2a2a;margin-top:2rem'>"
    "<p style='text-align:center;color:#3d3d3d;font-size:12px;padding-bottom:1rem'>"
    "Made with IBM Bob</p>",
    unsafe_allow_html=True,
)
