"""Shared local database (SQLite).

The experiment uses a self-contained SQLite database that ships in the
repository (``data/crm.db``), so the controlled experiments are fully
reproducible without provisioning any external service. From the perspective of
an agent or a workflow this is irrelevant: the database is reached only through
the tool interface in ``core/tools/database.py``. The storage backend is a
controlled implementation detail behind that boundary; the paradigm comparison
is unaffected by it. Real external services (Gmail, Calendar) are reserved for
the case study, where external-tool fidelity is part of the demonstration.
"""

import sqlite3
from pathlib import Path

#: Repository-local database file. Created by experiments/load_db.py.
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "crm.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with dict-like row access.

    Raises:
        FileNotFoundError: If the database has not been created yet.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run experiments/load_db.py first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
