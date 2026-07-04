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
    page_title="SupportTriage AI — Enterprise Ops",
    page_icon="🎫",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
/* ── Base ── */
.stApp { background-color: #0a0a0a; color: #e8e8e8; }
section[data-testid="stSidebar"] {
    background-color: #0f0f0f;
    border-right: 1px solid #1a1a1a;
}

/* ── Sidebar nav radio ── */
div[data-testid="stRadio"] > div { gap: 2px; }
div[data-testid="stRadio"] label {
    background: transparent; border-radius: 6px;
    padding: 0.45rem 0.75rem; color: #6f6f6f;
    font-size: 0.88rem; cursor: pointer;
    transition: background 0.15s; width: 100%; display: block;
}
div[data-testid="stRadio"] label:hover { background: #1a1a1a; color: #f4f4f4; }
div[data-testid="stRadio"] label[data-checked="true"],
div[data-testid="stRadio"] label[aria-checked="true"] {
    background: #0f2040 !important; color: #4d94ff !important; font-weight: 600;
}

/* ── Typography ── */
h1, h2, h3, h4 { color: #f4f4f4; letter-spacing: -0.3px; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #141414; border: 1px solid #1f1f1f;
    border-radius: 10px; padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] { color: #525252 !important; font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.6px; }
[data-testid="stMetricValue"] { color: #f4f4f4 !important; font-size: 1.6rem !important;
    font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: #0f62fe; color: #fff; border: none; border-radius: 6px;
    padding: 0.45rem 1.1rem; font-weight: 600; font-size: 0.85rem;
    transition: background 0.15s;
}
.stButton > button:hover { background: #0353e9; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: #141414 !important; color: #f4f4f4 !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important;
    font-size: 0.88rem !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: #141414 !important; color: #c6c6c6 !important;
    border-radius: 8px !important; border: 1px solid #1f1f1f !important;
    font-size: 0.88rem !important;
}
.streamlit-expanderContent { background: #0f0f0f !important; border: 1px solid #1a1a1a !important; }

/* ── Divider ── */
hr { border-color: #1a1a1a !important; margin: 0.8rem 0 !important; }

/* ── Badges ── */
.badge { display:inline-block; padding:1px 8px; border-radius:20px;
    font-size:0.7rem; font-weight:700; margin-right:3px; letter-spacing:0.3px; }
.badge-telegram { background:#0d2a3d; color:#4db8ff; border:1px solid #229ed944; }
.badge-email    { background:#071428; color:#82b4ff; border:1px solid #0043ce44; }
.badge-web      { background:#1a0a30; color:#c0a0ff; border:1px solid #6929c444; }
.badge-critical { background:#280808; color:#ff8389; border:1px solid #fa4d5644; }
.badge-high     { background:#281c00; color:#f5d87c; border:1px solid #f1c21b44; }
.badge-medium   { background:#071428; color:#82b4ff; border:1px solid #0f62fe44; }
.badge-low      { background:#071a0f; color:#74d08a; border:1px solid #42be6544; }
.badge-auto-routed  { background:#071a0f; color:#74d08a; border:1px solid #42be6544; }
.badge-human-review { background:#281c00; color:#f5d87c; border:1px solid #f1c21b44; }
.badge-escalated    { background:#280808; color:#ff8389; border:1px solid #fa4d5644; }
.badge-untriaged    { background:#141414; color:#525252; border:1px solid #222; }
.badge-approved     { background:#071a0f; color:#74d08a; border:1px solid #42be6544; }

/* ── SLA risk badges ── */
.sla-critical { display:inline-block;padding:1px 7px;border-radius:10px;
    font-size:0.68rem;font-weight:700;background:#280808;color:#ff8389;border:1px solid #fa4d5644; }
.sla-high     { display:inline-block;padding:1px 7px;border-radius:10px;
    font-size:0.68rem;font-weight:700;background:#281c00;color:#f5d87c;border:1px solid #f1c21b44; }
.sla-ok       { display:inline-block;padding:1px 7px;border-radius:10px;
    font-size:0.68rem;font-weight:700;background:#071a0f;color:#74d08a;border:1px solid #42be6544; }

/* ── Inbox cards ── */
.inbox-card {
    background:#111; border:1px solid #1f1f1f; border-radius:8px;
    padding:0.75rem 1rem; margin:0.2rem 0;
    display:flex; gap:0.85rem; align-items:flex-start;
    transition: border-color 0.15s, background 0.15s;
}
.inbox-card:hover { border-color: #2a2a2a; background:#151515; }
.inbox-card-telegram { border-left: 3px solid #229ed9 !important; }
.inbox-card-email    { border-left: 3px solid #0f62fe !important; }
.inbox-card-web      { border-left: 3px solid #6929c4 !important; }

/* ── Stat card (dashboard) ── */
.stat-card {
    background:#111; border:1px solid #1f1f1f; border-radius:10px;
    padding:1rem 1.2rem; text-align:center;
}
.stat-card-value { font-size:2rem; font-weight:700; color:#f4f4f4; line-height:1.1; }
.stat-card-label { font-size:0.7rem; color:#525252; text-transform:uppercase;
    letter-spacing:0.6px; margin-top:0.2rem; }
.stat-card-sub   { font-size:0.78rem; color:#6f6f6f; margin-top:0.25rem; }

/* ── Outage banners ── */
.outage-critical {
    background:#150303; border:1px solid #fa4d5666; border-left:4px solid #fa4d56;
    border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0;
}
.outage-warning {
    background:#150d00; border:1px solid #f1c21b44; border-left:4px solid #f1c21b;
    border-radius:8px; padding:0.8rem 1.1rem; margin:0.4rem 0;
}

/* ── Impact banner ── */
.impact-banner {
    background:linear-gradient(135deg,#001040,#0a2a7a);
    padding:1.1rem 1.4rem; border-radius:10px; margin-bottom:1rem;
    border: 1px solid #0f62fe33;
}

/* ── Confidence bar ── */
.conf-track { background:#1a1a1a; border-radius:4px; height:6px;
    width:100%; margin-top:3px; overflow:hidden; }

/* ── Terminal log ── */
.terminal {
    background:#050505; color:#3fb950;
    font-family:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;
    font-size:0.78rem; padding:1rem; border-radius:8px;
    white-space:pre-wrap; line-height:1.6;
    border:1px solid #0d1f0d; max-height:500px; overflow-y:auto;
}

/* ── HITL card ── */
.hitl-card {
    background:#0d0a00; border:1px solid #f1c21b22;
    border-left:3px solid #f1c21b; border-radius:8px;
    padding:0.85rem 1.1rem; margin-bottom:0.6rem;
}

/* ── Queue table ── */
.queue-row {
    display:flex; align-items:center; gap:0.75rem;
    padding:0.4rem 0.6rem; border-radius:6px;
    background:#111; border:1px solid #1f1f1f; margin-bottom:4px;
    font-size:0.82rem;
}

/* ── Status dot ── */
.dot-on  { display:inline-block;width:7px;height:7px;border-radius:50%;background:#42be65;margin-right:6px; }
.dot-off { display:inline-block;width:7px;height:7px;border-radius:50%;background:#2a2a2a;margin-right:6px; }

/* ── Stat row ── */
.stat-row { display:flex;justify-content:space-between;align-items:center;
    padding:0.3rem 0; border-bottom:1px solid #1a1a1a; }
.stat-row:last-child { border-bottom:none; }

/* ── Section header ── */
.section-header {
    font-size:0.72rem; color:#525252; text-transform:uppercase;
    letter-spacing:1px; margin:0 0 0.5rem 0; font-weight:600;
}

/* ── Priority bar ── */
.pri-bar-track { background:#1a1a1a; border-radius:3px; height:6px; flex:1; overflow:hidden; }
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

_CHANNEL_ICON  = {"telegram": "✈️", "email": "📧", "web": "🌐"}
_CHANNEL_COLOR = {"telegram": "#229ed9", "email": "#4d94ff", "web": "#a78bfa"}
_PRIORITY_COLOR = {
    "critical": "#ff8389", "high": "#f5d87c",
    "medium":   "#82b4ff", "low":  "#74d08a",
}
_PRIORITY_SLA = {"critical": 2, "high": 8, "medium": 24, "low": 72}  # hours


def _conf_bar_html(conf: float, width_px: int = 140) -> str:
    color  = "#42be65" if conf > 0.85 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
    filled = int(conf * width_px)
    return (
        "<div class='conf-track' style='width:{w}px'>"
        "<div style='background:{c};height:6px;width:{f}px;border-radius:4px'></div>"
        "</div>"
        "<small style='color:{c};font-size:0.72rem'>{p}</small>"
    ).format(w=width_px, c=color, f=filled, p="{:.0%}".format(conf))


def _ticket_badges(t) -> str:
    ch   = (t.channel  or "web").lower()
    pri  = (t.priority or "medium").lower()
    stat = (t.status   or "untriaged").lower().replace(" ", "-")
    cat  = _html.escape((t.category or "unknown").upper())
    return (
        "<span class='badge badge-{ch}'>{CH}</span>"
        "<span class='badge badge-{pri}'>{PRI}</span>"
        "<span class='badge badge-{stat}'>{STAT}</span>"
        "<span class='badge' style='background:#141414;color:#6f6f6f;"
        "border:1px solid #222'>{cat}</span>"
    ).format(ch=ch, CH=ch.upper(), pri=pri, PRI=pri.upper(),
             stat=stat, STAT=stat.upper(), cat=cat)


def _sla_badge(priority: str) -> str:
    p = (priority or "medium").lower()
    if p == "critical":
        return "<span class='sla-critical'>🔴 SLA: 2h</span>"
    if p == "high":
        return "<span class='sla-high'>🟡 SLA: 8h</span>"
    return "<span class='sla-ok'>🟢 SLA: {h}h</span>".format(
        h=_PRIORITY_SLA.get(p, 24)
    )


def _kpi_card(value: str, label: str, sub: str = "", color: str = "#f4f4f4") -> str:
    return (
        "<div class='stat-card'>"
        "<div class='stat-card-value' style='color:{c}'>{v}</div>"
        "<div class='stat-card-label'>{l}</div>"
        "{sub_html}"
        "</div>"
    ).format(
        c=color, v=value, l=label,
        sub_html="<div class='stat-card-sub'>{}</div>".format(sub) if sub else "",
    )


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
    st.markdown(
        "<div style='padding:1rem 0.5rem 0.5rem 0.5rem'>"
        "<h3 style='color:#f4f4f4;margin:0;font-size:1rem;font-weight:700'>🎫 SupportTriage AI</h3>"
        "<p style='color:#3d3d3d;font-size:0.68rem;margin:3px 0 0 0;letter-spacing:0.5px'>"
        "ENTERPRISE OPERATIONS CENTER</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "",
        ["📥 Inbox", "📊 Dashboard", "🧑‍💻 Review Queue", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.divider()

    # Channel status
    tg_connected = bool(st.session_state.get("tg_token"))
    gm_connected = bool(st.session_state.get("gmail_user"))
    st.markdown(
        "<p class='section-header' style='padding:0 0.5rem'>Live Channels</p>",
        unsafe_allow_html=True,
    )
    _tg_dot = "#42be65" if tg_connected else "#2a2a2a"
    _tg_col = "#42be65" if tg_connected else "#525252"
    _tg_lbl = "<b>Connected</b>" if tg_connected else "Not configured"
    _gm_dot = "#42be65" if gm_connected else "#2a2a2a"
    _gm_col = "#42be65" if gm_connected else "#525252"
    _gm_lbl = "<b>Connected</b>" if gm_connected else "Not configured"
    st.markdown(
        "<div style='padding:0 0.5rem'>"
        "<div style='display:flex;align-items:center;gap:0.5rem;padding:0.22rem 0'>"
        "<div style='width:6px;height:6px;border-radius:50%;background:{tg_dot};flex-shrink:0'></div>"
        "<span style='color:{tg_col};font-size:0.78rem'>✈️ Telegram &nbsp;{tg_lbl}</span>"
        "</div>"
        "<div style='display:flex;align-items:center;gap:0.5rem;padding:0.22rem 0'>"
        "<div style='width:6px;height:6px;border-radius:50%;background:{gm_dot};flex-shrink:0'></div>"
        "<span style='color:{gm_col};font-size:0.78rem'>📧 Gmail &nbsp;{gm_lbl}</span>"
        "</div>"
        "<div style='display:flex;align-items:center;gap:0.5rem;padding:0.22rem 0'>"
        "<div style='width:6px;height:6px;border-radius:50%;background:#42be65;flex-shrink:0'></div>"
        "<span style='color:#42be65;font-size:0.78rem'>🌐 Web Form &nbsp;<b>Active</b></span>"
        "</div>"
        "</div>".format(
            tg_dot=_tg_dot, tg_col=_tg_col, tg_lbl=_tg_lbl,
            gm_dot=_gm_dot, gm_col=_gm_col, gm_lbl=_gm_lbl,
        ),
        unsafe_allow_html=True,
    )

    st.divider()

    # Queue summary
    inbox_count     = len(st.session_state.get("inbox", []))
    review_count    = sum(1 for _, r in st.session_state.get("processed", []) if r.get("status") == "human-review")
    escalated_count = sum(1 for _, r in st.session_state.get("processed", []) if r.get("status") == "escalated")
    processed_count = len(st.session_state.get("processed", []))
    st.markdown(
        "<p class='section-header' style='padding:0 0.5rem'>Queue Summary</p>",
        unsafe_allow_html=True,
    )
    _rc_col = "#f1c21b" if review_count else "#f4f4f4"
    _ec_col = "#ff8389" if escalated_count else "#f4f4f4"
    st.markdown(
        "<div style='padding:0 0.5rem'>"
        "<div class='stat-row'><span style='color:#6f6f6f;font-size:0.78rem'>Inbox</span>"
        "<span style='color:#f4f4f4;font-weight:700;font-size:0.85rem'>{inbox}</span></div>"
        "<div class='stat-row'><span style='color:#6f6f6f;font-size:0.78rem'>Human Review</span>"
        "<span style='color:{rc};font-weight:700;font-size:0.85rem'>{review}</span></div>"
        "<div class='stat-row'><span style='color:#6f6f6f;font-size:0.78rem'>Escalated</span>"
        "<span style='color:{ec};font-weight:700;font-size:0.85rem'>{esc}</span></div>"
        "<div class='stat-row'><span style='color:#6f6f6f;font-size:0.78rem'>Processed</span>"
        "<span style='color:#f4f4f4;font-weight:700;font-size:0.85rem'>{proc}</span></div>"
        "</div>".format(
            inbox=inbox_count, rc=_rc_col, review=review_count,
            ec=_ec_col, esc=escalated_count, proc=processed_count,
        ),
        unsafe_allow_html=True,
    )

    st.divider()
    if st.button("🔄 Reset Inbox", use_container_width=True, key="reset_all"):
        from intake.channels import generate_background_volume
        st.session_state.inbox      = generate_background_volume(15)
        st.session_state.processed  = []
        st.session_state.log        = ""
        st.session_state.tg_last_id = 0
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Enterprise header
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    "<div style='display:flex;justify-content:space-between;align-items:center;"
    "padding:0.5rem 0 1rem 0;border-bottom:1px solid #1a1a1a;margin-bottom:1.5rem'>"
    "<div>"
    "<h1 style='color:#f4f4f4;margin:0;font-size:1.7rem;font-weight:700;letter-spacing:-0.5px'>"
    "SupportTriage <span style='color:#0f62fe'>AI</span>"
    "</h1>"
    "<p style='color:#3d3d3d;margin:0;font-size:0.75rem;letter-spacing:0.3px'>"
    "ENTERPRISE MULTI-CHANNEL OPERATIONS · IBM GRANITE 4.1 8B · HUMAN-IN-THE-LOOP"
    "</p>"
    "</div>"
    "<div style='display:flex;gap:0.5rem;align-items:center'>"
    "<span style='background:#071a0f;color:#42be65;padding:3px 10px;border-radius:20px;"
    "font-size:0.68rem;font-weight:700;border:1px solid #42be6533'>● LIVE</span>"
    "<span style='background:#111;color:#525252;padding:3px 10px;border-radius:20px;"
    "font-size:0.68rem;border:1px solid #1f1f1f'>IBM Granite 4.1 8B</span>"
    "<span style='background:#111;color:#525252;padding:3px 10px;border-radius:20px;"
    "font-size:0.68rem;border:1px solid #1f1f1f'>HITL · conf &gt; 85%</span>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ⚙️ Settings
# ══════════════════════════════════════════════════════════════════════════════

if page == "⚙️ Settings":
    st.markdown("<h2 style='color:#f4f4f4;margin-bottom:0.2rem'>⚙️ Channel Configuration</h2>",
                unsafe_allow_html=True)
    st.caption("Credentials are stored in your session only — never persisted to disk or GitHub.")

    with st.container(border=True):
        st.markdown("### ✈️ Telegram Bot")
        st.caption("Get your token from **@BotFather** on Telegram → `/newbot` → copy the API token.")
        tg_token_input = st.text_input(
            "Telegram Bot Token", value=st.session_state.get("tg_token", ""),
            type="password", placeholder="1234567890:ABCdef…", key="tg_token_field",
        )
        tg_col1, _ = st.columns([1, 3])
        if tg_col1.button("💾 Save & Test", key="save_tg", use_container_width=True):
            if tg_token_input.strip():
                try:
                    import requests as _req
                    r = _req.get(f"https://api.telegram.org/bot{tg_token_input}/getMe", timeout=5)
                    if r.status_code == 200:
                        bot_name = r.json()["result"]["username"]
                        st.session_state["tg_token"] = tg_token_input.strip()
                        st.success("✅ Connected to @{}".format(bot_name))
                    else:
                        st.error("❌ Invalid token — Telegram returned status {}".format(r.status_code))
                except Exception as e:
                    st.error("❌ Connection failed: {}".format(e))
            else:
                st.warning("Please enter a token.")

    with st.container(border=True):
        st.markdown("### 📧 Gmail / Email (IMAP + SMTP)")
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
        if st.button("💾 Save & Test Email Connection", key="save_gmail"):
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
                    st.success("✅ Connected to {} via {}".format(gmail_user_input.strip(), server))
                except Exception as e:
                    st.error("❌ Connection failed: {}".format(e))
            else:
                st.warning("Please enter both email address and app password.")

    with st.container(border=True):
        st.markdown("### 🌐 Web Form")
        st.info("✅ Customer web form is always active. Run it separately: `streamlit run ui/web_form.py --server.port 8502`")
        support_email = os.environ.get("SUPPORT_EMAIL", os.environ.get("GMAIL_USER", "not set"))
        st.caption("Submissions are sent to: **{}**".format(support_email))

    with st.container(border=True):
        st.markdown("### 🤖 AI Engine — IBM Granite")
        ai_key_input = st.text_input(
            "OpenRouter API Key", value=st.session_state.get("openrouter_key", ""),
            type="password", placeholder="sk-or-v1-…", key="ai_key_field",
        )
        if st.button("💾 Save AI Key", key="save_ai"):
            if ai_key_input.strip():
                st.session_state["openrouter_key"] = ai_key_input.strip()
                os.environ["OPENROUTER_API_KEY"]   = ai_key_input.strip()
                st.success("✅ IBM Granite API key saved for this session.")
            else:
                st.warning("Please enter a key.")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 📥 Inbox
# ══════════════════════════════════════════════════════════════════════════════

if page == "📥 Inbox":

    # Fetch buttons
    fetch_col_tg, fetch_col_gm, spacer = st.columns([1, 1, 4])

    if fetch_col_tg.button("✈️ Fetch Telegram", key="tg_fetch", use_container_width=True):
        tg_tok = st.session_state.get("tg_token", "")
        if not tg_tok:
            st.warning("No Telegram token saved. Go to ⚙️ Settings to configure it.")
        else:
            from intake.channels import fetch_telegram_updates
            with st.spinner("Polling Telegram…"):
                new_tickets, new_last_id = fetch_telegram_updates(tg_tok, st.session_state.tg_last_id)
            if new_tickets:
                st.session_state.inbox.extend(new_tickets)
                st.session_state.tg_last_id = new_last_id
                st.success("✅ {} new message(s) added.".format(len(new_tickets)))
                st.rerun()
            else:
                st.info("No new Telegram messages.")

    if fetch_col_gm.button("📧 Fetch Gmail", key="gm_fetch", use_container_width=True):
        gm_user = st.session_state.get("gmail_user", "")
        gm_pass = st.session_state.get("gmail_pass", "")
        if not gm_user or not gm_pass:
            st.warning("No Gmail credentials saved. Go to ⚙️ Settings to configure them.")
        else:
            from intake.channels import fetch_unread_emails
            with st.spinner("Reading Gmail IMAP…"):
                new_emails = fetch_unread_emails(gm_user, gm_pass)
            if new_emails:
                st.session_state.inbox.extend(new_emails)
                st.success("✅ {} unread email(s) added.".format(len(new_emails)))
                st.rerun()
            else:
                st.info("No unread [SUPPORT-TICKET] emails found.")

    inbox = st.session_state.inbox

    if not inbox:
        st.markdown(
            "<div style='text-align:center;padding:4rem 2rem'>"
            "<div style='font-size:2.5rem'>📭</div>"
            "<h3 style='color:#f4f4f4;margin:0.5rem 0'>Inbox is empty</h3>"
            "<p style='color:#525252'>Click <b>🔄 Reset Inbox</b> in the sidebar to reload "
            "the demo queue, or connect a live channel above.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # Search + filter bar
    sf_col1, sf_col2, sf_col3 = st.columns([3, 1, 1])
    search_q   = sf_col1.text_input("🔍 Search tickets", placeholder="Subject, sender, error code…", label_visibility="collapsed", key="inbox_search")
    pri_filter = sf_col2.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"], label_visibility="collapsed", key="inbox_pri")
    ch_filter  = sf_col3.selectbox("Channel", ["All", "Email", "Telegram", "Web"], label_visibility="collapsed", key="inbox_ch")

    # Apply filters
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

    # Header with channel pills
    ch_counts  = Counter(t.channel for t in inbox)
    ch_pills   = "  ".join(
        "<span style='background:{bg};color:{c};padding:2px 8px;border-radius:10px;"
        "font-size:0.72rem;font-weight:700;border:1px solid {c}33'>{i} {ch} {n}</span>".format(
            bg="#0a0a0a", c=_CHANNEL_COLOR.get(ch, "#525252"),
            i=_CHANNEL_ICON.get(ch, ""), ch=ch.upper(), n=n,
        )
        for ch, n in sorted(ch_counts.items())
    )
    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin:0.5rem 0'>"
        "<h3 style='color:#f4f4f4;margin:0'>📥 Triage Queue "
        "<span style='color:#3d3d3d;font-size:0.9rem;font-weight:400'>"
        "— {showing}/{total} tickets</span></h3>"
        "<div>{pills}</div>"
        "</div>".format(showing=len(visible), total=len(inbox), pills=ch_pills),
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='margin:0 0 0.5rem 0'>", unsafe_allow_html=True)

    if not visible:
        st.info("No tickets match your filter.")
        st.stop()

    # Ticket cards
    for t in visible:
        ch           = (t.channel or "web").lower()
        icon         = _CHANNEL_ICON.get(ch, "?")
        color        = _CHANNEL_COLOR.get(ch, "#8d8d8d")
        body_flat    = (t.body or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        preview      = (body_flat[:110] + "…") if len(body_flat) > 110 else body_flat
        id_safe      = _html.escape(t.id      or "")
        sender_safe  = _html.escape(t.sender  or "")
        subject_safe = _html.escape(t.subject or "")
        preview_safe = _html.escape(preview)
        sla_html     = _sla_badge(t.priority)
        errs = "  ".join(
            "<code style='background:#0d0d0d;color:#82b4ff;padding:1px 5px;"
            "border-radius:3px;font-size:0.7rem;border:1px solid #0f62fe22'>{e}</code>".format(
                e=_html.escape(e)
            ) for e in t.error_codes
        ) if t.error_codes else ""

        st.markdown(
            "<div class='inbox-card inbox-card-{ch}'>"
            "<span style='font-size:1rem;flex-shrink:0;padding-top:2px;opacity:0.8'>{icon}</span>"
            "<div style='flex:1;min-width:0'>"
            "<div style='display:flex;align-items:center;gap:0.4rem;margin-bottom:0.1rem;flex-wrap:wrap'>"
            "<span style='color:#3d3d3d;font-size:0.7rem;font-family:monospace'>{tid}</span>"
            "<span style='color:{color};font-size:0.7rem;font-weight:700'>{chan}</span>"
            "<span style='color:#525252;font-size:0.7rem'>{sender}</span>"
            "{sla}{errs}"
            "</div>"
            "<div style='color:#e8e8e8;font-weight:600;font-size:0.86rem;margin-bottom:0.1rem;"
            "white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{subject}</div>"
            "<div style='color:#525252;font-size:0.76rem;line-height:1.4'>{preview}</div>"
            "</div>"
            "<span class='badge badge-untriaged' style='flex-shrink:0;margin-top:2px'>UNTRIAGED</span>"
            "</div>".format(
                ch=ch, icon=icon, tid=id_safe, color=color, chan=ch.upper(),
                sender=sender_safe, sla=sla_html, errs=errs,
                subject=subject_safe, preview=preview_safe,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(
        "🚀 Run AI Triage on {} Ticket(s) — IBM Granite".format(len(inbox)),
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
# PAGE: 📊 Dashboard
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Dashboard":

    results = st.session_state.processed
    if not results:
        st.info("No processed tickets yet. Go to **📥 Inbox** and run AI triage first.")
        st.stop()

    # ── Compute all stats ──────────────────────────────────────────────────────
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
    misroute_saved  = int(len(auto_routed) * 0.35)  # 35% would have been misrouted manually
    annual_saving   = int(misroute_saved * 12 * 27)  # $27 avg cost per misroute

    # ── Impact banner ──────────────────────────────────────────────────────────
    st.markdown(
        "<div class='impact-banner'>"
        "<h4 style='color:white;margin:0;font-size:0.92rem;font-weight:700'>"
        "💡 Enterprise Business Impact</h4>"
        "<div style='display:flex;gap:2rem;margin-top:0.5rem;flex-wrap:wrap'>"
        "<div><div style='color:#a8c8ff;font-size:0.75rem'>Tickets Auto-Routed</div>"
        "<div style='color:white;font-size:1.1rem;font-weight:700'>{ar} <span style='font-size:0.78rem;color:#82b4ff'>({ar_pct:.0%})</span></div></div>"
        "<div><div style='color:#a8c8ff;font-size:0.75rem'>Misroutes Prevented</div>"
        "<div style='color:white;font-size:1.1rem;font-weight:700'>{ms}</div></div>"
        "<div><div style='color:#a8c8ff;font-size:0.75rem'>Est. Annual Saving</div>"
        "<div style='color:#42be65;font-size:1.1rem;font-weight:700'>${sav:,}</div></div>"
        "<div><div style='color:#a8c8ff;font-size:0.75rem'>Avg AI Confidence</div>"
        "<div style='color:white;font-size:1.1rem;font-weight:700'>{conf:.0%}</div></div>"
        "<div><div style='color:#a8c8ff;font-size:0.75rem'>SLA-Critical Tickets</div>"
        "<div style='color:#ff8389;font-size:1.1rem;font-weight:700'>{sla}</div></div>"
        "</div>"
        "</div>".format(
            ar=len(auto_routed), ar_pct=automation_rate,
            ms=misroute_saved, sav=annual_saving,
            conf=avg_conf, sla=sla_breach,
        ),
        unsafe_allow_html=True,
    )

    # ── 8-KPI grid (2 rows × 4 cols) ──────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🎫 Total Processed",   total)
    k2.metric("🤖 Auto-Routed",       "{} ({:.0%})".format(len(auto_routed), automation_rate))
    k3.metric("🧑‍💻 Human Review",    len(hitl_list),    delta="-{:.0%} held".format(hitl_rate) if hitl_list else None)
    k4.metric("🚨 Escalated",         len(escalated_list), delta="↑ {:.0%}".format(escalation_rate) if escalated_list else None)

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("📈 Avg Confidence",    "{:.0%}".format(avg_conf))
    k6.metric("⚡ Avg Severity",      "{:.1f}/10".format(avg_severity))
    k7.metric("✅ Agent-Approved",    len(approved_list))
    k8.metric("💰 Est. Annual Saving", "${:,}".format(annual_saving))

    st.divider()

    # ── Confidence gauge + Priority breakdown side by side ─────────────────────
    gauge_col, pri_col = st.columns([3, 2])

    with gauge_col:
        conf_color = "#42be65" if avg_conf > 0.85 else "#f1c21b" if avg_conf >= 0.6 else "#fa4d56"
        _conf_pct  = "{:.0%}".format(avg_conf)
        _conf_bar  = "{:.0f}".format(avg_conf * 100)
        st.markdown(
            "<div style='background:#111;border-radius:10px;padding:1rem 1.3rem;"
            "border:1px solid #1f1f1f'>"
            "<div style='display:flex;justify-content:space-between;margin-bottom:0.5rem'>"
            "<span style='color:#c6c6c6;font-size:0.82rem;font-weight:600'>"
            "AI Classification Confidence</span>"
            "<span style='color:{cc};font-size:1.2rem;font-weight:700'>{pct}</span>"
            "</div>"
            "<div style='position:relative;background:#1a1a1a;border-radius:4px;height:12px;width:100%'>"
            "<div style='background:{cc};border-radius:4px;height:12px;width:{bar}%'></div>"
            "<div style='position:absolute;top:-3px;left:85%;width:2px;height:18px;"
            "background:#fa4d56;opacity:0.9'></div>"
            "</div>"
            "<div style='display:flex;justify-content:space-between;margin-top:5px'>"
            "<small style='color:{cc};font-size:0.72rem'>{pct} batch average</small>"
            "<small style='color:#fa4d56;font-size:0.72rem'>▲ 85% HITL threshold</small>"
            "</div>"
            "</div>".format(cc=conf_color, pct=_conf_pct, bar=_conf_bar),
            unsafe_allow_html=True,
        )

    with pri_col:
        st.markdown(
            "<div style='background:#111;border-radius:10px;padding:1rem 1.3rem;"
            "border:1px solid #1f1f1f'>"
            "<div style='color:#c6c6c6;font-size:0.82rem;font-weight:600;margin-bottom:0.6rem'>"
            "Priority Distribution</div>",
            unsafe_allow_html=True,
        )
        for pri_name, pri_color in [("critical", "#ff8389"), ("high", "#f5d87c"),
                                     ("medium", "#82b4ff"), ("low", "#74d08a")]:
            cnt   = pri_counts.get(pri_name, 0)
            pct   = cnt / total if total else 0
            width = "{:.0f}".format(pct * 100)
            st.markdown(
                "<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem'>"
                "<span style='color:{c};font-size:0.72rem;font-weight:700;width:52px'>{p}</span>"
                "<div class='pri-bar-track'>"
                "<div style='background:{c};height:6px;border-radius:3px;width:{w}%'></div>"
                "</div>"
                "<span style='color:#525252;font-size:0.72rem;width:28px;text-align:right'>{n}</span>"
                "</div>".format(c=pri_color, p=pri_name.upper(), w=width, n=cnt),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # ── Outage Radar ───────────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='color:#f4f4f4;margin-bottom:0.1rem'>🚨 Outage Radar</h3>"
        "<p style='color:#525252;font-size:0.78rem;margin-bottom:0.75rem'>"
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
        ch_str   = " + ".join(
            "<span style='color:{c};font-weight:700'>{i} {ch}</span>".format(
                c=_CHANNEL_COLOR.get(c, "#8d8d8d"), i=_CHANNEL_ICON.get(c, ""), ch=c.upper(),
            ) for c in channels
        )
        ids_html     = " ".join(
            "<code style='background:#0d0d0d;color:#82b4ff;padding:1px 5px;"
            "border-radius:3px;font-size:0.7rem'>{id}</code>".format(id=_html.escape(t.id))
            for t in tix
        )
        symptom_safe = _html.escape(symptom)
        if count >= 3:
            outage_found = True
            st.markdown(
                "<div class='outage-critical'>"
                "<div style='font-size:0.95rem;font-weight:700;color:#ff8389;margin-bottom:0.3rem'>"
                "🚨 SYSTEMIC OUTAGE DETECTED — {count} reports"
                "</div>"
                "<div style='color:#f4f4f4;font-size:0.85rem;margin-bottom:0.2rem'>"
                "Symptom: <b>&quot;{symptom}&quot;</b> &nbsp;·&nbsp; Channels: {ch_str}"
                "</div>"
                "<div style='color:#525252;font-size:0.76rem;margin-bottom:0.25rem'>"
                "Affected: {ids}"
                "</div>"
                "<div style='color:#ff8389;font-size:0.76rem;font-weight:600'>"
                "⚡ Escalate to engineering — check status page and notify stakeholders."
                "</div>"
                "</div>".format(count=count, symptom=symptom_safe, ch_str=ch_str, ids=ids_html),
                unsafe_allow_html=True,
            )
        elif count == 2:
            st.markdown(
                "<div class='outage-warning'>"
                "<span style='color:#f5d87c;font-weight:700;font-size:0.83rem'>"
                "⚠️ Pattern emerging</span>&nbsp;&nbsp;"
                "<span style='color:#c6c6c6;font-size:0.8rem'>"
                "<b>{count} tickets</b> — <b>&quot;{symptom}&quot;</b> — {ch_str}"
                "</span>&nbsp;"
                "<span style='color:#525252;font-size:0.76rem'>Monitor for further reports.</span>"
                "</div>".format(count=count, symptom=symptom_safe, ch_str=ch_str),
                unsafe_allow_html=True,
            )

    if not outage_found and not any(len(v) >= 2 for v in symptom_tickets.values()):
        st.success("✅ No outage patterns detected across {} processed tickets.".format(total))

    st.divider()

    # ── Charts: category + channel + queue distribution ────────────────────────
    col_cat, col_ch, col_queue = st.columns(3)

    with col_cat:
        st.markdown(
            "<p class='section-header'>Volume by Category</p>",
            unsafe_allow_html=True,
        )
        st.bar_chart(
            pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
            .sort_values("Tickets", ascending=False),
            height=220,
        )

    with col_ch:
        st.markdown(
            "<p class='section-header'>Volume by Channel</p>",
            unsafe_allow_html=True,
        )
        st.bar_chart(
            pd.DataFrame.from_dict(ch_counts, orient="index", columns=["Tickets"]),
            height=220,
        )

    with col_queue:
        st.markdown(
            "<p class='section-header'>Routing Outcome</p>",
            unsafe_allow_html=True,
        )
        routing_data = {
            "Auto-Routed":    len(auto_routed),
            "Human Review":   len(hitl_list),
            "Escalated":      len(escalated_list),
            "Approved":       len(approved_list),
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

    st.markdown(
        "<p class='section-header'>Queue Depth &amp; Severity</p>",
        unsafe_allow_html=True,
    )
    tbl_cols = st.columns([3, 1, 1, 2])
    tbl_cols[0].markdown("**Queue**")
    tbl_cols[1].markdown("**Tickets**")
    tbl_cols[2].markdown("**Avg Sev**")
    tbl_cols[3].markdown("**Top Priority**")
    for q_name, q_tickets in sorted(queue_counts.items(), key=lambda x: -len(x[1])):
        avg_sev    = sum(t.classify_confidence for t in q_tickets) / len(q_tickets)
        top_pri    = Counter((t.priority or "medium").lower() for t in q_tickets).most_common(1)
        top_pri_s  = top_pri[0][0].upper() if top_pri else "—"
        pri_c      = _PRIORITY_COLOR.get(top_pri_s.lower(), "#6f6f6f")
        tbl_cols2  = st.columns([3, 1, 1, 2])
        tbl_cols2[0].markdown("`{}`".format(q_name))
        tbl_cols2[1].markdown("**{}**".format(len(q_tickets)))
        tbl_cols2[2].markdown("{:.0%}".format(avg_sev))
        tbl_cols2[3].markdown(
            "<span style='color:{c};font-weight:700;font-size:0.82rem'>{p}</span>".format(
                c=pri_c, p=top_pri_s),
            unsafe_allow_html=True,
        )

    st.divider()

    # ── System log ────────────────────────────────────────────────────────────
    with st.expander("⚙️ System Execution Log", expanded=False):
        log_text = _html.escape(st.session_state.log or "(no triage runs yet)")
        st.markdown("<div class='terminal'>{}</div>".format(log_text), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: 🧑‍💻 Review Queue
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🧑‍💻 Review Queue":

    results = st.session_state.processed
    if not results:
        st.info("No processed tickets yet. Go to **📥 Inbox** and run AI triage first.")
        st.stop()

    hitl_pairs = [
        (i, t, r) for i, (t, r) in enumerate(results)
        if r.get("status") == "human-review" and t.status != "approved"
    ]

    if not hitl_pairs:
        st.success("✅ Review queue is clear — all low-confidence tickets have been approved.")
        approved_count = sum(1 for _, r in results if r.get("status") == "approved")
        if approved_count:
            st.info("{} ticket(s) previously approved and routed by agents.".format(approved_count))
        st.stop()

    # Header + confidence distribution
    hdr_col, dist_col = st.columns([2, 3])
    with hdr_col:
        st.markdown(
            "<h3 style='color:#f1c21b;margin-bottom:0.3rem'>"
            "🧑‍💻 {} Ticket(s) Awaiting Approval</h3>"
            "<p style='color:#525252;font-size:0.8rem'>"
            "Confidence ≤ 85% — held for human review before routing.</p>".format(len(hitl_pairs)),
            unsafe_allow_html=True,
        )

    with dist_col:
        conf_vals  = [t.classify_confidence for _, t, _ in hitl_pairs]
        high_conf  = sum(1 for c in conf_vals if c >= 0.7)
        med_conf   = sum(1 for c in conf_vals if 0.5 <= c < 0.7)
        low_conf   = sum(1 for c in conf_vals if c < 0.5)
        dc1, dc2, dc3 = st.columns(3)
        dc1.metric("🟢 ≥ 70% conf", high_conf)
        dc2.metric("🟡 50–70%",      med_conf)
        dc3.metric("🔴 < 50%",       low_conf)

    # Bulk approve low-risk (high-confidence HITL)
    bulk_candidates = [(i, t, r) for i, t, r in hitl_pairs if t.classify_confidence >= 0.75]
    if bulk_candidates:
        if st.button(
            "⚡ Bulk Approve {} high-confidence tickets (≥ 75%)".format(len(bulk_candidates)),
            use_container_width=True, key="bulk_approve",
        ):
            for i, t, r in bulk_candidates:
                t.status     = "approved"
                results[i]   = (t, {**r, "status": "approved"})
                st.session_state.log += "  [BULK APPROVED] {} → {} (conf={:.0%})\n".format(
                    t.id, r.get("queue", "unknown"), t.classify_confidence)
            st.session_state.processed = results
            st.success("✅ {} tickets bulk-approved.".format(len(bulk_candidates)))
            st.rerun()

    st.divider()

    for idx, t, r in hitl_pairs:
        conf       = t.classify_confidence
        conf_color = "#42be65" if conf >= 0.7 else "#f1c21b" if conf >= 0.5 else "#fa4d56"
        ch_icon    = _CHANNEL_ICON.get(t.channel or "web", "?")

        with st.expander(
            "{icon}  {tid}  —  {subj}{ellip}".format(
                icon=ch_icon, tid=t.id,
                subj=t.subject[:72], ellip="…" if len(t.subject) > 72 else "",
            ),
            expanded=False,
        ):
            sender_safe = _html.escape(t.sender or "")
            st.markdown(
                "<div class='hitl-card'>"
                "<div style='margin-bottom:0.4rem'>{badges}</div>"
                "<div style='display:flex;gap:2rem;flex-wrap:wrap'>"
                "<span style='color:#525252;font-size:0.78rem'>Sender: "
                "<b style='color:#c6c6c6'>{sender}</b></span>"
                "<span style='color:#525252;font-size:0.78rem'>Queue held: "
                "<b style='color:#f1c21b'>human-review</b></span>"
                "<span style='color:#525252;font-size:0.78rem'>Severity: "
                "<b style='color:{cc}'>{sev:.1f}/10</b></span>"
                "<span style='color:#525252;font-size:0.78rem'>Confidence: "
                "<b style='color:{cc}'>{conf:.0%}</b></span>"
                "</div></div>".format(
                    badges=_ticket_badges(t), sender=sender_safe,
                    cc=conf_color, sev=r["severity_impact"], conf=conf,
                ),
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([1, 1])

            with c1:
                st.markdown(
                    "<p style='color:#6f6f6f;font-size:0.76rem;font-weight:600;"
                    "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.4rem'>"
                    "🔍 AI Reasoning</p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "| Field | Value |\n|---|---|\n"
                    "| Category   | `{}` |\n"
                    "| Priority   | `{}` |\n"
                    "| Confidence | `{:.0%}` |\n"
                    "| Threshold  | `85%` — below = held |".format(
                        t.category or "unknown", t.priority or "unknown", conf
                    )
                )
                st.markdown(_conf_bar_html(conf, 180), unsafe_allow_html=True)
                if t.error_codes:
                    st.markdown("**Error codes:** " + " ".join("`{}`".format(e) for e in t.error_codes))
                if t.symptoms:
                    chips = " ".join(
                        "<span style='background:#0d0d0d;color:#6f6f6f;padding:1px 7px;"
                        "border-radius:10px;font-size:0.7rem;border:1px solid #1f1f1f'>{s}</span>".format(
                            s=_html.escape(s)
                        ) for s in t.symptoms
                    )
                    st.markdown("**Symptoms:** {}".format(chips), unsafe_allow_html=True)
                st.markdown("**📝 AI Summary**")
                st.info(t.summary or "_(no summary)_")

            with c2:
                st.markdown(
                    "<p style='color:#6f6f6f;font-size:0.76rem;font-weight:600;"
                    "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.4rem'>"
                    "✉️ Draft Reply</p>",
                    unsafe_allow_html=True,
                )
                approved_queue = st.selectbox(
                    "Route to queue",
                    options=["queue-auth", "queue-billing", "queue-performance",
                             "queue-data-loss", "queue-product", "queue-general"],
                    index=0,
                    key="queue_select_{}".format(t.id),
                )
                edited_draft = st.text_area(
                    "Draft", value=t.draft_reply or "", height=220,
                    label_visibility="collapsed",
                    key="draft_{}".format(t.id),
                )
                if st.button(
                    "✅ Approve & Route",
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
                    st.success("✅ {} approved and routed to `{}`.".format(t.id, approved_queue))
                    st.rerun()


# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#1a1a1a;margin-top:2.5rem'>"
    "<p style='text-align:center;color:#2a2a2a;font-size:0.72rem;padding:0.5rem 0'>"
    "SupportTriage AI &nbsp;·&nbsp; IBM Granite 4.1 8B &nbsp;·&nbsp; "
    "Built with IBM Bob &nbsp;·&nbsp; IBM AI Builders Challenge 2026"
    "</p>",
    unsafe_allow_html=True,
)
