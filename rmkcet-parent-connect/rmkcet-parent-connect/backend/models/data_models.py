# models/data_models.py
"""Pydantic models for data validation."""
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict
from datetime import datetime


class StudentRecord:
    """Represents a student record parsed from Excel."""
    def __init__(self, reg_no="", name="", department="", phone="", email="",
                 marks=None, section=""):
        self.reg_no = self._clean_reg_no(reg_no)
        self.name = str(name).strip() if name else ""
        self.department = str(department).strip() if department else ""
        self.phone = self._clean_phone(phone)
        self.email = str(email).strip() if email else ""
        self.marks = marks or {}
        self.section = section

    @staticmethod
    def _clean_reg_no(val):
        """Clean registration number: remove .0, strip whitespace."""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s.replace(" ", "")

    @staticmethod
    def _clean_phone(val):
        """Extract 10-digit phone number."""
        if val is None:
            return ""

        raw = val
        if isinstance(val, float):
            if val.is_integer():
                raw = str(int(val))
            else:
                raw = format(val, "f")
        else:
            s = str(val).strip()
            # Convert scientific notation safely when present.
            if "e" in s.lower():
                try:
                    raw = format(Decimal(s), "f")
                except (InvalidOperation, ValueError):
                    raw = s
            else:
                raw = s

        digits = "".join(c for c in str(raw) if c.isdigit())
        # Take last 10 digits
        return digits[-10:] if len(digits) >= 10 else digits

    def is_valid(self):
        return bool(self.reg_no and self.name)

    def to_dict(self):
        return {
            "reg_no": self.reg_no,
            "name": self.name,
            "department": self.department,
            "phone": self.phone,
            "email": self.email,
            "marks": self.marks,
            "section": self.section,
        }


class TestInfo:
    """Represents test metadata extracted from Excel headers."""
    def __init__(self):
        self.test_name = ""
        self.semester = 0
        self.academic_year = ""
        self.batch_name = ""
        self.department = ""
        self.section = ""
        self.subjects = []          # [{name, code}]
        self.subject_columns = {}   # {col_index: subject_name}
        self.header_row = 0
        self.data_start_row = 7
        self.max_marks = 100

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "batch_name": self.batch_name,
            "department": self.department,
            "section": self.section,
            "subjects": self.subjects,
            "subject_columns": self.subject_columns,
            "header_row": self.header_row,
            "data_start_row": self.data_start_row,
            "max_marks": self.max_marks,
        }
