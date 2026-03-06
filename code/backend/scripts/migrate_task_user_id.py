"""
Migration: add user_id column to tasks table and backfill with the first user's ID.

Safe to run multiple times (idempotent).

Usage (from code/backend/):
    python scripts/migrate_task_user_id.py
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dev.db")


def run() -> None:
    if not os.path.exists(DB_PATH):
        print(f"[migrate] database not found at {DB_PATH} — nothing to do.")
        sys.exit(0)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Check whether user_id column already exists
    cur.execute("PRAGMA table_info(tasks)")
    columns = {row[1] for row in cur.fetchall()}

    if "user_id" not in columns:
        print("[migrate] adding user_id column to tasks …")
        cur.execute("ALTER TABLE tasks ADD COLUMN user_id VARCHAR(36)")
        con.commit()
        print("[migrate] column added.")
    else:
        print("[migrate] user_id column already exists, skipping ALTER TABLE.")

    # Fetch the first user's id to use as the backfill value
    cur.execute("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("[migrate] no users found in the database — cannot backfill. Create a user first.")
        con.close()
        sys.exit(1)

    first_user_id = row[0]

    # Backfill tasks that still have NULL user_id
    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id IS NULL")
    null_count = cur.fetchone()[0]

    if null_count == 0:
        print("[migrate] no tasks with NULL user_id — backfill not required.")
    else:
        cur.execute("UPDATE tasks SET user_id = ? WHERE user_id IS NULL", (first_user_id,))
        con.commit()
        print(f"[migrate] backfilled {null_count} task(s) with user_id={first_user_id}.")

    con.close()
    print("[migrate] done.")


if __name__ == "__main__":
    run()
