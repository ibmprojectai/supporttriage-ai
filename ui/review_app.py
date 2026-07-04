"""SupportTriage AI — Multi-Channel Agentic Support Operations Center.

Navigation (sidebar radio):
  📥 Inbox         — untriaged queue + Run AI Triage button
  📊 Dashboard     — KPIs, confidence gauge, Outage Radar, charts
  🧑‍💻 Review Queue — HITL approval queue
  ⚙️ Settings      — credential configuration, save + test per channel

Credentials are stored in st.session_state only — never committed to disk.

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
    page_title="SupportTriage AI — Ops Center",
    page_icon="🎫",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
/* ── Base ── */
.stApp { background-color: #0d0d0d; color: #e8e8e8; }
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #1f1f1f;
}

/* ── Sidebar nav radio ── */
div[data-testid="stRadio"] > div { gap: 2px; }
div[data-testid="stRadio"] label {
    background: transparent;
    border-radius: 6px;
    padding: 0.45rem 0.75rem;
    color: #8d8d8d;
    font-size: 0.88rem;
    cursor: pointer;
    transition: background 0.15s;
    width: 100%;
    display: block;
}
div[data-testid="stRadio"] label:hover { background: #1a1a1a; color: #f4f4f4; }
div[data-testid="stRadio"] label[data-checked="true"],
div[data-testid="stRadio"] label[aria-checked="true"] {
    background: #1a2a4a !important; color: #4d94ff !important; font-weight: 600;
}

/* ── Typography ── */
h1, h2, h3, h4 { color: #f4f4f4; letter-spacing: -0.3px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #161616; border-radius: 8px;
    padding: 3px; gap: 3px; border: 1px solid #222;
}
.stTabs [data-baseweb="tab"] {
    color: #6f6f6f; font-size: 0.85rem; font-weight: 500;
    border-radius: 6px; padding: 7px 14px; border: none; background: transparent;
}
.stTabs [aria-selected="true"] { background: #0f62fe !important; color: #fff !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #161616; border: 1px solid #222;
    border-radius: 10px; padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] { color: #6f6f6f !important; font-size: 0.75rem !important;
    text-transform: uppercase; letter-spacing: 0.5px; }
[data-testid="stMetricValue"] { color: #f4f4f4 !important; font-size: 1.65rem !important;
    font-weight: 700 !important; }

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
    background: #161616 !important; color: #f4f4f4 !important;
    border: 1px solid #2a2a2a !important; border-radius: 6px !important;
    font-size: 0.88rem !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background: #161616 !important; color: #c6c6c6 !important;
    border-radius: 8px !important; border: 1px solid #222 !important;
    font-size: 0.88rem !important;
}
.streamlit-expanderContent { background: #111 !important; border: 1px solid #1f1f1f !important; }

/* ── Divider ── */
hr { border-color: #1f1f1f !important; margin: 0.8rem 0 !important; }

/* ── Badges ── */
.badge { display:inline-block; padding:1px 8px; border-radius:20px;
    font-size:0.7rem; font-weight:700; margin-right:3px; letter-spacing:0.3px; }
.badge-telegram { background:#1a4a6b; color:#4db8ff; border:1px solid #229ed955; }
.badge-email    { background:#0a1e3d; color:#82b4ff; border:1px solid #0043ce55; }
.badge-web      { background:#2a1040; color:#c0a0ff; border:1px solid #6929c455; }
.badge-critical { background:#3d0a0a; color:#ff8389; border:1px solid #fa4d5655; }
.badge-high     { background:#3d2a00; color:#f5d87c; border:1px solid #f1c21b55; }
.badge-medium   { background:#0a1e3d; color:#82b4ff; border:1px solid #0f62fe55; }
.badge-low      { background:#0a2010; color:#74d08a; border:1px solid #42be6555; }
.badge-auto-routed  { background:#0a2010; color:#74d08a; border:1px solid #42be6555; }
.badge-human-review { background:#3d2a00; color:#f5d87c; border:1px solid #f1c21b55; }
.badge-escalated    { background:#3d0a0a; color:#ff8389; border:1px solid #fa4d5655; }
.badge-untriaged    { background:#1c1c1c; color:#6f6f6f; border:1px solid #2a2a2a; }
.badge-approved     { background:#0a2010; color:#74d08a; border:1px solid #42be6555; }

/* ── Inbox cards ── */
.inbox-card {
    background:#161616; border:1px solid #222; border-radius:8px;
    padding:0.75rem 1rem; margin:0.25rem 0;
    display:flex; gap:0.85rem; align-items:flex-start;
    transition: border-color 0.15s;
}
.inbox-card:hover { border-color: #333; }
.inbox-card-telegram { border-left: 3px solid #229ed9 !important; }
.inbox-card-email    { border-left: 3px solid #0f62fe !important; }
.inbox-card-web      { border-left: 3px solid #6929c4 !important; }

/* ── Outage banners ── */
.outage-critical {
    background:#1a0505; border:1px solid #fa4d5688; border-left:4px solid #fa4d56;
    border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0;
}
.outage-warning {
    background:#1a1000; border:1px solid #f1c21b55; border-left:4px solid #f1c21b;
    border-radius:8px; padding:0.8rem 1.1rem; margin:0.4rem 0;
}

/* ── Impact banner ── */
.impact-banner {
    background:linear-gradient(135deg,#001f5c,#0f3d99);
    padding:1.1rem 1.4rem; border-radius:10px; margin-bottom:1rem;
    border: 1px solid #1a4fff44;
}

/* ── Confidence bar ── */
.conf-track { background:#222; border-radius:4px; height:6px;
    width:100%; margin-top:3px; overflow:hidden; }

/* ── Terminal log ── */
.terminal {
    background:#080808; color:#3fb950;
    font-family:"IBM Plex Mono","SFMono-Regular",Consolas,monospace;
    font-size:0.78rem; padding:1rem; border-radius:8px;
    white-space:pre-wrap; line-height:1.6;
    border:1px solid #1a2a1a; max-height:500px; overflow-y:auto;
}

/* ── HITL card ── */
.hitl-card {
    background:#131000; border:1px solid #f1c21b33;
    border-left:3px solid #f1c21b; border-radius:8px;
    padding:0.85rem 1.1rem; margin-bottom:0.6rem;
}

/* ── Settings card ── */
.settings-card {
    background:#161616; border:1px solid #222; border-radius:10px;
    padding:1.2rem 1.4rem; margin-bottom:1rem;
}

/* ── Status dot ── */
.dot-on  { display:inline-block;width:7px;height:7px;border-radius:50%;background:#42be65;margin-right:6px; }
.dot-off { display:inline-block;width:7px;height:7px;border-radius:50%;background:#3d3d3d;margin-right:6px; }

/* ── Stat row ── */
.stat-row { display:flex;justify-content:space-between;align-items:center;
    padding:0.3rem 0; border-bottom:1px solid #1a1a1a; }
.stat-row:last-child { border-bottom:none; }
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


def _conf_bar_html(conf: float, width_px: int = 140) -> str:
    color = "#42be65" if conf > 0.85 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
    filled = int(conf * width_px)
    return (
        f"<div class='conf-track' style='width:{width_px}px'>"
        f"<div style='background:{color};height:6px;width:{filled}px;border-radius:4px'></div>"
        f"</div>"
        f"<small style='color:{color};font-size:0.72rem'>{conf:.0%}</small>"
    )


def _ticket_badges(t) -> str:
    ch   = (t.channel  or "web").lower()
    pri  = (t.priority or "medium").lower()
    stat = (t.status   or "untriaged").lower().replace(" ", "-")
    cat  = _html.escape((t.category or "unknown").upper())
    return (
        f"<span class='badge badge-{ch}'>{ch.upper()}</span>"
        f"<span class='badge badge-{pri}'>{pri.upper()}</span>"
        f"<span class='badge badge-{stat}'>{stat.upper()}</span>"
        f"<span class='badge' style='background:#1a1a1a;color:#8d8d8d;border:1px solid #2a2a2a'>{cat}</span>"
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

# Seed credentials from environment if not yet in session
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
# Sidebar — navigation + status
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("<div style='padding:1rem 0.5rem'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#f4f4f4;margin:0;font-size:1rem;font-weight:700'>🎫 SupportTriage AI</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#525252;font-size:0.72rem;margin:2px 0 0 0;letter-spacing:0.3px'>AGENTIC OPERATIONS CENTER</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "",
        ["📥 Inbox", "📊 Dashboard", "🧑‍💻 Review Queue", "⚙️ Settings"],
        label_visibility="collapsed",
    )

    st.divider()

    # ── Channel status indicators ──────────────────────────────────────────────
    tg_connected = bool(st.session_state.get("tg_token"))
    gm_connected = bool(st.session_state.get("gmail_user"))

    st.markdown(
        "<p style='color:#525252;font-size:0.7rem;margin:0 0 0.4rem 0;"
        "text-transform:uppercase;letter-spacing:1px;padding:0 0.5rem'>Channel Status</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
<div style='padding:0 0.5rem'>
  <div style='display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0'>
    <div style='width:7px;height:7px;border-radius:50%;
         background:{"#42be65" if tg_connected else "#2a2a2a"};flex-shrink:0'></div>
    <span style='color:{"#42be65" if tg_connected else "#525252"};font-size:0.8rem'>
      ✈️ Telegram &nbsp;{"<b>Connected</b>" if tg_connected else "Not configured"}
    </span>
  </div>
  <div style='display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0'>
    <div style='width:7px;height:7px;border-radius:50%;
         background:{"#42be65" if gm_connected else "#2a2a2a"};flex-shrink:0'></div>
    <span style='color:{"#42be65" if gm_connected else "#525252"};font-size:0.8rem'>
      📧 Gmail &nbsp;{"<b>Connected</b>" if gm_connected else "Not configured"}
    </span>
  </div>
  <div style='display:flex;align-items:center;gap:0.5rem;padding:0.25rem 0'>
    <div style='width:7px;height:7px;border-radius:50%;background:#42be65;flex-shrink:0'></div>
    <span style='color:#42be65;font-size:0.8rem'>🌐 Web Form &nbsp;<b>Active</b></span>
  </div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── Queue summary ──────────────────────────────────────────────────────────
    inbox_count   = len(st.session_state.get("inbox", []))
    review_count  = sum(
        1 for _, r in st.session_state.get("processed", [])
        if r.get("status") == "human-review"
    )
    processed_count = len(st.session_state.get("processed", []))

    st.markdown(
        "<p style='color:#525252;font-size:0.7rem;margin:0 0 0.4rem 0;"
        "text-transform:uppercase;letter-spacing:1px;padding:0 0.5rem'>Queue Summary</p>",
        unsafe_allow_html=True,
    )
    st.markdown(f"""
<div style='padding:0 0.5rem'>
  <div class='stat-row'>
    <span style='color:#8d8d8d;font-size:0.8rem'>Inbox</span>
    <span style='color:#f4f4f4;font-weight:700;font-size:0.88rem'>{inbox_count}</span>
  </div>
  <div class='stat-row'>
    <span style='color:#8d8d8d;font-size:0.8rem'>Awaiting Review</span>
    <span style='color:{"#f1c21b" if review_count else "#f4f4f4"};font-weight:700;font-size:0.88rem'>{review_count}</span>
  </div>
  <div class='stat-row'>
    <span style='color:#8d8d8d;font-size:0.8rem'>Processed</span>
    <span style='color:#f4f4f4;font-weight:700;font-size:0.88rem'>{processed_count}</span>
  </div>
</div>""", unsafe_allow_html=True)

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

st.markdown("""
<div style='display:flex;justify-content:space-between;align-items:center;
     padding:0.5rem 0 1rem 0;border-bottom:1px solid #1f1f1f;margin-bottom:1.5rem'>
  <div>
    <h1 style='color:#f4f4f4;margin:0;font-size:1.75rem;font-weight:700;letter-spacing:-0.5px'>
      SupportTriage <span style='color:#0f62fe'>AI</span>
    </h1>
    <p style='color:#525252;margin:0;font-size:0.78rem'>
      Multi-Channel Agentic Operations Center &nbsp;·&nbsp; IBM Granite 4.1 8B &nbsp;·&nbsp; Human-in-the-Loop
    </p>
  </div>
  <div style='display:flex;gap:0.5rem;align-items:center'>
    <span style='background:#0a2010;color:#42be65;padding:4px 12px;border-radius:20px;
          font-size:0.72rem;font-weight:700;border:1px solid #42be6544'>● LIVE</span>
    <span style='background:#161616;color:#6f6f6f;padding:4px 12px;border-radius:20px;
          font-size:0.72rem;border:1px solid #222'>IBM Granite 4.1 8B</span>
  </div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ⚙️ Settings
# ══════════════════════════════════════════════════════════════════════════════

if page == "⚙️ Settings":
    st.markdown("<h2 style='color:#f4f4f4;margin-bottom:0.2rem'>⚙️ Channel Configuration</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#6f6f6f;font-size:0.85rem;margin-bottom:1.5rem'>"
        "Configure your live channel integrations. Credentials are stored in your "
        "session only — never persisted to disk or GitHub.</p>",
        unsafe_allow_html=True,
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### ✈️ Telegram Bot")
        st.caption("Get your token from **@BotFather** on Telegram → `/newbot` → copy the API token.")
        tg_token_input = st.text_input(
            "Telegram Bot Token",
            value=st.session_state.get("tg_token", ""),
            type="password",
            placeholder="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ",
            key="tg_token_field",
        )
        tg_col1, tg_col2 = st.columns([1, 3])
        if tg_col1.button("💾 Save & Test", key="save_tg", use_container_width=True):
            if tg_token_input.strip():
                try:
                    import requests as _req
                    r = _req.get(
                        f"https://api.telegram.org/bot{tg_token_input}/getMe",
                        timeout=5,
                    )
                    if r.status_code == 200:
                        bot_name = r.json()["result"]["username"]
                        st.session_state["tg_token"] = tg_token_input.strip()
                        st.success(f"✅ Connected to @{bot_name}")
                    else:
                        st.error("❌ Invalid token — check and try again.")
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")
            else:
                st.warning("Please enter a token.")

    # ── Gmail IMAP ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 📧 Gmail / Email")
        st.caption(
            "Use a Gmail App Password (not your main password). "
            "Enable at: Google Account → Security → 2-Step Verification → App Passwords."
        )
        gm_col1, gm_col2 = st.columns(2)
        gmail_user_input = gm_col1.text_input(
            "Gmail Address",
            value=st.session_state.get("gmail_user", ""),
            placeholder="support@yourcompany.com",
            key="gmail_user_field",
        )
        gmail_pass_input = gm_col2.text_input(
            "App Password",
            value=st.session_state.get("gmail_pass", ""),
            type="password",
            placeholder="xxxx xxxx xxxx xxxx",
            key="gmail_pass_field",
        )
        imap_server_input = st.text_input(
            "IMAP Server",
            value=st.session_state.get("imap_server", "imap.gmail.com"),
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
                    st.session_state["gmail_user"]   = gmail_user_input.strip()
                    st.session_state["gmail_pass"]   = gmail_pass_input.strip()
                    st.session_state["imap_server"]  = server
                    st.success(f"✅ Connected to {gmail_user_input.strip()} via {server}")
                except Exception as e:
                    st.error(f"❌ Connection failed: {e}")
            else:
                st.warning("Please enter both email address and app password.")

    # ── Web Form ──────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 🌐 Web Form")
        st.info("✅ Web form intake is always active. Customers can submit tickets directly through the app.")

    # ── AI Engine ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("### 🤖 AI Engine")
        ai_key_input = st.text_input(
            "OpenRouter API Key (IBM Granite)",
            value=st.session_state.get("openrouter_key", ""),
            type="password",
            placeholder="sk-or-v1-…",
            key="ai_key_field",
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

    # ── Fetch buttons (use saved session credentials, no raw inputs) ───────────
    fetch_col_tg, fetch_col_gm, spacer = st.columns([1, 1, 4])

    if fetch_col_tg.button("✈️ Fetch Telegram", key="tg_fetch", use_container_width=True):
        tg_tok = st.session_state.get("tg_token", "")
        if not tg_tok:
            st.warning("No Telegram token saved. Go to ⚙️ Settings to configure it.")
        else:
            from intake.channels import fetch_telegram_updates
            with st.spinner("Polling Telegram…"):
                new_tickets, new_last_id = fetch_telegram_updates(
                    tg_tok, st.session_state.tg_last_id
                )
            if new_tickets:
                st.session_state.inbox.extend(new_tickets)
                st.session_state.tg_last_id = new_last_id
                st.success(f"✅ {len(new_tickets)} new message(s) added.")
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
            imap_srv = st.session_state.get("imap_server", "imap.gmail.com")
            with st.spinner("Reading Gmail IMAP…"):
                new_emails = fetch_unread_emails(gm_user, gm_pass)
            if new_emails:
                st.session_state.inbox.extend(new_emails)
                st.success(f"✅ {len(new_emails)} unread email(s) added.")
                st.rerun()
            else:
                st.info("No unread emails found.")

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

    # ── Header ─────────────────────────────────────────────────────────────────
    ch_counts  = Counter(t.channel for t in inbox)
    ch_summary = "  ·  ".join(
        "<span style='color:{c};font-size:0.82rem'>{i} {ch} ({n})</span>".format(
            c=_CHANNEL_COLOR.get(ch, "#8d8d8d"),
            i=_CHANNEL_ICON.get(ch, "?"),
            ch=ch.upper(), n=n,
        )
        for ch, n in sorted(ch_counts.items())
    )
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:0.5rem'>"
        f"<h3 style='color:#f4f4f4;margin:0'>📥 Triage Queue "
        f"<span style='color:#525252;font-size:1rem;font-weight:400'>— {len(inbox)} untriaged</span></h3>"
        f"<span style='color:#6f6f6f;font-size:0.8rem'>{ch_summary}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr style='margin:0 0 0.75rem 0'>", unsafe_allow_html=True)

    # ── Ticket cards ───────────────────────────────────────────────────────────
    for t in inbox:
        ch      = (t.channel or "web").lower()
        icon    = _CHANNEL_ICON.get(ch, "?")
        color   = _CHANNEL_COLOR.get(ch, "#8d8d8d")
        # Collapse newlines in preview so they don't fragment the HTML card
        body_flat    = (t.body or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        preview      = (body_flat[:120] + "…") if len(body_flat) > 120 else body_flat
        # Escape all user-supplied fields before HTML injection
        id_safe      = _html.escape(t.id      or "")
        sender_safe  = _html.escape(t.sender  or "")
        subject_safe = _html.escape(t.subject or "")
        preview_safe = _html.escape(preview)
        errs    = "  ".join(
            "<code style='background:#1a1a1a;color:#82b4ff;padding:1px 5px;"
            "border-radius:3px;font-size:0.72rem;border:1px solid #0f62fe33'>{e}</code>".format(
                e=_html.escape(e)
            )
            for e in t.error_codes
        ) if t.error_codes else ""

        st.markdown(f"""
<div class='inbox-card inbox-card-{ch}'>
  <span style='font-size:1.1rem;flex-shrink:0;padding-top:3px;opacity:0.85'>{icon}</span>
  <div style='flex:1;min-width:0'>
    <div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.15rem;flex-wrap:wrap'>
      <span style='color:#525252;font-size:0.72rem;font-family:monospace'>{id_safe}</span>
      <span style='color:{color};font-size:0.72rem;font-weight:700'>{ch.upper()}</span>
      <span style='color:#525252;font-size:0.72rem'>{sender_safe}</span>
      {errs}
    </div>
    <div style='color:#e8e8e8;font-weight:600;font-size:0.88rem;margin-bottom:0.15rem;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{subject_safe}</div>
    <div style='color:#525252;font-size:0.78rem;line-height:1.4'>{preview_safe}</div>
  </div>
  <span class='badge badge-untriaged' style='flex-shrink:0;margin-top:3px'>UNTRIAGED</span>
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

        raw = asyncio.run(_triage_all(list(inbox)))
        elapsed = time.perf_counter() - t_start

        new_results = []
        for i, (t, r) in enumerate(raw):
            new_results.append((t, r))
            progress.progress((i + 1) / n, text=f"Triaged {i+1}/{n}…")

        st.session_state.processed.extend(new_results)
        st.session_state.inbox = []

        log_lines = [f"[IBM Granite] {n} tickets in {elapsed:.2f}s (async batch)\n"]
        for t, r in new_results:
            log_lines.append(
                f"  [{t.channel.upper():<9}] {t.id:<10} "
                f"→ {r['queue']:<22} "
                f"| conf={t.classify_confidence:.2f} "
                f"| status={r.get('status','?'):<12} "
                f"| priority={t.priority or 'unknown'}\n"
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

    total        = len(results)
    auto_routed  = [p for p in results if p[1].get("status") == "auto-routed"]
    hitl_list    = [p for p in results if p[1].get("status") == "human-review"]
    escalated    = [p for p in results if p[1].get("status") == "escalated"]
    avg_conf     = sum(t.classify_confidence for t, _ in results) / total
    automation_rate = len(auto_routed) / total

    # ── Impact banner ──────────────────────────────────────────────────────────
    st.markdown("""<div class='impact-banner'>
<h4 style='color:white;margin:0;font-size:0.95rem;font-weight:700'>💡 Real-World Business Impact</h4>
<p style='color:#a8c8ff;margin:0.3rem 0 0 0;font-size:0.82rem;line-height:1.5'>
Support teams misroute <b style='color:white'>35% of tickets manually</b> — costing
<b style='color:white'>$329,000/year</b> for a 2,000-ticket/month operation.
HITL routing holds low-confidence tickets for agent review: only confidence &gt; 85% auto-routes.
</p>
</div>""", unsafe_allow_html=True)

    # ── KPI row ────────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎫 Processed",       total)
    m2.metric("🤖 Auto-Routed",     f"{len(auto_routed)} ({automation_rate:.0%})")
    m3.metric("🧑‍💻 Human Review",  len(hitl_list))
    m4.metric("🚨 Escalated",       len(escalated))
    m5.metric("📈 Avg Confidence",  f"{avg_conf:.0%}")

    st.divider()

    # ── Confidence gauge ───────────────────────────────────────────────────────
    conf_color = "#42be65" if avg_conf > 0.85 else "#f1c21b" if avg_conf >= 0.6 else "#fa4d56"
    st.markdown(f"""
<div style='background:#161616;border-radius:10px;padding:1rem 1.3rem;
     margin-bottom:1rem;border:1px solid #222'>
  <div style='display:flex;justify-content:space-between;margin-bottom:0.4rem'>
    <span style='color:#c6c6c6;font-size:0.82rem;font-weight:600'>
      Average Classification Confidence
    </span>
    <span style='color:{conf_color};font-size:1.15rem;font-weight:700'>{avg_conf:.0%}</span>
  </div>
  <div style='position:relative;background:#222;border-radius:4px;height:10px;width:100%'>
    <div style='background:{conf_color};border-radius:4px;height:10px;
         width:{avg_conf*100:.0f}%'></div>
    <div style='position:absolute;top:-2px;left:85%;width:1px;height:14px;
         background:#fa4d56;opacity:0.8'></div>
  </div>
  <div style='display:flex;justify-content:space-between;margin-top:4px'>
    <small style='color:{conf_color};font-size:0.72rem'>{avg_conf:.0%} batch average</small>
    <small style='color:#fa4d56;font-size:0.72rem'>▲ 85% auto-route threshold</small>
  </div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── Outage Radar ───────────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='color:#f4f4f4;margin-bottom:0.1rem'>🚨 Outage Radar</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#525252;font-size:0.8rem;margin-bottom:0.75rem'>"
        "Cross-channel symptom clustering · 3+ tickets = systemic outage</p>",
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
                c=_CHANNEL_COLOR.get(c, "#8d8d8d"),
                i=_CHANNEL_ICON.get(c, ""),
                ch=c.upper(),
            )
            for c in channels
        )
        ids_html = " ".join(
            "<code style='background:#1a1a1a;color:#82b4ff;padding:1px 5px;"
            "border-radius:3px;font-size:0.7rem'>{id}</code>".format(id=_html.escape(t.id))
            for t in tix
        )
        symptom_safe = _html.escape(symptom)
        if count >= 3:
            outage_found = True
            st.markdown(f"""<div class='outage-critical'>
<div style='font-size:0.95rem;font-weight:700;color:#ff8389;margin-bottom:0.35rem'>
  🚨 SYSTEMIC OUTAGE DETECTED
</div>
<div style='color:#f4f4f4;font-size:0.88rem;margin-bottom:0.25rem'>
  <b>{count} users</b> reporting <b>"{symptom_safe}"</b> across {ch_str}
</div>
<div style='color:#6f6f6f;font-size:0.78rem;margin-bottom:0.3rem'>{ids_html}</div>
<div style='color:#ff8389;font-size:0.78rem;font-weight:600'>
  ⚡ Escalate to engineering immediately.
</div>
</div>""", unsafe_allow_html=True)
        elif count == 2:
            st.markdown(f"""<div class='outage-warning'>
<span style='color:#f5d87c;font-weight:700;font-size:0.85rem'>⚠️ Pattern emerging</span>
&nbsp;&nbsp;
<span style='color:#c6c6c6;font-size:0.82rem'><b>{count} tickets</b> reporting
<b>"{symptom_safe}"</b> — {ch_str}</span>
&nbsp;
<span style='color:#525252;font-size:0.78rem'>Monitor for further reports.</span>
</div>""", unsafe_allow_html=True)

    if not outage_found and not any(len(v) >= 2 for v in symptom_tickets.values()):
        st.success("✅ No outage patterns detected in current batch.")

    st.divider()

    # ── Charts side by side ────────────────────────────────────────────────────
    col_cat, col_ch = st.columns(2)
    with col_cat:
        st.markdown("<h4 style='color:#c6c6c6;font-size:0.85rem;text-transform:uppercase;"
                    "letter-spacing:0.5px'>Volume by Category</h4>", unsafe_allow_html=True)
        cat_counts = Counter(t.category or "other" for t, _ in results)
        st.bar_chart(
            pd.DataFrame.from_dict(cat_counts, orient="index", columns=["Tickets"])
            .sort_values("Tickets", ascending=False)
        )
    with col_ch:
        st.markdown("<h4 style='color:#c6c6c6;font-size:0.85rem;text-transform:uppercase;"
                    "letter-spacing:0.5px'>Volume by Channel</h4>", unsafe_allow_html=True)
        ch_bar = Counter(t.channel for t, _ in results)
        st.bar_chart(pd.DataFrame.from_dict(ch_bar, orient="index", columns=["Tickets"]))

    st.divider()

    # ── System log ────────────────────────────────────────────────────────────
    with st.expander("⚙️ System Execution Log", expanded=False):
        log_text = _html.escape(st.session_state.log or "(no triage runs yet)")
        st.markdown(f"<div class='terminal'>{log_text}</div>", unsafe_allow_html=True)


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
        st.success(
            "✅ Review queue is clear — all low-confidence tickets have been approved."
        )
        st.stop()

    st.markdown(
        f"<h3 style='color:#f1c21b;margin-bottom:0.2rem'>"
        f"🧑‍💻 {len(hitl_pairs)} Ticket(s) Awaiting Agent Approval</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#525252;font-size:0.82rem;margin-bottom:1rem'>"
        "AI confidence ≤ 85% — these tickets are held for human review. "
        "Review the reasoning, edit the draft if needed, then approve to route.</p>",
        unsafe_allow_html=True,
    )

    for idx, t, r in hitl_pairs:
        conf       = t.classify_confidence
        conf_color = "#42be65" if conf > 0.85 else "#f1c21b" if conf >= 0.6 else "#fa4d56"
        ch_icon    = _CHANNEL_ICON.get(t.channel or "web", "?")

        with st.expander(
            f"{ch_icon}  {t.id}  —  {t.subject[:72]}{'…' if len(t.subject)>72 else ''}",
            expanded=False,
        ):
            sender_safe = _html.escape(t.sender or "")
            st.markdown(
                f"<div class='hitl-card'>"
                f"<div style='margin-bottom:0.4rem'>{_ticket_badges(t)}</div>"
                f"<div style='display:flex;gap:2rem;flex-wrap:wrap'>"
                f"<span style='color:#6f6f6f;font-size:0.8rem'>Sender: "
                f"<b style='color:#c6c6c6'>{sender_safe}</b></span>"
                f"<span style='color:#6f6f6f;font-size:0.8rem'>Held in: "
                f"<b style='color:#f1c21b'>human-review</b></span>"
                f"<span style='color:#6f6f6f;font-size:0.8rem'>Severity: "
                f"<b style='color:{conf_color}'>{r['severity_impact']:.1f}/10</b></span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([1, 1])

            with c1:
                st.markdown(
                    "<p style='color:#8d8d8d;font-size:0.78rem;font-weight:600;"
                    "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.4rem'>"
                    "🔍 AI Reasoning</p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"| Field | Value |\n|---|---|\n"
                    f"| Category   | `{t.category or 'unknown'}` |\n"
                    f"| Priority   | `{t.priority  or 'unknown'}` |\n"
                    f"| Confidence | `{conf:.0%}` |\n"
                    f"| Threshold  | `85%` — below = held for review |"
                )
                st.markdown(_conf_bar_html(conf, 180), unsafe_allow_html=True)
                if t.error_codes:
                    st.markdown(
                        "**Error codes:** " + " ".join(f"`{e}`" for e in t.error_codes)
                    )
                if t.symptoms:
                    chips = " ".join(
                        "<span style='background:#1a1a1a;color:#8d8d8d;padding:1px 7px;"
                        "border-radius:10px;font-size:0.72rem;border:1px solid #2a2a2a'>{s}</span>".format(
                            s=_html.escape(s)
                        )
                        for s in t.symptoms
                    )
                    st.markdown(f"**Symptoms:** {chips}", unsafe_allow_html=True)
                st.markdown("**📝 AI Summary**")
                st.info(t.summary or "_(no summary)_")

            with c2:
                st.markdown(
                    "<p style='color:#8d8d8d;font-size:0.78rem;font-weight:600;"
                    "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:0.4rem'>"
                    "✉️ Draft Reply</p>",
                    unsafe_allow_html=True,
                )
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
                    height=230,
                    label_visibility="collapsed",
                    key=f"draft_{t.id}",
                )
                if st.button(
                    "✅ Approve & Route",
                    key=f"approve_{t.id}",
                    use_container_width=True,
                    type="primary",
                ):
                    t.draft_reply = edited_draft
                    t.status      = "approved"
                    results[idx]  = (t, {**r, "queue": approved_queue, "status": "approved"})
                    st.session_state.processed = results
                    st.session_state.log += (
                        f"  [HITL APPROVED] {t.id} → {approved_queue} by agent\n"
                    )
                    st.success(f"✅ {t.id} approved and routed to `{approved_queue}`.")
                    st.rerun()


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#1a1a1a;margin-top:2.5rem'>"
    "<p style='text-align:center;color:#2a2a2a;font-size:11px;padding-bottom:1rem'>"
    "Made with IBM Bob</p>",
    unsafe_allow_html=True,
)
