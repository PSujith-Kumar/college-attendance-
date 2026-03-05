# utils/pdf_generator.py
"""Generate PDF reports for students."""
from fpdf import FPDF
from datetime import datetime


def generate_student_pdf(student_name, reg_no, department, subjects_marks,
                         counselor_name, test_name="Unit Test") -> bytes:
    """
    Generate a PDF report as bytes.
    subjects_marks: dict {subject_name: marks}
    """
    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "RMKCET", 0, 1, "C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Academic Progress Report", 0, 1, "C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 6, f"Test: {test_name}", 0, 1, "C")
    pdf.ln(8)

    # Student details
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Registration No : {reg_no}", 0, 1)
    pdf.cell(0, 8, f"Student Name    : {student_name}", 0, 1)
    pdf.cell(0, 8, f"Department      : {department}", 0, 1)
    pdf.cell(0, 8, f"Date            : {datetime.now().strftime('%d-%b-%Y')}", 0, 1)
    pdf.ln(8)

    # Marks table
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(102, 126, 234)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(110, 10, "Subject", 1, 0, "C", True)
    pdf.cell(40, 10, "Marks", 1, 1, "C", True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=11)
    total = 0
    count = 0
    for subj, marks in subjects_marks.items():
        pdf.cell(110, 9, f"  {subj}", 1)
        pdf.cell(40, 9, str(marks), 1, 1, "C")
        if str(marks).replace('.', '').isdigit():
            total += float(marks)
            count += 1

    if count > 0:
        pdf.ln(4)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"Average: {total/count:.1f}", 0, 1)

    # Footer
    pdf.ln(12)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, f"Counselor: {counselor_name}", 0, 1, "R")
    pdf.cell(0, 6, "RMK College of Engineering and Technology", 0, 1, "R")

    return pdf.output(dest='S')
