"""Create the local SQLite database and load the seed data.

Reads data/schema/schema.sql to create the tables and loads the JSON seed
files produced by experiments/seed_crm.py. Booleans are stored as integers
(0/1), the SQLite convention. Idempotent: the schema drops and recreates the
tables on each run.

Run:
    python experiments/seed_crm.py   # generate seed JSON first
    python experiments/load_db.py    # build data/crm.db
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = REPO / "data" / "crm.db"
SCHEMA_SQL = REPO / "data" / "schema" / "schema.sql"
SEED_DIR = REPO / "data" / "schema" / "seed"

TABLES = ["accounts", "contacts", "agents", "cases", "opportunities", "emails", "events"]


def _coerce(value: object) -> object:
    """Convert Python booleans to SQLite integers; pass others through."""
    if isinstance(value, bool):
        return int(value)
    return value


def load() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL.read_text())
        for table in TABLES:
            rows = json.loads((SEED_DIR / f"{table}.json").read_text())
            if not rows:
                continue
            columns = list(rows[0].keys())
            placeholders = ", ".join("?" for _ in columns)
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            conn.executemany(
                sql, [[_coerce(row[c]) for c in columns] for row in rows]
            )
            print(f"loaded {table}: {len(rows)} rows")
        conn.commit()
    finally:
        conn.close()
    print(f"database written to {DB_PATH}")


if __name__ == "__main__":
    load()
