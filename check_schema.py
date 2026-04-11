import sqlite3

db_path = r"c:\Users\HP\OneDrive\Desktop\college project\rmkcet-parent-connect\rmkcet-parent-connect\backend\data\rmkcet.db"
conn = sqlite3.connect(db_path)

# Get table schema
schema = conn.execute("PRAGMA table_info(users)").fetchall()
print("\n" + "="*80)
print("DATABASE SCHEMA - users table")
print("="*80)
print(f"{'ID':<5} {'Name':<20} {'Type':<15} {'Not Null':<10} {'Default':<10} {'PK'}")
print("-"*80)
for row in schema:
    print(f"{row[0]:<5} {row[1]:<20} {row[2]:<15} {str(row[3]):<10} {str(row[4]):<10} {row[5]}")

#Now check actual data
print("\n" + "="*80)
print("ACTUAL DATA - First user record")
print("="*80)
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
if user:
    for key in user.keys():
        print(f"{key:<20} = {user[key]}")

conn.close()
print("="*80 + "\n")
