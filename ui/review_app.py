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
from intake.zendesk_connector import fetch_ticket
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


# ── Run pipeline (cached so it only runs once per session) ─────────────────────
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


ticket, routing = run_pipeline()

# ── Two-tab layout ─────────────────────────────────────────────────────────────
tab_dash, tab_review = st.tabs(["📊 Dashboard", "🎫 Ticket Review"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — EXECUTIVE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:

    # ── Row of 4 KPI metrics ───────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Tickets Processed", 1)
    m2.metric("AI Confidence Score", f"{ticket.classify_confidence:.0%}")
    m3.metric("Severity Impact", f"{routing['severity_impact']:.1f} / 10")
    m4.metric("Escalation Status", "Yes" if routing["escalate"] else "No")

    st.divider()

    # ── Ticket volume by category bar chart ───────────────────────────────────
    st.subheader("📈 Ticket Volume by Category")
    _volume_data = {
        "authentication": 12,
        "billing": 5,
        "performance": 8,
        "data-loss": 2,
        "feature-request": 3,
    }
    chart_df = pd.DataFrame.from_dict(
        _volume_data, orient="index", columns=["Tickets"]
    )
    chart_df.index.name = "Category"
    st.bar_chart(chart_df)

    st.divider()

    # ── Outage alerts ─────────────────────────────────────────────────────────
    st.subheader("🚨 Outage Alerts")
    if ticket.symptoms:
        for symptom in ticket.symptoms:
            st.warning(
                f"Potential pattern detected: {symptom} — monitor for recurrence."
            )
    else:
        st.success("No active outage patterns detected.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TICKET REVIEW
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
