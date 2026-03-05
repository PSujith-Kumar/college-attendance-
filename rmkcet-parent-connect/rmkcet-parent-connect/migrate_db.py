# migrate_db.py
"""Database migration script - adds missing columns/tables to existing DB."""
import sqlite3
import os
from config import DATABASE_FILE


def migrate():
    """Run all migrations."""
    if not os.path.exists(DATABASE_FILE):
        print("No database found. Run the app first to create it.")
        return

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    migrations = [
        # Users table additions
        ("ALTER TABLE users ADD COLUMN is_locked INTEGER DEFAULT 0", "users.is_locked"),
        ("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1", "users.is_active"),
        ("ALTER TABLE users ADD COLUMN max_students INTEGER DEFAULT 30", "users.max_students"),
        ("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0", "users.failed_attempts"),
        ("ALTER TABLE users ADD COLUMN last_login TEXT", "users.last_login"),
        ("ALTER TABLE users ADD COLUMN reset_token TEXT", "users.reset_token"),
        ("ALTER TABLE users ADD COLUMN reset_token_expiry TEXT", "users.reset_token_expiry"),

        # Students table additions
        ("ALTER TABLE students ADD COLUMN email TEXT", "students.email"),
        ("ALTER TABLE students ADD COLUMN department TEXT", "students.department"),

        # Sessions table additions
        ("ALTER TABLE sessions ADD COLUMN role TEXT", "sessions.role"),
        ("ALTER TABLE sessions ADD COLUMN department TEXT", "sessions.department"),
        ("ALTER TABLE sessions ADD COLUMN name TEXT", "sessions.name"),

        # Tests table additions
        ("ALTER TABLE tests ADD COLUMN semester TEXT DEFAULT ''", "tests.semester"),
        ("ALTER TABLE tests ADD COLUMN total_students INTEGER DEFAULT 0", "tests.total_students"),

        # Marks table additions
        ("ALTER TABLE marks ADD COLUMN marks_json TEXT DEFAULT '{}'", "marks.marks_json"),
        ("ALTER TABLE marks ADD COLUMN total REAL DEFAULT 0", "marks.total"),
    ]

    for sql, desc in migrations:
        try:
            cursor.execute(sql)
            print(f"  ✅ Added: {desc}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  ⏭️ Already exists: {desc}")
            else:
                print(f"  ❌ Failed: {desc} — {e}")

    # Create missing tables
    tables = [
        ("""CREATE TABLE IF NOT EXISTS format_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            format_type TEXT DEFAULT 'text',
            description TEXT DEFAULT '',
            icon TEXT DEFAULT '📄',
            is_active INTEGER DEFAULT 1,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""", "format_settings"),
        ("""CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )""", "config"),
        ("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            counselor_email TEXT,
            reg_no TEXT,
            student_name TEXT,
            phone TEXT,
            format TEXT,
            status TEXT DEFAULT 'sent',
            sent_at TEXT DEFAULT (datetime('now'))
        )""", "messages"),
        ("""CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#667eea',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )""", "departments"),
    ]

    for sql, name in tables:
        try:
            cursor.execute(sql)
            print(f"  ✅ Table ensured: {name}")
        except Exception as e:
            print(f"  ❌ Table error ({name}): {e}")

    # Insert default formats if empty
    cursor.execute("SELECT COUNT(*) FROM format_settings")
    if cursor.fetchone()[0] == 0:
        default_formats = [
            ("WhatsApp Text", "whatsapp", "Plain text message via WhatsApp", "💬", 1, 1),
            ("PDF Report", "pdf", "PDF report card with marks table", "📄", 1, 0),
            ("Image Report", "image", "Visual report card image", "🖼️", 1, 0),
        ]
        cursor.executemany(
            "INSERT INTO format_settings (name, format_type, description, icon, is_active, is_default) VALUES (?,?,?,?,?,?)",
            default_formats
        )
        print("  ✅ Inserted default formats")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    print("🔄 Running RMKCET Parent Connect DB Migration...\n")
    migrate()
