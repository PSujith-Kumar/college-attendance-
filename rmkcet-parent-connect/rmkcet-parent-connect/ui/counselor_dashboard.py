# ui/counselor_dashboard.py
"""Counselor dashboard for student management, marks upload & messaging."""
import streamlit as st
import pandas as pd
from datetime import datetime

import database as db
from config import COUNTRY_CODE
from core.intelligent_parser import IntelligentParser
from core.dynamic_parser import parse_student_excel as parse_student_list
from core.student_matcher import match_students
from ui.styles import metric_card, status_badge
from utils.whatsapp_helper import get_whatsapp_link as generate_whatsapp_link
from utils.pdf_generator import generate_student_pdf
from utils.image_generator import generate_report_image
from utils.template_engine import TemplateEngine


def counselor_dashboard():
    """Main counselor dashboard."""
    user_email = st.session_state.get('user_email', '')
    user_name = st.session_state.get('user_name', '')
    department = st.session_state.get('department', '')

    st.markdown(f'<h2 style="color:#667eea;">👨‍🏫 Counselor Dashboard</h2>', unsafe_allow_html=True)
    st.markdown(f"Welcome, **{user_name}** | Department: **{department or 'Not assigned'}**")

    tabs = st.tabs(["📋 My Students", "📤 Upload Student List",
                     "📊 Upload Marks", "📨 Send Reports"])

    with tabs[0]:
        _my_students_tab(user_email)
    with tabs[1]:
        _upload_students_tab(user_email)
    with tabs[2]:
        _upload_marks_tab(user_email)
    with tabs[3]:
        _send_reports_tab(user_email)


# =========================================================================
# MY STUDENTS
# =========================================================================

def _my_students_tab(counselor_email):
    students = db.get_students_by_counselor(counselor_email)

    cols = st.columns(3)
    with cols[0]:
        metric_card("Total Students", len(students), "📋")
    with cols[1]:
        with_phone = sum(1 for s in students if s.get('phone'))
        metric_card("With Phone", with_phone, "📱")
    with cols[2]:
        metric_card("Without Phone", len(students) - with_phone, "❌")

    st.markdown("---")

    search = st.text_input("🔍 Search students", key="student_search",
                           placeholder="Name, register number...")

    filtered = students
    if search:
        q = search.lower()
        filtered = [s for s in students if q in s.get('name', '').lower()
                    or q in s.get('reg_no', '').lower()]

    if not filtered:
        st.info("No students found." if search else
                "No students assigned. Upload a student list to get started.")
        return

    # Student cards
    for student in filtered:
        phone_badge = status_badge("📱", "active") if student.get('phone') else status_badge("No Phone", "locked")
        st.markdown(f"""
        <div class="glass-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h4 style="margin:0; color:white;">
                        👨‍🎓 {student['name']} {phone_badge}
                    </h4>
                    <p style="color:#cbd5e1; font-size:0.85rem; margin:0.2rem 0;">
                        🔢 {student['reg_no']}
                        {f" &nbsp;|&nbsp; 📱 {student.get('phone', '')}" if student.get('phone') else ""}
                        {f" &nbsp;|&nbsp; 📧 {student.get('email', '')}" if student.get('email') else ""}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Export
    if students:
        df = pd.DataFrame(students)
        csv = df.to_csv(index=False)
        st.download_button("📥 Export Student List (CSV)", csv,
                          f"students_{datetime.now().strftime('%Y%m%d')}.csv",
                          "text/csv", use_container_width=True)


# =========================================================================
# UPLOAD STUDENT LIST
# =========================================================================

def _upload_students_tab(counselor_email):
    st.subheader("Upload Student List")
    st.info("📤 Upload an Excel file with student details (Name, Register No, Phone, Email).")

    uploaded = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'],
                                key="student_upload")

    if uploaded:
        try:
            students = parse_student_list(uploaded)
            if students:
                st.success(f"✅ Found {len(students)} students")

                df = pd.DataFrame(students)
                st.dataframe(df, use_container_width=True, hide_index=True)

                if st.button("💾 Import Students", use_container_width=True):
                    imported = 0
                    for s in students:
                        ok = db.add_student(
                            counselor_email=counselor_email,
                            reg_no=s.get('reg_no', ''),
                            name=s.get('name', ''),
                            department=st.session_state.get('department', ''),
                            phone=s.get('phone', ''),
                            email=s.get('email', '')
                        )
                        if ok:
                            imported += 1
                    st.success(f"✅ Imported {imported}/{len(students)} students!")
                    st.rerun()
            else:
                st.warning("No valid student data found in the file.")
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")


# =========================================================================
# UPLOAD MARKS
# =========================================================================

def _upload_marks_tab(counselor_email):
    st.subheader("Upload Student Marks")
    st.info("📊 Upload an Excel file with test marks. The system will auto-detect columns.")

    col1, col2 = st.columns(2)
    with col1:
        test_name = st.text_input("Test Name (e.g., CAT-1, Internal-2)")
    with col2:
        semester = st.text_input("Semester (e.g., Sem 3)")

    uploaded = st.file_uploader("Choose Marks Excel", type=['xlsx', 'xls'],
                                key="marks_upload")

    if uploaded and test_name:
        try:
            parser = IntelligentParser()
            results = parser.parse(uploaded)

            if results and results.get('students'):
                students_data = results['students']
                subjects = results.get('subjects', [])

                st.success(f"✅ Parsed {len(students_data)} students, {len(subjects)} subjects")
                st.write("**Detected Subjects:**", ", ".join(subjects) if subjects else "N/A")

                # Preview
                preview_data = []
                for s in students_data[:10]:
                    row = {
                        'Reg No': s.get('reg_no', ''),
                        'Name': s.get('name', ''),
                    }
                    for subj in subjects:
                        row[subj] = s.get('marks', {}).get(subj, '-')
                    if 'total' in s:
                        row['Total'] = s['total']
                    preview_data.append(row)

                st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)

                if len(students_data) > 10:
                    st.caption(f"Showing 10 of {len(students_data)} rows")

                # Match with DB students
                my_students = db.get_students_by_counselor(counselor_email)
                matched, unmatched = match_students(students_data, my_students)

                mc1, mc2 = st.columns(2)
                with mc1:
                    metric_card("Matched", len(matched), "✅")
                with mc2:
                    metric_card("Unmatched", len(unmatched), "⚠️")

                if unmatched:
                    with st.expander(f"⚠️ {len(unmatched)} Unmatched Students"):
                        for s in unmatched:
                            st.write(f"- {s.get('reg_no', '?')} — {s.get('name', '?')}")

                if st.button("💾 Save Marks", use_container_width=True):
                    ok, msg = db.save_test_marks(
                        test_name=test_name,
                        semester=semester or "",
                        counselor_email=counselor_email,
                        students=matched,
                        subjects=subjects
                    )
                    if ok:
                        st.success(f"✅ Marks saved for {len(matched)} students!")
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
            else:
                st.warning("Could not parse marks from the file. Check the format.")
        except Exception as e:
            st.error(f"Parse error: {str(e)}")
    elif uploaded and not test_name:
        st.warning("Please enter a test name before uploading.")


# =========================================================================
# SEND REPORTS
# =========================================================================

def _send_reports_tab(counselor_email):
    st.subheader("Send Reports to Parents")

    tests = db.get_tests_by_counselor(counselor_email)
    if not tests:
        st.info("No test data found. Upload marks first.")
        return

    test_options = {f"{t['test_name']} ({t.get('semester', '')})": t['id'] for t in tests}
    selected_test = st.selectbox("Select Test", list(test_options.keys()))
    test_id = test_options[selected_test]

    # Format selection
    formats = db.get_format_settings_list(active_only=True)
    if not formats:
        st.warning("No active formats. Ask admin to enable formats.")
        return

    format_options = {f"{f.get('icon', '📄')} {f['name']}": f for f in formats}
    selected_format = st.selectbox("Report Format", list(format_options.keys()))
    chosen_format = format_options[selected_format]

    st.markdown("---")

    # Get marks for this test
    marks = db.get_marks_by_test(test_id)
    students = db.get_students_by_counselor(counselor_email)

    if not marks:
        st.warning("No marks data for this test.")
        return

    # Build student marks lookup
    student_map = {s['reg_no']: s for s in students}
    sendable = []
    for m in marks:
        reg = m.get('reg_no', '')
        if reg in student_map and student_map[reg].get('phone'):
            sendable.append({**m, **student_map[reg]})

    cols = st.columns(3)
    with cols[0]:
        metric_card("Total Marks", len(marks), "📊")
    with cols[1]:
        metric_card("Sendable", len(sendable), "📨")
    with cols[2]:
        metric_card("Missing Phone", len(marks) - len(sendable), "❌")

    if not sendable:
        st.warning("No students with phone numbers to send reports to.")
        return

    # Preview & Send
    with st.expander("👁️ Preview Recipients"):
        for s in sendable[:20]:
            st.write(f"- {s.get('name', '?')} ({s.get('reg_no', '?')}) → 📱 {s.get('phone', '?')}")
        if len(sendable) > 20:
            st.caption(f"... and {len(sendable) - 20} more")

    if st.button("📨 Send All Reports", use_container_width=True, type="primary"):
        progress = st.progress(0)
        status_text = st.empty()
        sent = 0
        failed = 0

        for i, student in enumerate(sendable):
            try:
                status_text.text(f"Sending to {student.get('name', '')}... ({i+1}/{len(sendable)})")

                phone = student.get('phone', '')
                if not phone.startswith('+'):
                    phone = f"+{COUNTRY_CODE}{phone.lstrip('0')}"

                fmt_type = chosen_format.get('format_type', 'text')

                if fmt_type == 'whatsapp':
                    marks_table = TemplateEngine.format_marks_table_simple(student.get('marks', {}))
                    message = f"📊 {selected_test}\n👨‍🎓 {student.get('name','')}\n🔢 {student.get('reg_no','')}\n\n{marks_table}"
                    link = generate_whatsapp_link(phone, message)
                    sent += 1
                elif fmt_type == 'pdf':
                    marks_dict = student.get('marks', {})
                    generate_student_pdf(student.get('name',''), student.get('reg_no',''), '', marks_dict, selected_test)
                    sent += 1
                elif fmt_type == 'image':
                    marks_dict = student.get('marks', {})
                    generate_report_image(student.get('name',''), student.get('reg_no',''), '', marks_dict, selected_test)
                    sent += 1
                else:
                    marks_table = TemplateEngine.format_marks_table_simple(student.get('marks', {}))
                    message = f"📊 {selected_test}\n👨‍🎓 {student.get('name','')}\n{marks_table}"
                    sent += 1

                # Log message
                db.log_message(
                    counselor_email=counselor_email,
                    reg_no=student.get('reg_no', ''),
                    student_name=student.get('name', ''),
                    message=f"Report sent via {chosen_format['name']}",
                    fmt=chosen_format.get('format_type', 'message')
                )

            except Exception as e:
                failed += 1
                db.log_message(
                    counselor_email=counselor_email,
                    reg_no=student.get('reg_no', ''),
                    student_name=student.get('name', ''),
                    message=f"Failed: {str(e)}",
                    fmt=chosen_format.get('format_type', 'message')
                )

            progress.progress((i + 1) / len(sendable))

        status_text.empty()
        if sent:
            st.success(f"✅ Sent {sent} reports!")
        if failed:
            st.error(f"❌ {failed} failed")

    # WhatsApp link mode
    if chosen_format.get('format_type') == 'whatsapp':
        st.markdown("---")
        st.info("💡 **Alternative:** Generate individual WhatsApp links below")
        for s in sendable[:10]:
            phone = s.get('phone', '')
            if not phone.startswith('+'):
                phone = f"+{COUNTRY_CODE}{phone.lstrip('0')}"
            message = TemplateEngine.format_marks_table_simple(s.get('marks', {}))
            link = generate_whatsapp_link(phone, f"📊 {selected_test}\n👨‍🎓 {s.get('name','')}\n\n{message}")
            st.markdown(f"[📱 Send to {s.get('name', '?')}]({link})")
