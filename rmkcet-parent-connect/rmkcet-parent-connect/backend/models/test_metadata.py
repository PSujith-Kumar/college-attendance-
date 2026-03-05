# models/test_metadata.py
"""Test metadata extraction from Excel header rows."""
import re
from typing import Dict, Optional


# Roman numeral mapping
ROMAN_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

# Known test-type keywords
TEST_KEYWORDS = [
    "unit test", "iat", "internal assessment", "model exam",
    "semester exam", "mid term", "midterm", "cat", "cycle test",
]


def extract_test_info_from_text(text: str) -> Dict:
    """
    Parse a header string like:
      'ECE - Unit Test I - Result Analysis (2024-25) II Sem'
    Returns dict with test_name, semester, academic_year, department, batch_name.
    """
    info = {
        "test_name": "",
        "semester": 0,
        "academic_year": "",
        "department": "",
        "batch_name": "",
    }
    if not text:
        return info

    text = str(text).strip()

    # Academic year pattern: (2024-25) or 2024-2025
    year_match = re.search(r'\(?(\d{4})\s*[-/]\s*(\d{2,4})\)?', text)
    if year_match:
        y1 = year_match.group(1)
        y2 = year_match.group(2)
        if len(y2) == 2:
            y2 = y1[:2] + y2
        info["academic_year"] = f"{y1}-{y2[-2:]}"
        info["batch_name"] = info["academic_year"]

    # Semester: "II Sem" or "Sem 2" or "Semester II"
    sem_match = re.search(r'(?:semester|sem)\s*[-:]?\s*([IVX]+|\d+)', text, re.IGNORECASE)
    if not sem_match:
        sem_match = re.search(r'([IVX]+)\s*(?:sem|semester)', text, re.IGNORECASE)
    if sem_match:
        val = sem_match.group(1).upper()
        info["semester"] = ROMAN_MAP.get(val, int(val) if val.isdigit() else 0)

    # Test name: look for known keywords plus Roman/Arabic numeral
    for kw in TEST_KEYWORDS:
        pattern = re.compile(rf'({kw})\s*[-:]?\s*([IVX]+|\d+)?', re.IGNORECASE)
        m = pattern.search(text)
        if m:
            name = m.group(1).strip().title()
            num = m.group(2)
            if num:
                info["test_name"] = f"{name} {num.upper()}"
            else:
                info["test_name"] = name
            break

    if not info["test_name"]:
        info["test_name"] = "Unit Test"

    # Department: known codes before " - "
    dept_match = re.search(
        r'\b(ECE|CSE|EEE|MECH|CIVIL|AIDS|IT|BME|EE\s*\(?\s*VLSI\s*\)?|CSE\s*\(?\s*CS\s*\)?)\b',
        text, re.IGNORECASE
    )
    if dept_match:
        info["department"] = dept_match.group(1).upper().replace(" ", "")

    return info


def parse_semester_roman(val: str) -> int:
    """Convert Roman numeral or digit string to int."""
    val = str(val).strip().upper()
    return ROMAN_MAP.get(val, int(val) if val.isdigit() else 0)
