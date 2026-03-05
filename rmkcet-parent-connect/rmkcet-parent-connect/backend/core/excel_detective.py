# core/excel_detective.py
"""
Auto-detect column types in Excel by inspecting cell content.
Works regardless of header names or column positions.
"""
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple


def detect_column_types(df: pd.DataFrame, sample_rows: int = 20) -> Dict[str, int]:
    """
    Scan the first `sample_rows` of data to classify each column.
    Returns mapping: {'reg_no': col_idx, 'name': col_idx, 'phone': col_idx, ...}
    and a list of subject column indices.
    """
    detections = {}
    subject_columns = {}
    sample = df.head(sample_rows)

    for col_idx in range(len(df.columns)):
        col_data = sample.iloc[:, col_idx].dropna().astype(str)
        if col_data.empty:
            continue

        scores = {
            "sno": _score_sno(col_data),
            "reg_no": _score_reg_no(col_data),
            "name": _score_name(col_data),
            "phone": _score_phone(col_data),
            "email": _score_email(col_data),
            "marks": _score_marks(col_data),
        }

        best = max(scores, key=scores.get)
        confidence = scores[best]

        if confidence > 0.4:
            if best == "marks":
                # Try to get subject name from header
                header_val = str(df.columns[col_idx]).strip()
                if header_val and header_val.lower() not in ("unnamed", "nan", ""):
                    subject_columns[col_idx] = header_val
                else:
                    subject_columns[col_idx] = f"Subject_{col_idx}"
            elif best not in detections or confidence > detections[best][1]:
                detections[best] = (col_idx, confidence)

    result = {k: v[0] for k, v in detections.items()}
    result["subjects"] = subject_columns
    return result


def _score_sno(col: pd.Series) -> float:
    """S.No: small sequential integers like 1, 2, 3..."""
    try:
        nums = col.apply(lambda x: float(str(x).replace(".0", "")))
        if nums.max() < 200 and nums.min() >= 0:
            diffs = nums.diff().dropna()
            if len(diffs) > 0 and (diffs == 1).mean() > 0.7:
                return 0.9
        return 0.1
    except Exception:
        return 0.0


def _score_reg_no(col: pd.Series) -> float:
    """Registration numbers: long digits like 111624104001."""
    matches = col.apply(lambda x: bool(re.match(r'^\d{8,15}\.?0?$', str(x).strip())))
    return matches.mean()


def _score_name(col: pd.Series) -> float:
    """Names: alphabetic strings with spaces."""
    matches = col.apply(lambda x: bool(re.match(r'^[A-Za-z][A-Za-z\s\.\-]{2,50}$', str(x).strip())))
    return matches.mean()


def _score_phone(col: pd.Series) -> float:
    """Phone: 10+ digit numbers."""
    def is_phone(x):
        digits = ''.join(c for c in str(x) if c.isdigit())
        return len(digits) >= 10
    return col.apply(is_phone).mean()


def _score_email(col: pd.Series) -> float:
    """Email addresses."""
    matches = col.apply(lambda x: bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', str(x).strip())))
    return matches.mean()


def _score_marks(col: pd.Series) -> float:
    """Marks: numbers 0-100 or 'Absent'/'A'."""
    def is_mark(x):
        s = str(x).strip().upper()
        if s in ("ABSENT", "A", "AB", "-"):
            return True
        try:
            v = float(s)
            return 0 <= v <= 100
        except ValueError:
            return False
    return col.apply(is_mark).mean()


def find_header_row(df_raw: pd.DataFrame, max_rows: int = 15) -> int:
    """
    Find the row that looks like a header (contains keywords like 'Name', 'Reg', 'S.No').
    Returns 0-based row index.
    """
    keywords = ["name", "reg", "s.no", "sno", "sl", "roll", "student"]
    for i in range(min(max_rows, len(df_raw))):
        row_vals = [str(v).strip().lower() for v in df_raw.iloc[i].values if pd.notna(v)]
        matches = sum(1 for kw in keywords if any(kw in val for val in row_vals))
        if matches >= 2:
            return i
    return 0


def find_data_start_row(df_raw: pd.DataFrame, header_row: int) -> int:
    """Find where actual data begins after the header."""
    for i in range(header_row + 1, min(header_row + 10, len(df_raw))):
        row = df_raw.iloc[i]
        non_null = row.dropna()
        if len(non_null) >= 3:
            # Check if any cell looks like a reg_no or number
            for val in non_null:
                s = str(val).strip()
                if re.match(r'^\d{5,}', s):
                    return i
                try:
                    n = float(s)
                    if 0 < n < 200:  # Likely S.No
                        return i
                except ValueError:
                    continue
    return header_row + 1
