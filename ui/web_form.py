"""SupportTriage AI — Enterprise Customer Support Portal.

A standalone public-facing Streamlit app for customers to submit support tickets.
Submissions are emailed to the support inbox via SMTP and auto-tagged [SUPPORT-TICKET]
so the IMAP intake in the ops center picks them up automatically.

Launch:
    streamlit run ui/web_form.py --server.port 8502
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from intake.web_form import submit_web_ticket
import os as _os

st.set_page_config(
    page_title="Support Center — SupportTriage AI",
    page_icon="🎫",
    layout="centered",
)

st.markdown("""<style>
.stApp { background-color: #f5f5f5; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: #ffffff !important;
    border: 1px solid #dde1e7 !important;
    border-radius: 6px !important;
    color: #161616 !important;
    font-size: 0.92rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0f62fe !important;
    box-shadow: 0 0 0 2px #0f62fe22 !important;
}

/* Submit button */
.stButton > button {
    background: #0f62fe !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.65rem 2rem !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    letter-spacing: 0.2px !important;
    transition: background 0.15s !important;
}
.stButton > button:hover { background: #0353e9 !important; }

/* Labels */
label { color: #161616 !important; font-weight: 500 !important; font-size: 0.88rem !important; }

/* Caption / help text */
.stCaption, small { color: #6f6f6f !important; }

/* Section divider */
hr { border-color: #dde1e7 !important; margin: 1.25rem 0 !important; }

/* Required star */
.req { color: #da1e28; font-weight: 700; }

/* Info/success boxes */
.stAlert { border-radius: 8px !important; }
</style>""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;padding:2.5rem 0 2rem 0;"
    "border-bottom:1px solid #dde1e7;margin-bottom:2rem'>"
    "<div style='display:inline-flex;align-items:center;gap:0.6rem;margin-bottom:0.75rem'>"
    "<span style='font-size:1.8rem'>🎫</span>"
    "<span style='font-size:1.5rem;font-weight:700;color:#161616;letter-spacing:-0.5px'>"
    "Support Center</span>"
    "</div>"
    "<p style='color:#525252;margin:0;font-size:0.9rem;line-height:1.5'>"
    "Submit a support request and our team will respond within your SLA window."
    "</p>"
    "<div style='display:flex;justify-content:center;gap:1.5rem;margin-top:1rem;"
    "flex-wrap:wrap'>"
    "<span style='color:#525252;font-size:0.78rem'>🔴 Critical — 2 hours</span>"
    "<span style='color:#525252;font-size:0.78rem'>🟡 High — 8 hours</span>"
    "<span style='color:#525252;font-size:0.78rem'>🔵 Medium — 24 hours</span>"
    "<span style='color:#525252;font-size:0.78rem'>🟢 Low — 72 hours</span>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# ── Success state ──────────────────────────────────────────────────────────────
if st.session_state.submitted:
    st.markdown(
        "<div style='background:#defbe6;border:1px solid #24a148;border-radius:10px;"
        "padding:2.5rem 2rem;text-align:center;margin:1.5rem 0'>"
        "<div style='font-size:2.5rem;margin-bottom:0.5rem'>✅</div>"
        "<h2 style='color:#0e6027;margin:0;font-size:1.3rem;font-weight:700'>"
        "Ticket Submitted Successfully</h2>"
        "<p style='color:#198038;margin:0.75rem 0 0 0;font-size:0.88rem;line-height:1.6'>"
        "Your request has been received and assigned a ticket ID.<br>"
        "Our AI triage system is processing it now — you will hear from us within your SLA window."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # What happens next
    st.markdown(
        "<div style='background:#ffffff;border:1px solid #dde1e7;border-radius:10px;"
        "padding:1.25rem 1.5rem;margin-top:1rem'>"
        "<p style='color:#161616;font-weight:600;margin:0 0 0.75rem 0;font-size:0.88rem'>"
        "What happens next:</p>"
        "<div style='display:flex;flex-direction:column;gap:0.5rem'>"
        "<div style='display:flex;align-items:flex-start;gap:0.75rem'>"
        "<span style='background:#0f62fe;color:white;border-radius:50%;width:20px;height:20px;"
        "display:flex;align-items:center;justify-content:center;font-size:0.65rem;"
        "font-weight:700;flex-shrink:0;margin-top:1px'>1</span>"
        "<span style='color:#525252;font-size:0.85rem'>"
        "IBM Granite AI classifies your ticket and assigns priority</span></div>"
        "<div style='display:flex;align-items:flex-start;gap:0.75rem'>"
        "<span style='background:#0f62fe;color:white;border-radius:50%;width:20px;height:20px;"
        "display:flex;align-items:center;justify-content:center;font-size:0.65rem;"
        "font-weight:700;flex-shrink:0;margin-top:1px'>2</span>"
        "<span style='color:#525252;font-size:0.85rem'>"
        "Ticket is routed to the correct support queue automatically</span></div>"
        "<div style='display:flex;align-items:flex-start;gap:0.75rem'>"
        "<span style='background:#0f62fe;color:white;border-radius:50%;width:20px;height:20px;"
        "display:flex;align-items:center;justify-content:center;font-size:0.65rem;"
        "font-weight:700;flex-shrink:0;margin-top:1px'>3</span>"
        "<span style='color:#525252;font-size:0.85rem'>"
        "A support agent reviews, edits the AI draft, and sends a reply</span></div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("← Submit Another Request", key="reset_form"):
        st.session_state.submitted = False
        st.rerun()
    st.stop()

# ── Form ───────────────────────────────────────────────────────────────────────
with st.form("support_form", clear_on_submit=False):

    # Section: Contact
    st.markdown(
        "<p style='font-size:0.72rem;color:#525252;text-transform:uppercase;"
        "letter-spacing:0.8px;font-weight:600;margin-bottom:0.75rem'>Contact Information</p>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    full_name    = col1.text_input("Full Name ✳", placeholder="Jane Smith")
    sender_email = col2.text_input("Email Address ✳", placeholder="jane@company.com")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Section: Issue
    st.markdown(
        "<p style='font-size:0.72rem;color:#525252;text-transform:uppercase;"
        "letter-spacing:0.8px;font-weight:600;margin-bottom:0.75rem'>Issue Details</p>",
        unsafe_allow_html=True,
    )
    pr_col, pd_col = st.columns(2)
    product  = pr_col.selectbox("Product / Service ✳", [
        "DataPilot Pro", "DataPilot Lite", "DataPilot Business", "DataPilot Enterprise",
        "API Gateway", "CloudSync", "CloudSync Enterprise", "Analytics Dashboard", "Other",
    ])
    priority = pd_col.selectbox("Priority ✳", [
        "Low — general question or enhancement",
        "Medium — feature impacted but workaround exists",
        "High — significant impact, no workaround",
        "Critical — full outage or data loss",
    ])
    subject = st.text_input("Subject ✳", placeholder="One-line summary of the issue")
    body    = st.text_area(
        "Description ✳", height=200,
        placeholder=(
            "Please describe your issue in detail:\n\n"
            "• What were you trying to do?\n"
            "• What happened instead?\n"
            "• Any error codes or messages?\n"
            "• Steps to reproduce?\n"
            "• Steps you have already tried?"
        ),
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Section: Account
    st.markdown(
        "<p style='font-size:0.72rem;color:#525252;text-transform:uppercase;"
        "letter-spacing:0.8px;font-weight:600;margin-bottom:0.75rem'>Account (optional)</p>",
        unsafe_allow_html=True,
    )
    ac_col, env_col = st.columns(2)
    account_id   = ac_col.text_input("Account ID", placeholder="ACC-XXXXX")
    environment  = env_col.selectbox("Environment", ["Production", "Staging", "Development", "Unknown"])

    st.markdown("<br>", unsafe_allow_html=True)

    # Privacy note
    st.markdown(
        "<p style='color:#6f6f6f;font-size:0.75rem;text-align:center;margin-bottom:0.5rem'>"
        "✳ Required fields &nbsp;·&nbsp; "
        "Your data is processed securely and used only to resolve your support request.</p>",
        unsafe_allow_html=True,
    )

    submitted = st.form_submit_button(
        "🚀 Submit Support Request",
        use_container_width=True,
    )

# ── Handle submission ──────────────────────────────────────────────────────────
if submitted:
    # Extract priority label (first word)
    priority_clean = priority.split("—")[0].strip() if "—" in priority else priority

    if not full_name.strip() or not sender_email.strip() or not subject.strip() or not body.strip():
        st.error("⚠️ Please fill in all required fields marked with ✳")
    elif "@" not in sender_email or "." not in sender_email:
        st.error("⚠️ Please enter a valid email address.")
    else:
        dest      = _os.getenv("SUPPORT_EMAIL", _os.getenv("GMAIL_USER", ""))
        smtp_user = _os.getenv("GMAIL_USER", "")
        smtp_pass = _os.getenv("GMAIL_APP_PASSWORD", "")

        if dest and smtp_user and smtp_pass:
            with st.spinner("Submitting your ticket securely…"):
                ok, msg = submit_web_ticket(
                    sender_name=full_name.strip(),
                    sender_email=sender_email.strip(),
                    subject=subject.strip(),
                    body="Environment: {}\n\n{}".format(environment, body.strip()),
                    product=product,
                    priority=priority_clean,
                    account=account_id.strip(),
                    dest_email=dest,
                    smtp_user=smtp_user,
                    smtp_pass=smtp_pass,
                )
            if ok:
                st.session_state.submitted = True
                st.rerun()
            else:
                st.error("Failed to submit ticket: {}".format(msg))
                st.caption("Please try again or contact support directly.")
        else:
            # Demo mode — show success without sending
            st.session_state.submitted = True
            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;margin-top:3rem;padding-top:1.25rem;"
    "border-top:1px solid #dde1e7'>"
    "<p style='color:#a8a8a8;font-size:0.75rem;margin:0'>"
    "Powered by <b>SupportTriage AI</b> &nbsp;·&nbsp; IBM Granite 4.1 8B &nbsp;·&nbsp; "
    "Built with IBM Bob"
    "</p>"
    "</div>",
    unsafe_allow_html=True,
)
