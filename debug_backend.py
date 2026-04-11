import sys
sys.path.insert(0, r'c:\Users\HP\OneDrive\Desktop\college project\rmkcet-parent-connect\rmkcet-parent-connect\backend')

import database as db

users = db.get_all_users()
print("\n" + "="*100)
print("Backend Data being returned to template:")
print("="*100)

for u in users[:3]:  # Just first 3 to see structure
    print(f"\nUser: {u.get('name')}")
    print(f"  Keys in dict: {list(u.keys())}")
    print(f"  is_locked: {u.get('is_locked')} (type: {type(u.get('is_locked')).__name__})")
    print(f"  is_active: {u.get('is_active')} (type: {type(u.get('is_active')).__name__})")

print("\n" + "="*100)
print("All users summary:")
print("="*100)
for u in users:
    print(f"{u.get('name'):<20} | is_locked={u.get('is_locked')} | is_active={u.get('is_active')}")

print("="*100 + "\n")
