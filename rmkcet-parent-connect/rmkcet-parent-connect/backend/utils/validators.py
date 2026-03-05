# utils/validators.py
"""Input validation utilities."""
import re
from config import ALLOWED_EMAIL_DOMAINS


def validate_email(email: str) -> bool:
    """Validate email format and domain."""
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return False
    domain = email.split('@')[1]
    return domain in ALLOWED_EMAIL_DOMAINS


def validate_phone(phone) -> bool:
    """Validate 10-digit phone number."""
    digits = ''.join(c for c in str(phone) if c.isdigit())
    return len(digits) == 10


def validate_password(password: str):
    """Return (is_valid, message)."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if not any(c.isupper() for c in password):
        return False, "Include at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Include at least one number"
    return True, "Password is valid"
