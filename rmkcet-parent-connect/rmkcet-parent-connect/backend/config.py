# config.py - Central configuration
"""
All application settings in one place.
Database-stored settings override these defaults at runtime.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === Directories ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# === Database ===
DATABASE_FILE = os.path.join(DATA_DIR, "rmkcet.db")

# === Application ===
APP_NAME = "RMKCET Parent Connect"
APP_VERSION = "5.0"
APP_ICON = "🎓"
SESSION_TIMEOUT = 1800  # 30 minutes
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

# === Departments ===
DEFAULT_DEPARTMENTS = [
    {"code": "ECE", "name": "Electronics and Communication Engineering", "color": "#667eea"},
    {"code": "CSE", "name": "Computer Science Engineering", "color": "#764ba2"},
    {"code": "EEE", "name": "Electrical and Electronics Engineering", "color": "#f39c12"},
    {"code": "MECH", "name": "Mechanical Engineering", "color": "#e74c3c"},
    {"code": "CIVIL", "name": "Civil Engineering", "color": "#2ecc71"},
    {"code": "AIDS", "name": "Artificial Intelligence & Data Science", "color": "#9b59b6"},
    {"code": "EE(VLSI)", "name": "Electrical Engineering (VLSI)", "color": "#3498db"},
]

DEFAULT_SUBJECTS = {
    "ECE": [
        {"code": "MA", "name": "Mathematics", "emoji": "📘"},
        {"code": "CH", "name": "Chemistry", "emoji": "🧪"},
        {"code": "JAVA", "name": "Java Programming", "emoji": "☕"},
        {"code": "DSA", "name": "Data Structures", "emoji": "💾"},
        {"code": "AI", "name": "Artificial Intelligence", "emoji": "🤖"},
    ],
    "CSE": [
        {"code": "MA", "name": "Mathematics", "emoji": "📘"},
        {"code": "PHY", "name": "Physics", "emoji": "⚛️"},
        {"code": "C++", "name": "C++ Programming", "emoji": "⚙️"},
        {"code": "SDP", "name": "Skill Development", "emoji": "🔧"},
        {"code": "DPSD", "name": "Digital Principles", "emoji": "🔌"},
    ],
}

# Registration number department patterns
DEPT_REG_PATTERNS = {
    "AIDS": "201", "CSE": "108", "ECE": "104",
    "EEE": "110", "EE(VLSI)": "110", "MECH": "105", "CIVIL": "106",
}

# === Student Settings ===
MAX_STUDENTS_PER_COUNSELOR = 30
DATA_START_ROW = 7

# === Email (SMTP) ===
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "RMKCET Parent Connect <noreply@rmkcet.ac.in>")

# === Security ===
OTP_EXPIRY_SECONDS = 300
PASSWORD_RESET_TOKEN_EXPIRY = 3600
ALLOWED_EMAIL_DOMAINS = ["rmkcet.ac.in", "rmkec.ac.in", "gmail.com"]

# === WhatsApp ===
COUNTRY_CODE = os.getenv("COUNTRY_CODE", "91")
WHATSAPP_BASE_URL = "https://wa.me/"

# === Feature Toggles ===
ENABLE_REGISTRATION = False
ENABLE_BULK_SEND = True
ENABLE_REPORTS = True
ENABLE_ADMIN_PANEL = True
TEST_MODE = os.getenv("TEST_MODE", "False").strip().lower() == "true"

# === Format Settings ===
DEFAULT_FORMAT = "message"
ALLOWED_FORMATS = ["message", "pdf", "image"]
BULK_FORMAT = "same_as_individual"

# === Message Template ===
MESSAGE_TEMPLATE = """Dear Parent :  The Following is the {test_name} Marks Secured in each Course by your son/daughter

REGISTER NUMBER :  {reg_no}
NAME : {student_name}

{subjects_table}

Regards
PRINCIPAL
RMKCET
"""

# === Default Admin ===
DEFAULT_ADMIN = {
    "email": "admin@rmkcet.ac.in",
    "password": "Admin@123",
    "name": "System Administrator"
}

# === Theme ===
THEME = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#25D366",
    "warning": "#f39c12",
    "danger": "#f85032",
    "info": "#3498db",
    "dark": "#0a0c14",
    "light": "#1a1f2e",
    "card_bg": "rgba(20, 30, 50, 0.7)",
    "text_primary": "#ffffff",
    "text_secondary": "#cbd5e1",
}


def load_config_from_db():
    """Load configuration overrides from database."""
    try:
        from database import get_config
        for key, value in get_config().items():
            if key in globals():
                current = globals()[key]
                if isinstance(current, bool):
                    globals()[key] = bool(value)
                elif isinstance(current, int):
                    globals()[key] = int(value)
                elif isinstance(current, list) and isinstance(value, str):
                    import json
                    globals()[key] = json.loads(value)
                else:
                    globals()[key] = value
        return True
    except Exception:
        return False


def validate_config():
    """Return list of config warnings."""
    warnings = []
    if not TEST_MODE and (not SMTP_USERNAME or not SMTP_PASSWORD):
        warnings.append("Email credentials not configured.")
    if SESSION_TIMEOUT < 60:
        warnings.append("Session timeout is very low (<60s).")
    return warnings
