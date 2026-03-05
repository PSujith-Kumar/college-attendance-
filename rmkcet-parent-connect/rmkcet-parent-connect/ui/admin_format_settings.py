# ui/admin_format_settings.py
"""Admin format settings management tab."""
import streamlit as st
import database as db
from ui.styles import metric_card


def format_settings_tab():
    """Format settings management for mark report generation."""
    st.subheader("📨 Format Settings")
    st.info("Configure which message formats counselors can use when sending reports to parents.")

    formats = db.get_format_settings_list()

    # Overview metrics
    active_count = sum(1 for f in formats if f.get('is_active'))
    default_fmt = next((f for f in formats if f.get('is_default')), None)

    cols = st.columns(3)
    with cols[0]:
        metric_card("Total Formats", len(formats), "📋")
    with cols[1]:
        metric_card("Active Formats", active_count, "✅")
    with cols[2]:
        metric_card("Default Format", default_fmt['name'] if default_fmt else "None", "⭐")

    st.markdown("---")

    # Format cards
    for fmt in formats:
        _render_format_card(fmt)

    st.markdown("---")

    # Bulk actions
    st.markdown("### Bulk Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Enable All Formats", use_container_width=True):
            for fmt in formats:
                db.update_format_setting(fmt['id'], is_active=1)
            st.success("All formats enabled!")
            st.rerun()
    with col2:
        if st.button("❌ Disable Non-Default", use_container_width=True):
            for fmt in formats:
                if not fmt.get('is_default'):
                    db.update_format_setting(fmt['id'], is_active=0)
            st.success("Non-default formats disabled!")
            st.rerun()


def _render_format_card(fmt):
    """Render a single format setting card."""
    active_color = "#25D366" if fmt.get('is_active') else "#e74c3c"
    default_mark = " ⭐ DEFAULT" if fmt.get('is_default') else ""
    status_text = "Active" if fmt.get('is_active') else "Inactive"

    st.markdown(f"""
    <div class="glass-card" style="border-left: 4px solid {active_color};">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h4 style="margin:0; color:white;">
                    {fmt.get('icon', '📄')} {fmt['name']}{default_mark}
                </h4>
                <p style="color:#cbd5e1; font-size:0.85rem; margin:0.3rem 0;">
                    {fmt.get('description', 'No description')}
                </p>
            </div>
            <span style="color:{active_color}; font-weight:bold;">{status_text}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    fid = fmt['id']
    cols = st.columns(3)
    with cols[0]:
        if fmt.get('is_active'):
            if st.button("🔴 Disable", key=f"disable_fmt_{fid}", use_container_width=True):
                db.update_format_setting(fid, is_active=0)
                st.rerun()
        else:
            if st.button("🟢 Enable", key=f"enable_fmt_{fid}", use_container_width=True):
                db.update_format_setting(fid, is_active=1)
                st.rerun()
    with cols[1]:
        if not fmt.get('is_default'):
            if st.button("⭐ Set Default", key=f"default_fmt_{fid}", use_container_width=True):
                db.set_default_format(fid)
                st.success(f"'{fmt['name']}' set as default!")
                st.rerun()
    with cols[2]:
        # Preview
        if st.button("👁️ Preview", key=f"preview_fmt_{fid}", use_container_width=True):
            st.session_state[f'preview_fmt_{fid}'] = not st.session_state.get(f'preview_fmt_{fid}', False)

    if st.session_state.get(f'preview_fmt_{fid}'):
        st.info(f"**Format:** {fmt['name']}\n\n"
                f"**Type:** {fmt.get('format_type', 'text')}\n\n"
                f"**Description:** {fmt.get('description', 'N/A')}")
