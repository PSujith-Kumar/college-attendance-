# database.py - Complete database abstraction layer
"""
All database operations in one module.
Uses SQLite with row_factory for dict-like access.
"""
import sqlite3
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from config import DATABASE_FILE, DATA_DIR, DEFAULT_DEPARTMENTS, DEFAULT_ADMIN

os.makedirs(DATA_DIR, exist_ok=True)


def get_conn():
    """Get a database connection with row_factory."""
    conn = sqlite3.connect(DATABASE_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# =========================================================================
# INITIALIZATION
# =========================================================================

def init_database():
    """Create all tables and seed defaults."""
    conn = get_conn()
    conn.execute("PRAGMA journal_mode = WAL")
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
        year_level INTEGER DEFAULT 1,
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

    c.execute('''CREATE TABLE IF NOT EXISTS chief_admin_scopes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chief_admin_email TEXT NOT NULL,
        department TEXT NOT NULL,
        year_level INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chief_admin_email) REFERENCES users(email),
        UNIQUE(chief_admin_email, department, year_level)
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
        year_level INTEGER DEFAULT 1,
        test_name TEXT,
        department TEXT,
        section TEXT,
        file_hash TEXT,
        is_blocked INTEGER DEFAULT 0,
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

    c.execute('''CREATE TABLE IF NOT EXISTS counselor_mark_overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        counselor_email TEXT NOT NULL,
        test_id INTEGER NOT NULL,
        reg_no TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        marks TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (counselor_email) REFERENCES users(email),
        FOREIGN KEY (test_id) REFERENCES tests(id),
        UNIQUE(counselor_email, test_id, reg_no, subject_name)
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
    ensure_users_year_level_column()
    ensure_test_metadata_columns()
    ensure_chief_admin_scopes_table()
    ensure_counselor_mark_overrides_table()
    ensure_counselor_student_departments()
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


def is_system_admin(role):
    return str(role or "").strip().lower() == "admin"


def is_chief_admin(role):
    return str(role or "").strip().lower() == "chief_admin"


def get_chief_admin_scopes(chief_admin_email):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT department, year_level
        FROM chief_admin_scopes
        WHERE chief_admin_email=?
        ORDER BY department, year_level
        """,
        (chief_admin_email,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_chief_admin_scopes(chief_admin_email, scopes):
    """scopes: iterable of (department, year_level)."""
    cleaned = []
    for item in scopes or []:
        if not item:
            continue
        dep = str(item[0] or "").strip().upper()
        try:
            yr = int(item[1])
        except (TypeError, ValueError):
            continue
        if not dep or yr not in (1, 2, 3, 4):
            continue
        cleaned.append((dep, yr))

    conn = get_conn()
    conn.execute("DELETE FROM chief_admin_scopes WHERE chief_admin_email=?", (chief_admin_email,))
    for dep, yr in sorted(set(cleaned)):
        conn.execute(
            "INSERT OR IGNORE INTO chief_admin_scopes (chief_admin_email, department, year_level) VALUES (?,?,?)",
            (chief_admin_email, dep, yr),
        )
    conn.commit()
    conn.close()


def get_scoped_users_for_admin(actor_email, actor_role):
    """System admin sees all users; chief admin sees counselors in allowed dept/year, other chief admins with matching scopes, plus self."""
    if is_system_admin(actor_role):
        return get_all_users()

    if not is_chief_admin(actor_role):
        return []

    scopes = get_chief_admin_scopes(actor_email)
    if not scopes:
        own = get_user(actor_email)
        return [own] if own else []

    allowed = {(s["department"], int(s["year_level"])) for s in scopes}
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()

    filtered = []
    for r in rows:
        d = dict(r)
        if d.get("email") == actor_email:
            filtered.append(d)
            continue
        
        # Include counselors in allowed scopes
        if d.get("role") == "counselor":
            key = (str(d.get("department") or "").strip().upper(), int(d.get("year_level") or 1))
            if key in allowed:
                filtered.append(d)
            continue
        
        # Include other chief admins if they have ANY scope overlap with current chief admin
        if d.get("role") == "chief_admin":
            other_scopes = get_chief_admin_scopes(d.get("email"))
            other_allowed = {(s["department"], int(s["year_level"])) for s in other_scopes}
            if allowed & other_allowed:  # Check for scope intersection
                filtered.append(d)
    
    return filtered


def create_user(email, password, name, role="counselor", department=None, max_students=30,
                can_upload_students=True, year_level=1):
    conn = get_conn()
    try:
        conn.execute("""INSERT INTO users (email, password_hash, name, role, department, year_level, max_students, can_upload_students)
                        VALUES (?,?,?,?,?,?,?,?)""",
                            (email, hash_password(password), name, role, department, int(year_level or 1),
                             max_students, 1 if can_upload_students else 0))
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


def update_user_password(email, password_hash):
    """Update user password hash."""
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE email=?", (password_hash, email))
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
    try:
        row = conn.execute("""SELECT s.is_active, u.is_active as ua, u.is_locked
                          FROM active_sessions s JOIN users u ON s.user_email=u.email
                          WHERE s.session_id=?""", (session_id,)).fetchone()
        if not row or not row["is_active"] or not row["ua"] or row["is_locked"]:
            return False
        conn.execute("UPDATE active_sessions SET last_activity=? WHERE session_id=? AND is_active=1",
                     (datetime.now(), session_id))
        conn.commit()
        return True
    except sqlite3.OperationalError:
        # Do not fail request cycle when heartbeat write loses a lock race.
        return False
    finally:
        conn.close()


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


def get_all_unique_tests(filter_batch=None, filter_semester=None, filter_dept=None,
                         filter_counselor=None, filter_year_level=None, allowed_scopes=None):
    """Get unique uploaded tests, keeping latest per logical test key."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT t.id, t.test_name as t_name, t.test_date,
               tm.id as tm_id, tm.test_id, tm.test_name, tm.batch_name, tm.semester,
                         tm.department, tm.section, tm.year_level, tm.uploaded_at, tm.uploaded_by, tm.subjects,
               COALESCE(tm.is_blocked, 0) as is_blocked,
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
        section_val = str(d.get("section") or "")
        year_val = str(d.get("year_level") or "")
        counselor_val = str(d.get("uploaded_by") or "")
        if filter_batch and batch_val != str(filter_batch):
            continue
        if filter_semester and sem_val != str(filter_semester):
            continue
        if filter_dept and dept_val != str(filter_dept):
            continue
        if filter_counselor and counselor_val != str(filter_counselor):
            continue
        if filter_year_level and year_val != str(filter_year_level):
            continue
        if allowed_scopes:
            scope_key = (dept_val.strip().upper(), int(d.get("year_level") or 1))
            if scope_key not in allowed_scopes:
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
            year_val.strip().lower(),
            section_val.strip().lower(),
        )

        # If no metadata fields exist, use concrete test id to avoid collapsing unrelated rows.
        if not any(key):
            key = (f"id:{d.get('id')}", "", "", "", "", "")

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


def get_departments_for_admin(actor_email, actor_role, active_only=False):
    if is_system_admin(actor_role):
        return get_departments(active_only=active_only)
    if not is_chief_admin(actor_role):
        return []

    scopes = get_chief_admin_scopes(actor_email)
    allowed_depts = sorted({(s.get("department") or "").strip().upper() for s in scopes if s.get("department")})
    if not allowed_depts:
        return []

    conn = get_conn()
    placeholders = ",".join(["?"] * len(allowed_depts))
    sql = f"SELECT * FROM departments WHERE UPPER(code) IN ({placeholders})"
    params = list(allowed_depts)
    if active_only:
        sql += " AND is_active=1"
    sql += " ORDER BY name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_department_active(department_code):
    dep = str(department_code or "").strip().upper()
    if not dep:
        return True
    conn = get_conn()
    row = conn.execute("SELECT is_active FROM departments WHERE UPPER(code)=?", (dep,)).fetchone()
    conn.close()
    if not row:
        return True
    return bool(row["is_active"])


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
            conn.execute("""
                INSERT INTO counselor_students
                (counselor_email, reg_no, student_name, department, parent_phone, parent_email)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(counselor_email, reg_no) DO UPDATE SET
                    student_name=excluded.student_name,
                    department=COALESCE(NULLIF(excluded.department, ''), counselor_students.department),
                    parent_phone=COALESCE(NULLIF(excluded.parent_phone, ''), counselor_students.parent_phone),
                    parent_email=COALESCE(NULLIF(excluded.parent_email, ''), counselor_students.parent_email),
                    is_active=1,
                    uploaded_at=CURRENT_TIMESTAMP
            """,
            (
                counselor_email,
                s.get("reg_no", ""),
                s.get("name", ""),
                s.get("department", ""),
                s.get("phone", ""),
                s.get("email", ""),
            ))
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


def update_test_metadata_fields(test_id, test_name=None, semester=None, department=None, batch_name=None, section=None):
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
    if section is not None:
        sets.append("section=?")
        vals.append(section)

    if sets:
        vals.append(test_id)
        conn.execute(f"UPDATE test_metadata SET {','.join(sets)} WHERE test_id=?", vals)
        if test_name is not None:
            conn.execute("UPDATE tests SET test_name=? WHERE id=?", (test_name, test_id))
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
                                        (test_id, batch_name, semester, year_level, test_name, department, section, file_hash, is_blocked, academic_year,
                     subjects, subject_columns, header_row, data_start_row, uploaded_at, uploaded_by)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (test_id, metadata.get("batch_name"), metadata.get("semester"), metadata.get("year_level", 1),
                  metadata.get("test_name"), metadata.get("department"),
                                    metadata.get("section"), metadata.get("file_hash"), int(metadata.get("is_blocked") or 0),
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


def get_student_marks_for_reg_for_counselor(test_id, reg_no, counselor_email):
    base = get_student_marks_for_reg(test_id, reg_no)
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT subject_name, marks
        FROM counselor_mark_overrides
        WHERE counselor_email=? AND test_id=? AND reg_no=?
        """,
        (counselor_email, test_id, reg_no),
    ).fetchall()
    conn.close()
    merged = dict(base)
    for r in rows:
        merged[r["subject_name"]] = r["marks"]
    return merged


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

    def _is_named_subject(name):
        txt = str(name or "").strip()
        if not txt:
            return False
        low = txt.lower()
        if low.startswith("unnamed"):
            return False
        if re.match(r"^subject[_\s-]*\d+$", low):
            return False
        return True
    if meta and meta["subjects"]:
        try:
            subjects = [s for s in json.loads(meta["subjects"]) if _is_named_subject(s)]
        except:
            pass
    
    # If no subjects in metadata, extract from marks
    if not subjects:
        subjects = list(set(r["subject_name"] for r in rows if _is_named_subject(r["subject_name"])))
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


def get_test_marks_grouped_for_counselor(test_id, counselor_email):
    grouped = get_test_marks_grouped(test_id)
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT reg_no, subject_name, marks
        FROM counselor_mark_overrides
        WHERE counselor_email=? AND test_id=?
        """,
        (counselor_email, test_id),
    ).fetchall()
    conn.close()

    if not rows:
        return grouped

    by_key = {(str(s.get("reg_no") or ""), str(subj)): str(mark)
              for s in grouped.get("students", [])
              for subj, mark in (s.get("marks") or {}).items()}
    for r in rows:
        by_key[(str(r["reg_no"]), str(r["subject_name"]))] = str(r["marks"] or "")

    for student in grouped.get("students", []):
        reg_no = str(student.get("reg_no") or "")
        marks = student.get("marks") or {}
        for subj in list(marks.keys()):
            key = (reg_no, str(subj))
            if key in by_key:
                marks[subj] = by_key[key]
        student["marks"] = marks

    return grouped


def upsert_counselor_mark_override(counselor_email, test_id, reg_no, subject_name, marks):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO counselor_mark_overrides
            (counselor_email, test_id, reg_no, subject_name, marks, updated_at)
        VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
        ON CONFLICT(counselor_email, test_id, reg_no, subject_name)
        DO UPDATE SET marks=excluded.marks, updated_at=CURRENT_TIMESTAMP
        """,
        (counselor_email, test_id, reg_no, subject_name, str(marks or "")),
    )
    conn.commit()
    conn.close()


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


def get_message_history_filtered(day=None, counselor_query=None, limit=500,
                                filter_year=None, filter_month=None, filter_day=None,
                                allowed_counselors=None):
    """Admin-facing message history with optional day and counselor-name filters."""
    conn = get_conn()
    where = []
    params = []

    if day:
        where.append("DATE(sm.sent_at)=?")
        params.append(str(day))
    else:
        if filter_year:
            where.append("strftime('%Y', sm.sent_at)=?")
            params.append(str(filter_year).zfill(4))
        if filter_month:
            where.append("strftime('%m', sm.sent_at)=?")
            params.append(str(filter_month).zfill(2))
        if filter_day:
            where.append("strftime('%d', sm.sent_at)=?")
            params.append(str(filter_day).zfill(2))

    if counselor_query:
        q = f"%{str(counselor_query).strip().lower()}%"
        where.append("(LOWER(COALESCE(u.name, '')) LIKE ? OR LOWER(COALESCE(sm.counselor_email, '')) LIKE ?)")
        params.extend([q, q])

    if allowed_counselors is not None:
        allowed = [str(x).strip().lower() for x in allowed_counselors if str(x).strip()]
        if not allowed:
            conn.close()
            return []
        placeholders = ",".join(["?"] * len(allowed))
        where.append(f"LOWER(COALESCE(sm.counselor_email, '')) IN ({placeholders})")
        params.extend(allowed)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT ?"
        params.append(int(limit))

    rows = conn.execute(
        f"""
        SELECT sm.*, u.name AS counselor_name
        FROM sent_messages sm
        LEFT JOIN users u ON sm.counselor_email = u.email
        {where_sql}
        ORDER BY sm.sent_at DESC
        {limit_sql}
        """,
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_message_days(counselor_query=None):
    """Return available message dates with counts for day-wise navigation."""
    conn = get_conn()
    where = ""
    params = []
    if counselor_query:
        q = f"%{str(counselor_query).strip().lower()}%"
        where = "WHERE (LOWER(COALESCE(u.name, '')) LIKE ? OR LOWER(COALESCE(sm.counselor_email, '')) LIKE ?)"
        params.extend([q, q])

    rows = conn.execute(
        f"""
        SELECT COALESCE(DATE(sm.sent_at), 'Unknown') AS day,
               COUNT(*) AS total,
               COUNT(DISTINCT sm.counselor_email) AS counselors
        FROM sent_messages sm
        LEFT JOIN users u ON sm.counselor_email = u.email
        {where}
        GROUP BY DATE(sm.sent_at)
        ORDER BY day DESC
        """,
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_message_counselor_suggestions(query="", allowed_counselors=None, limit=25):
    conn = get_conn()
    where = ["u.role='counselor'"]
    params = []

    q = str(query or "").strip().lower()
    if q:
        like_q = f"%{q}%"
        where.append("(LOWER(COALESCE(u.name, '')) LIKE ? OR LOWER(COALESCE(u.email, '')) LIKE ?)")
        params.extend([like_q, like_q])

    if allowed_counselors is not None:
        allowed = [str(x).strip().lower() for x in allowed_counselors if str(x).strip()]
        if not allowed:
            conn.close()
            return []
        placeholders = ",".join(["?"] * len(allowed))
        where.append(f"LOWER(u.email) IN ({placeholders})")
        params.extend(allowed)

    where_sql = " AND ".join(where)
    params.append(int(limit))
    rows = conn.execute(
        f"""
        SELECT DISTINCT u.name, u.email
        FROM users u
        WHERE {where_sql}
        ORDER BY u.name
        LIMIT ?
        """,
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_message_by_id(message_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM sent_messages WHERE id=?", (int(message_id),))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected


def delete_messages_by_ids(message_ids):
    ids = [int(x) for x in (message_ids or []) if str(x).strip().isdigit()]
    if not ids:
        return 0

    placeholders = ",".join(["?"] * len(ids))
    conn = get_conn()
    cur = conn.execute(f"DELETE FROM sent_messages WHERE id IN ({placeholders})", ids)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected


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
    try:
        update_session_activity(session_id)
    except Exception:
        return False


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
    """Backward-compatible alias for counselor visible test database."""
    return get_visible_tests_for_counselor(counselor_email)


def get_marks_by_test(test_id):
    """Alias for get_test_marks with enriched data."""
    return get_test_marks(test_id)


def find_test_by_hash(file_hash, uploaded_by=None):
    """Find a previously uploaded test by file hash."""
    if not file_hash:
        return None
    conn = get_conn()
    if uploaded_by:
        row = conn.execute(
            """SELECT tm.test_id, tm.uploaded_by, tm.test_name, tm.batch_name, tm.semester, tm.department
               FROM test_metadata tm
               WHERE tm.file_hash=? AND tm.uploaded_by=?
               ORDER BY tm.uploaded_at DESC LIMIT 1""",
            (file_hash, uploaded_by),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT tm.test_id, tm.uploaded_by, tm.test_name, tm.batch_name, tm.semester, tm.department
               FROM test_metadata tm
               WHERE tm.file_hash=?
               ORDER BY tm.uploaded_at DESC LIMIT 1""",
            (file_hash,),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_visible_tests_for_counselor(counselor_email):
    """Return department+year-visible tests that contain marks for allocated students."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT t.id,
               COALESCE(tm.test_name, t.test_name) AS test_name,
               COALESCE(tm.semester, '') AS semester,
               COALESCE(tm.department, '') AS department,
               COALESCE(tm.year_level, 1) AS year_level,
               COALESCE(tm.batch_name, '') AS batch_name,
               COALESCE(tm.section, '') AS section,
               COALESCE(tm.is_blocked, 0) AS is_blocked,
               tm.uploaded_at,
               (SELECT COUNT(DISTINCT sm.reg_no)
                   FROM student_marks sm
                   JOIN counselor_students cs ON cs.reg_no = sm.reg_no
                   WHERE sm.test_id = t.id AND cs.counselor_email = ?) as student_count,
               (SELECT COUNT(DISTINCT s2.reg_no)
                   FROM sent_messages s2
                   WHERE s2.test_id = t.id AND s2.counselor_email = ?) as generated_count
        FROM tests t
        JOIN test_metadata tm ON t.id = tm.test_id
        JOIN users u ON u.email = ?
        WHERE COALESCE(tm.department, '') = COALESCE(u.department, '')
                    AND COALESCE(tm.year_level, 1) = COALESCE(u.year_level, 1)
          AND EXISTS (
              SELECT 1
              FROM student_marks sm
              JOIN counselor_students cs ON cs.reg_no = sm.reg_no
              WHERE sm.test_id = t.id AND cs.counselor_email = ?
          )
        ORDER BY tm.uploaded_at DESC, t.id DESC
        """,
        (counselor_email, counselor_email, counselor_email, counselor_email),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_existing_department_test(department, semester, test_name, batch_name=None):
    """Find latest existing test for the same department-semester-test tuple."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT tm.test_id, tm.file_hash, tm.uploaded_by, tm.uploaded_at
        FROM test_metadata tm
        WHERE LOWER(COALESCE(tm.department, '')) = LOWER(COALESCE(?, ''))
          AND LOWER(COALESCE(tm.semester, '')) = LOWER(COALESCE(?, ''))
          AND LOWER(COALESCE(tm.test_name, '')) = LOWER(COALESCE(?, ''))
          AND LOWER(COALESCE(tm.batch_name, '')) = LOWER(COALESCE(?, ''))
        ORDER BY tm.uploaded_at DESC, tm.test_id DESC
        LIMIT 1
        """,
        (department, str(semester), test_name, batch_name or ""),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def find_existing_department_year_test(department, year_level, semester, test_name, batch_name=None):
    """Find latest existing test for the same department+year+semester+test tuple."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT tm.test_id, tm.file_hash, tm.uploaded_by, tm.uploaded_at
        FROM test_metadata tm
        WHERE LOWER(COALESCE(tm.department, '')) = LOWER(COALESCE(?, ''))
          AND COALESCE(tm.year_level, 1) = COALESCE(?, 1)
          AND LOWER(COALESCE(tm.semester, '')) = LOWER(COALESCE(?, ''))
          AND LOWER(COALESCE(tm.test_name, '')) = LOWER(COALESCE(?, ''))
          AND LOWER(COALESCE(tm.batch_name, '')) = LOWER(COALESCE(?, ''))
        ORDER BY tm.uploaded_at DESC, tm.test_id DESC
        LIMIT 1
        """,
        (department, int(year_level or 1), str(semester), test_name, batch_name or ""),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_test_marks(test_name, semester, counselor_email, students, subjects,
                    batch_name=None, department=None, section=None,
                    file_hash=None, replace_test_id=None, sync_students=True,
                    year_level=1, enforce_assigned_match=True, uploaded_by=None):
    """
    High-level wrapper to create a test and save marks.
    students: list of dicts with 'reg_no', 'name', 'marks' (dict of subject: mark)
    subjects: list of subject names
    """
    # Hard guard: uploaded rows must match assigned counselor students by Reg No + Name.
    def _norm_reg(value):
        reg = str(value or "").strip().replace(" ", "")
        if reg.endswith(".0"):
            reg = reg[:-2]
        return reg.upper()

    def _norm_name(value):
        name = str(value or "").strip().lower()
        name = re.sub(r"\s+", " ", name)
        return name

    if enforce_assigned_match:
        # Validate students against assigned list (separate connection, short-lived)
        conn = get_conn()
        try:
            assigned_rows = conn.execute(
                "SELECT reg_no, student_name FROM counselor_students WHERE counselor_email=?",
                (counselor_email,),
            ).fetchall()
            assigned_map = {
                _norm_reg(r["reg_no"]): _norm_name(r["student_name"])
                for r in assigned_rows
                if _norm_reg(r["reg_no"])
            }
        finally:
            conn.close()

        if not assigned_map:
            return False, "No match: no students assigned to this counselor."

        mismatch_samples = []
        for student in students:
            reg = _norm_reg(student.get("reg_no"))
            name = _norm_name(student.get("name"))
            assigned_name = assigned_map.get(reg)
            if not reg or not assigned_name or not name or assigned_name != name:
                if len(mismatch_samples) < 5:
                    mismatch_samples.append(f"{student.get('reg_no', '')} ({student.get('name', '')})")

        if mismatch_samples:
            return False, f"No match: uploaded rows do not match assigned list (Reg No + Name). Examples: {', '.join(mismatch_samples)}"

    try:
        # Get or create batch/semester
        yr = datetime.now().year
        default_batch_name = f"{yr}-{str(yr + 1)[-2:]}"
        chosen_batch_name = (batch_name or default_batch_name).strip()
        batch_id = get_or_create_batch(chosen_batch_name)

        sem_num = 1
        try:
            sem_num = int(''.join(filter(str.isdigit, str(semester)))) or 1
        except Exception:
            pass
        semester_id = get_or_create_semester(batch_id, sem_num)

        # Create test or replace existing test content
        if replace_test_id:
            test_id = int(replace_test_id)
            # Use separate connection for deletion/update operations
            conn2 = get_conn()
            try:
                conn2.execute("DELETE FROM student_marks WHERE test_id=?", (test_id,))
                conn2.execute("DELETE FROM test_metadata WHERE test_id=?", (test_id,))
                conn2.execute("UPDATE tests SET semester_id=?, test_name=? WHERE id=?", (semester_id, test_name, test_id))
                conn2.commit()
            finally:
                conn2.close()
        else:
            test_id = create_test(semester_id, test_name)

        # Save metadata
        if not department:
            department = next((s.get("department", "") for s in students if s.get("department")), "")
        if not section:
            section = next((s.get("section", "") for s in students if s.get("section")), "")

        save_test_metadata(test_id, {
            "batch_name": chosen_batch_name,
            "semester": semester,
            "year_level": int(year_level or 1),
            "test_name": test_name,
            "department": department,
            "section": section,
            "file_hash": file_hash,
            "subjects": subjects,
            "uploaded_by": uploaded_by or counselor_email,
        })

        # Optionally sync roster/contact details from marksheet.
        if sync_students:
            roster = []
            for student in students:
                reg = str(student.get("reg_no", "")).strip()
                name = str(student.get("name", "")).strip() or reg
                if not reg:
                    continue
                roster.append({
                    "reg_no": reg,
                    "name": name,
                    "department": student.get("department", "") or department or "",
                    "phone": student.get("phone", ""),
                    "email": student.get("email", ""),
                })
            if roster:
                add_students_bulk(counselor_email, roster)

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

        # Tests visible for counselor (department + year with allocated students)
        tests_uploaded = conn.execute(
            """
            SELECT COUNT(DISTINCT tm.test_id)
            FROM test_metadata tm
            JOIN users u ON u.email=?
            WHERE COALESCE(tm.department, '') = COALESCE(u.department, '')
              AND COALESCE(tm.year_level, 1) = COALESCE(u.year_level, 1)
              AND EXISTS (
                    SELECT 1
                    FROM student_marks sm
                    JOIN counselor_students cs ON cs.reg_no = sm.reg_no
                    WHERE sm.test_id = tm.test_id AND cs.counselor_email = ?
              )
            """,
            (email, email),
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


def ensure_test_metadata_columns():
    """Backfill columns added after first release."""
    conn = get_conn()
    try:
        conn.execute("SELECT section FROM test_metadata LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE test_metadata ADD COLUMN section TEXT")
        conn.commit()

    try:
        conn.execute("SELECT file_hash FROM test_metadata LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE test_metadata ADD COLUMN file_hash TEXT")
        conn.commit()

    try:
        conn.execute("SELECT year_level FROM test_metadata LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE test_metadata ADD COLUMN year_level INTEGER DEFAULT 1")
        conn.execute("UPDATE test_metadata SET year_level=1 WHERE year_level IS NULL")
        conn.commit()

    try:
        conn.execute("SELECT is_blocked FROM test_metadata LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE test_metadata ADD COLUMN is_blocked INTEGER DEFAULT 0")
        conn.execute("UPDATE test_metadata SET is_blocked=0 WHERE is_blocked IS NULL")
        conn.commit()
    conn.close()


def ensure_users_year_level_column():
    """Add year_level to users if missing and backfill existing users."""
    conn = get_conn()
    try:
        conn.execute("SELECT year_level FROM users LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE users ADD COLUMN year_level INTEGER DEFAULT 1")
        conn.commit()

    conn.execute("UPDATE users SET year_level=1 WHERE year_level IS NULL OR year_level < 1")
    conn.commit()
    conn.close()


def ensure_chief_admin_scopes_table():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chief_admin_scopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chief_admin_email TEXT NOT NULL,
            department TEXT NOT NULL,
            year_level INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chief_admin_email) REFERENCES users(email),
            UNIQUE(chief_admin_email, department, year_level)
        )
        """
    )
    conn.commit()
    conn.close()


def ensure_counselor_mark_overrides_table():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS counselor_mark_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            counselor_email TEXT NOT NULL,
            test_id INTEGER NOT NULL,
            reg_no TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            marks TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (counselor_email) REFERENCES users(email),
            FOREIGN KEY (test_id) REFERENCES tests(id),
            UNIQUE(counselor_email, test_id, reg_no, subject_name)
        )
        """
    )
    conn.commit()
    conn.close()


def ensure_counselor_student_departments():
    """Backfill missing/empty student department from counselor account department."""
    conn = get_conn()
    conn.execute(
        """
        UPDATE counselor_students
        SET department = (
            SELECT UPPER(COALESCE(users.department, ''))
            FROM users
            WHERE users.email = counselor_students.counselor_email
        )
        WHERE COALESCE(TRIM(department), '') = ''
        """
    )
    conn.commit()
    conn.close()


def update_test_block_status(test_id, is_blocked):
    conn = get_conn()
    conn.execute(
        "UPDATE test_metadata SET is_blocked=? WHERE test_id=?",
        (1 if int(is_blocked) else 0, int(test_id)),
    )
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
