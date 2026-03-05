# ui/login_page.py
"""Login page with password reset support."""
import streamlit as st
import hashlib
import time
import uuid
from database import authenticate_user, get_user, check_user_access, update_user, register_session
from utils.validators import validate_email
from utils.otp_helper import generate_token
from utils.email_helper import send_password_reset_email
from database import create_reset_token, validate_reset_token, use_reset_token


def login_page():
    """Render the login page."""
    st.markdown("""
    <div style="max-width:450px; margin:2rem auto;">
        <div class="glass-card" style="text-align:center; padding:2rem;">
            <h2 style="background: linear-gradient(135deg, #667eea, #764ba2);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                🔐 Sign In
            </h2>
            <p style="color:#cbd5e1;">Enter your credentials to continue</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tab: Login or Forgot Password
    tab1, tab2 = st.tabs(["🔑 Login", "🔄 Reset Password"])

    with tab1:
        _render_login_form()

    with tab2:
        _render_reset_form()


def _render_login_form():
    with st.form("login_form"):
        email = st.text_input("📧 Email Address", placeholder="you@rmkcet.ac.in")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("🚀 Login", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
            return

        user = authenticate_user(email.strip().lower(), password)
        if not user:
            st.error("❌ Invalid email or password.")
            return

        # Check access
        allowed, msg = check_user_access(email.strip().lower())
        if not allowed:
            st.error(f"❌ {msg}")
            return

        # Create DB session
        session_id = str(uuid.uuid4())
        register_session(session_id, user['email'])

        # Set session state (keys must match what app.py reads)
        st.session_state['authenticated'] = True
        st.session_state['session_id'] = session_id
        st.session_state['user_email'] = user['email']
        st.session_state['user_name'] = user['name']
        st.session_state['user_role'] = user['role']
        st.session_state['department'] = user.get('department', '')
        st.session_state['login_time'] = time.time()
        st.session_state['page'] = 'admin' if user['role'] == 'admin' else 'counselor'

        # Update last login
        update_user(user['email'], last_login=time.strftime('%Y-%m-%d %H:%M:%S'))

        st.success(f"✅ Welcome, {user['name']}!")
        st.rerun()


def _render_reset_form():
    step = st.session_state.get('reset_step', 'email')

    if step == 'email':
        with st.form("reset_email_form"):
            email = st.text_input("📧 Your registered email")
            submitted = st.form_submit_button("📤 Send Reset Token", use_container_width=True)

        if submitted and email:
            user = get_user(email.strip().lower())
            if user:
                token = generate_token(8)
                create_reset_token(email.strip().lower(), token)
                sent = send_password_reset_email(email.strip().lower(), token)
                if sent:
                    st.success("✅ Reset token sent to your email!")
                else:
                    st.info(f"📋 Your reset token: **{token}** (email not configured)")
                st.session_state['reset_step'] = 'token'
                st.session_state['reset_email'] = email.strip().lower()
                st.rerun()
            else:
                st.error("Email not found.")

    elif step == 'token':
        with st.form("reset_token_form"):
            token = st.text_input("🔑 Enter reset token")
            new_pass = st.text_input("🔒 New password", type="password")
            confirm = st.text_input("🔒 Confirm password", type="password")
            submitted = st.form_submit_button("🔄 Reset Password", use_container_width=True)

        if submitted:
            if new_pass != confirm:
                st.error("Passwords don't match.")
                return
            if len(new_pass) < 6:
                st.error("Password must be at least 6 characters.")
                return

            result = validate_reset_token(token)
            if result:
                email = result['user_email']
                update_user(email, password=new_pass)
                use_reset_token(token)
                st.success("✅ Password reset successfully! Please login.")
                st.session_state['reset_step'] = 'email'
                st.rerun()
            else:
                st.error("Invalid or expired token.")

        if st.button("← Back"):
            st.session_state['reset_step'] = 'email'
            st.rerun()
