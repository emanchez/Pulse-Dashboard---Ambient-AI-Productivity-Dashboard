"""migrate_sqlite_to_pg.py — Migrate all data from local SQLite dev.db to Neon PostgreSQL.

Usage:
    # Full migration
    python scripts/migrate_sqlite_to_pg.py \\
        --sqlite-path data/dev.db \\
        --pg-url "postgresql://user:pass@host/db?sslmode=require"

    # Validate only (compare row counts, no writes)
    python scripts/migrate_sqlite_to_pg.py \\
        --sqlite-path data/dev.db \\
        --pg-url "postgresql://user:pass@host/db?sslmode=require" \\
        --validate-only

The --pg-url accepts any postgresql:// or postgresql+asyncpg:// format.
channel_binding=require is stripped automatically (asyncpg does not support it).

Tables are migrated in FK-dependency order:
  1. users               (no dependencies)
  2. tasks               (→ users)
  3. action_logs         (→ users, tasks)
  4. session_logs        (→ users, tasks)
  5. manual_reports      (→ users)
  6. system_states       (→ users)
  7. ai_usage_logs       (→ users)
  8. synthesis_reports   (→ users)

All inserts use ON CONFLICT (id) DO NOTHING for idempotency — safe to re-run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


# ── Tables in FK-safe insertion order ────────────────────────────────────────

TABLES: list[str] = [
    "users",
    "tasks",
    "action_logs",
    "session_logs",
    "manual_reports",
    "system_states",
    "ai_usage_logs",
    "synthesis_reports",
]

# Boolean columns in each table — SQLite stores as 0/1 integers.
BOOL_COLS: dict[str, set[str]] = {
    "users":             {"is_active"},
    "tasks":             {"is_completed"},
    "action_logs":       set(),
    "session_logs":      set(),
    "manual_reports":    set(),
    "system_states":     {"requires_recovery"},
    "ai_usage_logs":     {"was_mocked"},
    "synthesis_reports": set(),
}

# JSON TEXT columns in each table — SQLite stores as TEXT, PostgreSQL as JSON.
JSON_COLS: dict[str, set[str]] = {
    "manual_reports":    {"associated_task_ids", "tags"},
    "synthesis_reports": {"suggested_tasks"},
}


# ── URL helpers ───────────────────────────────────────────────────────────────

def _normalize_for_asyncpg(url: str) -> str:
    """Convert any SQLAlchemy-flavoured URL to a bare postgresql:// DSN for asyncpg.

    - postgresql+asyncpg:// → postgresql://
    - postgres://            → postgresql://
    - Strips channel_binding (libpq-only; asyncpg raises on unknown params)
    """
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://"):]
    elif url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if "channel_binding" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params.pop("channel_binding", None)
        new_query = urlencode({k: vals[0] for k, vals in params.items()})
        url = urlunparse(parsed._replace(query=new_query))
    return url


# ── Type conversion ───────────────────────────────────────────────────────────

def _convert_row(
    row: dict[str, Any],
    table: str,
) -> dict[str, Any]:
    """Convert SQLite raw values to Python types that asyncpg understands."""
    bool_cols = BOOL_COLS.get(table, set())
    json_cols = JSON_COLS.get(table, set())
    out: dict[str, Any] = {}

    for col, val in row.items():
        if val is None:
            out[col] = None
            continue

        # Boolean: SQLite stores 0/1 as int
        if col in bool_cols:
            out[col] = bool(val)
            continue

        # JSON TEXT → keep as serialized JSON string (asyncpg json columns expect a str)
        if col in json_cols:
            if isinstance(val, str):
                try:
                    # Validate it parses, then re-dump with consistent formatting
                    parsed = json.loads(val)
                    out[col] = json.dumps(parsed)
                except (json.JSONDecodeError, ValueError):
                    out[col] = val  # pass raw string on failure
            elif isinstance(val, (list, dict)):
                out[col] = json.dumps(val)
            else:
                out[col] = val
            continue

        # Datetime strings: parse to datetime object for asyncpg
        if isinstance(val, str) and col in (
            "created_at", "updated_at", "timestamp", "started_at", "ended_at",
            "deadline", "start_date", "end_date", "period_start", "period_end",
        ):
            try:
                out[col] = datetime.fromisoformat(val)
            except ValueError:
                out[col] = val  # pass raw if format unexpected
            continue

        out[col] = val

    return out


# ── SQLite reader ─────────────────────────────────────────────────────────────

def _read_sqlite_table(sqlite_path: str, table: str) -> list[dict[str, Any]]:
    """Return all rows from a SQLite table as a list of dicts."""
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(f"SELECT * FROM {table}")  # noqa: S608 — internal tool
        rows = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError as exc:
        print(f"  ⚠  Table '{table}' not found in SQLite — skipping. ({exc})")
        rows = []
    finally:
        conn.close()
    return rows


def _count_sqlite_table(sqlite_path: str, table: str) -> int:
    conn = sqlite3.connect(sqlite_path)
    try:
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
    except sqlite3.OperationalError:
        count = 0
    finally:
        conn.close()
    return count


# ── PostgreSQL writer ─────────────────────────────────────────────────────────

async def _insert_rows_pg(
    conn,
    table: str,
    rows: list[dict[str, Any]],
) -> int:
    """Insert rows into a PostgreSQL table using ON CONFLICT (id) DO NOTHING."""
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
    col_list = ", ".join(f'"{c}"' for c in columns)
    sql = (
        f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders}) '
        f"ON CONFLICT (id) DO NOTHING"
    )

    inserted = 0
    for raw_row in rows:
        converted = _convert_row(raw_row, table)
        values = [converted[c] for c in columns]
        try:
            await conn.execute(sql, *values)
            inserted += 1
        except Exception as exc:  # noqa: BLE001 — surface per-row errors without aborting
            print(f"  ⚠  Row insert failed in '{table}' (id={raw_row.get('id')}): {exc}")

    return inserted


async def _count_pg_table(conn, table: str) -> int:
    row = await conn.fetchrow(f'SELECT COUNT(*) AS n FROM "{table}"')  # noqa: S608
    return row["n"]


# ── Main migration ────────────────────────────────────────────────────────────

async def migrate(sqlite_path: str, pg_url: str, validate_only: bool) -> bool:
    """Run the migration or validation. Returns True if all checks pass."""
    import asyncpg  # imported here so the module is importable without asyncpg installed

    dsn = _normalize_for_asyncpg(pg_url)
    conn = await asyncpg.connect(dsn=dsn)

    try:
        all_ok = True

        if validate_only:
            print("\n── Validation (row count comparison) ──────────────────────────────")
            print(f"{'Table':<24} {'SQLite':>8} {'PostgreSQL':>12}  Status")
            print("─" * 58)
            for table in TABLES:
                sq = _count_sqlite_table(sqlite_path, table)
                pg = await _count_pg_table(conn, table)
                status = "✓" if sq == pg else "✗ MISMATCH"
                print(f"  {table:<22} {sq:>8} {pg:>12}  {status}")
                if sq != pg:
                    all_ok = False
            print()
            return all_ok

        # Full migration
        print("\n── Migration ───────────────────────────────────────────────────────")
        for table in TABLES:
            rows = _read_sqlite_table(sqlite_path, table)
            if not rows:
                print(f"  {table:<22}  0 rows (empty — skipped)")
                continue
            inserted = await _insert_rows_pg(conn, table, rows)
            print(f"  {table:<22}  {len(rows)} rows → {inserted} inserted (ON CONFLICT DO NOTHING)")

        # Post-migration validation
        print("\n── Post-migration validation ──────────────────────────────────────")
        print(f"{'Table':<24} {'SQLite':>8} {'PostgreSQL':>12}  Status")
        print("─" * 58)
        for table in TABLES:
            sq = _count_sqlite_table(sqlite_path, table)
            pg = await _count_pg_table(conn, table)
            status = "✓" if sq == pg else "✗ MISMATCH"
            print(f"  {table:<22} {sq:>8} {pg:>12}  {status}")
            if sq != pg:
                all_ok = False
        print()
        return all_ok

    finally:
        await conn.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite dev.db to Neon PostgreSQL."
    )
    parser.add_argument(
        "--sqlite-path",
        default="data/dev.db",
        help="Path to the SQLite database file (default: data/dev.db)",
    )
    parser.add_argument(
        "--pg-url",
        required=True,
        help=(
            "PostgreSQL connection string. Accepts postgresql://, "
            "postgresql+asyncpg://, or postgres:// formats."
        ),
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Compare row counts only — no data is written.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    success = asyncio.run(
        migrate(
            sqlite_path=args.sqlite_path,
            pg_url=args.pg_url,
            validate_only=args.validate_only,
        )
    )
    if not success:
        print("Migration completed with mismatches — review output above.")
        sys.exit(1)
    else:
        action = "Validation" if args.validate_only else "Migration"
        print(f"{action} completed successfully ✓")
        sys.exit(0)
