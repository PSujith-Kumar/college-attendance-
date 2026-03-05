# ui/components.py
"""Reusable UI components."""
import streamlit as st
from ui.styles import status_badge


def student_card(student: dict, show_marks: bool = False):
    """Render a student info card."""
    name = student.get("student_name") or student.get("name", "")
    reg = student.get("reg_no", "")
    phone = student.get("parent_phone") or student.get("phone", "")
    email = student.get("parent_email") or student.get("email", "")
    dept = student.get("department", "")

    badge_html = status_badge("Active", "active")

    html = f"""
    <div class="glass-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h4 style="margin:0; color:white;">👤 {name}</h4>
                <p style="margin:0.2rem 0; color:#cbd5e1; font-size:0.85rem;">
                    📋 {reg} &nbsp;|&nbsp; 🏛️ {dept}
                </p>
            </div>
            <div>{badge_html}</div>
        </div>
    """

    if phone or email:
        html += '<div style="margin-top:0.5rem; color:#cbd5e1; font-size:0.85rem;">'
        if phone:
            html += f'📱 {phone} &nbsp;'
        if email:
            html += f'📧 {email}'
        html += '</div>'

    if show_marks and student.get("marks"):
        html += '<div style="margin-top:0.8rem; border-top:1px solid rgba(102,126,234,0.2); padding-top:0.5rem;">'
        for subj, mark in student["marks"].items():
            try:
                v = float(mark)
                color = "#25D366" if v >= 50 else "#f85032"
            except (ValueError, TypeError):
                color = "#cbd5e1"
            html += f'<span style="margin-right:1rem;">📘 {subj}: <strong style="color:{color}">{mark}</strong></span>'
        html += '</div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def confirm_dialog(key: str, message: str = "Are you sure?"):
    """Simple confirmation pattern using session state."""
    confirm_key = f"confirm_{key}"
    if st.session_state.get(confirm_key):
        st.warning(message)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes", key=f"yes_{key}"):
                st.session_state[confirm_key] = False
                return True
        with col2:
            if st.button("❌ No", key=f"no_{key}"):
                st.session_state[confirm_key] = False
                return False
    return None
