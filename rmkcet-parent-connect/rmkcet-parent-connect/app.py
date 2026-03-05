# app.py
"""RMKCET Parent Connect - Main Application Entry Point."""
import streamlit as st
import time
from datetime import datetime

from config import APP_NAME, SESSION_TIMEOUT, THEME
import database as db
from ui.styles import load_custom_css as inject_css
from ui.login_page import login_page
from ui.admin_panel import admin_panel
from ui.counselor_dashboard import counselor_dashboard
from ui.test_results import test_results_page


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Initialize DB ───────────────────────────────────────────────────────────
db.init_database()

# ─── Inject CSS Theme ────────────────────────────────────────────────────────
inject_css()

# ─── Session Timer JS ────────────────────────────────────────────────────────
if st.session_state.get('authenticated'):
    # Auto-refresh session timer (JS injection)
    timer_js = f"""
    <script>
    (function() {{
        var timeout = {SESSION_TIMEOUT} * 1000;
        var lastActivity = Date.now();
        var warned = false;

        document.addEventListener('mousemove', function() {{ lastActivity = Date.now(); warned = false; }});
        document.addEventListener('keypress', function() {{ lastActivity = Date.now(); warned = false; }});
        document.addEventListener('click', function() {{ lastActivity = Date.now(); warned = false; }});

        setInterval(function() {{
            var elapsed = Date.now() - lastActivity;
            var remaining = Math.max(0, timeout - elapsed);
            var mins = Math.floor(remaining / 60000);
            var secs = Math.floor((remaining % 60000) / 1000);
            var el = document.getElementById('session-timer');
            if (el) {{
                el.textContent = mins + ':' + (secs < 10 ? '0' : '') + secs;
                if (remaining < 120000) {{
                    el.style.color = '#e74c3c';
                }} else {{
                    el.style.color = '#25D366';
                }}
            }}
            if (remaining <= 0) {{
                // Session expired
                window.location.reload();
            }}
        }}, 1000);
    }})();
    </script>
    """
    st.components.v1.html(timer_js, height=0)

# ─── Cleanup Stale Sessions ──────────────────────────────────────────────────
try:
    db.cleanup_stale_sessions()
except Exception:
    pass


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _check_session_valid():
    """Check if the current session is still valid."""
    session_id = st.session_state.get('session_id')
    if not session_id:
        return False
    return db.validate_session(session_id)


def _logout():
    """Log out the current user."""
    session_id = st.session_state.get('session_id')
    if session_id:
        db.end_session(session_id)

    for key in ['authenticated', 'session_id', 'user_email', 'user_name',
                'user_role', 'department', 'page']:
        st.session_state.pop(key, None)
    st.rerun()


def _render_sidebar():
    """Render the sidebar with user info and navigation."""
    with st.sidebar:
        # App title
        st.markdown(f"""
        <div style="text-align:center; padding:1rem 0;">
            <h2 style="color:#667eea; margin:0;">🎓 RMKCET</h2>
            <p style="color:#cbd5e1; font-size:0.85rem; margin:0;">Parent Connect</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # User info
        user_name = st.session_state.get('user_name', 'User')
        user_role = st.session_state.get('user_role', '')
        department = st.session_state.get('department', '')
        role_emoji = "👑" if user_role == 'admin' else "👨‍🏫"

        st.markdown(f"""
        <div class="glass-card" style="padding:0.8rem;">
            <p style="margin:0; color:white; font-weight:bold;">
                {role_emoji} {user_name}
            </p>
            <p style="margin:0.2rem 0 0 0; color:#cbd5e1; font-size:0.8rem;">
                {user_role.title()} {f'| {department}' if department else ''}
            </p>
            <p style="margin:0.3rem 0 0 0; color:#cbd5e1; font-size:0.75rem;">
                ⏱️ Session: <span id="session-timer" style="color:#25D366;">--:--</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        if user_role == 'admin':
            pages = {
                "🛡️ Admin Panel": "admin",
                "👨‍🏫 Counselor View": "counselor",
                "📊 Test Results": "test_results",
            }
        else:
            pages = {
                "👨‍🏫 Dashboard": "counselor",
                "📊 Test Results": "test_results",
            }

        for label, page_key in pages.items():
            if st.button(label, use_container_width=True,
                        type="primary" if st.session_state.get('page') == page_key else "secondary"):
                st.session_state['page'] = page_key
                st.rerun()

        st.markdown("---")

        # Quick stats
        if user_role == 'admin':
            sessions = db.get_active_sessions()
            st.caption(f"🔌 Active sessions: {len(sessions)}")

        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            _logout()


# ─── Main Application Logic ──────────────────────────────────────────────────

def main():
    """Main application routing."""
    # Check if user is authenticated
    if not st.session_state.get('authenticated'):
        login_page()
        return

    # Validate session
    if not _check_session_valid():
        st.warning("⏰ Your session has expired. Please log in again.")
        _logout()
        return

    # Update session activity
    session_id = st.session_state.get('session_id')
    if session_id:
        db.touch_session(session_id)

    # Render sidebar
    _render_sidebar()

    # Set default page
    if 'page' not in st.session_state:
        st.session_state['page'] = 'admin' if st.session_state.get('user_role') == 'admin' else 'counselor'

    # Route to page
    page = st.session_state.get('page', 'counselor')

    if page == 'admin' and st.session_state.get('user_role') == 'admin':
        admin_panel()
    elif page == 'counselor':
        counselor_dashboard()
    elif page == 'test_results':
        test_results_page()
    else:
        counselor_dashboard()


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
else:
    main()
