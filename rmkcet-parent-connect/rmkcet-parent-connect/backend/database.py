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
        FOREIGN KEY (counselor_email) REFERENCES users(email)
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

def authenticate_user(email: str, password: str):
    """Return user dict or None."""
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
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

def register_session(session_id, user_email, ip_address=None, user_agent=None):
    """Register new session. Returns (success, message)."""
    allowed, msg = check_user_access(user_email)
    if not allowed:
        return False, msg
    conn = get_conn()
    import uuid
    tab_id = str(uuid.uuid4())
    browser_info = (user_agent or "Unknown")[:100]
    now = datetime.now()
    # Deactivate old sessions
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


def search_students(counselor_email, query):
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute("""SELECT * FROM counselor_students
                           WHERE counselor_email=? AND (student_name LIKE ? OR reg_no LIKE ?
                           OR parent_phone LIKE ? OR parent_email LIKE ?)""",
                        (counselor_email, q, q, q, q)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


# =========================================================================
# MESSAGES
# =========================================================================

def log_message(counselor_email, reg_no, student_name, message, fmt="message",
                whatsapp_link=None, session_id=None):
    conn = get_conn()
    conn.execute("""INSERT INTO sent_messages
                    (counselor_email, reg_no, student_name, message, format, whatsapp_link, session_id)
                    VALUES (?,?,?,?,?,?,?)""",
                 (counselor_email, reg_no, student_name, message, fmt, whatsapp_link, session_id))
    conn.commit()
    conn.close()


def get_message_history(counselor_email=None, limit=100):
    conn = get_conn()
    if counselor_email:
        rows = conn.execute("SELECT * FROM sent_messages WHERE counselor_email=? ORDER BY sent_at DESC LIMIT ?",
                            (counselor_email, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sent_messages ORDER BY sent_at DESC LIMIT ?", (limit,)).fetchall()
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
    # Tests may be linked via test_metadata.uploaded_by or just return all tests
    rows = conn.execute("""SELECT DISTINCT t.id, t.test_name,
                           tm.semester, tm.department, tm.batch_name
                           FROM tests t
                           LEFT JOIN test_metadata tm ON t.id = tm.test_id
                           ORDER BY t.id DESC""").fetchall()
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
