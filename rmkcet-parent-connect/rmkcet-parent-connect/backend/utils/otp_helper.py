# utils/otp_helper.py
"""OTP and token generation."""
import random
import string


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


def generate_token(length: int = 32) -> str:
    """Generate a secure alphanumeric token."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
