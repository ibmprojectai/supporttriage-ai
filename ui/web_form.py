import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from intake.web_form import submit_web_ticket
import os as _os

st.set_page_config(page_title="Support Center", page_icon="🎫", layout="centered")

st.markdown("""<style>
.stApp { background-color: #f4f4f4; }
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: #ffffff !important;
    border: 1px solid #e0e0e0 !important;
    border-radius: 6px !important;
    color: #161616 !important;
    font-size: 0.95rem !important;
}
.stButton > button {
    background: #0f62fe !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.6rem 2rem !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    width: 100% !important;
}
.stButton > button:hover { background: #0353e9 !important; }
label { color: #161616 !important; font-weight: 500 !important; }
</style>""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style='text-align:center;padding:2rem 0 1.5rem 0;border-bottom:1px solid #e0e0e0;margin-bottom:2rem'>
  <h1 style='color:#161616;font-size:1.8rem;font-weight:700;margin:0'>
    🎫 Support Center
  </h1>
  <p style='color:#525252;margin:0.5rem 0 0 0;font-size:0.95rem'>
    Submit a support request and our team will respond within 24 hours.
  </p>
</div>
""", unsafe_allow_html=True)

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.session_state.submitted:
    st.markdown("""
    <div style='background:#defbe6;border:1px solid #24a148;border-radius:10px;padding:2rem;text-align:center;margin:2rem 0'>
      <h2 style='color:#0e6027;margin:0'>✅ Ticket Submitted Successfully</h2>
      <p style='color:#0e6027;margin:0.5rem 0 0 0'>
        Your request has been received. You will receive a confirmation email shortly.<br>
        Our AI triage system is already processing your ticket.
      </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Submit Another Request"):
        st.session_state.submitted = False
        st.rerun()
else:
    with st.form("support_form", clear_on_submit=False):
        st.markdown("#### Your Information")
        col1, col2 = st.columns(2)
        full_name = col1.text_input("Full Name *", placeholder="Jane Smith")
        sender_email = col2.text_input("Email Address *", placeholder="jane@company.com")

        st.markdown("#### Issue Details")
        product = st.selectbox("Product / Service *", [
            "DataPilot Pro", "DataPilot Lite", "API Gateway",
            "CloudSync", "Analytics Dashboard", "Other"
        ])
        priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
        subject = st.text_input("Subject *", placeholder="Brief description of the issue")
        body = st.text_area("Description *", height=180,
            placeholder=(
                "Please describe your issue in detail.\n\n"
                "Include:\n"
                "- What you were trying to do\n"
                "- What happened instead\n"
                "- Any error codes or messages you saw\n"
                "- Steps you have already tried"
            ))
        account_id = st.text_input("Account ID (if known)", placeholder="ACC-XXXXX")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚀 Submit Support Request", use_container_width=True)

    if submitted:
        if not full_name or not sender_email or not subject or not body:
            st.error("Please fill in all required fields marked with *")
        else:
            dest = _os.getenv("SUPPORT_EMAIL", _os.getenv("GMAIL_USER", ""))
            smtp_user = _os.getenv("GMAIL_USER", "")
            smtp_pass = _os.getenv("GMAIL_APP_PASSWORD", "")

            if dest and smtp_user and smtp_pass:
                with st.spinner("Submitting your ticket..."):
                    ok, msg = submit_web_ticket(
                        sender_name=full_name,
                        sender_email=sender_email,
                        subject=subject,
                        body=body,
                        product=product,
                        priority=priority,
                        account=account_id,
                        dest_email=dest,
                        smtp_user=smtp_user,
                        smtp_pass=smtp_pass,
                    )
                if ok:
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.error("Failed to submit: {}".format(msg))
            else:
                # Demo mode — no email credentials configured
                st.session_state.submitted = True
                st.rerun()
