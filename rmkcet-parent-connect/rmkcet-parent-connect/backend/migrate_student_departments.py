import database as db


def main():
    conn = db.get_conn()
    before = conn.execute(
        "SELECT COUNT(*) FROM counselor_students WHERE COALESCE(TRIM(department), '') = ''"
    ).fetchone()[0]
    conn.close()

    db.ensure_counselor_student_departments()

    conn = db.get_conn()
    after = conn.execute(
        "SELECT COUNT(*) FROM counselor_students WHERE COALESCE(TRIM(department), '') = ''"
    ).fetchone()[0]
    conn.close()

    print(f"Missing department rows before: {before}")
    print(f"Missing department rows after: {after}")
    print(f"Backfilled rows: {before - after}")


if __name__ == "__main__":
    main()
