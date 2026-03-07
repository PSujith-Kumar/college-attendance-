# database.py - Complete database abstraction layer
"""
All database operations in one module.
Uses SQLite with row_factory for dict-like access.
"""
import sqlite3
import hashlib
import json
import os
from datetime import datetime, timedelta
from config import DATABASE_FILE, DATA_DIR, DEFAULT_DEPARTMENTS, DEFAULT_ADMIN

os.makedirs(DATA_DIR, exist_ok=True)


def get_conn():
    """Get a database connection with row_factory."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =========================================================================
# INITIALIZATION
# =========================================================================

def init_database():
    """Create all tables and seed defaults."""
    conn = get_conn()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#667eea',
        is_active BOOLEAN DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        department TEXT,
        role TEXT DEFAULT 'counselor',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        last_activity TIMESTAMP,
        session_id TEXT,
        is_active BOOLEAN DEFAULT 1,
        is_locked BOOLEAN DEFAULT 0,
        lock_reason TEXT,
        max_students INTEGER DEFAULT 30,
        can_upload_students BOOLEAN DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS active_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        user_email TEXT NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        browser_info TEXT,
        tab_id TEXT,
        is_active BOOLEAN DEFAULT 1,
        forced_logout BOOLEAN DEFAULT 0,
        logout_reason TEXT,
        FOREIGN KEY (user_email) REFERENCES users(email)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS counselor_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        counselor_email TEXT NOT NULL,
        reg_no TEXT NOT NULL,
        student_name TEXT NOT NULL,
        department TEXT,
        parent_phone TEXT,
        parent_email TEXT,
        is_active BOOLEAN DEFAULT 1,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (counselor_email) REFERENCES users(email),
        UNIQUE(counselor_email, reg_no)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sent_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        counselor_email TEXT NOT NULL,
        test_id INTEGER,
        reg_no TEXT NOT NULL,
        student_name TEXT NOT NULL,
        message TEXT,
        format TEXT DEFAULT 'message',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'sent',
        delivery_status TEXT DEFAULT 'pending',
        whatsapp_link TEXT,
        error_message TEXT,
        session_id TEXT,
        FOREIGN KEY (counselor_email) REFERENCES users(email),
        FOREIGN KEY (test_id) REFERENCES tests(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        start_year INTEGER,
        end_year INTEGER,
        is_active BOOLEAN DEFAULT 1
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS semesters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        semester_number INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (batch_id) REFERENCES batches(id),
        UNIQUE(batch_id, semester_number)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester_id INTEGER NOT NULL,
        test_name TEXT NOT NULL,
        test_date DATE,
        max_marks INTEGER DEFAULT 100,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS test_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER UNIQUE NOT NULL,
        batch_name TEXT,
        semester INTEGER,
        test_name TEXT,
        department TEXT,
        academic_year TEXT,
        subjects TEXT,
        subject_columns TEXT,
        header_row TEXT,
        data_start_row INTEGER DEFAULT 7,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uploaded_by TEXT,
        FOREIGN KEY (test_id) REFERENCES tests(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS student_marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL,
        reg_no TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        subject_code TEXT,
        marks TEXT,
        department TEXT,
        uploaded_by TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (test_id) REFERENCES tests(id),
        UNIQUE(test_id, reg_no, subject_name)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        token TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN DEFAULT 0,
        FOREIGN KEY (user_email) REFERENCES users(email)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS format_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        default_format TEXT DEFAULT 'message',
        allowed_formats TEXT DEFAULT '["message","pdf","image"]',
        bulk_format TEXT DEFAULT 'same_as_individual',
        updated_by TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS app_config (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Seed default departments
    for dept in DEFAULT_DEPARTMENTS:
        c.execute('INSERT OR IGNORE INTO departments (code, name, color) VALUES (?,?,?)',
                  (dept["code"], dept["name"], dept["color"]))

    # Seed default batch
    c.execute("SELECT COUNT(*) FROM batches")
    if c.fetchone()[0] == 0:
        yr = datetime.now().year
        c.execute('INSERT INTO batches (name, start_year, end_year) VALUES (?,?,?)',
                  (f"{yr}-{str(yr+1)[-2:]}", yr, yr+1))

    # Seed format settings
    c.execute("SELECT COUNT(*) FROM format_settings")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO format_settings (default_format, allowed_formats) VALUES (?,?)",
                  ("message", json.dumps(["message", "pdf", "image"])))

    # Seed default admin
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO users (email, password_hash, name, role, max_students) VALUES (?,?,?,?,?)',
                  (DEFAULT_ADMIN["email"], hash_password(DEFAULT_ADMIN["password"]),
                   DEFAULT_ADMIN["name"], "admin", 100))

    conn.commit()
    conn.close()

    # Run migrations for existing DBs
    ensure_sent_messages_test_id_column()
    ensure_can_upload_students_column()
    return True


# =========================================================================
# CONFIG
# =========================================================================

def get_config():
    """Load all key/value config from app_config table."""
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(key, value):
    conn = get_conn()
    conn.execute("""INSERT INTO app_config (key, value, updated_at) VALUES (?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?""",
                 (key, str(value), datetime.now(), str(value), datetime.now()))
    conn.commit()
    conn.close()


# =========================================================================
# AUTH
# =========================================================================

def authenticate_user(identifier: str, password: str):
    """Return user dict or None. Identifier can be email or name."""
    conn = get_conn()
    # Try by email first
    user = conn.execute("SELECT * FROM users WHERE email=?", (identifier,)).fetchone()
    # If not found, try by name (case-insensitive)
    if not user:
        user = conn.execute("SELECT * FROM users WHERE LOWER(name)=LOWER(?)", (identifier,)).fetchone()
    conn.close()
    if user and user["password_hash"] == hash_password(password):
        return dict(user)
    return None


def get_user(email: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(email, password, name, role="counselor", department=None, max_students=30, can_upload_students=True):
    conn = get_conn()
    try:
        conn.execute("""INSERT INTO users (email, password_hash, name, role, department, max_students, can_upload_students)
                        VALUES (?,?,?,?,?,?,?)""",
                     (email, hash_password(password), name, role, department, max_students,
                      1 if can_upload_students else 0))
        conn.commit()
        return True, "User created"
    except sqlite3.IntegrityError:
        return False, "Email already exists"
    finally:
        conn.close()


def update_user(email, **kwargs):
    conn = get_conn()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k == "password":
            sets.append("password_hash=?")
            vals.append(hash_password(v))
        else:
            sets.append(f"{k}=?")
            vals.append(v)
    vals.append(email)
    conn.execute(f"UPDATE users SET {','.join(sets)} WHERE email=?", vals)
    conn.commit()
    conn.close()


def delete_user(email):
    conn = get_conn()
    conn.execute("DELETE FROM counselor_students WHERE counselor_email=?", (email,))
    conn.execute("DELETE FROM active_sessions WHERE user_email=?", (email,))
    conn.execute("DELETE FROM sent_messages WHERE counselor_email=?", (email,))
    conn.execute("DELETE FROM users WHERE email=?", (email,))
    conn.commit()
    conn.close()


def lock_user(email, reason="Locked by admin"):
    conn = get_conn()
    conn.execute("UPDATE users SET is_locked=1, lock_reason=? WHERE email=?", (reason, email))
    conn.execute("""UPDATE active_sessions SET is_active=0, forced_logout=1, logout_reason='account_locked'
                    WHERE user_email=? AND is_active=1""", (email,))
    conn.execute("UPDATE users SET session_id=NULL WHERE email=?", (email,))
    conn.commit()
    conn.close()


def unlock_user(email):
    conn = get_conn()
    conn.execute("UPDATE users SET is_locked=0, lock_reason=NULL WHERE email=?", (email,))
    conn.commit()
    conn.close()


def check_user_access(email):
    """Return (allowed: bool, message: str)."""
    user = get_user(email)
    if not user:
        return False, "User not found"
    if not user["is_active"]:
        return False, "Account deactivated"
    if user["is_locked"]:
        return False, "Account locked"
    return True, "Access granted"


# =========================================================================
# PASSWORD RESET
# =========================================================================

def create_reset_token(email, token):
    conn = get_conn()
    from config import PASSWORD_RESET_TOKEN_EXPIRY
    expires = datetime.now() + timedelta(seconds=PASSWORD_RESET_TOKEN_EXPIRY)
    conn.execute("INSERT INTO password_reset_tokens (user_email, token, expires_at) VALUES (?,?,?)",
                 (email, token, expires))
    conn.commit()
    conn.close()


def validate_reset_token(token):
    conn = get_conn()
    row = conn.execute("""SELECT * FROM password_reset_tokens
                          WHERE token=? AND used=0 AND expires_at>?""",
                       (token, datetime.now())).fetchone()
    conn.close()
    return dict(row) if row else None


def use_reset_token(token):
    conn = get_conn()
    conn.execute("UPDATE password_reset_tokens SET used=1 WHERE token=?", (token,))
    conn.commit()
    conn.close()


# =========================================================================
# SESSIONS
# =========================================================================
# INDUSTRIAL-GRADE SESSION MANAGEMENT
# =========================================================================

import hashlib
import secrets
from datetime import datetime, timedelta


def generate_session_token():
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def generate_session_fingerprint(ip_address, user_agent):
    """Generate a fingerprint to detect session hijacking attempts."""
    fingerprint_data = f"{ip_address or 'unknown'}|{(user_agent or 'unknown')[:50]}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]


def get_user_active_session(user_email):
    """Get active session for a user if any exists."""
    conn = get_conn()
    row = conn.execute("""SELECT * FROM active_sessions 
                          WHERE user_email=? AND is_active=1 
                          ORDER BY login_time DESC LIMIT 1""", (user_email,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        # Add device info
        try:
            ua = d.get("user_agent", "")
            if "Mobile" in ua or "Android" in ua or "iPhone" in ua:
                d["device_type"] = "Mobile"
            elif "Tablet" in ua or "iPad" in ua:
                d["device_type"] = "Tablet"
            else:
                d["device_type"] = "Desktop"
            # Browser detection
            if "Chrome" in ua:
                d["browser"] = "Chrome"
            elif "Firefox" in ua:
                d["browser"] = "Firefox"
            elif "Safari" in ua:
                d["browser"] = "Safari"
            elif "Edge" in ua:
                d["browser"] = "Edge"
            else:
                d["browser"] = "Unknown"
        except:
            d["device_type"] = "Unknown"
            d["browser"] = "Unknown"
        return d
    return None


def has_active_session(user_email):
    """Check if user has an active session on another device."""
    conn = get_conn()
    row = conn.execute("""SELECT COUNT(*) as cnt FROM active_sessions 
                          WHERE user_email=? AND is_active=1""", (user_email,)).fetchone()
    conn.close()
    return row["cnt"] > 0 if row else False


def validate_session_strict(session_id, ip_address=None, user_agent=None):
    """
    Industrial-grade session validation.
    Returns (is_valid, reason, user_email).
    """
    if not session_id:
        return False, "no_session", None
    
    conn = get_conn()
    row = conn.execute("""
        SELECT s.*, u.is_active as user_active, u.is_locked
        FROM active_sessions s
        JOIN users u ON s.user_email = u.email
        WHERE s.session_id=?
    """, (session_id,)).fetchone()
    
    if not row:
        conn.close()
        return False, "session_not_found", None
    
    session = dict(row)
    
    # Check if session is still active
    if not session.get("is_active"):
        conn.close()
        logout_reason = session.get("logout_reason", "unknown")
        return False, f"session_inactive:{logout_reason}", session["user_email"]
    
    # Check if user account is still valid
    if not session.get("user_active"):
        conn.close()
        return False, "user_deactivated", session["user_email"]
    
    if session.get("is_locked"):
        conn.close()
        return False, "user_locked", session["user_email"]
    
    # Check session timeout
    config = get_app_config()
    timeout_seconds = int(config.get("session_timeout", 1800))
    last_activity = session.get("last_activity")
    
    if last_activity:
        try:
            if isinstance(last_activity, str):
                last_activity = datetime.strptime(last_activity[:19], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - last_activity).total_seconds() > timeout_seconds:
                # Session timed out, mark it as inactive
                conn.execute("""
                    UPDATE active_sessions SET is_active=0, logout_reason='session_timeout'
                    WHERE session_id=?
                """, (session_id,))
                conn.commit()
                conn.close()
                return False, "session_timeout", session["user_email"]
        except:
            pass
    
    conn.close()
    return True, "valid", session["user_email"]


def force_logout_by_email(user_email, reason="new_device_login"):
    """Force logout all sessions for a user (called from new device)."""
    conn = get_conn()
    conn.execute("""UPDATE active_sessions SET is_active=0, forced_logout=1, logout_reason=?
                    WHERE user_email=? AND is_active=1""", (reason, user_email))
    conn.execute("UPDATE users SET session_id=NULL WHERE email=?", (user_email,))
    conn.commit()
    conn.close()
    return True


def register_session(session_id, user_email, ip_address=None, user_agent=None, force_logout_others=True):
    """Register new session. Returns (success, message)."""
    allowed, msg = check_user_access(user_email)
    if not allowed:
        return False, msg
    conn = get_conn()
    import uuid
    tab_id = str(uuid.uuid4())
    browser_info = (user_agent or "Unknown")[:100]
    fingerprint = generate_session_fingerprint(ip_address, user_agent)
    now = datetime.now()
    # Deactivate old sessions if force_logout_others is True
    if force_logout_others:
        conn.execute("""UPDATE active_sessions SET is_active=0, logout_reason='new_login'
                        WHERE user_email=? AND is_active=1""", (user_email,))
    conn.execute("""INSERT INTO active_sessions
                    (session_id, user_email, ip_address, user_agent, browser_info, tab_id, login_time, last_activity)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (session_id, user_email, ip_address, user_agent, browser_info, tab_id, now, now))
    conn.execute("UPDATE users SET last_activity=?, session_id=?, last_login=? WHERE email=?",
                 (now, session_id, now, user_email))
    conn.commit()
    conn.close()
    return True, "Session registered"


def update_session_activity(session_id):
    conn = get_conn()
    row = conn.execute("""SELECT s.is_active, u.is_active as ua, u.is_locked
                          FROM active_sessions s JOIN users u ON s.user_email=u.email
                          WHERE s.session_id=?""", (session_id,)).fetchone()
    if not row or not row["is_active"] or not row["ua"] or row["is_locked"]:
        conn.close()
        return False
    conn.execute("UPDATE active_sessions SET last_activity=? WHERE session_id=? AND is_active=1",
                 (datetime.now(), session_id))
    conn.commit()
    conn.close()
    return True


def end_session(session_id, reason="user_logout"):
    conn = get_conn()
    row = conn.execute("SELECT user_email FROM active_sessions WHERE session_id=?", (session_id,)).fetchone()
    email = row["user_email"] if row else None
    conn.execute("UPDATE active_sessions SET is_active=0, logout_reason=? WHERE session_id=?",
                 (reason, session_id))
    if email:
        conn.execute("UPDATE users SET session_id=NULL WHERE email=? AND session_id=?",
                     (email, session_id))
    conn.commit()
    conn.close()


def cleanup_stale_sessions():
    from config import SESSION_TIMEOUT
    conn = get_conn()
    cutoff = datetime.now() - timedelta(seconds=SESSION_TIMEOUT)
    conn.execute("""UPDATE active_sessions SET is_active=0, logout_reason='session_timeout'
                    WHERE last_activity<? AND is_active=1""", (cutoff,))
    conn.commit()
    conn.close()


def force_logout_user(email, reason="admin_action"):
    conn = get_conn()
    conn.execute("""UPDATE active_sessions SET is_active=0, forced_logout=1, logout_reason=?
                    WHERE user_email=? AND is_active=1""", (reason, email))
    conn.execute("UPDATE users SET session_id=NULL WHERE email=?", (email,))
    conn.commit()
    conn.close()


def get_active_sessions():
    conn = get_conn()
    rows = conn.execute("""SELECT s.*, u.name, u.role, u.department,
                                  u.is_active as user_active, u.is_locked, u.lock_reason
                           FROM active_sessions s
                           LEFT JOIN users u ON s.user_email=u.email
                           WHERE s.is_active=1
                           ORDER BY s.last_activity DESC""").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Calculate time ago
        try:
            la = d.get("last_activity", "")
            if isinstance(la, str) and la:
                la = datetime.strptime(la[:19], "%Y-%m-%d %H:%M:%S")
            diff = int((datetime.now() - la).total_seconds())
            if diff < 60:
                d["time_ago"] = f"{diff}s ago"
            elif diff < 3600:
                d["time_ago"] = f"{diff//60}m ago"
            else:
                d["time_ago"] = f"{diff//3600}h ago"
            # Status
            if diff < 120:
                d["status"] = "Active"
            elif diff < 600:
                d["status"] = "Idle"
            else:
                d["status"] = "Inactive"
        except Exception:
            d["time_ago"] = "Unknown"
            d["status"] = "Unknown"
        result.append(d)
    return result


def get_active_sessions_count():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM active_sessions WHERE is_active=1").fetchone()[0]
    conn.close()
    return count


def clear_inactive_sessions():
    conn = get_conn()
    conn.execute("DELETE FROM active_sessions WHERE is_active=0")
    conn.commit()
    conn.close()


def logout_all_users():
    conn = get_conn()
    conn.execute("UPDATE active_sessions SET is_active=0, logout_reason='admin_logout_all'")
    conn.execute("UPDATE users SET session_id=NULL")
    conn.commit()
    conn.close()


# =========================================================================
# SESSION MONITORING & STATISTICS
# =========================================================================

def get_session_statistics():
    """Get comprehensive session monitoring statistics."""
    conn = get_conn()
    
    # Active sessions count
    active_count = conn.execute("SELECT COUNT(*) FROM active_sessions WHERE is_active=1").fetchone()[0]
    
    # Total sessions today
    today_sessions = conn.execute("""SELECT COUNT(*) FROM active_sessions 
                                      WHERE DATE(login_time)=DATE('now')""").fetchone()[0]
    
    # Average session duration (in minutes)
    avg_duration = conn.execute("""
        SELECT AVG((JULIANDAY(COALESCE(last_activity, login_time)) - JULIANDAY(login_time)) * 24 * 60)
        FROM active_sessions WHERE is_active=0 AND logout_reason IS NOT NULL
    """).fetchone()[0] or 0
    
    # Sessions by logout reason
    logout_reasons = conn.execute("""
        SELECT logout_reason, COUNT(*) as cnt 
        FROM active_sessions 
        WHERE is_active=0 AND logout_reason IS NOT NULL
        GROUP BY logout_reason
    """).fetchall()
    
    # Peak concurrent sessions (approximate)
    peak_sessions = conn.execute("""
        SELECT MAX(concurrent_count) FROM (
            SELECT COUNT(*) as concurrent_count 
            FROM active_sessions 
            GROUP BY DATE(login_time), strftime('%H', login_time)
        )
    """).fetchone()[0] or 0
    
    # Forced logouts count
    forced_logouts = conn.execute("""
        SELECT COUNT(*) FROM active_sessions WHERE forced_logout=1
    """).fetchone()[0]
    
    # Sessions by device type (based on user_agent)
    mobile_sessions = conn.execute("""
        SELECT COUNT(*) FROM active_sessions 
        WHERE user_agent LIKE '%Mobile%' OR user_agent LIKE '%Android%' OR user_agent LIKE '%iPhone%'
    """).fetchone()[0]
    
    desktop_sessions = conn.execute("""
        SELECT COUNT(*) FROM active_sessions 
        WHERE user_agent NOT LIKE '%Mobile%' AND user_agent NOT LIKE '%Android%' AND user_agent NOT LIKE '%iPhone%'
    """).fetchone()[0]
    
    conn.close()
    
    return {
        "active_sessions": active_count,
        "today_sessions": today_sessions,
        "avg_duration_minutes": round(avg_duration, 1),
        "logout_reasons": {r["logout_reason"]: r["cnt"] for r in logout_reasons},
        "peak_concurrent": peak_sessions,
        "forced_logouts": forced_logouts,
        "mobile_sessions": mobile_sessions,
        "desktop_sessions": desktop_sessions,
    }


def get_session_history(limit=100, user_email=None):
    """Get session history with detailed information."""
    conn = get_conn()
    if user_email:
        rows = conn.execute("""
            SELECT s.*, u.name, u.role, u.department
            FROM active_sessions s
            LEFT JOIN users u ON s.user_email = u.email
            WHERE s.user_email=?
            ORDER BY s.login_time DESC LIMIT ?
        """, (user_email, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT s.*, u.name, u.role, u.department
            FROM active_sessions s
            LEFT JOIN users u ON s.user_email = u.email
            ORDER BY s.login_time DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        # Calculate session duration
        try:
            login = d.get("login_time", "")
            last_act = d.get("last_activity", login)
            if isinstance(login, str) and login:
                login_dt = datetime.strptime(login[:19], "%Y-%m-%d %H:%M:%S")
                last_dt = datetime.strptime(last_act[:19], "%Y-%m-%d %H:%M:%S")
                duration_mins = int((last_dt - login_dt).total_seconds() / 60)
                d["duration"] = f"{duration_mins}m" if duration_mins < 60 else f"{duration_mins//60}h {duration_mins%60}m"
        except:
            d["duration"] = "Unknown"
        result.append(d)
    return result


def get_user_session_history(user_email, limit=20):
    """Get session history for a specific user."""
    return get_session_history(limit=limit, user_email=user_email)


# =========================================================================
# APP CONFIGURATION
# =========================================================================

def get_app_config():
    """Get all app configuration settings."""
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    conn.close()
    config = {r["key"]: r["value"] for r in rows}
    # Set defaults if not present - ALL customizable colors with proper labels
    defaults = {
        # Session Settings
        "session_timeout": "1800",
        "allow_concurrent_sessions": "false",
        "max_concurrent_sessions": "1",
        "session_monitoring_enabled": "true",
        "session_heartbeat_interval": "30",
        
        # Theme Colors - Primary
        "color_primary": "#667eea",
        "color_primary_dark": "#5a6fd6",
        "color_secondary": "#764ba2",
        "color_accent": "#a78bfa",
        
        # Theme Colors - Semantic
        "color_success": "#25D366",
        "color_warning": "#f59e0b",
        "color_danger": "#ef4444",
        "color_info": "#3b82f6",
        
        # Theme Colors - Background
        "color_bg_primary": "#0a0c14",
        "color_bg_secondary": "#0f1219",
        "color_bg_card": "rgba(20, 30, 50, 0.65)",
        
        # Theme Colors - Text
        "color_text": "#e2e8f0",
        "color_text_dim": "#94a3b8",
        "color_text_muted": "#64748b",
        
        # Theme Colors - Borders
        "color_border": "rgba(102, 126, 234, 0.18)",
    }
    for key, default_val in defaults.items():
        if key not in config:
            config[key] = default_val
    return config


def update_app_config(key, value):
    """Update a single app config setting."""
    conn = get_conn()
    conn.execute("""INSERT INTO app_config (key, value, updated_at) VALUES (?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?""",
                 (key, str(value), datetime.now(), str(value), datetime.now()))
    conn.commit()
    conn.close()


def update_app_config_bulk(settings: dict):
    """Update multiple app config settings at once."""
    conn = get_conn()
    for key, value in settings.items():
        conn.execute("""INSERT INTO app_config (key, value, updated_at) VALUES (?,?,?)
                        ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?""",
                     (key, str(value), datetime.now(), str(value), datetime.now()))
    conn.commit()
    conn.close()


def get_session_timeout():
    """Get session timeout value from config."""
    config = get_app_config()
    try:
        return int(config.get("session_timeout", 1800))
    except:
        return 1800


# =========================================================================
# COUNSELOR SUBMISSIONS HISTORY
# =========================================================================

def get_counselor_submissions(counselor_email, limit=50):
    """Get a counselor's test upload history."""
    conn = get_conn()
    rows = conn.execute("""
     SELECT tm.*, t.test_name as t_name, t.id as test_id,
         COALESCE(tm.semester, s.semester_number) as semester,
         COALESCE(tm.batch_name, b.name) as batch_name,
         COALESCE(tm.department, '') as department,
         COALESCE(tm.test_name, t.test_name) as test_name,
               (SELECT COUNT(DISTINCT sm.reg_no) FROM student_marks sm WHERE sm.test_id = t.id) as student_count
        FROM test_metadata tm
        JOIN tests t ON tm.test_id = t.id
     LEFT JOIN semesters s ON t.semester_id = s.id
     LEFT JOIN batches b ON s.batch_id = b.id
        WHERE tm.uploaded_by = ?
        ORDER BY tm.uploaded_at DESC
        LIMIT ?
    """, (counselor_email, limit)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        # Parse subjects JSON
        try:
            d["subjects_list"] = json.loads(d.get("subjects", "[]"))
        except:
            d["subjects_list"] = []
        result.append(d)
    return result


def get_all_unique_tests(filter_batch=None, filter_semester=None, filter_dept=None, filter_counselor=None):
    """Get unique uploaded tests, keeping latest per logical test key."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT t.id, t.test_name as t_name, t.test_date,
               tm.id as tm_id, tm.test_id, tm.test_name, tm.batch_name, tm.semester,
               tm.department, tm.uploaded_at, tm.uploaded_by, tm.subjects,
               u.name as uploaded_by_name,
               (SELECT COUNT(DISTINCT sm.reg_no) FROM student_marks sm WHERE sm.test_id = t.id) as student_count,
               0 as is_duplicate
        FROM tests t
        LEFT JOIN test_metadata tm ON tm.test_id = t.id
        LEFT JOIN users u ON tm.uploaded_by = u.email
        ORDER BY COALESCE(tm.uploaded_at, t.test_date) DESC, t.id DESC
    """).fetchall()
    conn.close()

    seen = set()
    result = []
    for r in rows:
        d = dict(r)
        d["test_id"] = d.get("test_id") or d.get("id")

        # Apply filters safely on normalized values.
        batch_val = str(d.get("batch_name") or "")
        sem_val = str(d.get("semester") or "")
        dept_val = str(d.get("department") or "")
        counselor_val = str(d.get("uploaded_by") or "")
        if filter_batch and batch_val != str(filter_batch):
            continue
        if filter_semester and sem_val != str(filter_semester):
            continue
        if filter_dept and dept_val != str(filter_dept):
            continue
        if filter_counselor and counselor_val != str(filter_counselor):
            continue

        try:
            d["subjects"] = json.loads(d.get("subjects") or "[]")
        except Exception:
            d["subjects"] = []

        if not d.get("test_name"):
            d["test_name"] = d.get("t_name") or f"Test #{d.get('id')}"

        key = (
            (d.get("test_name") or "").strip().lower(),
            batch_val.strip().lower(),
            sem_val.strip().lower(),
            dept_val.strip().lower(),
        )

        # If no metadata fields exist, use concrete test id to avoid collapsing unrelated rows.
        if not any(key):
            key = (f"id:{d.get('id')}", "", "", "")

        if key in seen:
            continue
        seen.add(key)
        result.append(d)

    result.sort(key=lambda x: ((x.get("test_name") or "").lower(), (x.get("uploaded_at") or "")), reverse=False)
    return result


# =========================================================================
# DEPARTMENTS
# =========================================================================

def get_departments(active_only=True):
    conn = get_conn()
    if active_only:
        rows = conn.execute("SELECT * FROM departments WHERE is_active=1 ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM departments ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_department(code, name, color="#667eea"):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO departments (code, name, color) VALUES (?,?,?)", (code, name, color))
        conn.commit()
        return True, "Department created"
    except sqlite3.IntegrityError:
        return False, "Department code already exists"
    finally:
        conn.close()


def update_department(dept_id, **kwargs):
    conn = get_conn()
    sets = [f"{k}=?" for k in kwargs]
    vals = list(kwargs.values()) + [dept_id]
    conn.execute(f"UPDATE departments SET {','.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_department(dept_id):
    conn = get_conn()
    conn.execute("DELETE FROM departments WHERE id=?", (dept_id,))
    conn.commit()
    conn.close()


# =========================================================================
# STUDENTS
# =========================================================================

def get_students(counselor_email):
    conn = get_conn()
    rows = conn.execute("""SELECT * FROM counselor_students
                           WHERE counselor_email=? ORDER BY student_name""",
                        (counselor_email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_count(counselor_email):
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM counselor_students WHERE counselor_email=?",
                         (counselor_email,)).fetchone()[0]
    conn.close()
    return count


def add_student(counselor_email, reg_no, name, department=None, phone=None, email=None):
    conn = get_conn()
    try:
        conn.execute("""INSERT INTO counselor_students
                        (counselor_email, reg_no, student_name, department, parent_phone, parent_email)
                        VALUES (?,?,?,?,?,?)""",
                     (counselor_email, reg_no, name, department, phone, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def add_students_bulk(counselor_email, students):
    """students: list of dicts with reg_no, name, department, phone, email."""
    conn = get_conn()
    added = 0
    for s in students:
        try:
            conn.execute("""INSERT OR REPLACE INTO counselor_students
                            (counselor_email, reg_no, student_name, department, parent_phone, parent_email)
                            VALUES (?,?,?,?,?,?)""",
                         (counselor_email, s.get("reg_no", ""), s.get("name", ""),
                          s.get("department", ""), s.get("phone", ""), s.get("email", "")))
            added += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return added


def delete_student(counselor_email, reg_no):
    conn = get_conn()
    conn.execute("DELETE FROM counselor_students WHERE counselor_email=? AND reg_no=?",
                 (counselor_email, reg_no))
    conn.commit()
    conn.close()


def delete_all_students(counselor_email):
    conn = get_conn()
    conn.execute("DELETE FROM counselor_students WHERE counselor_email=?", (counselor_email,))
    conn.commit()
    conn.close()


def update_student(counselor_email, reg_no, student_name=None, department=None, parent_phone=None, parent_email=None):
    """Update a single student under a counselor."""
    conn = get_conn()
    sets = []
    vals = []
    if student_name is not None:
        sets.append("student_name=?")
        vals.append(student_name)
    if department is not None:
        sets.append("department=?")
        vals.append(department)
    if parent_phone is not None:
        sets.append("parent_phone=?")
        vals.append(parent_phone)
    if parent_email is not None:
        sets.append("parent_email=?")
        vals.append(parent_email)

    if not sets:
        conn.close()
        return False

    vals.extend([counselor_email, reg_no])
    conn.execute(
        f"UPDATE counselor_students SET {','.join(sets)} WHERE counselor_email=? AND reg_no=?",
        vals,
    )
    conn.commit()
    conn.close()
    return True


def admin_upsert_student(counselor_email, reg_no, student_name, department="", parent_phone="", parent_email=""):
    """Admin-facing upsert for counselor student records."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO counselor_students
           (counselor_email, reg_no, student_name, department, parent_phone, parent_email)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(counselor_email, reg_no)
           DO UPDATE SET student_name=excluded.student_name,
                         department=excluded.department,
                         parent_phone=excluded.parent_phone,
                         parent_email=excluded.parent_email""",
        (counselor_email, reg_no, student_name, department, parent_phone, parent_email),
    )
    conn.commit()
    conn.close()
    return True


def search_students(counselor_email, query):
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute("""SELECT * FROM counselor_students
                           WHERE counselor_email=? AND (student_name LIKE ? OR reg_no LIKE ?
                           OR parent_phone LIKE ? OR parent_email LIKE ?)""",
                        (counselor_email, q, q, q, q)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_test_id_for_counselor(counselor_email):
    """Return latest uploaded test id for counselor, or None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT test_id FROM test_metadata WHERE uploaded_by=? ORDER BY uploaded_at DESC LIMIT 1",
        (counselor_email,),
    ).fetchone()
    conn.close()
    return int(row["test_id"]) if row and row.get("test_id") is not None else None


def update_test_metadata_fields(test_id, test_name=None, semester=None, department=None, batch_name=None):
    """Allow edits to parsed test metadata before sending reports."""
    conn = get_conn()
    sets = []
    vals = []
    if test_name is not None:
        sets.append("test_name=?")
        vals.append(test_name)
    if semester is not None:
        sets.append("semester=?")
        vals.append(semester)
    if department is not None:
        sets.append("department=?")
        vals.append(department)
    if batch_name is not None:
        sets.append("batch_name=?")
        vals.append(batch_name)

    if sets:
        vals.append(test_id)
        conn.execute(f"UPDATE test_metadata SET {','.join(sets)} WHERE test_id=?", vals)
        conn.commit()
    conn.close()
    return True


def get_sent_reg_nos_for_test(counselor_email, test_id):
    """Get already-sent student reg numbers for a counselor/test."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT reg_no FROM sent_messages WHERE counselor_email=? AND test_id=?",
        (counselor_email, test_id),
    ).fetchall()
    conn.close()
    return {r["reg_no"] for r in rows}


def get_pending_students_for_test(counselor_email, test_id):
    """Get counselor students who have not been sent report for this test."""
    students = get_students(counselor_email)
    sent = get_sent_reg_nos_for_test(counselor_email, test_id)
    return [s for s in students if s.get("reg_no") not in sent]


# =========================================================================
# BATCHES & SEMESTERS
# =========================================================================

def get_batches():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM batches ORDER BY start_year DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_or_create_batch(name):
    conn = get_conn()
    row = conn.execute("SELECT id FROM batches WHERE name=?", (name,)).fetchone()
    if row:
        conn.close()
        return row["id"]
    parts = name.split("-")
    start = int(parts[0]) if parts[0].isdigit() else datetime.now().year
    end = start + 1
    conn.execute("INSERT INTO batches (name, start_year, end_year) VALUES (?,?,?)", (name, start, end))
    conn.commit()
    bid = conn.execute("SELECT id FROM batches WHERE name=?", (name,)).fetchone()["id"]
    conn.close()
    return bid


def get_or_create_semester(batch_id, semester_number):
    conn = get_conn()
    row = conn.execute("SELECT id FROM semesters WHERE batch_id=? AND semester_number=?",
                       (batch_id, semester_number)).fetchone()
    if row:
        conn.close()
        return row["id"]
    conn.execute("INSERT INTO semesters (batch_id, semester_number) VALUES (?,?)",
                 (batch_id, semester_number))
    conn.commit()
    sid = conn.execute("SELECT id FROM semesters WHERE batch_id=? AND semester_number=?",
                       (batch_id, semester_number)).fetchone()["id"]
    conn.close()
    return sid


# =========================================================================
# TESTS & MARKS
# =========================================================================

def create_test(semester_id, test_name, max_marks=100):
    conn = get_conn()
    conn.execute("INSERT INTO tests (semester_id, test_name, max_marks) VALUES (?,?,?)",
                 (semester_id, test_name, max_marks))
    conn.commit()
    tid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return tid


def get_tests():
    conn = get_conn()
    rows = conn.execute("""SELECT t.*, s.semester_number, b.name as batch_name
                           FROM tests t
                           JOIN semesters s ON t.semester_id=s.id
                           JOIN batches b ON s.batch_id=b.id
                           ORDER BY t.id DESC""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_test_metadata(test_id, metadata: dict):
    conn = get_conn()
    conn.execute("""INSERT OR REPLACE INTO test_metadata
                    (test_id, batch_name, semester, test_name, department, academic_year,
                     subjects, subject_columns, header_row, data_start_row, uploaded_at, uploaded_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (test_id, metadata.get("batch_name"), metadata.get("semester"),
                  metadata.get("test_name"), metadata.get("department"),
                  metadata.get("academic_year"), json.dumps(metadata.get("subjects", [])),
                  json.dumps(metadata.get("subject_columns", {})),
                  metadata.get("header_row"), metadata.get("data_start_row", 7),
                  datetime.now(), metadata.get("uploaded_by")))
    conn.commit()
    conn.close()


def save_student_marks(test_id, marks_data, uploaded_by=None):
    """marks_data: list of dicts {reg_no, subject_name, subject_code, marks, department}."""
    conn = get_conn()
    for m in marks_data:
        try:
            conn.execute("""INSERT OR REPLACE INTO student_marks
                            (test_id, reg_no, subject_name, subject_code, marks, department, uploaded_by)
                            VALUES (?,?,?,?,?,?,?)""",
                         (test_id, m["reg_no"], m["subject_name"],
                          m.get("subject_code", ""), str(m.get("marks", "")),
                          m.get("department", ""), uploaded_by))
        except Exception:
            continue
    conn.commit()
    conn.close()


def get_test_marks(test_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM student_marks WHERE test_id=?", (test_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_test_metadata(test_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM test_metadata WHERE test_id=?", (test_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_marks_for_reg(test_id, reg_no):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM student_marks WHERE test_id=? AND reg_no=?",
                        (test_id, reg_no)).fetchall()
    conn.close()
    return {r["subject_name"]: r["marks"] for r in rows}


def get_test_marks_grouped(test_id):
    """Get test marks grouped by student with all subjects in columns."""
    conn = get_conn()
    
    # Get all marks for this test
    rows = conn.execute("""
        SELECT DISTINCT reg_no, subject_name, marks, department
        FROM student_marks WHERE test_id = ?
        ORDER BY reg_no, subject_name
    """, (test_id,)).fetchall()
    
    # Get subjects list from metadata
    meta = conn.execute("SELECT subjects FROM test_metadata WHERE test_id = ?", (test_id,)).fetchone()
    conn.close()
    
    subjects = []
    if meta and meta["subjects"]:
        try:
            subjects = json.loads(meta["subjects"])
        except:
            pass
    
    # If no subjects in metadata, extract from marks
    if not subjects:
        subjects = list(set(r["subject_name"] for r in rows if r["subject_name"]))
        subjects.sort()
    
    # Group by student
    students = {}
    for r in rows:
        reg = r["reg_no"]
        if reg not in students:
            students[reg] = {
                "reg_no": reg,
                "department": r["department"] or "",
                "marks": {}
            }
        students[reg]["marks"][r["subject_name"]] = r["marks"]
    
    return {
        "subjects": subjects,
        "students": list(students.values())
    }


# =========================================================================
# MESSAGES
# =========================================================================

def log_message(counselor_email, reg_no, student_name, message, fmt="message",
                     whatsapp_link=None, session_id=None, test_id=None):
    conn = get_conn()
    conn.execute("""INSERT INTO sent_messages
                          (counselor_email, test_id, reg_no, student_name, message, format, whatsapp_link, session_id)
                          VALUES (?,?,?,?,?,?,?,?)""",
                      (counselor_email, test_id, reg_no, student_name, message, fmt, whatsapp_link, session_id))
    conn.commit()
    conn.close()


def get_message_history(counselor_email=None, limit=100):
    conn = get_conn()
    if counselor_email:
        rows = conn.execute("""
            SELECT sm.*, u.name as counselor_name 
            FROM sent_messages sm 
            LEFT JOIN users u ON sm.counselor_email = u.email 
            WHERE sm.counselor_email=? 
            ORDER BY sm.sent_at DESC LIMIT ?
        """, (counselor_email, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT sm.*, u.name as counselor_name 
            FROM sent_messages sm 
            LEFT JOIN users u ON sm.counselor_email = u.email 
            ORDER BY sm.sent_at DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_message_stats(counselor_email=None):
    conn = get_conn()
    if counselor_email:
        total = conn.execute("SELECT COUNT(*) FROM sent_messages WHERE counselor_email=?",
                             (counselor_email,)).fetchone()[0]
        today = conn.execute("SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND DATE(sent_at)=DATE('now')",
                             (counselor_email,)).fetchone()[0]
        week = conn.execute("SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND sent_at>=DATE('now','-7 days')",
                            (counselor_email,)).fetchone()[0]
        month = conn.execute("SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND sent_at>=DATE('now','-30 days')",
                             (counselor_email,)).fetchone()[0]
        unique = conn.execute("SELECT COUNT(DISTINCT reg_no) FROM sent_messages WHERE counselor_email=?",
                              (counselor_email,)).fetchone()[0]
        conn.close()
        return {"total": total, "today": today, "week": week, "month": month, "unique": unique}
    else:
        total = conn.execute("SELECT COUNT(*) FROM sent_messages").fetchone()[0]
        today = conn.execute("SELECT COUNT(*) FROM sent_messages WHERE DATE(sent_at)=DATE('now')").fetchone()[0]
        counselors = conn.execute("SELECT COUNT(DISTINCT counselor_email) FROM sent_messages").fetchone()[0]
        conn.close()
        return {"total": total, "today": today, "active_counselors": counselors}


# =========================================================================
# FORMAT SETTINGS
# =========================================================================

def get_format_settings():
    conn = get_conn()
    row = conn.execute("SELECT * FROM format_settings ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["allowed_formats"] = json.loads(d["allowed_formats"])
        except Exception:
            d["allowed_formats"] = ["message", "pdf", "image"]
        return d
    return {"default_format": "message", "allowed_formats": ["message", "pdf", "image"],
            "bulk_format": "same_as_individual"}


def update_format_settings(default_format, allowed_formats, bulk_format, updated_by=None):
    conn = get_conn()
    conn.execute("""UPDATE format_settings
                    SET default_format=?, allowed_formats=?, bulk_format=?, updated_by=?, updated_at=?
                    WHERE id=(SELECT MAX(id) FROM format_settings)""",
                 (default_format, json.dumps(allowed_formats), bulk_format,
                  updated_by, datetime.now()))
    conn.commit()
    conn.close()


# =========================================================================
# CONVENIENCE ALIASES & MISSING FUNCTIONS
# =========================================================================

def validate_session(session_id):
    """Check if session_id is active in active_sessions."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM active_sessions WHERE session_id=? AND is_active=1",
                       (session_id,)).fetchone()
    conn.close()
    return row is not None


def touch_session(session_id):
    """Alias for update_session_activity."""
    update_session_activity(session_id)


def get_students_by_counselor(counselor_email):
    """Get students with field names the UI expects."""
    students = get_students(counselor_email)
    result = []
    for s in students:
        result.append({
            'reg_no': s.get('reg_no', ''),
            'name': s.get('student_name', s.get('name', '')),
            'phone': s.get('parent_phone', s.get('phone', '')),
            'email': s.get('parent_email', s.get('email', '')),
            'department': s.get('department', ''),
        })
    return result


def get_tests_by_counselor(counselor_email):
    """Get tests that have marks uploaded by this counselor."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT t.id,
               COALESCE(tm.test_name, t.test_name) as test_name,
               COALESCE(tm.semester, '') as semester,
               COALESCE(tm.department, '') as department,
               COALESCE(tm.batch_name, '') as batch_name,
               tm.uploaded_at
        FROM tests t
        LEFT JOIN test_metadata tm ON t.id = tm.test_id
        WHERE tm.uploaded_by = ?
        ORDER BY tm.uploaded_at DESC, t.id DESC
    """, (counselor_email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_marks_by_test(test_id):
    """Alias for get_test_marks with enriched data."""
    return get_test_marks(test_id)


def save_test_marks(test_name, semester, counselor_email, students, subjects):
    """
    High-level wrapper to create a test and save marks.
    students: list of dicts with 'reg_no', 'name', 'marks' (dict of subject: mark)
    subjects: list of subject names
    """
    conn = get_conn()
    try:
        # Get or create batch/semester
        yr = datetime.now().year
        batch_name = f"{yr}-{str(yr + 1)[-2:]}"
        batch_id = get_or_create_batch(batch_name)

        sem_num = 1
        try:
            sem_num = int(''.join(filter(str.isdigit, str(semester)))) or 1
        except Exception:
            pass
        semester_id = get_or_create_semester(batch_id, sem_num)

        # Create test
        test_id = create_test(semester_id, test_name)

        # Save metadata
        save_test_metadata(test_id, {
            "batch_name": batch_name,
            "semester": semester,
            "test_name": test_name,
            "subjects": subjects,
            "uploaded_by": counselor_email,
        })

        # Save marks
        marks_data = []
        for student in students:
            marks_dict = student.get('marks', {})
            for subj in subjects:
                mark_val = marks_dict.get(subj, '')
                marks_data.append({
                    "reg_no": student.get('reg_no', ''),
                    "subject_name": subj,
                    "subject_code": "",
                    "marks": mark_val,
                    "department": student.get('department', ''),
                })

        save_student_marks(test_id, marks_data, uploaded_by=counselor_email)
        return True, f"Saved marks for {len(students)} students"
    except Exception as e:
        return False, str(e)


def get_format_settings_list(active_only=False):
    """Return format settings as a list of individual format entries for the UI."""
    settings = get_format_settings()
    allowed = settings.get("allowed_formats", ["message", "pdf", "image"])
    default = settings.get("default_format", "message")

    formats = [
        {"id": 1, "name": "WhatsApp Text", "format_type": "whatsapp",
         "description": "Plain text message via WhatsApp", "icon": "💬",
         "is_active": "whatsapp" in allowed or "message" in allowed,
         "is_default": default in ("message", "whatsapp")},
        {"id": 2, "name": "PDF Report", "format_type": "pdf",
         "description": "PDF report card", "icon": "📄",
         "is_active": "pdf" in allowed,
         "is_default": default == "pdf"},
        {"id": 3, "name": "Image Report", "format_type": "image",
         "description": "Visual report card image", "icon": "🖼️",
         "is_active": "image" in allowed,
         "is_default": default == "image"},
    ]

    if active_only:
        formats = [f for f in formats if f["is_active"]]
    return formats


def update_format_setting(fmt_id, is_active=None):
    """Toggle a format type on/off."""
    fmt_map = {1: "message", 2: "pdf", 3: "image"}
    fmt_type = fmt_map.get(fmt_id)
    if not fmt_type:
        return

    settings = get_format_settings()
    allowed = settings.get("allowed_formats", ["message", "pdf", "image"])

    if is_active and fmt_type not in allowed:
        allowed.append(fmt_type)
    elif not is_active and fmt_type in allowed:
        allowed.remove(fmt_type)

    conn = get_conn()
    conn.execute("UPDATE format_settings SET allowed_formats=? WHERE id=(SELECT MAX(id) FROM format_settings)",
                 (json.dumps(allowed),))
    conn.commit()
    conn.close()


def set_default_format(fmt_id):
    """Set a format as the default."""
    fmt_map = {1: "message", 2: "pdf", 3: "image"}
    fmt_type = fmt_map.get(fmt_id, "message")
    conn = get_conn()
    conn.execute("UPDATE format_settings SET default_format=? WHERE id=(SELECT MAX(id) FROM format_settings)",
                 (fmt_type,))
    conn.commit()
    conn.close()


# =========================================================================
# COUNSELOR ACTIVITY TRACKING
# =========================================================================

def get_counselor_activity_summary():
    """Get a summary of each counselor's activity for the admin overview."""
    conn = get_conn()
    counselors = conn.execute(
        "SELECT email, name, department, last_login, last_activity, max_students, can_upload_students "
        "FROM users WHERE role='counselor' ORDER BY name"
    ).fetchall()

    result = []
    for c_row in counselors:
        email = c_row["email"]

        # Student count
        student_count = conn.execute(
            "SELECT COUNT(*) FROM counselor_students WHERE counselor_email=?", (email,)
        ).fetchone()[0]

        # Students with phone
        phone_count = conn.execute(
            "SELECT COUNT(*) FROM counselor_students WHERE counselor_email=? AND parent_phone IS NOT NULL AND parent_phone != ''",
            (email,)
        ).fetchone()[0]

        # Tests uploaded (via test_metadata.uploaded_by)
        tests_uploaded = conn.execute(
            "SELECT COUNT(DISTINCT tm.test_id) FROM test_metadata tm WHERE tm.uploaded_by=?", (email,)
        ).fetchone()[0]

        # Total messages sent
        total_messages = conn.execute(
            "SELECT COUNT(*) FROM sent_messages WHERE counselor_email=?", (email,)
        ).fetchone()[0]

        # Messages this week
        week_messages = conn.execute(
            "SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND sent_at >= DATE('now', '-7 days')",
            (email,)
        ).fetchone()[0]

        # Unique students messaged
        unique_messaged = conn.execute(
            "SELECT COUNT(DISTINCT reg_no) FROM sent_messages WHERE counselor_email=?", (email,)
        ).fetchone()[0]

        # Last message sent
        last_msg_row = conn.execute(
            "SELECT MAX(sent_at) as last_sent FROM sent_messages WHERE counselor_email=?", (email,)
        ).fetchone()
        last_message_at = last_msg_row["last_sent"] if last_msg_row else None

        # Determine work status
        has_students = student_count > 0
        has_tests = tests_uploaded > 0
        has_messages = total_messages > 0
        if has_students and has_tests and has_messages:
            work_status = "Complete"
        elif has_students and has_tests:
            work_status = "Partial - No Reports Sent"
        elif has_students:
            work_status = "Partial - No Tests Uploaded"
        else:
            work_status = "Not Started"

        result.append({
            "email": email,
            "name": c_row["name"],
            "department": c_row["department"] or "N/A",
            "last_login": c_row["last_login"],
            "last_activity": c_row["last_activity"],
            "max_students": c_row["max_students"],
            "can_upload_students": c_row["can_upload_students"],
            "student_count": student_count,
            "students_with_phone": phone_count,
            "tests_uploaded": tests_uploaded,
            "total_messages": total_messages,
            "week_messages": week_messages,
            "unique_students_messaged": unique_messaged,
            "last_message_at": last_message_at,
            "work_status": work_status,
        })

    conn.close()
    return result


def get_counselor_detailed_activity(counselor_email):
    """Get detailed activity breakdown for a single counselor."""
    conn = get_conn()

    # Basic info
    user = conn.execute("SELECT * FROM users WHERE email=?", (counselor_email,)).fetchone()
    if not user:
        conn.close()
        return None

    info = dict(user)

    # Students
    students = conn.execute(
        "SELECT * FROM counselor_students WHERE counselor_email=? ORDER BY student_name",
        (counselor_email,)
    ).fetchall()
    info["students"] = [dict(s) for s in students]
    info["student_count"] = len(students)
    info["students_with_phone"] = sum(1 for s in students if s["parent_phone"])

    # Tests uploaded
    tests = conn.execute(
        "SELECT tm.*, t.test_name as t_name FROM test_metadata tm "
        "JOIN tests t ON tm.test_id = t.id "
        "WHERE tm.uploaded_by=? ORDER BY tm.uploaded_at DESC",
        (counselor_email,)
    ).fetchall()
    info["tests"] = [dict(t) for t in tests]
    info["tests_uploaded"] = len(tests)

    # Messages
    messages = conn.execute(
        "SELECT * FROM sent_messages WHERE counselor_email=? ORDER BY sent_at DESC LIMIT 200",
        (counselor_email,)
    ).fetchall()
    info["messages"] = [dict(m) for m in messages]
    info["total_messages"] = len(messages)

    # Message stats
    info["messages_today"] = conn.execute(
        "SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND DATE(sent_at)=DATE('now')",
        (counselor_email,)
    ).fetchone()[0]
    info["messages_this_week"] = conn.execute(
        "SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND sent_at >= DATE('now', '-7 days')",
        (counselor_email,)
    ).fetchone()[0]
    info["messages_this_month"] = conn.execute(
        "SELECT COUNT(*) FROM sent_messages WHERE counselor_email=? AND sent_at >= DATE('now', '-30 days')",
        (counselor_email,)
    ).fetchone()[0]
    info["unique_students_messaged"] = conn.execute(
        "SELECT COUNT(DISTINCT reg_no) FROM sent_messages WHERE counselor_email=?",
        (counselor_email,)
    ).fetchone()[0]

    # Session history
    sessions = conn.execute(
        "SELECT login_time, last_activity, logout_reason, is_active "
        "FROM active_sessions WHERE user_email=? ORDER BY login_time DESC LIMIT 20",
        (counselor_email,)
    ).fetchall()
    info["sessions"] = [dict(s) for s in sessions]

    conn.close()
    return info


def ensure_can_upload_students_column():
    """Add can_upload_students column if it doesn't exist (migration)."""
    conn = get_conn()
    try:
        conn.execute("SELECT can_upload_students FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN can_upload_students BOOLEAN DEFAULT 1")
        conn.commit()
    conn.close()


def ensure_sent_messages_test_id_column():
    """Add test_id to sent_messages if missing (migration)."""
    conn = get_conn()
    try:
        conn.execute("SELECT test_id FROM sent_messages LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE sent_messages ADD COLUMN test_id INTEGER")
        conn.commit()
    conn.close()


# =========================================================================
# TEST MANAGEMENT (ADMIN)
# =========================================================================

def get_all_tests_with_details(filter_batch=None, filter_semester=None, filter_dept=None, filter_counselor=None):
    """Get all tests with enriched details including duplicate detection."""
    conn = get_conn()
    
    # Build query
    query = """
        SELECT t.id, t.test_name as t_name, t.test_date, t.max_marks,
               tm.test_name, tm.batch_name, tm.semester, tm.department, 
               tm.uploaded_at, tm.uploaded_by, tm.subjects,
               u.name as uploaded_by_name,
               (SELECT COUNT(DISTINCT sm.reg_no) FROM student_marks sm WHERE sm.test_id = t.id) as student_count
        FROM tests t
        LEFT JOIN test_metadata tm ON t.id = tm.test_id
        LEFT JOIN users u ON tm.uploaded_by = u.email
        WHERE 1=1
    """
    params = []
    
    if filter_batch:
        query += " AND tm.batch_name = ?"
        params.append(filter_batch)
    if filter_semester:
        query += " AND tm.semester = ?"
        params.append(filter_semester)
    if filter_dept:
        query += " AND tm.department = ?"
        params.append(filter_dept)
    if filter_counselor:
        query += " AND tm.uploaded_by = ?"
        params.append(filter_counselor)
    
    query += " ORDER BY tm.uploaded_at DESC"
    
    rows = conn.execute(query, params).fetchall()
    
    tests = []
    # Track potential duplicates: same test_name + batch + semester + department
    seen = {}
    
    for r in rows:
        test = dict(r)
        # Parse subjects JSON
        try:
            test["subjects"] = json.loads(test.get("subjects") or "[]")
        except:
            test["subjects"] = []
        
        # Use t_name if test_name from metadata is missing
        if not test["test_name"]:
            test["test_name"] = test.get("t_name", f"Test #{test['id']}")
        
        # Duplicate detection key
        dup_key = f"{test.get('test_name', '')}|{test.get('batch_name', '')}|{test.get('semester', '')}|{test.get('department', '')}"
        
        if dup_key in seen and dup_key != "|||":
            # This is a duplicate
            test["is_duplicate"] = True
            # Mark the earlier one also as duplicate
            if not seen[dup_key].get("marked_dup"):
                seen[dup_key]["is_duplicate"] = True
                seen[dup_key]["marked_dup"] = True
        else:
            test["is_duplicate"] = False
            seen[dup_key] = test
        
        tests.append(test)
    
    conn.close()
    return tests


def delete_test(test_id):
    """Delete a test and all its associated marks."""
    conn = get_conn()
    conn.execute("DELETE FROM student_marks WHERE test_id = ?", (test_id,))
    conn.execute("DELETE FROM test_metadata WHERE test_id = ?", (test_id,))
    conn.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()
    return True


def cleanup_duplicate_tests():
    """Remove duplicate test uploads, keeping only the most recent one."""
    conn = get_conn()
    
    # Find duplicates: same test_name, batch, semester, department
    duplicates = conn.execute("""
        SELECT test_name, batch_name, semester, department, 
               GROUP_CONCAT(test_id) as test_ids,
               COUNT(*) as cnt
        FROM test_metadata
        GROUP BY test_name, batch_name, semester, department
        HAVING cnt > 1
    """).fetchall()
    
    deleted_count = 0
    
    for dup in duplicates:
        test_ids = [int(x) for x in dup["test_ids"].split(",")]
        
        # Keep the most recent (highest ID), delete others
        test_ids_sorted = sorted(test_ids, reverse=True)
        keep_id = test_ids_sorted[0]
        delete_ids = test_ids_sorted[1:]
        
        for tid in delete_ids:
            conn.execute("DELETE FROM student_marks WHERE test_id = ?", (tid,))
            conn.execute("DELETE FROM test_metadata WHERE test_id = ?", (tid,))
            conn.execute("DELETE FROM tests WHERE id = ?", (tid,))
            deleted_count += 1
    
    conn.commit()
    conn.close()
    return deleted_count
