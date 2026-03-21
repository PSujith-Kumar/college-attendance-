# utils/whatsapp_helper.py
"""WhatsApp link generation."""
import urllib.parse
from config import COUNTRY_CODE


def get_whatsapp_link(phone_number, message: str) -> str:
    """Generate a direct WhatsApp app deep link with pre-filled message."""
    phone = ''.join(c for c in str(phone_number) if c.isdigit())[-10:]
    cc = ''.join(c for c in str(COUNTRY_CODE) if c.isdigit()) or "91"
    full_phone = f"{cc}{phone}"
    encoded = urllib.parse.quote(message)
    return f"whatsapp://send?phone={full_phone}&text={encoded}"


def format_phone_display(phone_number) -> str:
    """Format phone for display: +91 XXXXX XXXXX."""
    phone = ''.join(c for c in str(phone_number) if c.isdigit())
    if len(phone) == 10:
        return f"+{COUNTRY_CODE} {phone[:5]} {phone[5:]}"
    return phone
