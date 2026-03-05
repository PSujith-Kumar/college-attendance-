# utils/image_generator.py
"""Generate image report cards for students using Pillow."""
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
import os


# Colors
BG_COLOR = (10, 12, 20)
CARD_BG = (20, 30, 50)
PRIMARY = (102, 126, 234)
SECONDARY = (118, 75, 162)
SUCCESS = (37, 211, 102)
WARNING = (243, 156, 18)
DANGER = (248, 80, 50)
WHITE = (255, 255, 255)
GREY = (203, 213, 225)


def _get_font(size: int, bold: bool = False):
    """Get a font, falling back gracefully."""
    font_names = [
        "arial.ttf", "Arial.ttf", "arialbd.ttf",
        "DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
    ]
    if bold:
        font_names = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] + font_names

    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue

    # Last resort
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def generate_report_image(student_name: str, reg_no: str, department: str,
                          subjects_marks: dict, counselor_name: str,
                          test_name: str = "Unit Test") -> bytes:
    """
    Generate a visually appealing report card image.
    Returns PNG bytes.
    """
    # Calculate dimensions
    num_subjects = len(subjects_marks)
    height = 500 + (num_subjects * 50)
    width = 700

    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(28, bold=True)
    font_subtitle = _get_font(16, bold=True)
    font_body = _get_font(14)
    font_small = _get_font(12)
    font_marks = _get_font(16, bold=True)

    y = 20

    # === Header background ===
    draw.rounded_rectangle([20, y, width - 20, y + 90], radius=15, fill=CARD_BG,
                           outline=PRIMARY, width=2)

    # Title
    draw.text((40, y + 10), "RMKCET", fill=PRIMARY, font=font_title)
    draw.text((40, y + 45), "Academic Progress Report", fill=GREY, font=font_subtitle)
    draw.text((width - 200, y + 15), test_name, fill=WHITE, font=font_subtitle)
    draw.text((width - 200, y + 40), datetime.now().strftime("%d %b %Y"), fill=GREY, font=font_small)

    y += 110

    # === Student info card ===
    draw.rounded_rectangle([20, y, width - 20, y + 100], radius=15, fill=CARD_BG)

    draw.text((40, y + 10), f"Reg No:  {reg_no}", fill=WHITE, font=font_body)
    draw.text((40, y + 35), f"Name:    {student_name}", fill=WHITE, font=font_body)
    draw.text((40, y + 60), f"Dept:    {department}", fill=WHITE, font=font_body)

    y += 120

    # === Marks table header ===
    draw.rounded_rectangle([20, y, width - 20, y + 40], radius=10, fill=PRIMARY)
    draw.text((40, y + 10), "Subject", fill=WHITE, font=font_subtitle)
    draw.text((width - 120, y + 10), "Marks", fill=WHITE, font=font_subtitle)

    y += 50

    # === Marks rows ===
    total = 0
    count = 0
    for subj, marks in subjects_marks.items():
        # Row background
        row_color = (25, 35, 55) if count % 2 == 0 else CARD_BG
        draw.rounded_rectangle([20, y, width - 20, y + 45], radius=8, fill=row_color)

        draw.text((40, y + 12), subj, fill=WHITE, font=font_body)

        # Color-code marks
        mark_str = str(marks)
        try:
            mark_val = float(mark_str)
            if mark_val >= 85:
                mark_color = SUCCESS
            elif mark_val >= 50:
                mark_color = WARNING
            else:
                mark_color = DANGER
            total += mark_val
            count += 1
        except (ValueError, TypeError):
            mark_color = GREY

        draw.text((width - 100, y + 12), mark_str, fill=mark_color, font=font_marks)
        y += 50

    # === Average ===
    y += 10
    if count > 0:
        avg = total / count
        avg_color = SUCCESS if avg >= 50 else DANGER
        draw.rounded_rectangle([20, y, width - 20, y + 45], radius=10, fill=CARD_BG,
                               outline=avg_color, width=2)
        draw.text((40, y + 12), f"Average: {avg:.1f}", fill=avg_color, font=font_subtitle)
        y += 55

    # === Footer ===
    y += 10
    draw.text((40, y), f"Counselor: {counselor_name}", fill=GREY, font=font_small)
    draw.text((40, y + 20), "RMK College of Engineering and Technology", fill=GREY, font=font_small)

    # Export to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()
