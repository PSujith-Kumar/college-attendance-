# reset.py
"""Reset utility - clears data from the database while keeping structure."""
import sqlite3
import os
import sys
from config import DATABASE_FILE


def reset_all():
    """Remove the entire database file and start fresh."""
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)
        print("✅ Database deleted. It will be recreated on next app start.")
    else:
        print("No database found.")


def reset_sessions():
    """Clear all sessions."""
    if not os.path.exists(DATABASE_FILE):
        print("No database found.")
        return
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()
    print("✅ All sessions cleared.")


def reset_marks():
    """Clear all marks and test data."""
    if not os.path.exists(DATABASE_FILE):
        print("No database found.")
        return
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("DELETE FROM marks")
    conn.execute("DELETE FROM tests")
    conn.commit()
    conn.close()
    print("✅ All marks and tests cleared.")


def reset_messages():
    """Clear all message logs."""
    if not os.path.exists(DATABASE_FILE):
        print("No database found.")
        return
    conn = sqlite3.connect(DATABASE_FILE)
    try:
        conn.execute("DELETE FROM messages")
        conn.commit()
        print("✅ All message logs cleared.")
    except Exception as e:
        print(f"Error: {e}")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset.py [all|sessions|marks|messages]")
        print("  all      - Delete entire database")
        print("  sessions - Clear active sessions")
        print("  marks    - Clear marks and test data")
        print("  messages - Clear message logs")
        sys.exit(1)

    action = sys.argv[1].lower()
    actions = {
        'all': reset_all,
        'sessions': reset_sessions,
        'marks': reset_marks,
        'messages': reset_messages,
    }

    if action in actions:
        confirm = input(f"⚠️ Reset '{action}'? Type YES to confirm: ")
        if confirm == "YES":
            actions[action]()
        else:
            print("Cancelled.")
    else:
        print(f"Unknown action: {action}")
