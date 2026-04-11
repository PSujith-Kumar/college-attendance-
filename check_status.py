import sqlite3
import os

db_path = r"c:\Users\HP\OneDrive\Desktop\college project\rmkcet-parent-connect\rmkcet-parent-connect\backend\data\rmkcet.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute('SELECT name, email, is_locked, is_active FROM users ORDER BY name').fetchall()

print("\n" + "="*80)
print("USER STATUS (Based on is_locked field)")
print("="*80)
print(f"{'Name':<25} {'Email':<35} {'Status':<15}")
print("-"*80)

for r in rows:
    status = "INACTIVE" if r['is_locked'] else "ACTIVE"
    print(f"{r['name']:<25} {r['email']:<35} {status:<15}")

print("-"*80)
active_count = sum(1 for r in rows if not r['is_locked'])
inactive_count = sum(1 for r in rows if r['is_locked'])
print(f"Total: {len(rows)} | Active: {active_count} | Inactive: {inactive_count}")
print("="*80 + "\n")

conn.close()
