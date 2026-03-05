# ui/admin_panel.py
"""Admin panel with user, department, session, and config management."""
import streamlit as st
import pandas as pd
import json
from datetime import datetime

import database as db
from config import ALLOWED_EMAIL_DOMAINS, SESSION_TIMEOUT
from ui.styles import metric_card, status_badge
from ui.admin_format_settings import format_settings_tab
from utils.validators import validate_email, validate_password


def admin_panel():
    """Main admin panel entry point."""
    st.markdown('<h2 style="color:#667eea;">🛡️ Admin Panel</h2>', unsafe_allow_html=True)

    tabs = st.tabs([
        "👥 Users", "🏛️ Departments", "📊 Overview",
        "🔍 Sessions", "⚙️ Settings", "📨 Format Settings", "📋 Message Logs"
    ])

    with tabs[0]:
        _users_tab()
    with tabs[1]:
        _departments_tab()
    with tabs[2]:
        _overview_tab()
    with tabs[3]:
        _sessions_tab()
    with tabs[4]:
        _settings_tab()
    with tabs[5]:
        format_settings_tab()
    with tabs[6]:
        _message_logs_tab()


# =========================================================================
# USERS TAB
# =========================================================================

def _users_tab():
    st.subheader("User Management")

    # Quick stats
    users = db.get_all_users()
    admins = [u for u in users if u['role'] == 'admin']
    counselors = [u for u in users if u['role'] == 'counselor']
    locked = [u for u in users if u.get('is_locked')]

    cols = st.columns(4)
    with cols[0]:
        metric_card("Total Users", len(users), "👥")
    with cols[1]:
        metric_card("Admins", len(admins), "👑")
    with cols[2]:
        metric_card("Counselors", len(counselors), "👨‍🏫")
    with cols[3]:
        metric_card("Locked", len(locked), "🔒")

    st.markdown("---")

    # Create / Search
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("➕ Create User", use_container_width=True):
            st.session_state['admin_action'] = 'create_user'

    with col2:
        search = st.text_input("🔍 Search users", placeholder="Name, email, role...")

    # Filter
    if search:
        q = search.lower()
        users = [u for u in users if q in u['name'].lower() or q in u['email'].lower()
                 or q in u.get('role', '').lower() or q in u.get('department', '').lower()]

    # Create user form
    if st.session_state.get('admin_action') == 'create_user':
        _create_user_form()

    # User list
    for user in users:
        _render_user_card(user)


def _create_user_form():
    st.markdown("### ➕ Create New User")
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
        with col2:
            role = st.selectbox("Role", ["counselor", "admin"])
            departments = db.get_departments()
            dept_names = ["None"] + [d["code"] for d in departments]
            dept = st.selectbox("Department", dept_names)
            max_students = st.number_input("Max Students", min_value=1, max_value=200, value=30)

        submitted = st.form_submit_button("✅ Create User", use_container_width=True)

    if submitted:
        if not name or not email or not password:
            st.error("All fields are required.")
            return
        if not validate_email(email):
            st.error(f"Invalid email. Allowed domains: {', '.join(ALLOWED_EMAIL_DOMAINS)}")
            return
        valid, msg = validate_password(password)
        if not valid:
            st.error(msg)
            return

        dept_val = dept if dept != "None" else None
        ok, msg = db.create_user(email.lower(), password, name, role, dept_val, max_students)
        if ok:
            st.success(f"✅ User '{name}' created!")
            st.session_state['admin_action'] = None
            st.rerun()
        else:
            st.error(msg)


def _render_user_card(user):
    role_badge = status_badge(user['role'].title(),
                              'admin' if user['role'] == 'admin' else 'counselor')
    lock_badge = status_badge("Locked", "locked") if user.get('is_locked') else ""
    active_badge = "" if user.get('is_active', True) else status_badge("Inactive", "inactive")

    st.markdown(f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h4 style="margin:0; color:white;">
                    👤 {user['name']} {role_badge} {lock_badge} {active_badge}
                </h4>
                <p style="margin:0.2rem 0; color:#cbd5e1; font-size:0.85rem;">
                    📧 {user['email']}
                    {f" &nbsp;|&nbsp; 🏛️ {user.get('department', '')}" if user.get('department') else ""}
                    &nbsp;|&nbsp; 📊 Max: {user.get('max_students', 30)} students
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Action buttons
    cols = st.columns(5)
    uid = user['email'].replace('@', '_').replace('.', '_')

    with cols[0]:
        if st.button("✏️ Edit", key=f"edit_{uid}", use_container_width=True):
            st.session_state[f'editing_{uid}'] = True

    with cols[1]:
        if user.get('is_locked'):
            if st.button("🔓 Unlock", key=f"unlock_{uid}", use_container_width=True):
                db.unlock_user(user['email'])
                st.success("Unlocked!")
                st.rerun()
        else:
            if st.button("🔒 Lock", key=f"lock_{uid}", use_container_width=True):
                db.lock_user(user['email'])
                st.success("Locked!")
                st.rerun()

    with cols[2]:
        if st.button("🔑 Reset PW", key=f"resetpw_{uid}", use_container_width=True):
            db.update_user(user['email'], password="Reset@123")
            st.success("Password reset to: Reset@123")

    with cols[3]:
        if st.button("🚪 Force Logout", key=f"logout_{uid}", use_container_width=True):
            db.force_logout_user(user['email'])
            st.success("Force logged out!")
            st.rerun()

    with cols[4]:
        if user['role'] != 'admin' or len([u for u in db.get_all_users() if u['role'] == 'admin']) > 1:
            if st.button("🗑️ Delete", key=f"del_{uid}", use_container_width=True):
                st.session_state[f'confirm_del_{uid}'] = True

    # Confirm delete
    if st.session_state.get(f'confirm_del_{uid}'):
        st.warning(f"⚠️ Permanently delete **{user['name']}** and all their data?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Confirm Delete", key=f"cdel_{uid}"):
                db.delete_user(user['email'])
                st.session_state[f'confirm_del_{uid}'] = False
                st.success("Deleted!")
                st.rerun()
        with c2:
            if st.button("❌ Cancel", key=f"ccancel_{uid}"):
                st.session_state[f'confirm_del_{uid}'] = False
                st.rerun()

    # Edit form
    if st.session_state.get(f'editing_{uid}'):
        _render_edit_user_form(user, uid)


def _render_edit_user_form(user, uid):
    with st.form(f"edit_form_{uid}"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Name", value=user['name'])
            new_role = st.selectbox("Role", ["counselor", "admin"],
                                    index=0 if user['role'] == 'counselor' else 1)
        with col2:
            depts = db.get_departments()
            dept_codes = ["None"] + [d["code"] for d in depts]
            current_idx = 0
            if user.get('department') in dept_codes:
                current_idx = dept_codes.index(user['department'])
            new_dept = st.selectbox("Department", dept_codes, index=current_idx)
            new_max = st.number_input("Max Students", value=user.get('max_students', 30),
                                      min_value=1, max_value=200)

        submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

    if submitted:
        db.update_user(user['email'],
                       name=new_name,
                       role=new_role,
                       department=new_dept if new_dept != "None" else None,
                       max_students=new_max)
        st.session_state[f'editing_{uid}'] = False
        st.success("Updated!")
        st.rerun()

    if st.button("Cancel", key=f"cancel_edit_{uid}"):
        st.session_state[f'editing_{uid}'] = False
        st.rerun()


# =========================================================================
# DEPARTMENTS TAB
# =========================================================================

def _departments_tab():
    st.subheader("Department Management")

    departments = db.get_departments(active_only=False)

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("➕ Add Department", use_container_width=True):
            st.session_state['admin_action'] = 'create_dept'
    with col2:
        search = st.text_input("🔍 Search departments", key="dept_search")

    if st.session_state.get('admin_action') == 'create_dept':
        with st.form("create_dept_form"):
            code = st.text_input("Department Code (e.g., CSE)")
            name = st.text_input("Full Department Name")
            color = st.color_picker("Color", "#667eea")
            submitted = st.form_submit_button("✅ Create", use_container_width=True)

        if submitted:
            if code and name:
                ok, msg = db.create_department(code.upper(), name, color)
                if ok:
                    st.success("Department created!")
                    st.session_state['admin_action'] = None
                    st.rerun()
                else:
                    st.error(msg)

    # Filter
    if search:
        q = search.lower()
        departments = [d for d in departments if q in d['code'].lower() or q in d['name'].lower()]

    # Grid display
    cols = st.columns(3)
    for i, dept in enumerate(departments):
        with cols[i % 3]:
            active_text = "Active" if dept['is_active'] else "Inactive"
            badge = status_badge(active_text, "active" if dept['is_active'] else "inactive")
            st.markdown(f"""
            <div class="glass-card" style="border-left: 4px solid {dept['color']};">
                <h4 style="margin:0; color:white;">{dept['code']} {badge}</h4>
                <p style="color:#cbd5e1; font-size:0.85rem; margin:0.3rem 0;">{dept['name']}</p>
                <div style="width:30px; height:6px; background:{dept['color']}; border-radius:3px;"></div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if dept['is_active']:
                    if st.button("🔴 Deactivate", key=f"deact_dept_{dept['id']}", use_container_width=True):
                        db.update_department(dept['id'], is_active=0)
                        st.rerun()
                else:
                    if st.button("🟢 Activate", key=f"act_dept_{dept['id']}", use_container_width=True):
                        db.update_department(dept['id'], is_active=1)
                        st.rerun()
            with c2:
                if st.button("🗑️ Delete", key=f"del_dept_{dept['id']}", use_container_width=True):
                    db.delete_department(dept['id'])
                    st.rerun()


# =========================================================================
# OVERVIEW TAB
# =========================================================================

def _overview_tab():
    st.subheader("System Overview")

    users = db.get_all_users()
    departments = db.get_departments()
    sessions = db.get_active_sessions()
    msg_stats = db.get_message_stats()
    try:
        tests = db.get_tests()
    except Exception:
        tests = []

    cols = st.columns(4)
    with cols[0]:
        metric_card("Users", len(users), "👥")
    with cols[1]:
        metric_card("Departments", len(departments), "🏛️")
    with cols[2]:
        metric_card("Active Sessions", len(sessions), "🔌")
    with cols[3]:
        metric_card("Total Messages", msg_stats.get('total', 0), "📨")

    st.markdown("---")

    cols2 = st.columns(3)
    with cols2[0]:
        metric_card("Today's Messages", msg_stats.get('today', 0), "📅")
    with cols2[1]:
        metric_card("Tests Uploaded", len(tests), "📊")
    with cols2[2]:
        metric_card("Active Counselors", msg_stats.get('active_counselors', 0), "👨‍🏫")


# =========================================================================
# SESSIONS TAB
# =========================================================================

def _sessions_tab():
    st.subheader("Active Session Monitoring")

    sessions = db.get_active_sessions()

    cols = st.columns(4)
    with cols[0]:
        metric_card("Active Sessions", len(sessions), "🔌")
    with cols[1]:
        active_count = sum(1 for s in sessions if s.get('status') == 'Active')
        metric_card("Currently Active", active_count, "🟢")
    with cols[2]:
        idle_count = sum(1 for s in sessions if s.get('status') == 'Idle')
        metric_card("Idle", idle_count, "🟡")
    with cols[3]:
        inactive_count = sum(1 for s in sessions if s.get('status') == 'Inactive')
        metric_card("Inactive", inactive_count, "🔴")

    st.markdown("---")

    # Bulk actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧹 Clear Inactive", use_container_width=True):
            db.clear_inactive_sessions()
            st.success("Cleared!")
            st.rerun()
    with col2:
        if st.button("🚪 Logout All", use_container_width=True):
            db.logout_all_users()
            st.warning("All users logged out!")
            st.rerun()
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Session cards
    for session in sessions:
        status = session.get('status', 'Unknown')
        status_color = {"Active": "#25D366", "Idle": "#f39c12", "Inactive": "#e74c3c"}.get(status, "#cbd5e1")
        role_badge = status_badge(session.get('role', 'unknown').title(),
                                  'admin' if session.get('role') == 'admin' else 'counselor')

        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid {status_color};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h4 style="margin:0; color:white;">
                        👤 {session.get('name', 'Unknown')} {role_badge}
                    </h4>
                    <p style="margin:0.2rem 0; color:#cbd5e1; font-size:0.85rem;">
                        📧 {session.get('user_email', '')}
                        {f" &nbsp;|&nbsp; 🏛️ {session.get('department', '')}" if session.get('department') else ""}
                    </p>
                    <p style="margin:0.2rem 0; color:#cbd5e1; font-size:0.8rem;">
                        🕐 Login: {session.get('login_time', 'N/A')}
                        &nbsp;|&nbsp; ⏱️ {session.get('time_ago', 'N/A')}
                    </p>
                </div>
                <div>
                    <span class="badge badge-{'active' if status == 'Active' else 'idle' if status == 'Idle' else 'locked'}">{status}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        sid = session.get('session_id', '')[:8]
        with cols[0]:
            if st.button("🚪 Force Logout", key=f"session_logout_{sid}"):
                db.force_logout_user(session.get('user_email', ''))
                st.rerun()
        with cols[1]:
            if st.button("🔒 Lock Account", key=f"session_lock_{sid}"):
                db.lock_user(session.get('user_email', ''))
                st.success("Account locked!")
                st.rerun()


# =========================================================================
# SETTINGS TAB
# =========================================================================

def _settings_tab():
    st.subheader("Configuration")

    with st.form("config_form"):
        st.markdown("#### General Settings")
        col1, col2 = st.columns(2)
        with col1:
            app_name = st.text_input("Application Name", value="RMKCET Parent Connect")
            session_timeout = st.number_input("Session Timeout (seconds)",
                                              value=SESSION_TIMEOUT, min_value=60, max_value=7200)
        with col2:
            max_students = st.number_input("Default Max Students/Counselor",
                                           value=30, min_value=1, max_value=200)
            country_code = st.text_input("Country Code", value="91")

        st.markdown("#### Email Configuration")
        col3, col4 = st.columns(2)
        with col3:
            smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP Port", value=587)
        with col4:
            smtp_user = st.text_input("SMTP Username", type="default")
            smtp_pass = st.text_input("SMTP Password", type="password")

        st.markdown("#### Email Domains")
        domains_text = st.text_area("Allowed Email Domains (one per line)",
                                    value="\n".join(ALLOWED_EMAIL_DOMAINS))

        submitted = st.form_submit_button("💾 Save Settings", use_container_width=True)

    if submitted:
        db.set_config("APP_NAME", app_name)
        db.set_config("SESSION_TIMEOUT", session_timeout)
        db.set_config("MAX_STUDENTS_PER_COUNSELOR", max_students)
        db.set_config("COUNTRY_CODE", country_code)
        db.set_config("SMTP_SERVER", smtp_server)
        db.set_config("SMTP_PORT", smtp_port)
        if smtp_user:
            db.set_config("SMTP_USERNAME", smtp_user)
        if smtp_pass:
            db.set_config("SMTP_PASSWORD", smtp_pass)
        domains = [d.strip() for d in domains_text.strip().split("\n") if d.strip()]
        db.set_config("ALLOWED_EMAIL_DOMAINS", json.dumps(domains))
        st.success("✅ Settings saved!")


# =========================================================================
# MESSAGE LOGS TAB
# =========================================================================

def _message_logs_tab():
    st.subheader("Message History")

    stats = db.get_message_stats()
    cols = st.columns(3)
    with cols[0]:
        metric_card("Total Messages", stats.get('total', 0), "📨")
    with cols[1]:
        metric_card("Today", stats.get('today', 0), "📅")
    with cols[2]:
        metric_card("Active Counselors", stats.get('active_counselors', 0), "👨‍🏫")

    st.markdown("---")

    messages = db.get_message_history(limit=200)

    if messages:
        df = pd.DataFrame(messages)
        display_cols = ['counselor_email', 'reg_no', 'student_name', 'format', 'sent_at', 'status']
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True, hide_index=True)

        # Export
        csv = df[available_cols].to_csv(index=False)
        st.download_button("📥 Export to CSV", csv,
                          f"message_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                          "text/csv", use_container_width=True)
    else:
        st.info("No messages sent yet.")
