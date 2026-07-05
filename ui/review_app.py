"""SupportTriage AI — Enterprise Multi-Channel Agentic Operations Center.

Navigation (sidebar radio):
  📥 Inbox         — live queue with search/filter + SLA risk badges
  📊 Dashboard     — 8-KPI grid, SLA analytics, outage radar, charts
  🧑‍💻 Review Queue — HITL approval with confidence distribution
  ⚙️ Settings      — credential configuration, save + test per channel

Launch:
    streamlit run ui/review_app.py
"""

from __future__ import annotations

import asyncio
import html as _html
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SupportTriage AI",
    page_icon="🎫",
    layout="wide",
)

# ── CSS — NinjaOne-grade enterprise dark UI ────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
.stApp {
    background-color: #0b1120;
    color: #cbd5e1;
    font-family: 'Inter', -apple-system, "Segoe UI", system-ui, sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1526 !important;
    border-right: 1px solid #1e2d45 !important;
    width: 220px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }

/* ── Sidebar nav radio ── */
div[data-testid="stRadio"] > div { gap: 2px !important; padding: 0 0.5rem; }
div[data-testid="stRadio"] label {
    background: transparent !important;
    border-radius: 7px !important;
    padding: 0.52rem 0.9rem !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    width: 100% !important;
    display: block !important;
    transition: all 0.1s !important;
    border: none !important;
}
div[data-testid="stRadio"] label:hover {
    background: #162032 !important;
    color: #94a3b8 !important;
}
div[data-testid="stRadio"] label[data-checked="true"],
div[data-testid="stRadio"] label[aria-checked="true"] {
    background: #1d3a6e !important;
    color: #60a5fa !important;
    font-weight: 600 !important;
}

/* ── Typography ── */
h1, h2, h3, h4 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
    letter-spacing: -0.4px !important;
    line-height: 1.3 !important;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #111d30 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 10px !important;
    padding: 1rem 1.1rem !important;
    position: relative !important;
    overflow: hidden !important;
}
[data-testid="stMetricLabel"] {
    color: #475569 !important;
    font-size: 0.66rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px !important;
}
[data-testid="stMetricDelta"] { font-size: 0.7rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: #2563eb !important;
    color: #fff !important;
    border: none !important;
    border-radius: 7px !important;
    padding: 0.45rem 1.1rem !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.1px !important;
    transition: background 0.12s !important;
    box-shadow: 0 1px 3px #00000055 !important;
}
.stButton > button:hover { background: #1d4ed8 !important; }
.stButton > button[kind="primary"] { background: #2563eb !important; }
.stButton > button[kind="secondary"] {
    background: #162032 !important;
    color: #94a3b8 !important;
    border: 1px solid #1e2d45 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #1e2d45 !important;
    color: #cbd5e1 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: #0d1526 !important;
    color: #cbd5e1 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 7px !important;
    font-size: 0.84rem !important;
    font-family: inherit !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px #2563eb22 !important;
}
label[data-testid="stWidgetLabel"] { color: #64748b !important; font-size: 0.78rem !important; }

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: #111d30 !important;
    color: #94a3b8 !important;
    border-radius: 8px !important;
    border: 1px solid #1e2d45 !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 0.6rem 0.9rem !important;
}
.streamlit-expanderHeader:hover { background: #162032 !important; color: #cbd5e1 !important; }
.streamlit-expanderContent {
    background: #0f1a2e !important;
    border: 1px solid #1e2d45 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 1rem 1rem 0.8rem !important;
}

/* ── Divider ── */
hr { border: none !important; border-top: 1px solid #1e2d45 !important; margin: 1rem 0 !important; }

/* ── Alerts ── */
.stAlert { border-radius: 8px !important; font-size: 0.83rem !important; border: none !important; }
.stAlert[data-baseweb="notification"] { background: #111d30 !important; }

/* ── Badges / Pills ── */
.pill {
    display: inline-flex; align-items: center;
    padding: 2px 9px; border-radius: 20px;
    font-size: 0.65rem; font-weight: 700;
    letter-spacing: 0.3px; margin-right: 4px;
    white-space: nowrap;
}
.pill-critical { background: #450a0a; color: #f87171; }
.pill-high     { background: #431407; color: #fb923c; }
.pill-medium   { background: #172554; color: #60a5fa; }
.pill-low      { background: #052e16; color: #4ade80; }
.pill-auto     { background: #052e16; color: #4ade80; }
.pill-review   { background: #431407; color: #fb923c; }
.pill-escalated{ background: #450a0a; color: #f87171; }
.pill-approved { background: #052e16; color: #4ade80; }
.pill-untriaged{ background: #1e2d45; color: #475569; }
.pill-telegram { background: #1e3a5f; color: #93c5fd; }
.pill-email    { background: #1e2d45; color: #a5b4fc; }
.pill-web      { background: #2e1065; color: #c4b5fd; }
.pill-cat      { background: #1e2d45; color: #94a3b8;  border: 1px solid #2d3f58; }

/* ── SLA pills ── */
.sla-critical { display:inline-flex;align-items:center;padding:2px 8px;border-radius:4px;font-size:0.63rem;font-weight:700;background:#450a0a;color:#f87171; }
.sla-high     { display:inline-flex;align-items:center;padding:2px 8px;border-radius:4px;font-size:0.63rem;font-weight:700;background:#431407;color:#fb923c; }
.sla-ok       { display:inline-flex;align-items:center;padding:2px 8px;border-radius:4px;font-size:0.63rem;font-weight:700;background:#052e16;color:#4ade80; }

/* ── KPI panel card ── */
.kpi-panel {
    background: #111d30; border: 1px solid #1e2d45;
    border-radius: 10px; padding: 1.1rem 1.3rem;
    position: relative;
}
.kpi-panel::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2px; background: #2563eb; border-radius: 10px 10px 0 0;
}
.kpi-val { font-size: 2rem; font-weight: 800; color: #f1f5f9; letter-spacing: -0.6px; line-height: 1.1; }
.kpi-lbl { font-size: 0.63rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #475569; margin-top: 0.2rem; }
.kpi-sub { font-size: 0.72rem; color: #64748b; margin-top: 0.15rem; }

/* ── Inbox ticket row ── */
.tkt-row {
    background: #111d30; border: 1px solid #1e2d45;
    border-radius: 10px; padding: 0.75rem 1rem;
    margin-bottom: 0.35rem;
    display: flex; gap: 0.85rem; align-items: flex-start;
    transition: border-color 0.1s, background 0.1s;
    cursor: default;
}
.tkt-row:hover { background: #162032; border-color: #2563eb44; }
.tkt-row-critical { border-top: 2px solid #f87171 !important; }
.tkt-row-high     { border-top: 2px solid #fb923c !important; }
.tkt-row-medium   { border-top: 2px solid #60a5fa !important; }
.tkt-row-low      { border-top: 2px solid #4ade80 !important; }

/* ── Section header label ── */
.sec-lbl {
    font-size: 0.63rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.4px; color: #334155; margin: 0 0 0.55rem 0;
}

/* ── Data panel (reasoning table etc.) ── */
.data-panel {
    background: #0d1526; border: 1px solid #1e2d45;
    border-radius: 8px; overflow: hidden;
}
.dp-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.32rem 0.75rem; border-bottom: 1px solid #141f33;
    font-size: 0.8rem;
}
.dp-row:last-child { border-bottom: none; }
.dp-key { color: #475569; font-weight: 500; }
.dp-val { color: #94a3b8; font-weight: 600; text-align: right; }

/* ── AI suggestion panel ── */
.ai-box {
    background: #0f1e3a; border: 1px solid #1e3a6e;
    border-top: 2px solid #2563eb;
    border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.6rem;
}
.ai-box-lbl {
    font-size: 0.63rem; font-weight: 700; color: #3b82f6;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.45rem;
}
.ai-box-text {
    font-size: 0.82rem; color: #94a3b8; line-height: 1.7;
    white-space: pre-wrap; font-family: inherit;
}

/* ── HITL card header ── */
.hitl-hdr {
    background: #111d30; border: 1px solid #1e3a6e;
    border-top: 2px solid #fb923c;
    border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.75rem;
}

/* ── Outage cards ── */
.outage-critical {
    background: #1a0a0a; border: 1px solid #7f1d1d55;
    border-top: 2px solid #f87171;
    border-radius: 8px; padding: 0.9rem 1.1rem; margin: 0.5rem 0;
}
.outage-warn {
    background: #1a1000; border: 1px solid #78350f55;
    border-top: 2px solid #fb923c;
    border-radius: 8px; padding: 0.7rem 0.95rem; margin: 0.3rem 0;
}

/* ── Confidence track ── */
.ctrack { background: #1e2d45; border-radius: 3px; height: 6px; overflow: hidden; margin-top: 3px; }

/* ── Terminal log ── */
.terminal {
    background: #060d18; color: #4ade80;
    font-family: "SFMono-Regular", "Cascadia Code", Consolas, monospace;
    font-size: 0.74rem; padding: 1rem; border-radius: 8px;
    white-space: pre-wrap; line-height: 1.7;
    border: 1px solid #052e16; max-height: 420px; overflow-y: auto;
}

/* ── Impact banner ── */
.impact-banner {
    background: linear-gradient(135deg, #0f1e3a 0%, #111d30 100%);
    border: 1px solid #1e3a6e; border-top: 2px solid #2563eb;
    border-radius: 10px; padding: 1rem 1.4rem; margin-bottom: 1.2rem;
}

/* ── Priority bar track ── */
.pri-track { background: #1e2d45; border-radius: 3px; height: 6px; flex: 1; overflow: hidden; }

/* ── Status dot ── */
.dot-on  { display:inline-block;width:7px;height:7px;border-radius:50%;background:#4ade80;margin-right:5px;box-shadow:0 0 5px #4ade8088; }
.dot-off { display:inline-block;width:7px;height:7px;border-radius:50%;background:#1e2d45;margin-right:5px; }

/* ── Sidebar stat row ── */
.sb-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.28rem 0; border-bottom: 1px solid #141f33; font-size: 0.78rem;
}
.sb-row:last-child { border-bottom: none; }

/* ── Streamlit table ── */
.stDataFrame { border-radius: 8px !important; overflow: hidden !important; }

/* ── Bar chart dark ── */
[data-testid="stArrowVegaLiteChart"] { background: transparent !important; }

/* ── Progress bar ── */
.stProgress > div > div { background: #2563eb !important; border-radius: 4px !important; }
.stProgress > div { background: #1e2d45 !important; border-radius: 4px !important; }

/* ── Info/warning/success boxes ── */
div[data-testid="stNotification"] { border-radius: 8px !important; }
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Constants & Helpers
# ══════════════════════════════════════════════════════════════════════════════

_CHANNEL_ICON  = {"telegram": "✈", "email": "✉", "web": "⊕"}
_CHANNEL_COLOR = {"telegram": "#93c5fd", "email": "#a5b4fc", "web": "#c4b5fd"}
_PRIORITY_COLOR = {
    "critical": "#f87171", "high": "#fb923c",
    "medium":   "#60a5fa", "low":  "#4ade80",
}
_PRIORITY_SLA = {"critical": 2, "high": 8, "medium": 24, "low": 72}


def _conf_bar_html(conf: float, width_px: int = 160) -> str:
    color  = "#4ade80" if conf > 0.85 else "#fb923c" if conf >= 0.6 else "#f87171"
    filled = int(conf * width_px)
    return (
        "<div class='ctrack' style='width:{w}px'>"
        "<div style='background:{c};height:6px;width:{f}px;border-radius:3px'></div>"
        "</div>"
        "<small style='color:{c};font-size:0.68rem;font-weight:600'>{p}</small>"
    ).format(w=width_px, c=color, f=filled, p="{:.0%}".format(conf))


def _pills(t) -> str:
    ch   = (t.channel  or "web").lower()
    pri  = (t.priority or "medium").lower()
    stat = (t.status   or "untriaged").lower().replace(" ", "-")
    cat  = _html.escape((t.category or "unknown").upper())
    return (
        "<span class='pill pill-{ch}'>{CH}</span>"
        "<span class='pill pill-{pri}'>{PRI}</span>"
        "<span class='pill pill-{stat}'>{STAT}</span>"
        "<span class='pill pill-cat'>{cat}</span>"
    ).format(ch=ch, CH=ch.upper(), pri=pri, PRI=pri.upper(),
             stat=stat, STAT=stat.upper(), cat=cat)


def _sla_badge(priority: str) -> str:
    p = (priority or "medium").lower()
    if p == "critical":
        return "<span class='sla-critical'>SLA 2h</span>"
    if p == "high":
        return "<span class='sla-high'>SLA 8h</span>"
    return "<span class='sla-ok'>SLA {h}h</span>".format(h=_PRIORITY_SLA.get(p, 24))


def _dp_row(key: str, val: str) -> str:
    return (
        "<div class='dp-row'>"
        "<span class='dp-key'>{k}</span>"
        "<span class='dp-val'>{v}</span>"
        "</div>"
    ).format(k=key, v=val)


# ══════════════════════════════════════════════════════════════════════════════
# State initialisation
# ══════════════════════════════════════════════════════════════════════════════

if "inbox" not in st.session_state:
    from intake.channels import generate_background_volume
    st.session_state.inbox = generate_background_volume(15)

if "processed" not in st.session_state:
    st.session_state.processed: list[tuple] = []

if "log" not in st.session_state:
    st.session_state.log = ""

if "tg_last_id" not in st.session_state:
    st.session_state.tg_last_id = 0

if "tg_token" not in st.session_state:
    st.session_state.tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if "gmail_user" not in st.session_state:
    st.session_state.gmail_user = os.environ.get("GMAIL_USER", "")
if "gmail_pass" not in st.session_state:
    st.session_state.gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
if "imap_server" not in st.session_state:
    st.session_state.imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")
if "openrouter_key" not in st.session_state:
    st.session_state.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    # Logo / brand
    st.markdown(
        "<div style='padding:1.4rem 1rem 0.8rem 1rem;border-bottom:1px solid #1e2d45'>"
        "<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:3px'>"
        "<div style='width:28px;height:28px;background:#2563eb;border-radius:7px;"
        "display:flex;align-items:center;justify-content:center;"
        "font-size:0.9rem;flex-shrink:0'>&#127915;</div>"
        "<span style='color:#f1f5f9;font-size:0.95rem;font-weight:700;"
        "letter-spacing:-0.3px'>SupportTriage</span>"
        "<span style='color:#2563eb;font-size:0.95rem;font-weight:800'>AI</span>"
        "</div>"
        "<span style='color:#1e3a6e;font-size:0.6rem;letter-spacing:1.5px;"
        "font-weight:700;text-transform:uppercase'>ENTERPRISE OPS CENTER</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    page = st.radio(
        "",
        ["📥  Inbox", "📊  Dashboard", "🧑‍💻  Review Queue", "⚙️  Settings"],
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)

    # Channel status
    tg_connected = bool(st.session_state.get("tg_token"))
    gm_connected = bool(st.session_state.get("gmail_user"))

    st.markdown(
        "<div style='padding:0.7rem 1rem 0.4rem'>"
        "<p class='sec-lbl' style='margin-bottom:0.5rem'>Live Channels</p>",
        unsafe_allow_html=True,
    )
    _tg_dot = "dot-on" if tg_connected else "dot-off"
    _tg_lbl = "Connected" if tg_connected else "Not configured"
    _tg_col = "#4ade80" if tg_connected else "#475569"
    _gm_dot = "dot-on" if gm_connected else "dot-off"
    _gm_lbl = "Connected" if gm_connected else "Not configured"
    _gm_col = "#4ade80" if gm_connected else "#475569"
    st.markdown(
        "<div style='padding:0 0 0.5rem'>"
        "<div style='display:flex;align-items:center;gap:0.4rem;padding:0.22rem 0'>"
        "<span class='{tg_dot}'></span>"
        "<span style='font-size:0.78rem;color:{tg_col}'>Telegram &nbsp;"
        "<span style='font-weight:600'>{tg_lbl}</span></span>"
        "</div>"
        "<div style='display:flex;align-items:center;gap:0.4rem;padding:0.22rem 0'>"
        "<span class='{gm_dot}'></span>"
        "<span style='font-size:0.78rem;color:{gm_col}'>Gmail &nbsp;"
        "<span style='font-weight:600'>{gm_lbl}</span></span>"
        "</div>"
        "<div style='display:flex;align-items:center;gap:0.4rem;padding:0.22rem 0'>"
        "<span class='dot-on'></span>"
        "<span style='font-size:0.78rem;color:#4ade80'>Web Form &nbsp;"
        "<span style='font-weight:600'>Active</span></span>"
        "</div>"
        "</div></div>".format(
            tg_dot=_tg_dot, tg_col=_tg_col, tg_lbl=_tg_lbl,
            gm_dot=_gm_dot, gm_col=_gm_col, gm_lbl=_gm_lbl,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)

    # Queue summary
    inbox_count     = len(st.session_state.get("inbox", []))
    review_count    = sum(1 for _, r in st.session_state.get("processed", []) if r.get("status") == "human-review")
    escalated_count = sum(1 for _, r in st.session_state.get("processed", []) if r.get("status") == "escalated")
    processed_count = len(st.session_state.get("processed", []))

    _rc_col = "#fb923c" if review_count else "#94a3b8"
    _ec_col = "#f87171" if escalated_count else "#94a3b8"

    st.markdown(
        "<div style='padding:0.7rem 1rem'>"
        "<p class='sec-lbl' style='margin-bottom:0.5rem'>Queue Summary</p>"
        "<div class='sb-row'><span style='color:#475569'>Inbox</span>"
        "<span style='color:#f1f5f9;font-weight:700'>{inbox}</span></div>"
        "<div class='sb-row'><span style='color:#475569'>Human Review</span>"
        "<span style='color:{rc};font-weight:700'>{review}</span></div>"
        "<div class='sb-row'><span style='color:#475569'>Escalated</span>"
        "<span style='color:{ec};font-weight:700'>{esc}</span></div>"
        "<div class='sb-row'><span style='color:#475569'>Processed</span>"
        "<span style='color:#94a3b8;font-weight:700'>{proc}</span></div>"
        "</div>".format(
            inbox=inbox_count, rc=_rc_col, review=review_count,
            ec=_ec_col, esc=escalated_count, proc=processed_count,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)
    st.markdown("<div style='padding:0.6rem 0.5rem'>", unsafe_allow_html=True)
    if st.button("↺  Reset Inbox", use_container_width=True, key="reset_all"):
        from intake.channels import generate_background_volume
        st.session_state.inbox      = generate_background_volume(15)
        st.session_state.processed  = []
        st.session_state.log        = ""
        st.session_state.tg_last_id = 0
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Top header bar
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    "<div style='display:flex;justify-content:space-between;align-items:center;"
    "padding:0 0 1.2rem 0;border-bottom:1px solid #1e2d45;margin-bottom:1.6rem'>"
    "<div>"
    "<h1 style='margin:0;font-size:1.5rem;font-weight:800;letter-spacing:-0.5px;"
    "color:#f1f5f9'>SupportTriage <span style='color:#2563eb'>AI</span></h1>"
    "<p style='color:#334155;margin:2px 0 0;font-size:0.72rem;letter-spacing:0.2px'>"
    "Multi-channel  ·  IBM Granite 4.1  ·  Human-in-the-Loop  ·  RAG-powered drafts"
    "</p>"
    "</div>"
    "<div style='display:flex;gap:0.5rem;align-items:center'>"
    "<span style='background:#052e16;color:#4ade80;padding:4px 10px;border-radius:20px;"
    "font-size:0.63rem;font-weight:700;letter-spacing:0.5px'>"
    "&#9679; LIVE</span>"
    "<span style='background:#111d30;color:#475569;padding:4px 10px;border-radius:20px;"
    "font-size:0.63rem;font-weight:600;border:1px solid #1e2d45'>"
    "Granite 4.1 8B</span>"
    "<span style='background:#111d30;color:#475569;padding:4px 10px;border-radius:20px;"
    "font-size:0.63rem;font-weight:600;border:1px solid #1e2d45'>"
    "HITL &gt;85%</span>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── strip leading spaces from radio labels for page matching ──────────────────
page = page.strip()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ⚙️  Settings
# ══════════════════════════════════════════════════════════════════════════════

if page == "⚙️  Settings":
    st.markdown(
        "<h2 style='margin-bottom:0.2rem'>Channel Configuration</h2>"
        "<p style='color:#475569;font-size:0.8rem;margin-bottom:1.4rem'>"
        "Credentials are stored in your session only — never persisted to disk or GitHub.</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("#### ✈  Telegram Bot")
        st.caption("Get your token from **@BotFather** on Telegram → `/newbot` → copy the API token.")
        tg_token_input = st.text_input(
            "Telegram Bot Token", value=st.session_state.get("tg_token", ""),
            type="password", placeholder="1234567890:ABCdef…", key="tg_token_field",
        )
        tg_col1, _ = st.columns([1, 3])
        if tg_col1.button("Save & Test", key="save_tg", use_container_width=True):
            if tg_token_input.strip():
                try:
                    import requests as _req
                    r = _req.get("https://api.telegram.org/bot{}/getMe".format(tg_token_input), timeout=5)
                    if r.status_code == 200:
                        bot_name = r.json()["result"]["username"]
                        st.session_state["tg_token"] = tg_token_input.strip()
                        st.success("Connected to @{}".format(bot_name))
                    else:
                        st.error("Invalid token — Telegram returned {}".format(r.status_code))
                except Exception as e:
                    st.error("Connection failed: {}".format(e))
            else:
                st.warning("Please enter a token.")

    with st.container(border=True):
        st.markdown("#### ✉  Gmail / Email  (IMAP + SMTP)")
        st.caption("Use a Gmail App Password. Enable at: Google Account → Security → 2-Step Verification → App Passwords.")
        gm_col1, gm_col2 = st.columns(2)
        gmail_user_input = gm_col1.text_input(
            "Gmail Address", value=st.session_state.get("gmail_user", ""),
            placeholder="support@yourcompany.com", key="gmail_user_field",
        )
        gmail_pass_input = gm_col2.text_input(
            "App Password", value=st.session_state.get("gmail_pass", ""),
            type="password", placeholder="xxxx xxxx xxxx xxxx", key="gmail_pass_field",
        )
        imap_server_input = st.text_input(
            "IMAP Server", value=st.session_state.get("imap_server", "imap.gmail.com"),
            help="imap.gmail.com for Gmail · outlook.office365.com for Outlook",
            key="imap_server_field",
        )
        if st.button("Save & Test Email", key="save_gmail"):
            if gmail_user_input.strip() and gmail_pass_input.strip():
                import imaplib as _imap
                try:
                    server = imap_server_input.strip() or "imap.gmail.com"
                    mail = _imap.IMAP4_SSL(server)
                    mail.login(gmail_user_input.strip(), gmail_pass_input.strip())
                    mail.logout()
                    st.session_state["gmail_user"]  = gmail_user_input.strip()
                    st.session_state["gmail_pass"]  = gmail_pass_input.strip()
                    st.session_state["imap_server"] = server
                    st.success("Connected to {} via {}".format(gmail_user_input.strip(), server))
                except Exception as e:
                    st.error("Connection failed: {}".format(e))
            else:
                st.warning("Please enter both email address and app password.")

    with st.container(border=True):
        st.markdown("#### ⊕  Web Form")
        st.info("Customer web form is always active. Run it separately: `streamlit run ui/web_form.py --server.port 8502`")
        support_email = os.environ.get("SUPPORT_EMAIL", os.environ.get("GMAIL_USER", "not set"))
        st.caption("Submissions are sent to: **{}**".format(support_email))

    with st.container(border=True):
        st.markdown("#### ⚡  AI Engine — IBM Granite")
        ai_key_input = st.text_input(
            "OpenRouter API Key", value=st.session_state.get("openrouter_key", ""),
            type="password", placeholder="sk-or-v1-…", key="ai_key_field",
        )
        if st.button("Save AI Key", key="save_ai"):
            if ai_key_input.strip():
                st.session_state["openrouter_key"] = ai_key_input.strip()
                os.environ["OPENROUTER_API_KEY"]   = ai_key_input.strip()
                st.success("IBM Granite API key saved for this session.")
            else:
                st.warning("Please enter a key.")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 📥  Inbox
# ══════════════════════════════════════════════════════════════════════════════

if page == "📥  Inbox":

    # Fetch row
    fetch_col_tg, fetch_col_gm, spacer = st.columns([1, 1, 4])

    if fetch_col_tg.button("✈  Fetch Telegram", key="tg_fetch", use_container_width=True):
        tg_tok = st.session_state.get("tg_token", "")
        if not tg_tok:
            st.warning("No Telegram token. Go to Settings to configure it.")
        else:
            from intake.channels import fetch_telegram_updates
            with st.spinner("Polling Telegram…"):
                new_tickets, new_last_id = fetch_telegram_updates(tg_tok, st.session_state.tg_last_id)
            if new_tickets:
                st.session_state.inbox.extend(new_tickets)
                st.session_state.tg_last_id = new_last_id
                st.success("{} new message(s) added.".format(len(new_tickets)))
                st.rerun()
            else:
                st.info("No new Telegram messages.")

    if fetch_col_gm.button("✉  Fetch Gmail", key="gm_fetch", use_container_width=True):
        gm_user = st.session_state.get("gmail_user", "")
        gm_pass = st.session_state.get("gmail_pass", "")
        if not gm_user or not gm_pass:
            st.warning("No Gmail credentials. Go to Settings to configure them.")
        else:
            from intake.channels import fetch_unread_emails
            with st.spinner("Reading Gmail IMAP…"):
                new_emails = fetch_unread_emails(gm_user, gm_pass)
            if new_emails:
                st.session_state.inbox.extend(new_emails)
                st.success("{} unread email(s) added.".format(len(new_emails)))
                st.rerun()
            else:
                st.info("No unread [SUPPORT-TICKET] emails found.")

    inbox = st.session_state.inbox

    if not inbox:
        st.markdown(
            "<div style='text-align:center;padding:5rem 2rem'>"
            "<div style='font-size:2.8rem;opacity:0.3'>&#128236;</div>"
            "<h3 style='color:#334155;margin:0.6rem 0 0.3rem;font-weight:600'>Inbox is empty</h3>"
            "<p style='color:#334155;font-size:0.84rem'>Click <b>Reset Inbox</b> in the sidebar to reload "
            "the demo queue, or connect a live channel above.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Search + filter bar
    sf_col1, sf_col2, sf_col3 = st.columns([3, 1, 1])
    search_q   = sf_col1.text_input("", placeholder="Search by subject, sender, error code…",
                                    label_visibility="collapsed", key="inbox_search")
    pri_filter = sf_col2.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"],
                                   label_visibility="collapsed", key="inbox_pri")
    ch_filter  = sf_col3.selectbox("Channel", ["All", "Email", "Telegram", "Web"],
                                   label_visibility="collapsed", key="inbox_ch")

    # Filters
    visible = inbox
    if search_q:
        q = search_q.lower()
        visible = [t for t in visible if q in (t.subject or "").lower()
                   or q in (t.sender or "").lower()
                   or any(q in e.lower() for e in t.error_codes)]
    if pri_filter != "All":
        visible = [t for t in visible if (t.priority or "").lower() == pri_filter.lower()]
    if ch_filter != "All":
        visible = [t for t in visible if (t.channel or "").lower() == ch_filter.lower()]

    # Header row with channel pill counts
    ch_counts = Counter(t.channel for t in inbox)
    ch_pills  = "  ".join(
        "<span style='background:{bg};color:{c};padding:2px 10px;border-radius:20px;"
        "font-size:0.65rem;font-weight:700;letter-spacing:0.2px'>{ch} {n}</span>".format(
            bg="#111d30", c=_CHANNEL_COLOR.get(ch, "#475569"),
            ch=ch.upper(), n=n,
        )
        for ch, n in sorted(ch_counts.items())
    )
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin:0.6rem 0 0.4rem'>"
        "<div style='display:flex;align-items:baseline;gap:0.6rem'>"
        "<h3 style='margin:0;font-size:1.1rem'>Triage Queue</h3>"
        "<span style='color:#334155;font-size:0.82rem'>{showing} / {total} tickets</span>"
        "</div>"
        "<div style='display:flex;gap:0.35rem'>{pills}</div>"
        "</div>".format(showing=len(visible), total=len(inbox), pills=ch_pills),
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='margin:0 0 0.6rem'>", unsafe_allow_html=True)

    if not visible:
        st.info("No tickets match your filter.")
        st.stop()

    # Ticket rows
    for t in visible:
        pri   = (t.priority or "medium").lower()
        ch    = (t.channel  or "web").lower()
        icon  = _CHANNEL_ICON.get(ch, "?")
        body_flat   = (t.body or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        preview     = (body_flat[:115] + "…") if len(body_flat) > 115 else body_flat
        id_safe     = _html.escape(t.id      or "")
        sender_safe = _html.escape(t.sender  or "")
        subj_safe   = _html.escape(t.subject or "")
        prev_safe   = _html.escape(preview)
        sla_html    = _sla_badge(t.priority)
        errs = "  ".join(
            "<code style='background:#0d1526;color:#60a5fa;padding:1px 5px;"
            "border-radius:3px;font-size:0.68rem;border:1px solid #1e3a6e'>{e}</code>".format(
                e=_html.escape(e)
            ) for e in t.error_codes
        ) if t.error_codes else ""

        st.markdown(
            "<div class='tkt-row tkt-row-{pri}'>"
            "<span style='font-size:0.88rem;flex-shrink:0;padding-top:3px;"
            "color:{chcol};opacity:0.85'>{icon}</span>"
            "<div style='flex:1;min-width:0'>"
            "<div style='display:flex;align-items:center;gap:0.4rem;margin-bottom:0.15rem;flex-wrap:wrap'>"
            "<span style='color:#1e3a6e;font-size:0.68rem;font-family:monospace;font-weight:600'>{tid}</span>"
            "<span style='color:{chcol};font-size:0.68rem;font-weight:700'>{chan}</span>"
            "<span style='color:#475569;font-size:0.68rem'>{sender}</span>"
            "{sla}{errs}"
            "</div>"
            "<div style='color:#e2e8f0;font-weight:600;font-size:0.87rem;margin-bottom:0.12rem;"
            "white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{subj}</div>"
            "<div style='color:#475569;font-size:0.76rem;line-height:1.4'>{prev}</div>"
            "</div>"
            "<span class='pill pill-untriaged' style='flex-shrink:0;margin-top:2px'>UNTRIAGED</span>"
            "</div>".format(
                pri=pri, icon=icon, chcol=_CHANNEL_COLOR.get(ch, "#475569"),
                tid=id_safe, chan=ch.upper(), sender=sender_safe,
                sla=sla_html, errs=errs, subj=subj_safe, prev=prev_safe,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    if st.button(
        "Run AI Triage on {} Ticket(s)  —  IBM Granite".format(len(inbox)),
        type="primary", use_container_width=True, key="run_triage",
    ):
        from guardrails.pii_redactor import redact
        from pipeline.classify import classify
        from pipeline.draft import draft_reply
        from pipeline.extract import extract
        from pipeline.summarize import summarize
        from rag.store import init_store
        from routing.router import route

        n          = len(inbox)
        progress   = st.progress(0, text="Initialising IBM Granite…")
        collection = init_store()
        t_start    = time.perf_counter()

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

        raw     = asyncio.run(_triage_all(list(inbox)))
        elapsed = time.perf_counter() - t_start

        new_results = []
        for i, (t, r) in enumerate(raw):
            new_results.append((t, r))
            progress.progress((i + 1) / n, text="Triaged {}/{}…".format(i + 1, n))

        st.session_state.processed.extend(new_results)
        st.session_state.inbox = []

        log_lines = ["[IBM Granite] {} tickets in {:.2f}s (async batch)\n".format(n, elapsed)]
        for t, r in new_results:
            log_lines.append(
                "  [{:<9}] {:<10} → {:<22} | conf={:.2f} | status={:<12} | priority={}\n".format(
                    t.channel.upper(), t.id, r["queue"],
                    t.classify_confidence, r.get("status", "?"),
                    t.priority or "unknown",
                )
            )
        st.session_state.log += "".join(log_lines)
        progress.empty()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 📊  Dashboard
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊  Dashboard":

    results = st.session_state.processed
    if not results:
        st.info("No processed tickets yet. Go to Inbox and run AI triage first.")
        st.stop()

    # Compute stats
    total           = len(results)
    auto_routed     = [p for p in results if p[1].get("status") == "auto-routed"]
    hitl_list       = [p for p in results if p[1].get("status") == "human-review"]
    escalated_list  = [p for p in results if p[1].get("status") == "escalated"]
    approved_list   = [p for p in results if p[1].get("status") == "approved"]
    avg_conf        = sum(t.classify_confidence for t, _ in results) / total
    automation_rate = len(auto_routed) / total
    escalation_rate = len(escalated_list) / total
    hitl_rate       = len(hitl_list) / total
    avg_severity    = sum(r.get("severity_impact", 0) for _, r in results) / total
    pri_counts      = Counter((t.priority or "medium").lower() for t, _ in results)
    cat_counts      = Counter((t.category or "other").lower() for t, _ in results)
    ch_counts       = Counter(t.channel for t, _ in results)
    sla_breach      = sum(1 for t, _ in results if (t.priority or "").lower() == "critical")
    misroute_saved  = int(len(auto_routed) * 0.35)
    annual_saving   = int(misroute_saved * 12 * 27)

    # ── Impact banner ──────────────────────────────────────────────────────────
    st.markdown(
        "<div class='impact-banner'>"
        "<p class='sec-lbl' style='margin-bottom:0.6rem'>Enterprise Business Impact</p>"
        "<div style='display:flex;gap:2.5rem;flex-wrap:wrap'>"
        "<div><div style='color:#334155;font-size:0.72rem;font-weight:600'>Auto-Routed</div>"
        "<div style='color:#f1f5f9;font-size:1.35rem;font-weight:800;letter-spacing:-0.4px'>"
        "{ar} <span style='font-size:0.78rem;color:#60a5fa;font-weight:600'>({ar_pct:.0%})</span></div></div>"
        "<div><div style='color:#334155;font-size:0.72rem;font-weight:600'>Misroutes Prevented</div>"
        "<div style='color:#f1f5f9;font-size:1.35rem;font-weight:800;letter-spacing:-0.4px'>{ms}</div></div>"
        "<div><div style='color:#334155;font-size:0.72rem;font-weight:600'>Est. Annual Saving</div>"
        "<div style='color:#4ade80;font-size:1.35rem;font-weight:800;letter-spacing:-0.4px'>${sav:,}</div></div>"
        "<div><div style='color:#334155;font-size:0.72rem;font-weight:600'>Avg AI Confidence</div>"
        "<div style='color:#f1f5f9;font-size:1.35rem;font-weight:800;letter-spacing:-0.4px'>{conf:.0%}</div></div>"
        "<div><div style='color:#334155;font-size:0.72rem;font-weight:600'>Critical SLA Tickets</div>"
        "<div style='color:#f87171;font-size:1.35rem;font-weight:800;letter-spacing:-0.4px'>{sla}</div></div>"
        "</div>"
        "</div>".format(
            ar=len(auto_routed), ar_pct=automation_rate,
            ms=misroute_saved, sav=annual_saving,
            conf=avg_conf, sla=sla_breach,
        ),
        unsafe_allow_html=True,
    )

    # ── KPI grid — 8 cards ─────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Processed",   total)
    k2.metric("Auto-Routed",       "{} ({:.0%})".format(len(auto_routed), automation_rate))
    k3.metric("Human Review",      len(hitl_list),
              delta="-{:.0%} held".format(hitl_rate) if hitl_list else None)
    k4.metric("Escalated",         len(escalated_list),
              delta="↑ {:.0%}".format(escalation_rate) if escalated_list else None)

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Avg Confidence",    "{:.0%}".format(avg_conf))
    k6.metric("Avg Severity",      "{:.1f} / 10".format(avg_severity))
    k7.metric("Agent-Approved",    len(approved_list))
    k8.metric("Est. Annual Saving", "${:,}".format(annual_saving))

    st.divider()

    # ── Confidence gauge + Priority breakdown ──────────────────────────────────
    gauge_col, pri_col = st.columns([3, 2])

    with gauge_col:
        conf_c = "#4ade80" if avg_conf > 0.85 else "#fb923c" if avg_conf >= 0.6 else "#f87171"
        bar_w  = "{:.0f}".format(avg_conf * 100)
        st.markdown(
            "<div class='kpi-panel' style='margin-bottom:0'>"
            "<p class='sec-lbl'>AI Classification Confidence</p>"
            "<div style='display:flex;justify-content:space-between;align-items:baseline;margin-bottom:0.6rem'>"
            "<span style='color:#94a3b8;font-size:0.8rem'>Batch average</span>"
            "<span style='color:{cc};font-size:1.6rem;font-weight:800;letter-spacing:-0.5px'>"
            "{pct}</span>"
            "</div>"
            "<div style='background:#1e2d45;border-radius:5px;height:10px;width:100%;overflow:hidden'>"
            "<div style='background:{cc};height:10px;width:{bw}%;border-radius:5px;transition:width 0.5s'>"
            "</div></div>"
            "<div style='display:flex;justify-content:space-between;margin-top:6px'>"
            "<small style='color:{cc};font-size:0.7rem;font-weight:600'>{pct} batch avg</small>"
            "<small style='color:#f87171;font-size:0.7rem'>▲ 85% HITL threshold</small>"
            "</div>"
            "</div>".format(cc=conf_c, pct="{:.0%}".format(avg_conf), bw=bar_w),
            unsafe_allow_html=True,
        )

    with pri_col:
        st.markdown(
            "<div class='kpi-panel' style='margin-bottom:0'>"
            "<p class='sec-lbl'>Priority Distribution</p>",
            unsafe_allow_html=True,
        )
        for pri_name, pri_color in [("critical", "#f87171"), ("high", "#fb923c"),
                                     ("medium",   "#60a5fa"), ("low",  "#4ade80")]:
            cnt   = pri_counts.get(pri_name, 0)
            pct   = cnt / total if total else 0
            width = "{:.0f}".format(pct * 100)
            st.markdown(
                "<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem'>"
                "<span style='color:{c};font-size:0.68rem;font-weight:700;width:54px;text-transform:uppercase'>"
                "{p}</span>"
                "<div class='pri-track'>"
                "<div style='background:{c};height:6px;border-radius:3px;width:{w}%'></div>"
                "</div>"
                "<span style='color:#475569;font-size:0.72rem;width:26px;text-align:right;font-weight:600'>"
                "{n}</span>"
                "</div>".format(c=pri_color, p=pri_name, w=width, n=cnt),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ── Outage Radar ───────────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='margin-bottom:0.15rem'>Outage Radar</h3>"
        "<p style='color:#334155;font-size:0.78rem;margin-bottom:0.85rem'>"
        "Cross-channel symptom clustering — 3+ tickets triggers systemic outage alert</p>",
        unsafe_allow_html=True,
    )

    symptom_tickets: dict[str, list] = defaultdict(list)
    for t, _ in results:
        for sym in (t.symptoms or []):
            symptom_tickets[sym].append(t)

    outage_found = False
    for symptom, tix in sorted(symptom_tickets.items(), key=lambda x: -len(x[1])):
        count    = len(tix)
        channels = sorted({t.channel for t in tix})
        ch_str   = "  ".join(
            "<span style='color:{c};font-weight:700;font-size:0.78rem'>{ch}</span>".format(
                c=_CHANNEL_COLOR.get(c, "#475569"), ch=c.upper(),
            ) for c in channels
        )
        ids_html  = " ".join(
            "<code style='background:#0d1526;color:#60a5fa;padding:1px 5px;"
            "border-radius:3px;font-size:0.68rem'>{id}</code>".format(id=_html.escape(t.id))
            for t in tix
        )
        sym_safe = _html.escape(symptom)
        if count >= 3:
            outage_found = True
            st.markdown(
                "<div class='outage-critical'>"
                "<div style='font-size:0.9rem;font-weight:700;color:#f87171;margin-bottom:0.3rem'>"
                "SYSTEMIC OUTAGE — {count} reports</div>"
                "<div style='color:#e2e8f0;font-size:0.83rem;margin-bottom:0.2rem'>"
                "Symptom: <b>&quot;{symptom}&quot;</b> &nbsp;·&nbsp; Channels: {ch_str}"
                "</div>"
                "<div style='color:#475569;font-size:0.74rem;margin-bottom:0.2rem'>"
                "Affected: {ids}</div>"
                "<div style='color:#f87171;font-size:0.74rem;font-weight:600'>"
                "Escalate to engineering — check status page and notify stakeholders."
                "</div>"
                "</div>".format(count=count, symptom=sym_safe, ch_str=ch_str, ids=ids_html),
                unsafe_allow_html=True,
            )
        elif count == 2:
            st.markdown(
                "<div class='outage-warn'>"
                "<span style='color:#fb923c;font-weight:700;font-size:0.82rem'>"
                "Pattern emerging</span>&nbsp;&nbsp;"
                "<span style='color:#94a3b8;font-size:0.8rem'>"
                "<b>{count} tickets</b> — <b>&quot;{symptom}&quot;</b> — {ch_str}"
                "</span>&nbsp;"
                "<span style='color:#475569;font-size:0.74rem'>Monitor for further reports.</span>"
                "</div>".format(count=count, symptom=sym_safe, ch_str=ch_str),
                unsafe_allow_html=True,
            )

    if not outage_found and not any(len(v) >= 2 for v in symptom_tickets.values()):
        st.success("No outage patterns detected across {} processed tickets.".format(total))

    st.divider()

    # ── Charts ─────────────────────────────────────────────────────────────────
    col_cat, col_ch, col_queue = st.columns(3)

    with col_cat:
        st.markdown("<p class='sec-lbl'>Volume by Category</p>", unsafe_allow_html=True)
        st.bar_chart(
            pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
            .sort_values("Tickets", ascending=False),
            height=220,
        )

    with col_ch:
        st.markdown("<p class='sec-lbl'>Volume by Channel</p>", unsafe_allow_html=True)
        st.bar_chart(
            pd.DataFrame.from_dict(ch_counts, orient="index", columns=["Tickets"]),
            height=220,
        )

    with col_queue:
        st.markdown("<p class='sec-lbl'>Routing Outcome</p>", unsafe_allow_html=True)
        routing_data = {
            "Auto-Routed":  len(auto_routed),
            "Human Review": len(hitl_list),
            "Escalated":    len(escalated_list),
            "Approved":     len(approved_list),
        }
        st.bar_chart(
            pd.DataFrame.from_dict(routing_data, orient="index", columns=["Tickets"]),
            height=220,
        )

    st.divider()

    # ── Queue depth table ──────────────────────────────────────────────────────
    queue_counts: dict[str, list] = defaultdict(list)
    for t, r in results:
        queue_counts[r.get("queue", "unknown")].append(t)

    st.markdown("<p class='sec-lbl'>Queue Depth &amp; Severity</p>", unsafe_allow_html=True)
    tbl_cols = st.columns([3, 1, 1, 2])
    for hdr, col in zip(["Queue", "Tickets", "Avg Conf", "Top Priority"], tbl_cols):
        col.markdown(
            "<span style='color:#334155;font-size:0.72rem;font-weight:700'>{}</span>".format(hdr),
            unsafe_allow_html=True,
        )
    for q_name, q_tickets in sorted(queue_counts.items(), key=lambda x: -len(x[1])):
        avg_sev   = sum(t.classify_confidence for t in q_tickets) / len(q_tickets)
        top_pri   = Counter((t.priority or "medium").lower() for t in q_tickets).most_common(1)
        top_pri_s = top_pri[0][0].upper() if top_pri else "—"
        pri_c     = _PRIORITY_COLOR.get(top_pri_s.lower(), "#475569")
        row_c     = st.columns([3, 1, 1, 2])
        row_c[0].markdown(
            "<code style='background:#0d1526;color:#94a3b8;font-size:0.78rem;"
            "padding:2px 6px;border-radius:4px;border:1px solid #1e2d45'>{}</code>".format(q_name),
            unsafe_allow_html=True,
        )
        row_c[1].markdown("**{}**".format(len(q_tickets)))
        row_c[2].markdown("{:.0%}".format(avg_sev))
        row_c[3].markdown(
            "<span style='color:{c};font-weight:700;font-size:0.82rem'>{p}</span>".format(
                c=pri_c, p=top_pri_s),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── System log ────────────────────────────────────────────────────────────
    with st.expander("System Execution Log", expanded=False):
        log_text = _html.escape(st.session_state.log or "(no triage runs yet)")
        st.markdown("<div class='terminal'>{}</div>".format(log_text), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 🧑‍💻  Review Queue
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🧑‍💻  Review Queue":

    results = st.session_state.processed
    if not results:
        st.info("No processed tickets yet. Go to Inbox and run AI triage first.")
        st.stop()

    hitl_pairs = [
        (i, t, r) for i, (t, r) in enumerate(results)
        if r.get("status") == "human-review" and t.status != "approved"
    ]

    if not hitl_pairs:
        st.success("Review queue is clear — all low-confidence tickets have been approved.")
        approved_count = sum(1 for _, r in results if r.get("status") == "approved")
        if approved_count:
            st.info("{} ticket(s) previously approved and routed by agents.".format(approved_count))
        st.stop()

    # Header + confidence distribution
    hdr_col, dist_col = st.columns([2, 3])
    with hdr_col:
        st.markdown(
            "<h3 style='margin-bottom:0.15rem'>{n} Ticket(s) Awaiting Approval</h3>"
            "<p style='color:#475569;font-size:0.78rem;margin:0'>"
            "Confidence &le; 85% — held for human review before routing.</p>".format(n=len(hitl_pairs)),
            unsafe_allow_html=True,
        )
    with dist_col:
        conf_vals = [t.classify_confidence for _, t, _ in hitl_pairs]
        high_conf = sum(1 for c in conf_vals if c >= 0.7)
        med_conf  = sum(1 for c in conf_vals if 0.5 <= c < 0.7)
        low_conf  = sum(1 for c in conf_vals if c < 0.5)
        dc1, dc2, dc3 = st.columns(3)
        dc1.metric("≥ 70% conf", high_conf)
        dc2.metric("50 – 70%",   med_conf)
        dc3.metric("< 50%",      low_conf)

    # Bulk approve
    bulk_candidates = [(i, t, r) for i, t, r in hitl_pairs if t.classify_confidence >= 0.75]
    if bulk_candidates:
        if st.button(
            "Bulk Approve {} high-confidence tickets (≥ 75%)".format(len(bulk_candidates)),
            use_container_width=True, key="bulk_approve",
        ):
            for i, t, r in bulk_candidates:
                t.status   = "approved"
                results[i] = (t, {**r, "status": "approved"})
                st.session_state.log += "  [BULK APPROVED] {} → {} (conf={:.0%})\n".format(
                    t.id, r.get("queue", "unknown"), t.classify_confidence)
            st.session_state.processed = results
            st.success("{} tickets bulk-approved.".format(len(bulk_candidates)))
            st.rerun()

    st.divider()

    for idx, t, r in hitl_pairs:
        conf       = t.classify_confidence
        conf_color = "#4ade80" if conf >= 0.7 else "#fb923c" if conf >= 0.5 else "#f87171"
        ch         = (t.channel or "web").lower()
        sender_safe = _html.escape(t.sender or "")

        with st.expander(
            "{ch}  {tid}  —  {subj}{ellip}".format(
                ch=_CHANNEL_ICON.get(ch, "?"), tid=t.id,
                subj=t.subject[:72], ellip="…" if len(t.subject) > 72 else "",
            ),
            expanded=False,
        ):
            # HITL header card
            st.markdown(
                "<div class='hitl-hdr'>"
                "<div style='margin-bottom:0.4rem'>{pills}</div>"
                "<div style='display:flex;gap:2rem;flex-wrap:wrap'>"
                "<span style='color:#475569;font-size:0.76rem'>Sender: "
                "<b style='color:#94a3b8'>{sender}</b></span>"
                "<span style='color:#475569;font-size:0.76rem'>Queue held: "
                "<b style='color:#fb923c'>human-review</b></span>"
                "<span style='color:#475569;font-size:0.76rem'>Severity: "
                "<b style='color:{cc}'>{sev:.1f} / 10</b></span>"
                "<span style='color:#475569;font-size:0.76rem'>Confidence: "
                "<b style='color:{cc}'>{conf:.0%}</b></span>"
                "</div>"
                "</div>".format(
                    pills=_pills(t), sender=sender_safe,
                    cc=conf_color, sev=r["severity_impact"], conf=conf,
                ),
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([1, 1])

            with c1:
                st.markdown("<p class='sec-lbl'>AI Reasoning</p>", unsafe_allow_html=True)
                st.markdown(
                    "<div class='data-panel'>"
                    + _dp_row("Category",   _html.escape(t.category or "unknown"))
                    + _dp_row("Priority",   _html.escape(t.priority or "unknown"))
                    + _dp_row("Confidence", "{:.0%}".format(conf))
                    + _dp_row("Threshold",  "85% — below = held")
                    + "</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div style='margin-top:0.5rem'>{}</div>".format(_conf_bar_html(conf, 180)),
                    unsafe_allow_html=True,
                )
                if t.error_codes:
                    codes = " ".join(
                        "<code style='background:#0d1526;color:#60a5fa;padding:1px 5px;"
                        "border-radius:3px;font-size:0.7rem;border:1px solid #1e3a6e'>{e}</code>".format(
                            e=_html.escape(e))
                        for e in t.error_codes
                    )
                    st.markdown(
                        "<div style='margin-top:0.5rem'><span style='color:#475569;"
                        "font-size:0.74rem;font-weight:600'>Error codes:</span> {}</div>".format(codes),
                        unsafe_allow_html=True,
                    )
                if t.symptoms:
                    chips = " ".join(
                        "<span style='background:#0d1526;color:#475569;padding:1px 7px;"
                        "border-radius:10px;font-size:0.7rem;border:1px solid #1e2d45'>{s}</span>".format(
                            s=_html.escape(s)) for s in t.symptoms
                    )
                    st.markdown(
                        "<div style='margin-top:0.4rem'>"
                        "<span style='color:#475569;font-size:0.74rem;font-weight:600'>"
                        "Symptoms:</span> {}</div>".format(chips),
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    "<p class='sec-lbl' style='margin-top:0.75rem'>AI Summary</p>",
                    unsafe_allow_html=True,
                )
                st.info(t.summary or "_(no summary)_")

            with c2:
                st.markdown("<p class='sec-lbl'>Draft Reply</p>", unsafe_allow_html=True)
                approved_queue = st.selectbox(
                    "Route to queue",
                    options=["queue-auth", "queue-billing", "queue-performance",
                             "queue-data-loss", "queue-product", "queue-general"],
                    index=0,
                    key="queue_select_{}".format(t.id),
                )

                # ── AI Suggestion Panel ──────────────────────────────────────
                draft_key = "draft_{}".format(t.id)
                use_key   = "use_draft_{}".format(t.id)
                ai_draft  = (t.draft_reply or "").strip()

                if ai_draft and not ai_draft.startswith("[STUB]"):
                    draft_preview = ai_draft[:420] + ("…" if len(ai_draft) > 420 else "")
                    st.markdown(
                        "<div class='ai-box'>"
                        "<div class='ai-box-lbl'>&#9671; AI-generated draft</div>"
                        "<div class='ai-box-text'>{preview}</div>"
                        "</div>".format(preview=_html.escape(draft_preview)),
                        unsafe_allow_html=True,
                    )
                    if st.button("Use This Draft", key=use_key, use_container_width=True):
                        st.session_state[draft_key] = ai_draft

                if draft_key not in st.session_state:
                    st.session_state[draft_key] = ai_draft

                edited_draft = st.text_area(
                    "Draft", height=220,
                    label_visibility="collapsed",
                    key=draft_key,
                )
                if st.button(
                    "Approve & Route",
                    key="approve_{}".format(t.id),
                    use_container_width=True, type="primary",
                ):
                    t.draft_reply = edited_draft
                    t.status      = "approved"
                    results[idx]  = (t, {**r, "queue": approved_queue, "status": "approved"})
                    st.session_state.processed = results
                    st.session_state.log += (
                        "  [HITL APPROVED] {} → {} by agent\n".format(t.id, approved_queue)
                    )
                    st.success("{} approved and routed to {}.".format(t.id, approved_queue))
                    st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='margin-top:3rem'>"
    "<p style='text-align:center;color:#1e2d45;font-size:0.7rem;padding:0.5rem 0'>"
    "SupportTriage AI &nbsp;·&nbsp; IBM Granite 4.1 8B &nbsp;·&nbsp; "
    "Built with IBM Bob &nbsp;·&nbsp; IBM AI Builders Challenge 2026"
    "</p>",
    unsafe_allow_html=True,
)
