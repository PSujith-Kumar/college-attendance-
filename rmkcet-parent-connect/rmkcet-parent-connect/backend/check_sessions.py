# check_sessions.py
"""Diagnostic script to check active sessions in the database."""
import sqlite3
import os
from config import DATABASE_FILE
from datetime import datetime


def check():
    if not os.path.exists(DATABASE_FILE):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM sessions ORDER BY last_activity DESC")
        sessions = cursor.fetchall()
    except Exception:
        print("No sessions table found.")
        conn.close()
        return

    if not sessions:
        print("No sessions in database.")
        conn.close()
        return

    print(f"\n📋 Total sessions: {len(sessions)}\n")
    print(f"{'Session ID':<12} {'Email':<30} {'Role':<10} {'Login':<20} {'Last Activity':<20} {'Status'}")
    print("-" * 110)

    for s in sessions:
        sid = dict(s).get('session_id', '?')[:10]
        email = dict(s).get('user_email', '?')
        role = dict(s).get('role', '?')
        login = dict(s).get('login_time', '?')
        last = dict(s).get('last_activity', '?')
        is_active = dict(s).get('is_active', 0)
        status = "🟢 Active" if is_active else "🔴 Ended"

        print(f"{sid:<12} {email:<30} {role:<10} {str(login):<20} {str(last):<20} {status}")

    conn.close()


if __name__ == "__main__":
    check()
