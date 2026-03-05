# core/student_matcher.py
"""
Match students between counselor lists and marks sheets.
Uses fuzzy reg_no matching with cleaning.
"""
import re
from typing import List, Dict, Optional


def clean_reg_no(val) -> str:
    """Normalize registration number."""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return re.sub(r'\s+', '', s)


def match_students_to_marks(students: List[Dict], marks_by_reg: Dict) -> List[Dict]:
    """
    Match counselor students to their marks.
    students: [{reg_no, name, phone, email, ...}]
    marks_by_reg: {reg_no: {subject: mark, ...}}
    Returns list of matched dicts with marks merged in.
    """
    results = []

    # Build lookup with cleaned keys
    marks_lookup = {clean_reg_no(k): v for k, v in marks_by_reg.items()}

    for student in students:
        clean = clean_reg_no(student.get("reg_no", ""))
        entry = dict(student)
        entry["marks"] = marks_lookup.get(clean, {})
        entry["matched"] = clean in marks_lookup
        results.append(entry)

    return results


def get_unmatched_marks(students: List[Dict], marks_by_reg: Dict) -> Dict:
    """Return marks entries that didn't match any student."""
    student_regs = {clean_reg_no(s["reg_no"]) for s in students}
    return {k: v for k, v in marks_by_reg.items()
            if clean_reg_no(k) not in student_regs}


def match_students(parsed_marks: List[Dict], db_students: List[Dict]):
    """
    Match parsed marks data against DB students.
    Returns (matched, unmatched) lists.
    """
    db_lookup = {clean_reg_no(s.get("reg_no", "")): s for s in db_students}
    matched = []
    unmatched = []
    for m in parsed_marks:
        clean = clean_reg_no(m.get("reg_no", ""))
        if clean in db_lookup:
            entry = {**db_lookup[clean], **m}
            matched.append(entry)
        else:
            unmatched.append(m)
    return matched, unmatched
