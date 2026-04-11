import sqlite3

db_path = r"c:\Users\HP\OneDrive\Desktop\college project\rmkcet-parent-connect\rmkcet-parent-connect\backend\data\rmkcet.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute('SELECT name, email, is_locked, is_active FROM users ORDER BY name').fetchall()

print("\n" + "="*100)
print("DATABASE DEBUG - Checking is_locked values")
print("="*100)

for r in rows:
    is_locked_val = r['is_locked']
    is_locked_type = type(is_locked_val).__name__
    print(f"Name: {r['name']:<20} | is_locked={is_locked_val} (type:{is_locked_type}) | is_active={r['is_active']}")

print("="*100 + "\n")

conn.close()
