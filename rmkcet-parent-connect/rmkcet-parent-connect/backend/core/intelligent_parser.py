# core/intelligent_parser.py
"""
Intelligent Excel parser that auto-detects structure, extracts metadata,
and parses student marks from any Excel format.
"""
import re
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple

from models.data_models import StudentRecord, TestInfo
from models.test_metadata import extract_test_info_from_text
from core.excel_detective import detect_column_types, find_header_row, find_data_start_row


class IntelligentParser:
    """Parse uploaded Excel files intelligently."""

    def __init__(self):
        self.test_info = TestInfo()
        self.students: List[StudentRecord] = []
        self.raw_headers = []
        self.errors = []

    def parse_file(self, file_obj, filename: str = "") -> Tuple[TestInfo, List[StudentRecord]]:
        """
        Main entry: parse an uploaded Excel file.
        Returns (TestInfo, [StudentRecord]).
        """
        self.errors = []
        self.students = []
        self.test_info = TestInfo()

        try:
            xl = pd.ExcelFile(file_obj)
        except Exception as e:
            self.errors.append(f"Cannot read Excel file: {e}")
            return self.test_info, self.students

        # Extract metadata from filename
        if filename:
            meta = extract_test_info_from_text(filename)
            self.test_info.test_name = meta.get("test_name", "")
            self.test_info.semester = meta.get("semester", 0)
            self.test_info.academic_year = meta.get("academic_year", "")
            self.test_info.batch_name = meta.get("batch_name", "")
            self.test_info.department = meta.get("department", "")

        # Process each sheet
        all_students = {}
        for sheet_name in xl.sheet_names:
            try:
                students = self._parse_sheet(xl, sheet_name)
                for s in students:
                    key = s.reg_no
                    if key in all_students:
                        # Merge marks from different sections
                        all_students[key].marks.update(s.marks)
                    else:
                        all_students[key] = s
            except Exception as e:
                self.errors.append(f"Error in sheet '{sheet_name}': {e}")

        self.students = list(all_students.values())

        # Also extract metadata from sheet header rows
        if xl.sheet_names:
            self._extract_header_metadata(xl, xl.sheet_names[0])

        return self.test_info, self.students

    def _parse_sheet(self, xl: pd.ExcelFile, sheet_name: str) -> List[StudentRecord]:
        """Parse a single sheet."""
        # Read raw to find header
        df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        if df_raw.empty:
            return []

        header_row = find_header_row(df_raw)
        data_start = find_data_start_row(df_raw, header_row)

        # Re-read with proper header
        df = pd.read_excel(xl, sheet_name=sheet_name, header=header_row)

        if df.empty:
            return []

        # Detect columns
        detections = detect_column_types(df)
        reg_col = detections.get("reg_no")
        name_col = detections.get("name")
        phone_col = detections.get("phone")
        email_col = detections.get("email")
        subject_cols = detections.get("subjects", {})

        if reg_col is None and name_col is None:
            self.errors.append(f"Sheet '{sheet_name}': Cannot detect reg_no or name columns")
            return []

        # Update test_info subjects
        for col_idx, subj_name in subject_cols.items():
            self.test_info.subject_columns[col_idx] = subj_name
            if subj_name not in [s.get("name") for s in self.test_info.subjects]:
                code = self._generate_subject_code(subj_name)
                self.test_info.subjects.append({"name": subj_name, "code": code})

        # Parse each row
        students = []
        section = sheet_name.strip().upper() if len(sheet_name.strip()) <= 2 else ""

        for idx in range(len(df)):
            try:
                row = df.iloc[idx]

                reg_no = str(row.iloc[reg_col]).strip() if reg_col is not None else ""
                name = str(row.iloc[name_col]).strip() if name_col is not None else ""
                phone = str(row.iloc[phone_col]).strip() if phone_col is not None else ""
                email = str(row.iloc[email_col]).strip() if email_col is not None else ""

                if not reg_no or reg_no.lower() in ("nan", "none", ""):
                    continue

                # Parse marks
                marks = {}
                for col_idx, subj_name in subject_cols.items():
                    mark_val = self._parse_mark(row.iloc[col_idx])
                    marks[subj_name] = mark_val

                student = StudentRecord(
                    reg_no=reg_no, name=name, department=self.test_info.department,
                    phone=phone, email=email, marks=marks, section=section
                )
                if student.is_valid():
                    students.append(student)
            except Exception:
                continue

        return students

    def _extract_header_metadata(self, xl: pd.ExcelFile, sheet_name: str):
        """Extract test info from the first few rows of the sheet."""
        try:
            df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None, nrows=10)
            for i in range(min(5, len(df_raw))):
                for val in df_raw.iloc[i]:
                    if pd.notna(val):
                        text = str(val).strip()
                        if len(text) > 10:
                            meta = extract_test_info_from_text(text)
                            if meta["test_name"] and not self.test_info.test_name:
                                self.test_info.test_name = meta["test_name"]
                            if meta["semester"] and not self.test_info.semester:
                                self.test_info.semester = meta["semester"]
                            if meta["academic_year"] and not self.test_info.academic_year:
                                self.test_info.academic_year = meta["academic_year"]
                                self.test_info.batch_name = meta["academic_year"]
                            if meta["department"] and not self.test_info.department:
                                self.test_info.department = meta["department"]
        except Exception:
            pass

    @staticmethod
    def _parse_mark(val) -> str:
        """Parse a single mark value."""
        if pd.isna(val):
            return "Absent"
        s = str(val).strip().upper()
        if s in ("ABSENT", "A", "AB", "-", ""):
            return "Absent"
        try:
            n = float(s)
            if n == int(n):
                return str(int(n))
            return str(round(n, 1))
        except ValueError:
            return s

    @staticmethod
    def _generate_subject_code(name: str) -> str:
        """Generate a short code from subject name."""
        # Use uppercase initials
        words = re.sub(r'[^A-Za-z\s]', '', name).split()
        if len(words) == 1:
            return words[0][:4].upper()
        return "".join(w[0] for w in words if w).upper()[:5]
