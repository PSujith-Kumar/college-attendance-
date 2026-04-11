import sqlite3

db_path = r"c:\Users\HP\OneDrive\Desktop\college project\rmkcet-parent-connect\rmkcet-parent-connect\backend\data\rmkcet.db"
conn = sqlite3.connect(db_path)

# Lock the first counselor for testing
conn.execute("UPDATE users SET is_locked=1 WHERE email='chandipriya@rmkcet.ac.in'")
conn.commit()

# Check the result
conn.row_factory = sqlite3.Row
users = conn.execute("SELECT name, email, is_locked FROM users ORDER BY name").fetchall()
print("\n" + "="*70)
print("UPDATED USER STATUS")
print("="*70)
for u in users:
    status = "INACTIVE ✓ (LOCKED)" if u['is_locked'] else "ACTIVE ✓ (NOT LOCKED)"
    print(f"{u['name']:<25} | {status}")
print("="*70 + "\n")

conn.close()
