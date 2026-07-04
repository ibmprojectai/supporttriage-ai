"""Streamlit Multi-Channel Support Operations Center.

Tabs (post-triage):
  📊 Operations Dashboard  — KPIs, confidence gauge, outage radar, category + channel charts
  📥 Triaged Queue         — expandable ticket cards with editable draft replies
  ⚙️ System Logs           — execution log from the async triage run

Launch:
    streamlit run ui/review_app.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SupportTriage AI", page_icon="🎫", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.stApp { background-color: #161616; color: #f4f4f4; }
.stTabs [data-baseweb="tab"] { color: #8d8d8d; font-size: 0.95rem; }
.stTabs [aria-selected="true"] { color: #0f62fe !important; border-bottom: 2px solid #0f62fe; }
.badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:700; margin-right:4px; }
.badge-critical { background:#fa4d56; color:white; }
.badge-high { background:#f1c21b; color:#161616; }
.badge-medium { background:#0f62fe; color:white; }
.badge-low { background:#42be65; color:#161616; }
.badge-cat { background:#393939; color:#c6c6c6; }
.badge-email { background:#0043ce; color:white; }
.badge-twitter { background:#1d9bf0; color:white; }
.badge-chat { background:#6929c4; color:white; }
.ticket-critical { background:#2d1b1b; border-left:4px solid #fa4d56; border-radius:8px; padding:1rem; margin:0.4rem 0; }
.ticket-high { background:#2d2410; border-left:4px solid #f1c21b; border-radius:8px; padding:1rem; margin:0.4rem 0; }
.ticket-medium { background:#1a2635; border-left:4px solid #0f62fe; border-radius:8px; padding:1rem; margin:0.4rem 0; }
.ticket-low { background:#1a2d1e; border-left:4px solid #42be65; border-radius:8px; padding:1rem; margin:0.4rem 0; }
.outage-alert { background:#2d1b1b; border:2px solid #fa4d56; border-radius:10px; padding:1rem; margin:0.5rem 0; }
.impact-banner { background:linear-gradient(135deg,#0043ce,#0f62fe); padding:1.2rem 1.5rem; border-radius:10px; margin-bottom:1rem; }
.conf-wrap { background:#393939; border-radius:6px; height:10px; width:100%; margin-top:4px; }
.terminal { background:#000; color:#42be65; font-family:monospace; font-size:0.82rem; padding:1rem; border-radius:8px; white-space:pre-wrap; }
</style>""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='color:#f4f4f4;margin-bottom:0'>🎫 SupportTriage <span style='color:#0f62fe'>AI</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8d8d8d;margin-top:0'>Multi-Channel Support Operations Center — powered by IBM Granite</p>", unsafe_allow_html=True)
st.divider()

# ── State init ─────────────────────────────────────────────────────────────────
if "inbox" not in st.session_state:
    from intake.data_generator import generate_inbox
    st.session_state.inbox = generate_inbox(20)
if "triaged" not in st.session_state:
    st.session_state.triaged = []
if "log" not in st.session_state:
    st.session_state.log = ""

channel_icons = {"email": "📧", "twitter": "🐦", "chat": "💬"}

# ══════════════════════════════════════════════════════════════════════════════
# INBOX VIEW — shown before triage runs
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.triaged:

    st.markdown("<h3 style='color:#f4f4f4'>📥 Incoming Support Queue — 20 Untriaged Tickets</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8d8d8d'>Tickets arriving from "
        "<b style='color:#f4f4f4'>Email</b>, "
        "<b style='color:#1d9bf0'>Twitter/X</b>, and "
        "<b style='color:#6929c4'>Live Chat</b>. "
        "IBM Granite has not processed these yet.</p>",
        unsafe_allow_html=True,
    )

    for t in st.session_state.inbox:
        icon = channel_icons.get(t.channel, "📧")
        ch_color = "#0043ce" if t.channel == "email" else "#1d9bf0" if t.channel == "twitter" else "#6929c4"
        body_preview = (t.body[:120] + "...") if len(t.body) > 120 else t.body
        st.markdown(f"""
<div style='background:#262626;border-radius:8px;padding:0.8rem 1rem;margin:0.3rem 0;
     display:flex;gap:1rem;align-items:flex-start'>
  <span style='font-size:1.3rem;padding-top:2px'>{icon}</span>
  <div style='flex:1;min-width:0'>
    <div style='margin-bottom:0.2rem'>
      <span style='color:#8d8d8d;font-size:0.78rem'>{t.id} &nbsp;·&nbsp;
      <span style='color:{ch_color};font-weight:700'>{t.channel.upper()}</span>
      &nbsp;·&nbsp; {t.sender}</span>
    </div>
    <div style='color:#f4f4f4;font-weight:600;margin-bottom:0.2rem'>{t.subject}</div>
    <div style='color:#8d8d8d;font-size:0.82rem'>{body_preview}</div>
  </div>
  <span style='background:#393939;color:#8d8d8d;padding:2px 10px;border-radius:20px;
        font-size:0.75rem;white-space:nowrap;flex-shrink:0'>UNTRIAGED</span>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀 Run AI Triage on All 20 Tickets (IBM Granite)", type="primary", use_container_width=True):
        from guardrails.pii_redactor import redact
        from pipeline.classify import classify
        from pipeline.draft import draft_reply
        from pipeline.extract import extract
        from pipeline.summarize import summarize
        from rag.store import init_store
        from routing.router import route

        progress = st.progress(0, text="Initialising IBM Granite via OpenRouter…")
        collection = init_store()
        t_start = time.perf_counter()

        async def _triage_all():
            async def _one(t):
                t.body = redact(t.body)
                t.thread = [redact(m) for m in t.thread]
                t = await classify(t)
                t = await extract(t)
                t = await summarize(t)
                t = await draft_reply(t, collection)
                r = route(t)
                return t, r

            tasks = [_one(t) for t in st.session_state.inbox]
            return await asyncio.gather(*tasks)

        raw = asyncio.run(_triage_all())
        elapsed = time.perf_counter() - t_start

        results = []
        for i, (t, r) in enumerate(raw):
            results.append((t, r))
            progress.progress((i + 1) / 20, text=f"Triaged {i+1}/20 tickets…")

        st.session_state.triaged = results
        st.session_state.log = (
            f"[IBM Granite] Processed 20 tickets in {elapsed:.2f}s using async batching\n"
        )
        for t, r in results:
            st.session_state.log += (
                f"  [{t.channel.upper():<7}] {t.id:<8} → {r['queue']:<22} "
                f"| conf={t.classify_confidence:.2f} "
                f"| escalate={str(r['escalate']):<5} "
                f"| priority={t.priority or 'unknown'}\n"
            )

        progress.empty()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TRIAGED VIEW — shown after triage completes
# ══════════════════════════════════════════════════════════════════════════════
else:
    results = st.session_state.triaged

    # ── Reset button ───────────────────────────────────────────────────────────
    if st.button("🔄 Reset Inbox", use_container_width=False):
        st.session_state.triaged = []
        st.session_state.log = ""
        from intake.data_generator import generate_inbox
        st.session_state.inbox = generate_inbox(20)
        st.rerun()

    tab_dash, tab_queue, tab_logs = st.tabs(
        ["📊 Operations Dashboard", "📥 Triaged Queue", "⚙️ System Logs"]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — OPERATIONS DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════
    with tab_dash:
        total        = len(results)
        escalated    = sum(1 for _, r in results if r["escalate"])
        human_review = sum(1 for _, r in results if r.get("requires_human_review"))
        auto_routed  = sum(1 for t, r in results if t.classify_confidence >= 0.8 and not r["escalate"])
        avg_conf     = sum(t.classify_confidence for t, _ in results) / total
        automation_rate = auto_routed / total

        # ── Business impact banner ─────────────────────────────────────────────
        st.markdown("""<div class='impact-banner'>
<h4 style='color:white;margin:0'>💡 Real-World Business Impact</h4>
<p style='color:#d0e2ff;margin:0.4rem 0 0 0'>
Teams misroute <b style='color:white'>35% of tickets</b> manually — costing
<b style='color:white'>$329,000/year</b> for a 2,000-ticket/month team.
This system auto-routes with confidence scoring, flags outages in real time
across <b style='color:white'>Email, Twitter/X, and Live Chat</b>,
and drafts grounded replies — reducing misrouting to near zero.
</p>
</div>""", unsafe_allow_html=True)

        # ── KPI metrics ────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🎫 Tickets Processed", total)
        m2.metric("🤖 Auto-Routed",       f"{auto_routed} ({automation_rate:.0%})")
        m3.metric("🚨 Escalated",         f"{escalated} ({escalated/total:.0%})")
        m4.metric("⚠️ Human Review",      f"{human_review} ({human_review/total:.0%})")

        st.divider()

        # ── Confidence gauge ───────────────────────────────────────────────────
        conf_color = "#42be65" if avg_conf >= 0.8 else "#f1c21b" if avg_conf >= 0.6 else "#fa4d56"
        st.markdown(f"""<div style='background:#262626;border-radius:12px;padding:1.2rem;margin-bottom:1rem'>
<div style='display:flex;justify-content:space-between'>
<b style='color:#f4f4f4'>Average AI Confidence Across All Channels</b>
<span style='color:{conf_color};font-size:1.3rem;font-weight:700'>{avg_conf:.0%}</span>
</div>
<div class='conf-wrap'>
<div style='background:{conf_color};border-radius:6px;height:10px;width:{avg_conf*100:.0f}%'></div>
</div>
</div>""", unsafe_allow_html=True)

        # ── Outage Radar ───────────────────────────────────────────────────────
        st.subheader("🚨 Outage Radar")
        from collections import Counter
        all_symptoms = [s for t, _ in results for s in (t.symptoms or [])]
        symptom_counts = Counter(all_symptoms)
        outages_found = False
        for symptom, count in symptom_counts.most_common():
            if count >= 2:
                outages_found = True
                st.markdown(f"""<div class='outage-alert'>
<b style='color:#fa4d56'>🚨 POTENTIAL OUTAGE DETECTED</b>&nbsp;&nbsp;
<span style='color:#f4f4f4'><b>{count} tickets</b> across multiple channels reporting: <b>"{symptom}"</b></span><br>
<span style='color:#8d8d8d;font-size:0.82rem'>Investigate immediately — this may indicate a systemic failure affecting multiple customers.</span>
</div>""", unsafe_allow_html=True)
        if not outages_found:
            st.success("✅ No outage patterns detected across current inbox.")

        st.divider()

        # ── Category bar chart ─────────────────────────────────────────────────
        st.subheader("📊 Ticket Volume by Category")
        cat_counts = Counter(t.category or "other" for t, _ in results)
        st.bar_chart(
            pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
            .sort_values("Tickets", ascending=False)
        )

        # ── Channel breakdown ──────────────────────────────────────────────────
        st.subheader("📡 Ticket Volume by Channel")
        ch_counts = Counter(t.channel for t, _ in results)
        st.bar_chart(pd.DataFrame.from_dict(ch_counts, orient="index", columns=["Tickets"]))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — TRIAGED QUEUE
    # ══════════════════════════════════════════════════════════════════════════
    with tab_queue:
        st.markdown("<h3 style='color:#f4f4f4'>Triaged Ticket Queue</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p style='color:#8d8d8d'>🔴 Escalated &nbsp;&nbsp; "
            "🟡 Human Review &nbsp;&nbsp; 🟢 Auto-Routed</p>",
            unsafe_allow_html=True,
        )

        for t, r in results:
            pri        = (t.priority or "medium").lower()
            conf       = t.classify_confidence
            conf_color = "#42be65" if conf >= 0.8 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
            icon       = channel_icons.get(t.channel, "📧")

            if r["escalate"] and not r.get("requires_human_review"):
                escalate_badge = "🚨 ESCALATED"
                escalate_color = "#fa4d56"
            elif r.get("requires_human_review"):
                escalate_badge = "⚠️ HUMAN REVIEW"
                escalate_color = "#f1c21b"
            else:
                escalate_badge = "✅ AUTO-ROUTED"
                escalate_color = "#42be65"

            symptoms_html = " ".join(
                f"<span style='background:#393939;color:#c6c6c6;padding:1px 7px;"
                f"border-radius:10px;font-size:0.72rem'>{s}</span>"
                for s in (t.symptoms or [])
            )

            with st.expander(f"{icon} {t.id} — {t.subject}", expanded=False):
                c1, c2 = st.columns([1, 1])

                with c1:
                    st.markdown(
                        f"<span class='badge badge-cat'>{(t.category or 'unknown').upper()}</span>"
                        f"<span class='badge badge-{pri}'>{pri.upper()}</span>"
                        f"<span class='badge badge-{t.channel}'>{t.channel.upper()}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Sender:** {t.sender}")
                    st.markdown(f"**Queue:** `{r['queue']}`")
                    st.markdown(
                        f"**Severity:** <span style='color:{conf_color}'>{r['severity_impact']:.1f}/10</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"**Status:** <span style='color:{escalate_color};font-weight:700'>{escalate_badge}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"**AI Confidence:** <span style='color:{conf_color};font-weight:700'>{conf:.0%}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div class='conf-wrap'>"
                        f"<div style='background:{conf_color};border-radius:6px;height:10px;"
                        f"width:{conf*100:.0f}%'></div></div>",
                        unsafe_allow_html=True,
                    )
                    if t.error_codes:
                        st.markdown("**Error Codes:** " + " ".join(f"`{e}`" for e in t.error_codes))
                    if t.symptoms:
                        st.markdown(f"**Symptoms:** {symptoms_html}", unsafe_allow_html=True)

                with c2:
                    st.markdown("**📝 AI Summary**")
                    st.info(t.summary or "_(no summary)_")
                    st.markdown("**✉️ Draft Reply** _(editable)_")
                    edited = st.text_area(
                        "reply",
                        value=t.draft_reply or "",
                        height=200,
                        label_visibility="collapsed",
                        key=f"reply_{t.id}",
                    )
                    if st.button("✅ Approve & Send", key=f"approve_{t.id}", use_container_width=True):
                        st.success(f"✅ Reply for {t.id} approved!")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — SYSTEM LOGS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_logs:
        st.markdown("<h3 style='color:#f4f4f4'>⚙️ System Execution Log</h3>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='terminal'>{st.session_state.log}</div>",
            unsafe_allow_html=True,
        )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#393939;margin-top:2rem'>"
    "<p style='text-align:center;color:#525252;font-size:12px;padding-bottom:1rem'>"
    "Made with IBM Bob</p>",
    unsafe_allow_html=True,
)
