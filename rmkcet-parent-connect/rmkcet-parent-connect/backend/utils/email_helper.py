# utils/email_helper.py
"""Email sending via SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, TEST_MODE


def send_email(to_email: str, subject: str, body: str, html: bool = False) -> bool:
    """Send an email. Returns True on success."""
    if TEST_MODE:
        print(f"[TEST MODE] Email to {to_email}: {subject}")
        return True

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Email not configured")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send password reset email with token."""
    subject = "RMKCET Parent Connect - Password Reset"
    body = f"""
    <h2>Password Reset Request</h2>
    <p>Your password reset token is:</p>
    <h1 style="color: #667eea; letter-spacing: 5px;">{token}</h1>
    <p>This token expires in 1 hour.</p>
    <p>If you did not request this, please ignore this email.</p>
    <br>
    <p>— RMKCET Parent Connect</p>
    """
    return send_email(to_email, subject, body, html=True)
