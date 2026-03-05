# utils/whatsapp_helper.py
"""WhatsApp link generation."""
import urllib.parse
from config import COUNTRY_CODE, WHATSAPP_BASE_URL


def get_whatsapp_link(phone_number, message: str) -> str:
    """Generate WhatsApp link with pre-filled message."""
    phone = ''.join(c for c in str(phone_number) if c.isdigit())[-10:]
    full_phone = f"{COUNTRY_CODE}{phone}"
    encoded = urllib.parse.quote(message)
    return f"{WHATSAPP_BASE_URL}{full_phone}?text={encoded}"


def format_phone_display(phone_number) -> str:
    """Format phone for display: +91 XXXXX XXXXX."""
    phone = ''.join(c for c in str(phone_number) if c.isdigit())
    if len(phone) == 10:
        return f"+{COUNTRY_CODE} {phone[:5]} {phone[5:]}"
    return phone
