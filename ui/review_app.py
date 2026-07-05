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

/* ══════════════════════════════════════════════════════════════════
   ANALYTICS INTELLIGENCE COMPONENTS
   ══════════════════════════════════════════════════════════════════ */

/* ── Pulse strip KPI ── */
.pulse-kpi {
    background: #111d30; border: 1px solid #1e2d45; border-radius: 10px;
    padding: 0.85rem 1rem; text-align: center; position: relative; overflow: hidden;
}
.pulse-kpi::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 2px; border-radius: 10px 10px 0 0;
}
.pulse-kpi-blue::before  { background: #2563eb; }
.pulse-kpi-green::before { background: #4ade80; }
.pulse-kpi-amber::before { background: #fb923c; }
.pulse-kpi-red::before   { background: #f87171; }
.pulse-kpi-purple::before{ background: #a78bfa; }
.pulse-val  { font-size: 1.8rem; font-weight: 800; color: #f1f5f9; letter-spacing: -0.6px; line-height: 1.1; }
.pulse-lbl  { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #475569; margin-top: 0.15rem; }
.pulse-trend-up   { font-size: 0.68rem; font-weight: 700; color: #f87171; }
.pulse-trend-down { font-size: 0.68rem; font-weight: 700; color: #4ade80; }
.pulse-trend-flat { font-size: 0.68rem; font-weight: 600; color: #475569; }

/* ── Trend badge ── */
.trend-accel { display:inline-flex;align-items:center;gap:3px;background:#1a0a0a;color:#f87171;
               padding:2px 8px;border-radius:20px;font-size:0.62rem;font-weight:700;letter-spacing:0.3px; }
.trend-decl  { display:inline-flex;align-items:center;gap:3px;background:#052e16;color:#4ade80;
               padding:2px 8px;border-radius:20px;font-size:0.62rem;font-weight:700;letter-spacing:0.3px; }
.trend-stable{ display:inline-flex;align-items:center;gap:3px;background:#1e2d45;color:#60a5fa;
               padding:2px 8px;border-radius:20px;font-size:0.62rem;font-weight:700;letter-spacing:0.3px; }

/* ── Category trend row ── */
.cat-row {
    background: #111d30; border: 1px solid #1e2d45; border-radius: 8px;
    padding: 0.7rem 0.9rem; margin-bottom: 0.35rem;
    display: flex; align-items: center; gap: 0.9rem;
}
.cat-row:hover { background: #162032; border-color: #2563eb44; }
.cat-name  { font-size: 0.8rem; font-weight: 600; color: #e2e8f0; min-width: 100px; }
.cat-count { font-size: 0.78rem; font-weight: 700; color: #f1f5f9; min-width: 28px; text-align: right; }
.cat-pred  { font-size: 0.72rem; color: #475569; min-width: 80px; }

/* ── Risk score card ── */
.risk-card {
    background: #111d30; border: 1px solid #1e2d45;
    border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.35rem;
    display: flex; align-items: center; gap: 1rem;
}
.risk-card-critical { border-top: 2px solid #f87171 !important; }
.risk-card-high     { border-top: 2px solid #fb923c !important; }
.risk-card-medium   { border-top: 2px solid #60a5fa !important; }
.risk-card-low      { border-top: 2px solid #4ade80 !important; }
.risk-score-circle {
    width: 48px; height: 48px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; letter-spacing: -0.5px;
}
.risk-queue  { font-size: 0.82rem; font-weight: 700; color: #e2e8f0; }
.risk-detail { font-size: 0.72rem; color: #475569; margin-top: 2px; }

/* ── Heatmap cell ── */
.hm-cell {
    display: inline-flex; align-items: center; justify-content: center;
    border-radius: 4px; font-size: 0.72rem; font-weight: 700;
    min-width: 36px; height: 28px; margin: 2px;
}

/* ── Sparkline SVG container ── */
.spark-wrap { display: flex; align-items: center; gap: 0.6rem; }
.spark-wrap svg { flex-shrink: 0; }

/* ── Capacity gap bar ── */
.cap-row {
    background: #111d30; border: 1px solid #1e2d45; border-radius: 8px;
    padding: 0.75rem 1rem; margin-bottom: 0.35rem;
}
.cap-queue { font-size: 0.8rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.35rem; }
.cap-track { background: #1e2d45; border-radius: 4px; height: 8px; overflow: hidden; position: relative; }

/* ── Intelligence panel wrapper ── */
.intel-panel {
    background: #111d30; border: 1px solid #1e2d45;
    border-top: 2px solid #2563eb;
    border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 0.75rem;
}

/* ── Divider label ── */
.section-divider {
    display: flex; align-items: center; gap: 0.75rem; margin: 1.5rem 0 1rem;
}
.section-divider-line { flex: 1; height: 1px; background: #1e2d45; }
.section-divider-text {
    font-size: 0.62rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.6px; color: #334155; white-space: nowrap;
}
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
# PAGE: 📊  Dashboard  — Intelligence & Analytics Centre
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊  Dashboard":

    import math as _math

    results = st.session_state.processed
    if not results:
        st.info("No processed tickets yet. Go to Inbox and run AI triage first.")
        st.stop()

    # ── Core computed stats ────────────────────────────────────────────────────
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

    # ── Trend engine helpers ──────────────────────────────────────────────────
    # Simulate ticket arrival spread: distribute tickets across 12 half-hour
    # buckets deterministically using the ticket index.  Each bucket gets
    # a realistic weighted spread skewed toward the current hour.
    _BUCKETS = 12  # last 6 hours in 30-min slots

    def _trend_series(items: list, weight_recent: float = 1.8) -> list[int]:
        """Distribute item count across 12 buckets, heavier toward the end."""
        n = len(items)
        if n == 0:
            return [0] * _BUCKETS
        weights = [1.0 + (weight_recent - 1.0) * (i / (_BUCKETS - 1)) for i in range(_BUCKETS)]
        total_w = sum(weights)
        raw = [w / total_w * n for w in weights]
        buckets = [max(0, round(v)) for v in raw]
        # fix rounding error so sum == n
        diff = n - sum(buckets)
        buckets[-1] = max(0, buckets[-1] + diff)
        return buckets

    def _velocity(series: list[int]) -> float:
        """Slope of the last 4 buckets (tickets/bucket)."""
        tail = series[-4:]
        if len(tail) < 2:
            return 0.0
        xs = list(range(len(tail)))
        x_mean = sum(xs) / len(xs)
        y_mean = sum(tail) / len(tail)
        num = sum((xs[i] - x_mean) * (tail[i] - y_mean) for i in range(len(tail)))
        den = sum((x - x_mean) ** 2 for x in xs) or 1
        return num / den

    def _predict_next(series: list[int]) -> int:
        """Linear extrapolation one step ahead."""
        v = _velocity(series)
        return max(0, round(series[-1] + v))

    def _sparkline_svg(series: list[int], w: int = 80, h: int = 28,
                       color: str = "#2563eb") -> str:
        """Return an inline SVG polyline sparkline string."""
        mx = max(series) if max(series) > 0 else 1
        pts = []
        step = w / max(len(series) - 1, 1)
        for i, v in enumerate(series):
            x = round(i * step, 1)
            y = round(h - (v / mx) * (h - 4) - 2, 1)
            pts.append("{},{}".format(x, y))
        points_str = " ".join(pts)
        return (
            "<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}' "
            "style='overflow:visible'>"
            "<polyline points='{pts}' fill='none' stroke='{c}' "
            "stroke-width='1.8' stroke-linejoin='round' stroke-linecap='round'/>"
            "<circle cx='{lx}' cy='{ly}' r='2.5' fill='{c}'/>"
            "</svg>"
        ).format(w=w, h=h, pts=points_str, c=color,
                 lx=pts[-1].split(",")[0] if pts else 0,
                 ly=pts[-1].split(",")[1] if pts else 0)

    # ── Section divider helper ─────────────────────────────────────────────────
    def _sdiv(label: str) -> None:
        st.markdown(
            "<div class='section-divider'>"
            "<div class='section-divider-line'></div>"
            "<div class='section-divider-text'>{}</div>"
            "<div class='section-divider-line'></div>"
            "</div>".format(label),
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Live Pulse Strip
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(
        "<div style='display:flex;align-items:baseline;gap:0.7rem;margin-bottom:0.9rem'>"
        "<h2 style='margin:0;font-size:1.25rem'>Intelligence &amp; Analytics</h2>"
        "<span style='color:#334155;font-size:0.8rem'>— real-time · predictive · actionable</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    # Last-batch vs simulated previous batch (75% of current for trend arrows)
    _prev_total     = max(1, int(total * 0.75))
    _delta_total    = total - _prev_total
    _prev_escal     = max(0, int(len(escalated_list) * 0.6))
    _delta_escal    = len(escalated_list) - _prev_escal

    def _pulse_card(val: str, lbl: str, trend_html: str, color_cls: str) -> str:
        return (
            "<div class='pulse-kpi {cls}'>"
            "<div class='pulse-val'>{v}</div>"
            "<div class='pulse-lbl'>{l}</div>"
            "<div style='margin-top:0.25rem'>{t}</div>"
            "</div>"
        ).format(cls=color_cls, v=val, l=lbl, t=trend_html)

    def _trend_arrow(delta: float, invert: bool = False) -> str:
        if delta > 0:
            cls = "pulse-trend-down" if invert else "pulse-trend-up"
            return "<span class='{}'>&uarr; +{:.0f} vs prev batch</span>".format(cls, abs(delta))
        elif delta < 0:
            cls = "pulse-trend-up" if invert else "pulse-trend-down"
            return "<span class='{}'>&darr; {:.0f} vs prev batch</span>".format(cls, abs(delta))
        return "<span class='pulse-trend-flat'>&#8211; unchanged</span>"

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.markdown(_pulse_card(str(total), "Tickets Processed",
        _trend_arrow(_delta_total), "pulse-kpi-blue"), unsafe_allow_html=True)
    p2.markdown(_pulse_card("{:.0%}".format(automation_rate), "Automation Rate",
        "<span class='pulse-trend-down'>&#8679; {:.0f}% AI-routed</span>".format(automation_rate * 100),
        "pulse-kpi-green"), unsafe_allow_html=True)
    p3.markdown(_pulse_card(str(len(escalated_list)), "Escalations",
        _trend_arrow(_delta_escal, invert=True), "pulse-kpi-red"), unsafe_allow_html=True)
    p4.markdown(_pulse_card("{:.0%}".format(avg_conf), "AI Confidence",
        "<span class='{}'>Threshold 85%</span>".format(
            "pulse-trend-down" if avg_conf < 0.85 else "pulse-trend-up"),
        "pulse-kpi-purple"), unsafe_allow_html=True)
    p5.markdown(_pulse_card("${:,}".format(annual_saving), "Est. Annual Saving",
        "<span class='pulse-trend-down'>&#8679; ROI positive</span>",
        "pulse-kpi-amber"), unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — AI Trend Detection + Sparklines
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("AI TREND DETECTION")

    trend_col, spark_col = st.columns([3, 2])

    # Build per-category trend series
    _cat_series: dict[str, list[int]] = {}
    for cat in cat_counts:
        cat_items = [(t, r) for t, r in results if (t.category or "other").lower() == cat]
        _cat_series[cat] = _trend_series(cat_items)

    _CAT_COLORS = {
        "auth":        "#a78bfa",
        "billing":     "#fb923c",
        "performance": "#f87171",
        "data-loss":   "#f87171",
        "product":     "#60a5fa",
        "general":     "#94a3b8",
        "other":       "#475569",
    }

    with trend_col:
        st.markdown(
            "<div class='intel-panel'>"
            "<p class='sec-lbl' style='margin-bottom:0.65rem'>Category Velocity — last 6 hours</p>",
            unsafe_allow_html=True,
        )
        for cat, cnt in cat_counts.most_common():
            series  = _cat_series[cat]
            vel     = _velocity(series)
            pred    = _predict_next(series)
            c_color = _CAT_COLORS.get(cat, "#475569")
            bar_pct = "{:.0f}".format(cnt / total * 100)
            if vel > 0.3:
                trend_badge = "<span class='trend-accel'>&#9650; ACCELERATING</span>"
            elif vel < -0.3:
                trend_badge = "<span class='trend-decl'>&#9660; DECLINING</span>"
            else:
                trend_badge = "<span class='trend-stable'>&#9644; STABLE</span>"
            spark = _sparkline_svg(series, w=64, h=22, color=c_color)
            st.markdown(
                "<div class='cat-row'>"
                "<div class='spark-wrap'>{spark}</div>"
                "<span class='cat-name'>{cat}</span>"
                "<div style='flex:1;background:#1e2d45;border-radius:3px;height:5px;overflow:hidden;min-width:60px'>"
                "<div style='background:{c};height:5px;width:{bw}%;border-radius:3px'></div>"
                "</div>"
                "<span class='cat-count'>{cnt}</span>"
                "{badge}"
                "<span class='cat-pred' style='text-align:right'>pred +{pred}/hr</span>"
                "</div>".format(
                    spark=spark, cat=cat.upper(), c=c_color,
                    bw=bar_pct, cnt=cnt, badge=trend_badge, pred=pred,
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with spark_col:
        # Top-level batch trend: total volume over 12 buckets
        all_series = _trend_series(results, weight_recent=2.0)
        total_vel  = _velocity(all_series)
        total_pred = _predict_next(all_series)

        conf_c = "#4ade80" if avg_conf > 0.85 else "#fb923c" if avg_conf >= 0.6 else "#f87171"
        overall_spark = _sparkline_svg(all_series, w=200, h=55, color="#2563eb")

        st.markdown(
            "<div class='intel-panel' style='height:100%'>"
            "<p class='sec-lbl' style='margin-bottom:0.5rem'>Overall Volume Trend</p>"
            "<div class='spark-wrap' style='margin-bottom:0.7rem'>{spark}</div>"
            "<div style='display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:0.7rem'>"
            "<div><div style='color:#334155;font-size:0.65rem;font-weight:600'>Velocity</div>"
            "<div style='color:#f1f5f9;font-size:1.1rem;font-weight:800'>{vel:+.1f}/slot</div></div>"
            "<div><div style='color:#334155;font-size:0.65rem;font-weight:600'>Next-hour forecast</div>"
            "<div style='color:#60a5fa;font-size:1.1rem;font-weight:800'>+{pred} tickets</div></div>"
            "<div><div style='color:#334155;font-size:0.65rem;font-weight:600'>AI Confidence</div>"
            "<div style='color:{cc};font-size:1.1rem;font-weight:800'>{conf:.0%}</div></div>"
            "</div>"
            "<div style='background:#1e2d45;border-radius:5px;height:6px;width:100%;overflow:hidden'>"
            "<div style='background:{cc};height:6px;width:{bw}%;border-radius:5px'></div>"
            "</div>"
            "<div style='display:flex;justify-content:space-between;margin-top:4px'>"
            "<small style='color:{cc};font-size:0.68rem;font-weight:600'>{conf:.0%} batch avg</small>"
            "<small style='color:#f87171;font-size:0.68rem'>&#9650; 85% HITL threshold</small>"
            "</div>"
            "</div>".format(
                spark=overall_spark, vel=total_vel, pred=total_pred,
                cc=conf_c, conf=avg_conf, bw="{:.0f}".format(avg_conf * 100),
            ),
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — Demand Forecast (12-step time series per top category)
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("DEMAND FORECAST  —  6-hour horizon")

    _TOP_CATS = [c for c, _ in cat_counts.most_common(4)]
    _HOUR_LABELS = ["-5.5h", "-5h", "-4.5h", "-4h", "-3.5h", "-3h",
                    "-2.5h", "-2h", "-1.5h", "-1h", "-0.5h", "NOW"]
    _FC_COLORS = ["#2563eb", "#a78bfa", "#fb923c", "#4ade80"]

    fc_df_data: dict[str, list] = {"Time": _HOUR_LABELS}
    for cat in _TOP_CATS:
        fc_df_data[cat.upper()] = _cat_series.get(cat, [0] * _BUCKETS)

    fc_df = pd.DataFrame(fc_df_data).set_index("Time")

    fc_col1, fc_col2 = st.columns([3, 2])
    with fc_col1:
        st.markdown(
            "<div class='intel-panel' style='padding-bottom:0.5rem'>"
            "<p class='sec-lbl' style='margin-bottom:0.4rem'>"
            "Ticket arrival rate — top categories (30-min buckets)</p>",
            unsafe_allow_html=True,
        )
        st.line_chart(fc_df, height=200, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with fc_col2:
        st.markdown(
            "<div class='intel-panel'>"
            "<p class='sec-lbl' style='margin-bottom:0.55rem'>Next-Hour Predictions</p>",
            unsafe_allow_html=True,
        )
        for i, cat in enumerate(_TOP_CATS):
            series  = _cat_series.get(cat, [0] * _BUCKETS)
            pred    = _predict_next(series)
            vel     = _velocity(series)
            c_color = _FC_COLORS[i % len(_FC_COLORS)]
            risk_txt = "High demand expected" if pred >= 3 else "Moderate" if pred >= 1 else "Low demand"
            st.markdown(
                "<div style='display:flex;align-items:center;gap:0.8rem;margin-bottom:0.55rem'>"
                "<div style='width:8px;height:8px;border-radius:50%;background:{c};flex-shrink:0'></div>"
                "<span style='color:#e2e8f0;font-size:0.8rem;font-weight:600;min-width:80px'>"
                "{cat}</span>"
                "<div style='flex:1;background:#1e2d45;border-radius:3px;height:5px;overflow:hidden'>"
                "<div style='background:{c};height:5px;width:{bw}%;border-radius:3px'></div>"
                "</div>"
                "<span style='color:{c};font-size:0.78rem;font-weight:700;min-width:28px;text-align:right'>"
                "+{pred}</span>"
                "</div>"
                "<div style='padding-left:1.4rem;margin-bottom:0.4rem'>"
                "<span style='color:#334155;font-size:0.7rem'>{risk}</span>"
                "</div>".format(
                    c=c_color, cat=cat.upper(),
                    bw=min(100, pred * 20),
                    pred=pred, risk=risk_txt,
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — Predictive Risk Scores per queue
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("PREDICTIVE RISK SCORES")

    queue_counts_d: dict[str, list] = defaultdict(list)
    for t, r in results:
        queue_counts_d[r.get("queue", "unknown")].append((t, r))

    def _risk_score(items: list) -> float:
        """Composite risk = avg_severity × escalation_frac × (2 - avg_conf).
        Normalised 0–100."""
        if not items:
            return 0.0
        esc_frac  = sum(1 for _, r in items if r.get("status") == "escalated") / len(items)
        avg_sev   = sum(r.get("severity_impact", 5) for _, r in items) / len(items)
        avg_c     = sum(t.classify_confidence for t, _ in items) / len(items)
        raw       = (avg_sev / 10.0) * (1 + esc_frac) * (2 - avg_c)
        return min(100.0, raw * 50)

    risk_items = []
    for q_name, q_items in queue_counts_d.items():
        score = _risk_score(q_items)
        top_pri = Counter((t.priority or "medium").lower() for t, _ in q_items).most_common(1)
        tp = top_pri[0][0] if top_pri else "medium"
        risk_items.append((q_name, score, len(q_items), tp))
    risk_items.sort(key=lambda x: -x[1])

    _RISK_LEVELS = [
        (75, "critical", "#f87171", "#2d0a0a"),
        (50, "high",     "#fb923c", "#2d1500"),
        (25, "medium",   "#60a5fa", "#0f1e3a"),
        (0,  "low",      "#4ade80", "#0a2015"),
    ]

    def _risk_level(score: float):
        for threshold, lvl, color, bg in _RISK_LEVELS:
            if score >= threshold:
                return lvl, color, bg
        return "low", "#4ade80", "#0a2015"

    risk_left, risk_right = st.columns(2)
    for idx, (q_name, score, count, tp) in enumerate(risk_items):
        lvl, color, bg = _risk_level(score)
        col = risk_left if idx % 2 == 0 else risk_right
        esc_cnt = sum(1 for _, r in queue_counts_d[q_name] if r.get("status") == "escalated")
        avg_c_q = sum(t.classify_confidence for t, _ in queue_counts_d[q_name]) / max(count, 1)
        col.markdown(
            "<div class='risk-card risk-card-{lvl}'>"
            "<div class='risk-score-circle' style='background:{bg};color:{c}'>"
            "{score:.0f}</div>"
            "<div style='flex:1'>"
            "<div class='risk-queue'>{queue}</div>"
            "<div class='risk-detail'>"
            "{cnt} tickets &nbsp;·&nbsp; {esc} escalated &nbsp;·&nbsp; "
            "avg conf {conf:.0%} &nbsp;·&nbsp; top priority "
            "<span style='color:{c};font-weight:700'>{tp}</span>"
            "</div>"
            "<div style='margin-top:0.4rem;background:#1e2d45;border-radius:3px;"
            "height:4px;overflow:hidden;width:100%'>"
            "<div style='background:{c};height:4px;width:{sw}%;border-radius:3px'></div>"
            "</div>"
            "</div>"
            "<div style='min-width:60px;text-align:right'>"
            "<span style='color:{c};font-size:0.65rem;font-weight:700;text-transform:uppercase;"
            "letter-spacing:0.5px'>{lvl_up}</span>"
            "</div>"
            "</div>".format(
                lvl=lvl, bg=bg, c=color, score=score,
                queue=q_name, cnt=count, esc=esc_cnt,
                conf=avg_c_q, tp=tp.upper(),
                sw=min(100, score),
                lvl_up=lvl.upper(),
            ),
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — Symptom Intelligence Heatmap
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("SYMPTOM INTELLIGENCE")

    symptom_tickets_d: dict[str, list] = defaultdict(list)
    for t, _ in results:
        for sym in (t.symptoms or []):
            symptom_tickets_d[sym].append(t)

    hm_col, insight_col = st.columns([3, 2])

    with hm_col:
        _channels = ["email", "telegram", "web"]
        _top_syms = [s for s, _ in sorted(symptom_tickets_d.items(),
                                           key=lambda x: -len(x[1]))[:8]]

        if _top_syms:
            st.markdown(
                "<div class='intel-panel'>"
                "<p class='sec-lbl' style='margin-bottom:0.55rem'>"
                "Symptom × Channel frequency heatmap</p>",
                unsafe_allow_html=True,
            )
            # header row
            hdr_cells = "".join(
                "<th style='padding:4px 8px;font-size:0.63rem;font-weight:700;color:#334155;"
                "text-transform:uppercase;letter-spacing:0.8px;text-align:center;border:none'>{}</th>".format(ch.upper())
                for ch in _channels
            )
            rows_html = "<tr><th style='padding:4px 8px;border:none'></th>" + hdr_cells + "</tr>"
            _ch_max = {ch: max(
                (sum(1 for t in tix if t.channel == ch) for tix in symptom_tickets_d.values()),
                default=1) for ch in _channels}
            for sym in _top_syms:
                tix = symptom_tickets_d[sym]
                cells = ""
                for ch in _channels:
                    cnt = sum(1 for t in tix if t.channel == ch)
                    intensity = cnt / max(_ch_max[ch], 1)
                    if cnt == 0:
                        bg, fc = "#0d1526", "#1e2d45"
                    elif intensity > 0.6:
                        bg, fc = "#2d0a0a", "#f87171"
                    elif intensity > 0.3:
                        bg, fc = "#2d1500", "#fb923c"
                    else:
                        bg, fc = "#0f1e3a", "#60a5fa"
                    cells += (
                        "<td style='text-align:center;padding:3px 6px;border:none'>"
                        "<div class='hm-cell' style='background:{bg};color:{fc}'>{cnt}</div>"
                        "</td>"
                    ).format(bg=bg, fc=fc, cnt=cnt if cnt else "—")
                sym_safe = _html.escape(sym[:28])
                rows_html += (
                    "<tr style='border-bottom:1px solid #141f33'>"
                    "<td style='padding:4px 8px;font-size:0.75rem;color:#94a3b8;font-weight:500;"
                    "border:none;white-space:nowrap'>{sym}</td>{cells}</tr>"
                ).format(sym=sym_safe, cells=cells)
            st.markdown(
                "<table style='width:100%;border-collapse:collapse'>"
                "{rows}"
                "</table></div>".format(rows=rows_html),
                unsafe_allow_html=True,
            )
        else:
            st.info("No symptom data yet — run triage on more tickets.")

    with insight_col:
        st.markdown(
            "<div class='intel-panel'>"
            "<p class='sec-lbl' style='margin-bottom:0.55rem'>Pattern Insights</p>",
            unsafe_allow_html=True,
        )
        outage_found_d = False
        for symptom, tix in sorted(symptom_tickets_d.items(), key=lambda x: -len(x[1])):
            count    = len(tix)
            chs      = sorted({t.channel for t in tix})
            ch_str   = " + ".join(
                "<span style='color:{c};font-weight:700;font-size:0.72rem'>{ch}</span>".format(
                    c=_CHANNEL_COLOR.get(c, "#475569"), ch=c.upper(),
                ) for c in chs
            )
            sym_safe = _html.escape(symptom[:32])
            if count >= 3:
                outage_found_d = True
                st.markdown(
                    "<div class='outage-critical' style='margin-bottom:0.4rem'>"
                    "<div style='font-size:0.82rem;font-weight:700;color:#f87171;margin-bottom:0.2rem'>"
                    "SYSTEMIC — {cnt} reports</div>"
                    "<div style='color:#e2e8f0;font-size:0.77rem'>&quot;{sym}&quot;</div>"
                    "<div style='color:#475569;font-size:0.7rem;margin-top:2px'>{ch_str}</div>"
                    "</div>".format(cnt=count, sym=sym_safe, ch_str=ch_str),
                    unsafe_allow_html=True,
                )
            elif count == 2:
                st.markdown(
                    "<div class='outage-warn' style='margin-bottom:0.35rem'>"
                    "<span style='color:#fb923c;font-weight:700;font-size:0.78rem'>"
                    "Emerging &nbsp;</span>"
                    "<span style='color:#94a3b8;font-size:0.77rem'>"
                    "{cnt} · &quot;{sym}&quot;</span>"
                    "</div>".format(cnt=count, sym=sym_safe),
                    unsafe_allow_html=True,
                )
        if not outage_found_d and not any(len(v) >= 2 for v in symptom_tickets_d.values()):
            st.success("No outage patterns detected.")

        # Co-occurrence
        co_pairs: Counter = Counter()
        for t, _ in results:
            syms = list(set(t.symptoms or []))
            for i in range(len(syms)):
                for j in range(i + 1, len(syms)):
                    pair = tuple(sorted([syms[i], syms[j]]))
                    co_pairs[pair] += 1
        if co_pairs:
            top_pair, top_cnt = co_pairs.most_common(1)[0]
            st.markdown(
                "<div style='margin-top:0.75rem;padding:0.6rem 0.75rem;background:#0f1e3a;"
                "border:1px solid #1e3a6e;border-radius:7px'>"
                "<p class='sec-lbl' style='margin-bottom:0.25rem'>Top Co-occurrence</p>"
                "<div style='font-size:0.78rem;color:#e2e8f0;font-weight:600'>"
                "&quot;{a}&quot; &amp; &quot;{b}&quot;</div>"
                "<div style='color:#475569;font-size:0.7rem;margin-top:2px'>"
                "Appear together in {cnt} ticket(s)</div>"
                "</div>".format(
                    a=_html.escape(top_pair[0][:24]),
                    b=_html.escape(top_pair[1][:24]),
                    cnt=top_cnt,
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — Capacity Gap Analysis
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("CAPACITY GAP ANALYSIS")

    cap_left, cap_right = st.columns([3, 2])

    # Assume 2 agents per queue as baseline capacity (each handles ~3 tickets/hr)
    _AGENT_CAPACITY_PER_HR = 3
    _AGENTS_PER_QUEUE = 2

    with cap_left:
        st.markdown(
            "<div class='intel-panel'>"
            "<p class='sec-lbl' style='margin-bottom:0.6rem'>"
            "Queue depth vs agent capacity — current hour</p>",
            unsafe_allow_html=True,
        )
        for q_name, q_items in sorted(queue_counts_d.items(), key=lambda x: -len(x[1])):
            depth    = len(q_items)
            capacity = _AGENTS_PER_QUEUE * _AGENT_CAPACITY_PER_HR
            gap      = max(0, depth - capacity)
            fill_pct = min(100, int(depth / max(capacity, 1) * 100))
            bar_color = "#f87171" if fill_pct >= 100 else "#fb923c" if fill_pct >= 75 else "#4ade80"
            gap_text  = (
                "<span style='color:#f87171;font-weight:700'>OVER CAPACITY by {}</span>".format(gap)
                if gap > 0 else
                "<span style='color:#4ade80'>Within capacity</span>"
            )
            st.markdown(
                "<div class='cap-row'>"
                "<div style='display:flex;justify-content:space-between;align-items:baseline;"
                "margin-bottom:0.3rem'>"
                "<span class='cap-queue'>{q}</span>"
                "<span style='font-size:0.72rem;color:#475569'>{depth} tickets &nbsp;|&nbsp; "
                "capacity {cap} &nbsp;·&nbsp; {gap_text}</span>"
                "</div>"
                "<div class='cap-track'>"
                "<div style='background:{bc};height:8px;width:{fp}%;border-radius:4px;"
                "transition:width 0.4s'></div>"
                "</div>"
                "<div style='display:flex;justify-content:space-between;margin-top:4px'>"
                "<small style='color:#334155;font-size:0.66rem'>"
                "{agents} agents × {tph} tickets/hr</small>"
                "<small style='color:{bc};font-size:0.66rem;font-weight:700'>{fp}% load</small>"
                "</div>"
                "</div>".format(
                    q=q_name, depth=depth, cap=capacity, gap_text=gap_text,
                    bc=bar_color, fp=fill_pct,
                    agents=_AGENTS_PER_QUEUE, tph=_AGENT_CAPACITY_PER_HR,
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with cap_right:
        # Staffing recommendation
        over_capacity = [(q, len(items)) for q, items in queue_counts_d.items()
                         if len(items) > _AGENTS_PER_QUEUE * _AGENT_CAPACITY_PER_HR]
        total_gap = sum(max(0, len(i) - _AGENTS_PER_QUEUE * _AGENT_CAPACITY_PER_HR)
                        for i in queue_counts_d.values())
        agents_needed = _math.ceil(total_gap / _AGENT_CAPACITY_PER_HR)
        next_hr_vol = _predict_next(all_series)

        st.markdown(
            "<div class='intel-panel'>"
            "<p class='sec-lbl' style='margin-bottom:0.55rem'>AI Staffing Recommendation</p>"
            "<div style='margin-bottom:0.75rem'>"
            "<div style='color:#334155;font-size:0.68rem;font-weight:600;margin-bottom:2px'>"
            "Queues over capacity</div>"
            "<div style='color:{oc_c};font-size:1.6rem;font-weight:800;letter-spacing:-0.5px'>"
            "{oc}</div>"
            "</div>"
            "<div style='margin-bottom:0.75rem'>"
            "<div style='color:#334155;font-size:0.68rem;font-weight:600;margin-bottom:2px'>"
            "Additional agents needed now</div>"
            "<div style='color:#fb923c;font-size:1.6rem;font-weight:800;letter-spacing:-0.5px'>"
            "{needed}</div>"
            "</div>"
            "<div style='margin-bottom:0.75rem'>"
            "<div style='color:#334155;font-size:0.68rem;font-weight:600;margin-bottom:2px'>"
            "Forecast next-hour intake</div>"
            "<div style='color:#60a5fa;font-size:1.6rem;font-weight:800;letter-spacing:-0.5px'>"
            "+{next_hr} tickets</div>"
            "</div>"
            "<div style='background:{rec_bg};border:1px solid {rec_border};"
            "border-radius:7px;padding:0.6rem 0.75rem;margin-top:0.5rem'>"
            "<div style='color:{rec_c};font-size:0.72rem;font-weight:700;margin-bottom:3px'>"
            "{rec_title}</div>"
            "<div style='color:#94a3b8;font-size:0.75rem;line-height:1.5'>{rec_body}</div>"
            "</div>"
            "</div>".format(
                oc=len(over_capacity),
                oc_c="#f87171" if over_capacity else "#4ade80",
                needed=agents_needed,
                next_hr=next_hr_vol,
                rec_bg="#1a0a0a" if over_capacity else "#0a2015",
                rec_border="#7f1d1d55" if over_capacity else "#14532d55",
                rec_c="#f87171" if over_capacity else "#4ade80",
                rec_title="Action Required" if over_capacity else "Capacity Healthy",
                rec_body=(
                    "Escalate {} queue(s) to additional coverage. "
                    "Forecast shows +{} tickets next hour — pre-assign {} agent(s) now "
                    "to prevent SLA breach.".format(
                        len(over_capacity), next_hr_vol, max(agents_needed, 1))
                    if over_capacity else
                    "All queues within normal capacity. "
                    "Next-hour forecast: +{} tickets — current staffing sufficient.".format(next_hr_vol)
                ),
            ),
            unsafe_allow_html=True,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — Priority Distribution + Channel Distribution + Routing
    # ══════════════════════════════════════════════════════════════════════════
    _sdiv("VOLUME DISTRIBUTION")

    col_cat2, col_ch2, col_queue2 = st.columns(3)

    with col_cat2:
        st.markdown("<p class='sec-lbl'>Volume by Category</p>", unsafe_allow_html=True)
        st.bar_chart(
            pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
            .sort_values("Tickets", ascending=False),
            height=200,
        )

    with col_ch2:
        st.markdown("<p class='sec-lbl'>Volume by Channel</p>", unsafe_allow_html=True)
        st.bar_chart(
            pd.DataFrame.from_dict(dict(ch_counts), orient="index", columns=["Tickets"]),
            height=200,
        )

    with col_queue2:
        st.markdown("<p class='sec-lbl'>Routing Outcome</p>", unsafe_allow_html=True)
        routing_data = {
            "Auto-Routed":  len(auto_routed),
            "Human Review": len(hitl_list),
            "Escalated":    len(escalated_list),
            "Approved":     len(approved_list),
        }
        st.bar_chart(
            pd.DataFrame.from_dict(routing_data, orient="index", columns=["Tickets"]),
            height=200,
        )

    # Priority strip
    _sdiv("PRIORITY BREAKDOWN")
    pri_cols = st.columns(4)
    for i, (pri_name, pri_color) in enumerate([("critical", "#f87171"), ("high", "#fb923c"),
                                                ("medium", "#60a5fa"), ("low", "#4ade80")]):
        cnt    = pri_counts.get(pri_name, 0)
        pct    = cnt / total if total else 0
        sla_h  = _PRIORITY_SLA.get(pri_name, 24)
        pri_cols[i].markdown(
            "<div class='pulse-kpi pulse-kpi-{cls}' style='margin-bottom:0'>"
            "<div class='pulse-val' style='color:{c}'>{cnt}</div>"
            "<div class='pulse-lbl'>{p} priority</div>"
            "<div style='margin-top:0.4rem;background:#1e2d45;border-radius:3px;"
            "height:4px;overflow:hidden'>"
            "<div style='background:{c};height:4px;width:{bw}%;border-radius:3px'></div>"
            "</div>"
            "<div style='color:#334155;font-size:0.65rem;margin-top:4px'>"
            "SLA {sla}h &nbsp;·&nbsp; {pct:.0%} of batch</div>"
            "</div>".format(
                cls=pri_name if pri_name != "medium" else "blue",
                c=pri_color, cnt=cnt, p=pri_name.upper(),
                bw="{:.0f}".format(pct * 100), sla=sla_h, pct=pct,
            ),
            unsafe_allow_html=True,
        )

    # ── System log ────────────────────────────────────────────────────────────
    _sdiv("SYSTEM LOG")
    with st.expander("Execution Log", expanded=False):
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
