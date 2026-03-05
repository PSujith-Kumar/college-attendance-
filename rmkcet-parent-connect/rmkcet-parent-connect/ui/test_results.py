# ui/test_results.py
"""Test results analytics dashboard."""
import streamlit as st
import pandas as pd
from datetime import datetime

import database as db
from ui.styles import metric_card


def test_results_page():
    """Test results analytics page for counselors."""
    user_email = st.session_state.get('user_email', '')
    st.markdown('<h2 style="color:#667eea;">📊 Test Results Analytics</h2>', unsafe_allow_html=True)

    tests = db.get_tests_by_counselor(user_email)

    if not tests:
        st.info("No test data available. Upload marks from the Counselor Dashboard first.")
        return

    # Test selector
    test_options = {f"{t['test_name']} ({t.get('semester', '')})": t['id'] for t in tests}
    selected = st.selectbox("Select Test", list(test_options.keys()))
    test_id = test_options[selected]

    marks = db.get_marks_by_test(test_id)
    if not marks:
        st.warning("No marks data for this test.")
        return

    # Build dataframe from marks
    df = pd.DataFrame(marks)

    # Overall stats
    st.markdown("### 📈 Overall Statistics")
    _overall_stats(df)

    st.markdown("---")

    # Subject-wise analysis
    st.markdown("### 📚 Subject-wise Analysis")
    _subject_analysis(df)

    st.markdown("---")

    # Performance distribution
    st.markdown("### 📊 Performance Distribution")
    _performance_distribution(df)

    st.markdown("---")

    # Student-wise breakdown
    st.markdown("### 👨‍🎓 Student-wise Breakdown")
    _student_breakdown(df)


def _overall_stats(df):
    """Display overall test statistics."""
    # Try to compute totals
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    # Remove non-mark columns
    exclude = ['id', 'test_id', 'student_id']
    mark_cols = [c for c in numeric_cols if c not in exclude]

    if 'total' in df.columns:
        totals = pd.to_numeric(df['total'], errors='coerce')
    elif mark_cols:
        totals = df[mark_cols].sum(axis=1)
    else:
        st.info("No numeric marks data found.")
        return

    cols = st.columns(4)
    with cols[0]:
        metric_card("Students", len(df), "👥")
    with cols[1]:
        metric_card("Average", f"{totals.mean():.1f}", "📊")
    with cols[2]:
        metric_card("Highest", f"{totals.max():.1f}", "🏆")
    with cols[3]:
        metric_card("Lowest", f"{totals.min():.1f}", "📉")

    pass_count = (totals >= totals.max() * 0.4).sum()
    fail_count = len(totals) - pass_count

    cols2 = st.columns(3)
    with cols2[0]:
        metric_card("Pass (≥40%)", int(pass_count), "✅")
    with cols2[1]:
        metric_card("Fail (<40%)", int(fail_count), "❌")
    with cols2[2]:
        pct = (pass_count / len(totals) * 100) if len(totals) > 0 else 0
        metric_card("Pass %", f"{pct:.1f}%", "📈")


def _subject_analysis(df):
    """Subject-wise bar chart analysis."""
    # Try to get subject columns from marks_json
    if 'marks_json' in df.columns:
        import json
        subject_data = {}
        for _, row in df.iterrows():
            try:
                marks_dict = json.loads(row['marks_json']) if isinstance(row['marks_json'], str) else {}
                for subj, mark in marks_dict.items():
                    if subj not in subject_data:
                        subject_data[subj] = []
                    try:
                        subject_data[subj].append(float(mark))
                    except (ValueError, TypeError):
                        pass
            except:
                pass

        if subject_data:
            stats = []
            for subj, marks_list in subject_data.items():
                if marks_list:
                    s = pd.Series(marks_list)
                    stats.append({
                        'Subject': subj,
                        'Average': round(s.mean(), 2),
                        'Highest': round(s.max(), 2),
                        'Lowest': round(s.min(), 2),
                        'Pass %': round((s >= s.max() * 0.4).sum() / len(s) * 100, 1)
                    })

            if stats:
                stats_df = pd.DataFrame(stats)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)

                # Bar chart
                chart_df = stats_df.set_index('Subject')[['Average', 'Highest', 'Lowest']]
                st.bar_chart(chart_df)
                return

    st.info("Subject-wise data not available for detailed analysis.")


def _performance_distribution(df):
    """Grade distribution chart."""
    if 'total' in df.columns:
        totals = pd.to_numeric(df['total'], errors='coerce').dropna()
    else:
        numeric_cols = [c for c in df.select_dtypes(include='number').columns
                        if c not in ['id', 'test_id', 'student_id']]
        if numeric_cols:
            totals = df[numeric_cols].sum(axis=1)
        else:
            st.info("No numeric data for distribution.")
            return

    if totals.empty:
        return

    max_mark = totals.max()
    if max_mark == 0:
        return

    # Grade bins (relative to max)
    grades = {
        'A+ (≥90%)': (totals >= max_mark * 0.9).sum(),
        'A (80-89%)': ((totals >= max_mark * 0.8) & (totals < max_mark * 0.9)).sum(),
        'B+ (70-79%)': ((totals >= max_mark * 0.7) & (totals < max_mark * 0.8)).sum(),
        'B (60-69%)': ((totals >= max_mark * 0.6) & (totals < max_mark * 0.7)).sum(),
        'C (50-59%)': ((totals >= max_mark * 0.5) & (totals < max_mark * 0.6)).sum(),
        'D (40-49%)': ((totals >= max_mark * 0.4) & (totals < max_mark * 0.5)).sum(),
        'F (<40%)': (totals < max_mark * 0.4).sum()
    }

    grade_df = pd.DataFrame([
        {'Grade': k, 'Count': int(v)} for k, v in grades.items()
    ])
    st.dataframe(grade_df, use_container_width=True, hide_index=True)
    st.bar_chart(grade_df.set_index('Grade'))


def _student_breakdown(df):
    """Student-wise performance table."""
    display_cols = ['reg_no', 'name']
    available = [c for c in display_cols if c in df.columns]

    if 'total' in df.columns:
        available.append('total')

    if 'marks_json' in df.columns:
        import json
        expanded_rows = []
        for _, row in df.iterrows():
            new_row = {c: row[c] for c in available if c in row.index}
            try:
                marks_dict = json.loads(row['marks_json']) if isinstance(row['marks_json'], str) else {}
                new_row.update(marks_dict)
            except:
                pass
            expanded_rows.append(new_row)
        display_df = pd.DataFrame(expanded_rows)
    else:
        display_df = df[available] if available else df

    # Search
    search = st.text_input("🔍 Search student", key="results_search",
                           placeholder="Name or register number...")
    if search:
        q = search.lower()
        mask = display_df.apply(lambda r: q in str(r).lower(), axis=1)
        display_df = display_df[mask]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Export
    csv = display_df.to_csv(index=False)
    st.download_button("📥 Export Results (CSV)", csv,
                      f"test_results_{datetime.now().strftime('%Y%m%d')}.csv",
                      "text/csv", use_container_width=True)
