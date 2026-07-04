"""Streamlit agent-review interface.

Runs the full triage pipeline on a mock ticket and presents the AI-generated
output for a human support agent to review and optionally edit before approving.

Launch:
    streamlit run ui/review_app.py
"""

from __future__ import annotations

import asyncio
import sys
import os

# Allow importing project modules from the repo root when running via streamlit
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from guardrails.pii_redactor import redact
from intake.zendesk_connector import fetch_all_tickets, fetch_ticket
from pipeline.classify import classify
from pipeline.draft import draft_reply
from pipeline.extract import extract
from pipeline.summarize import summarize
from rag.store import init_store
from routing.router import route


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="supporttriage-ai — Agent Review",
    page_icon="🎫",
    layout="wide",
)

st.title("🎫 supporttriage-ai — Agent Review")
st.caption(
    "AI-generated triage output for human review. "
    "Edit the draft reply before approving."
)


# ── Single-ticket pipeline (cached) ───────────────────────────────────────────
@st.cache_resource(show_spinner="Running triage pipeline …")
def run_pipeline():
    async def _run():
        ticket = fetch_ticket("mock")
        ticket.body = redact(ticket.body)
        ticket.thread = [redact(msg) for msg in ticket.thread]
        ticket = await classify(ticket)
        ticket = await extract(ticket)
        ticket = await summarize(ticket)
        collection = init_store()
        ticket = await draft_reply(ticket, collection)
        routing = route(ticket)
        return ticket, routing
    return asyncio.run(_run())


# ── Batch pipeline — classify + route all 15 tickets (cached) ─────────────────
@st.cache_resource(show_spinner="Classifying all 15 tickets …")
def run_batch_pipeline():
    """Classify and route all 15 mock tickets. Returns list of (ticket, routing) tuples."""
    async def _run():
        tickets = fetch_all_tickets()
        results = []
        for t in tickets:
            t.body = redact(t.body)
            t = await classify(t)
            routing = route(t)
            results.append((t, routing))
        return results
    return asyncio.run(_run())


ticket, routing = run_pipeline()
batch_results = run_batch_pipeline()

# ── Three-tab layout ───────────────────────────────────────────────────────────
tab_dash, tab_all, tab_review = st.tabs(["📊 Dashboard", "🗂️ All Tickets", "🎫 Ticket Review"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EXECUTIVE DASHBOARD (driven by batch data)
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:

    # ── Compute batch stats ────────────────────────────────────────────────────
    total        = len(batch_results)
    escalated    = sum(1 for _, r in batch_results if r["escalate"])
    human_review = sum(1 for _, r in batch_results if r["requires_human_review"])
    avg_conf     = sum(t.classify_confidence for t, _ in batch_results) / total

    # ── Business impact banner ─────────────────────────────────────────────────
    st.markdown("""
<div style='background:#0f62fe;padding:1rem 1.5rem;border-radius:8px;margin-bottom:1rem'>
<h4 style='color:white;margin:0'>💡 Business Impact</h4>
<p style='color:#d0e2ff;margin:0.3rem 0 0 0'>
Teams handling 2,000 tickets/month misroute ~35% manually — costing <b style='color:white'>$329,000/year</b>.
This system reduces misrouting through AI confidence scoring, auto-escalation, and RAG-grounded replies.
</p>
</div>
""", unsafe_allow_html=True)

    # ── Row of 5 KPI metrics (real batch numbers) ──────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎫 Tickets Processed", total)
    m2.metric("AI Avg Confidence",    f"{avg_conf:.0%}")
    m3.metric("🚨 Escalated",         escalated)
    m4.metric("👤 Human Review",       human_review)
    m5.metric("💰 Est. Annual Saving", "$329K")

    # ── Confidence gauge (single featured ticket) ──────────────────────────────
    st.subheader("🎯 AI Confidence Gauge — Featured Ticket")
    conf  = ticket.classify_confidence
    color = "#42be65" if conf >= 0.8 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
    label = (
        "High Confidence ✅" if conf >= 0.8
        else "Medium Confidence ⚠️" if conf >= 0.6
        else "Low Confidence — Human Review Required 🚨"
    )
    st.markdown(f"""
<div style='background:#262626;border-radius:12px;padding:1.2rem;margin-bottom:1rem'>
<div style='display:flex;justify-content:space-between;margin-bottom:0.5rem'>
<span style='color:#f4f4f4;font-weight:600'>Classification Confidence</span>
<span style='color:{color};font-weight:700;font-size:1.3rem'>{conf:.0%}</span>
</div>
<div style='background:#393939;border-radius:6px;height:18px;width:100%'>
<div style='background:{color};border-radius:6px;height:18px;width:{conf*100:.0f}%'>
</div>
</div>
<p style='color:{color};margin:0.5rem 0 0 0;font-size:0.9rem'>{label}</p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Ticket volume by category (real data from batch) ──────────────────────
    st.subheader("📈 Ticket Volume by Category")
    from collections import Counter
    cat_counts = Counter(
        t.category or "unknown" for t, _ in batch_results
    )
    chart_df = pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
    chart_df.index.name = "Category"
    chart_df = chart_df.sort_values("Tickets", ascending=False)
    st.bar_chart(chart_df)

    st.divider()

    # ── Outage alerts (symptoms from all batch tickets) ────────────────────────
    st.subheader("🚨 Outage Alerts")
    all_symptoms = [s for t, _ in batch_results for s in (t.symptoms or [])]
    if all_symptoms:
        for symptom in all_symptoms:
            st.warning(f"Potential pattern detected: {symptom} — monitor for recurrence.")
    else:
        st.success("No active outage patterns detected across all tickets.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ALL TICKETS
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:

    st.subheader("🗂️ Batch Triage Results — All 15 Tickets")
    st.caption("AI classification and routing for every ticket in this session.")

    # ── Summary metrics ────────────────────────────────────────────────────────
    bm1, bm2, bm3, bm4 = st.columns(4)
    bm1.metric("Total Tickets",  total)
    bm2.metric("🚨 Escalated",   escalated)
    bm3.metric("👤 Human Review", human_review)
    bm4.metric("Avg Confidence", f"{avg_conf:.0%}")

    st.divider()

    # ── Build dataframe ────────────────────────────────────────────────────────
    rows = []
    for t, r in batch_results:
        rows.append({
            "ID":         t.id,
            "Subject":    t.subject[:60] + "…" if len(t.subject) > 60 else t.subject,
            "Category":   t.category or "—",
            "Priority":   t.priority or "—",
            "Confidence": f"{t.classify_confidence:.0%}",
            "Queue":      r["queue"],
            "Escalate":   "🚨 Yes" if r["escalate"] else "✅ No",
            "H-Review":   "👤 Yes" if r["requires_human_review"] else "—",
            "Symptoms":   ", ".join(t.symptoms[:2]) if t.symptoms else "—",
            # Hidden numeric columns for row colouring
            "_escalate":  r["escalate"],
            "_human":     r["requires_human_review"],
        })

    df = pd.DataFrame(rows)

    # ── Row colour helper ──────────────────────────────────────────────────────
    def _row_color(row):
        if row["_escalate"] and not row["_human"]:
            # Red for hard escalations (critical / data-loss)
            bg = "background-color: #fff1f1; color: #a2191f"
        elif row["_human"]:
            # Yellow for human-review
            bg = "background-color: #fdf6dd; color: #6c3c00"
        else:
            # Green for standard routing
            bg = "background-color: #defbe6; color: #044317"
        return [bg] * len(row)

    display_cols = ["ID", "Subject", "Category", "Priority",
                    "Confidence", "Queue", "Escalate", "H-Review", "Symptoms"]

    styled = (
        df[display_cols + ["_escalate", "_human"]]
        .style
        .apply(_row_color, axis=1)
        .hide(axis="index")
    )

    st.dataframe(styled, use_container_width=True, height=560)

    st.divider()

    # ── Category bar chart ─────────────────────────────────────────────────────
    st.subheader("📊 Tickets per Category")
    batch_cat_df = (
        df.groupby("Category")
        .size()
        .reset_index(name="Count")
        .set_index("Category")
    )
    st.bar_chart(batch_cat_df)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TICKET REVIEW (single featured ticket)
# ══════════════════════════════════════════════════════════════════════════════
with tab_review:

    # ── Layout: two columns ───────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("📋 Ticket Details")

        st.markdown(f"**Ticket ID:** `{ticket.id}`")
        st.markdown(f"**Sender:** {ticket.sender}")
        st.markdown(f"**Subject:** {ticket.subject}")
        st.markdown(f"**Account:** `{ticket.account}`")
        st.markdown(f"**Product:** {ticket.product}")

        st.divider()
        st.subheader("🔍 AI Classification")

        c1, c2 = st.columns(2)
        c1.metric("Category", ticket.category.title() if ticket.category else "—")
        c2.metric("Priority", ticket.priority.title() if ticket.priority else "—")

        if ticket.error_codes:
            st.markdown("**Error Codes:** " + "  ".join(f"`{e}`" for e in ticket.error_codes))
        else:
            st.markdown("**Error Codes:** _(none detected)_")

        st.divider()
        st.subheader("📦 Routing")

        rc1, rc2 = st.columns(2)
        rc1.metric("Queue", routing["queue"])
        rc2.metric("AI Confidence", f"{ticket.classify_confidence:.0%}")

        st.markdown("**Tags:** " + "  ".join(f"`{t}`" for t in routing["tags"]))

        if ticket.requires_human_review:
            st.warning("⚠️ Low confidence — this ticket requires human review before routing.")
        elif routing["escalate"]:
            st.error("⚠️ This ticket is flagged for **immediate escalation**.")
        else:
            st.success("✅ Standard queue routing.")

        st.divider()
        st.subheader("📝 Summary")
        st.info(ticket.summary or "_(no summary generated)_")

    with col_right:
        st.subheader("✉️ Draft Reply")
        st.caption("Edit the AI-generated draft below before approving.")

        edited_reply = st.text_area(
            label="Draft reply",
            value=ticket.draft_reply,
            height=380,
            label_visibility="collapsed",
        )

        st.divider()
        st.subheader("🧵 Original Thread")
        with st.expander("View thread", expanded=False):
            for i, msg in enumerate(ticket.thread, 1):
                st.markdown(f"**{i}.** {msg}")
            st.markdown("---")
            st.markdown("**Original body (PII redacted):**")
            st.text(ticket.body)

    # ── Approve button ────────────────────────────────────────────────────────
    st.divider()
    approve_col, _ = st.columns([1, 3])
    with approve_col:
        if st.button("✅ Approve & Send", type="primary", use_container_width=True):
            # TODO: replace with real Zendesk reply API call
            st.success("Reply approved! (stub mode — no message sent)")
            st.code(edited_reply, language=None)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='margin-top:2rem'><p style='text-align:center;color:#888;font-size:12px'>"
    "Made with IBM Bob</p>",
    unsafe_allow_html=True,
)
