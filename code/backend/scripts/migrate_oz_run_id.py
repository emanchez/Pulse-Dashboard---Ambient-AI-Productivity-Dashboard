"""Migrate oz_run_id → llm_run_id on synthesis_reports and ai_usage_logs.

Phase 4.1.2 — OZ Replacement: renames the oz_run_id column on both
affected tables to llm_run_id.

Safe to re-run (checks column existence before altering).
Requires SQLite >= 3.26 for RENAME COLUMN support.

Usage (from code/backend/):
    python scripts/migrate_oz_run_id.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dev.db")


def migrate(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"  DB not found at {db_path} — nothing to migrate.")
        return

    # Check SQLite version supports RENAME COLUMN (>= 3.26.0)
    ver = sqlite3.sqlite_version_info
    if ver < (3, 26, 0):
        print(
            f"  ERROR: SQLite {sqlite3.sqlite_version} does not support RENAME COLUMN "
            "(requires >= 3.26). Manually recreate the table as a fallback."
        )
        sys.exit(1)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    for table in ("synthesis_reports", "ai_usage_logs"):
        cols = {row[1] for row in cur.execute(f"PRAGMA table_info({table})")}
        if not cols:
            print(f"  {table}: table does not exist — skipping.")
            continue

        if "llm_run_id" in cols and "oz_run_id" not in cols:
            print(f"  {table}: already migrated (llm_run_id present, oz_run_id absent) — skipping.")
        elif "oz_run_id" in cols and "llm_run_id" not in cols:
            cur.execute(f"ALTER TABLE {table} RENAME COLUMN oz_run_id TO llm_run_id")
            print(f"  {table}: renamed oz_run_id → llm_run_id ✓")
        elif "oz_run_id" in cols and "llm_run_id" in cols:
            print(
                f"  {table}: BOTH oz_run_id and llm_run_id present — "
                "manual cleanup required. Leaving as-is."
            )
        else:
            print(f"  {table}: neither oz_run_id nor llm_run_id found — schema unexpected, skipping.")

    con.commit()
    con.close()


if __name__ == "__main__":
    print(f"Migrating oz_run_id → llm_run_id...")
    print(f"DB: {os.path.abspath(DB_PATH)}")
    migrate(DB_PATH)
    print("Migration complete.")
