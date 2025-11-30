import streamlit as st

from trustguard.llm import llm_assess_message
import os
from trustguard.storage import load_contacts, save_contacts, hash_safe_word, verify_safe_word
from trustguard.templates import generate_report

st.set_page_config(page_title="TrustGuard", page_icon="🛡️", layout="centered")

# Accessible, elderly-friendly styling
st.markdown(
    """
    <style>
    :root {
        --tg-text: #ffffff;
        --tg-muted: #dddddd;
        --tg-primary: #005fcc;
        --tg-success: #1a7f37;
        --tg-danger: #b00020;
        --tg-border: #222222;
    }

    html, body, [class^="css"], .stApp {
        color: var(--tg-text) !important;
        font-size: 20px;
        line-height: 1.6;
    }

    .block-container { max-width: 880px; padding: 2rem 1.5rem; }
    h1, h2, h3 { letter-spacing: 0.2px; }
    h1 { font-size: 34px; }
    h2 { font-size: 28px; }
    h3 { font-size: 24px; }

    textarea, input, select { font-size: 20px !important; }
    textarea { min-height: 200px !important; }

    .stButton>button {
        font-size: 20px;
        padding: 14px 18px;
        border: 2px solid var(--tg-border);
        border-radius: 8px;
        background: var(--tg-primary);
        color: #ffffff;
        font-weight: 700;
    }

    .stMarkdown ul { margin-left: 1.2rem; }
    .stCaption { font-size: 18px; color: var(--tg-muted); }

    [data-testid="stProgressBar"] div div { background-color: var(--tg-primary) !important; }

    .tg-section { border: 2px solid var(--tg-border); padding: 16px; border-radius: 10px; background: #222222; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛡️ TrustGuard")

#Banner
st.markdown(
    """
TrustGuard helps you:
- Check if a message looks risky
- Keep a small list of trusted contacts with a shared safe word
- Generate clear consent and report templates you can download

All data stays on your device. No cloud or external APIs.
"""
)

# Tabs
check_tab, contacts_tab, report_tab, learn_tab = st.tabs([
    "Check a Message", "Trusted Contacts", "Report", "Learn"
])

with check_tab:
    st.subheader("Check a Message")
    sample = """URGENT: Your account will be suspended in 24 hours! Click https://rnicrosoft.com-login.example.zip to verify your password and 2FA code now!"""
    st.markdown('<div class="tg-section">', unsafe_allow_html=True)
    msg = st.text_area("Message text", height=220, value=sample)
    sender = st.text_input("Sender", placeholder="e.g., no-reply@google.com or google.com")
    allow = st.text_input("Trusted brands/domains (comma-separated)", placeholder="e.g., google.com, microsoft.com")
    st.caption("Requires `OPENAI_API_KEY`. Tap Analyze to check risk.")
    analyze = st.button("Analyze Message")
    st.markdown('</div>', unsafe_allow_html=True)
    if analyze:
        try:
            allowlist = [a.strip() for a in (allow or "").split(",") if a.strip()]
            ai = llm_assess_message(msg, sender=sender, allowlist=allowlist)
            st.markdown(f"### Risk: {ai['verdict']} ({ai['score']}/100)")
            st.progress(ai['score'] / 100)
            st.caption(f"Confidence: {ai.get('confidence', 0.6):.2f}")
            if ai.get("reasons"):
                st.markdown("**Reasons**")
                for r in ai["reasons"]:
                    st.write(f"- {r}")
            if ai.get("advice"):
                st.markdown("**Advice**")
                for a in ai["advice"]:
                    st.write(f"- {a}")
        except Exception as e:
            st.error(f"AI check failed: {e}")
            st.caption("Set OPENAI_API_KEY and try again.")
        st.markdown('<div class="tg-section">', unsafe_allow_html=True)
        st.markdown("**Next steps**")
        st.write("- Never share passwords or codes.")
        st.write("- Call the company using their official number.")
        st.write("- If unsure, verify with a trusted contact and your safe word.")
        st.markdown('</div>', unsafe_allow_html=True)

with contacts_tab:
    st.subheader("Trusted Contacts")
    st.caption("People you can safely speak to about accounts, appointments, and emergencies.")

    contacts = load_contacts()

    with st.expander("Add or Update Contact"):
        name = st.text_input("Name")
        channel = st.text_input("Phone or Email")
        safe_word = st.text_input("Shared Safe Word", type="password", help="A word you both know and can confirm")
        if st.button("Save Contact"):
            if not name or not channel or not safe_word:
                st.error("Please fill in all fields.")
            else:
                hashed = hash_safe_word(safe_word)
                # Replace if exists
                remaining = [c for c in contacts if c.get("name") != name]
                remaining.append({"name": name, "channel": channel, "safe_hash": hashed})
                save_contacts(remaining)
                st.success(f"Saved contact: {name}")
                contacts = remaining

    if contacts:
        st.markdown("**Your Contacts**")
        for c in contacts:
            st.write(f"- {c['name']} · {c['channel']}")
    else:
        st.info("No contacts yet. Add one above.")

    st.divider()
    st.markdown("**Verify a Safe Word**")
    if contacts:
        pick = st.selectbox("Choose contact", [c["name"] for c in contacts])
        attempt = st.text_input("Enter safe word", type="password")
        if st.button("Verify"):
            contact = next((c for c in contacts if c["name"] == pick), None)
            if contact and verify_safe_word(contact["safe_hash"], attempt):
                st.success("Match. You can trust this conversation starter.")
            else:
                st.error("No match. Hang up and call back using your own contact list.")
    else:
        st.caption("Add a contact to enable verification.")

with report_tab:
    st.subheader("Scam Report")
    st.markdown('<div class="tg-section">', unsafe_allow_html=True)
    r_name = st.text_input("Your Name", key="report_name")
    r_contact = st.text_input("Your Phone or Email", key="report_contact")
    r_summary = st.text_area("What happened?", key="report_summary")
    generate = st.button("Generate Report")
    st.markdown('</div>', unsafe_allow_html=True)
    if generate:
        if not r_name or not r_contact or not r_summary:
            st.error("Please fill in all fields.")
        else:
            rep = generate_report(r_name, r_contact, r_summary)
            st.text_area("Preview", rep, height=200)
            st.download_button("Download Report", data=rep.encode("utf-8"), file_name="scam_report.txt")

with learn_tab:
    st.subheader("Learn: 10 Quick Safeguards")
    tips = [
        "Use a shared safe word with a trusted contact.",
        "Never share 2FA codes, OTPs, or passwords.",
        "Pause: urgent threats push quick decisions.",
        "Check the sender's address; beware lookalike domains.",
        "Type official websites yourself; avoid clicking links.",
        "If unsure, call back using a number you already trust.",
        "Ignore payment via gift cards, crypto, or wire transfers.",
        "Be wary of mixed scripts or odd characters in links.",
        "Keep devices up to date; enable multifactor auth.",
        "Talk to family/caregivers before large decisions."
    ]
    st.markdown('<div class="tg-section">', unsafe_allow_html=True)
    for t in tips:
        st.write(f"- {t}")
    st.markdown('</div>', unsafe_allow_html=True)

# Hide deploy button
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)