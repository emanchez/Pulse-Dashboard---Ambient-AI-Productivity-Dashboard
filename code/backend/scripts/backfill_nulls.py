"""Backfill NULL user_id and start_date values before schema hardening migration.

This script is idempotent — safe to run multiple times.
It:
  1. Finds the single dev user's id.
  2. Sets user_id on action_logs / system_states rows that have NULL user_id.
  3. Sets start_date = created_at on system_states rows that have NULL start_date.
  4. Sets orphaned task_id references to NULL (rows whose task_id points to a
     non-existent task) on action_logs and session_logs, so FK creation won't fail.

MUST run AFTER backing up dev.db:
    cp data/dev.db data/dev.db.pre-schema-hardening.bak
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# ── Resolve path ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # code/backend/
DB_PATH = BASE_DIR / "data" / "dev.db"

if not DB_PATH.exists():
    print(f"ERROR: database not found at {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

try:
    # ── 1. Find the single user ───────────────────────────────────────────────
    users = conn.execute("SELECT id FROM users").fetchall()
    if len(users) == 0:
        print("ERROR: No users found in the database. Run create_dev_user.py first.")
        sys.exit(1)
    if len(users) > 1:
        print(f"WARNING: {len(users)} users found. Using the first one.")
    user_id: str = users[0]["id"]
    print(f"Using user_id: {user_id}")

    # ── 2. Backfill action_logs.user_id ──────────────────────────────────────
    before = conn.execute("SELECT COUNT(*) FROM action_logs WHERE user_id IS NULL").fetchone()[0]
    if before > 0:
        conn.execute(
            "UPDATE action_logs SET user_id = ? WHERE user_id IS NULL",
            (user_id,),
        )
        after = conn.execute("SELECT COUNT(*) FROM action_logs WHERE user_id IS NULL").fetchone()[0]
        print(f"action_logs.user_id: {before} NULLs → {after} NULLs (updated {before - after} rows)")
    else:
        print("action_logs.user_id: no NULLs, nothing to do")

    # ── 3. Backfill system_states.user_id ────────────────────────────────────
    before = conn.execute("SELECT COUNT(*) FROM system_states WHERE user_id IS NULL").fetchone()[0]
    if before > 0:
        conn.execute(
            "UPDATE system_states SET user_id = ? WHERE user_id IS NULL",
            (user_id,),
        )
        after = conn.execute("SELECT COUNT(*) FROM system_states WHERE user_id IS NULL").fetchone()[0]
        print(f"system_states.user_id: {before} NULLs → {after} NULLs (updated {before - after} rows)")
    else:
        print("system_states.user_id: no NULLs, nothing to do")

    # ── 4. Backfill system_states.start_date ─────────────────────────────────
    before = conn.execute("SELECT COUNT(*) FROM system_states WHERE start_date IS NULL").fetchone()[0]
    if before > 0:
        conn.execute(
            "UPDATE system_states SET start_date = created_at WHERE start_date IS NULL"
        )
        after = conn.execute("SELECT COUNT(*) FROM system_states WHERE start_date IS NULL").fetchone()[0]
        print(f"system_states.start_date: {before} NULLs → {after} NULLs (updated {before - after} rows)")
    else:
        print("system_states.start_date: no NULLs, nothing to do")

    # ── 5. Null-out orphaned task_id on action_logs ──────────────────────────
    orphaned_al = conn.execute(
        "SELECT COUNT(*) FROM action_logs "
        "WHERE task_id IS NOT NULL AND task_id NOT IN (SELECT id FROM tasks)"
    ).fetchone()[0]
    if orphaned_al > 0:
        conn.execute(
            "UPDATE action_logs SET task_id = NULL "
            "WHERE task_id IS NOT NULL AND task_id NOT IN (SELECT id FROM tasks)"
        )
        print(f"action_logs.task_id: nulled {orphaned_al} orphaned references")
    else:
        print("action_logs.task_id: no orphaned references")

    # ── 6. Null-out orphaned task_id on session_logs ─────────────────────────
    orphaned_sl = conn.execute(
        "SELECT COUNT(*) FROM session_logs "
        "WHERE task_id IS NOT NULL AND task_id NOT IN (SELECT id FROM tasks)"
    ).fetchone()[0]
    if orphaned_sl > 0:
        conn.execute(
            "UPDATE session_logs SET task_id = NULL "
            "WHERE task_id IS NOT NULL AND task_id NOT IN (SELECT id FROM tasks)"
        )
        print(f"session_logs.task_id: nulled {orphaned_sl} orphaned references")
    else:
        print("session_logs.task_id: no orphaned references")

    conn.commit()
    print("\nBackfill complete — all NULLs resolved, orphaned FKs cleared.")

except Exception as exc:
    conn.rollback()
    print(f"ERROR: {exc}")
    raise
finally:
    conn.close()
