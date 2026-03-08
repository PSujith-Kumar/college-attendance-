# core/dynamic_parser.py
"""
Dynamic parser for student Excel uploads (student lists with contact info).
Detects columns by content, not position.
"""
import re
import pandas as pd
from typing import List, Dict
from models.data_models import StudentRecord
from core.excel_detective import detect_column_types, find_header_row


def _excel_cell_to_text(value) -> str:
    """Convert Excel cell values to stable text without scientific notation."""
    if value is None or pd.isna(value):
        return ""

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")

    return str(value).strip()


def _find_column_by_header(df: pd.DataFrame, keywords: List[str]):
    """Fallback header keyword matcher when content-based detection misses a column."""
    for idx, col in enumerate(df.columns):
        name = str(col).strip().lower()
        if any(k in name for k in keywords):
            return idx
    return None


def parse_student_excel(file_obj) -> List[Dict]:
    """
    Parse an Excel file containing student list with contact info.
    Returns list of dicts: [{reg_no, name, department, phone, email}].
    """
    try:
        xl = pd.ExcelFile(file_obj)
    except Exception as e:
        raise ValueError(f"Cannot read Excel file: {e}")

    all_students = []

    for sheet_name in xl.sheet_names:
        df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        if df_raw.empty:
            continue

        header_row = find_header_row(df_raw)
        df = pd.read_excel(xl, sheet_name=sheet_name, header=header_row)
        if df.empty:
            continue

        detections = detect_column_types(df)
        reg_col = detections.get("reg_no")
        name_col = detections.get("name")
        phone_col = detections.get("phone")
        email_col = detections.get("email")

        # Header-based fallbacks for sparse or mixed-format contact columns.
        if reg_col is None:
            reg_col = _find_column_by_header(df, ["reg", "register", "roll"])
        if name_col is None:
            name_col = _find_column_by_header(df, ["name", "student"])
        if phone_col is None:
            phone_col = _find_column_by_header(df, ["phone", "mobile", "contact", "whatsapp", "parent"])
        if email_col is None:
            email_col = _find_column_by_header(df, ["email", "mail"])

        if reg_col is None and name_col is None:
            continue

        for idx in range(len(df)):
            try:
                row = df.iloc[idx]
                reg = _excel_cell_to_text(row.iloc[reg_col]) if reg_col is not None else ""
                name = _excel_cell_to_text(row.iloc[name_col]) if name_col is not None else ""
                phone = _excel_cell_to_text(row.iloc[phone_col]) if phone_col is not None else ""
                email = _excel_cell_to_text(row.iloc[email_col]) if email_col is not None else ""

                rec = StudentRecord(reg_no=reg, name=name, phone=phone, email=email)
                if rec.is_valid():
                    all_students.append(rec.to_dict())
            except Exception:
                continue

    return all_students
