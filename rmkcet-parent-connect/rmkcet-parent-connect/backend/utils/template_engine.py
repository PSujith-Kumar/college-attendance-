# utils/template_engine.py
"""Dynamic template engine for message generation."""
from typing import Dict, List
from datetime import datetime


class TemplateEngine:
    """Handles dynamic template filling with subject data."""

    @staticmethod
    def format_subjects_table(subjects: List[Dict], marks: Dict, width: int = 15) -> str:
        """
        Format subjects into a text table.
        subjects: [{'code': 'MA', 'name': 'Maths', 'emoji': '📘'}, ...]
        marks: {'MA': 85, 'Chemistry': 90, ...}
        """
        lines = []
        for subject in subjects:
            code = subject.get('code', '')
            name = subject.get('name', '')
            mark = marks.get(code, marks.get(name, 'N/A'))
            lines.append(f"{name} :\t{mark}")
        return "\n".join(lines)

    @staticmethod
    def format_marks_table_simple(marks: Dict) -> str:
        """Format marks dict as simple text table."""
        lines = []
        for subj, mark in marks.items():
            lines.append(f"{subj} :\t{mark}")
        return "\n".join(lines) if lines else "No marks available"

    @staticmethod
    def fill_template(template: str, **kwargs) -> str:
        """Fill a template string with variables."""
        kwargs.setdefault("date", datetime.now().strftime("%d-%b-%Y"))
        for key, val in kwargs.items():
            template = template.replace(f"{{{key}}}", str(val))
        return template

    @staticmethod
    def get_message_variables() -> Dict[str, str]:
        return {
            '{app_name}': 'Application name',
            '{reg_no}': 'Registration number',
            '{student_name}': 'Student name',
            '{department}': 'Department',
            '{test_name}': 'Test name',
            '{subjects_table}': 'Formatted marks table',
            '{counselor_name}': 'Counselor name',
            '{date}': 'Current date',
        }
