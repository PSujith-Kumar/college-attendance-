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

        if reg_col is None and name_col is None:
            continue

        for idx in range(len(df)):
            try:
                row = df.iloc[idx]
                reg = str(row.iloc[reg_col]).strip() if reg_col is not None else ""
                name = str(row.iloc[name_col]).strip() if name_col is not None else ""
                phone = str(row.iloc[phone_col]).strip() if phone_col is not None else ""
                email = str(row.iloc[email_col]).strip() if email_col is not None else ""

                rec = StudentRecord(reg_no=reg, name=name, phone=phone, email=email)
                if rec.is_valid():
                    all_students.append(rec.to_dict())
            except Exception:
                continue

    return all_students
