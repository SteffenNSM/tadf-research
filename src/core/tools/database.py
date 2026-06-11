"""Database tools shared by workflow nodes and agent loops.

Exposes read-only access to the CRM tables as LangChain tools so that both the
agent (LLM-directed invocation) and the workflow (deterministic invocation via
``read_table``) use the same access path. The backend is the local SQLite
database (``core/db.py``); from the LLM's perspective the data is reachable only
through these tools. Write access is not exposed here; state-changing operations
belong to the action-execution archetype (F).

Schema (mirrored from the CRMArena Salesforce object model, Huang et al., 2025):
    accounts(id, name, region, industry, type)
    contacts(id, account_id, name, email)
    agents(id, name, team, region)
    cases(id, account_id, agent_id, subject, issue_category, status, priority,
          created_at, closed_at, transfer_count)
    opportunities(id, account_id, owner_agent_id, name, amount, stage,
                  created_at, close_date, is_won)
"""

from typing import Any

from langchain_core.tools import tool

from src.core.db import get_connection

#: Tables that may be queried via the generic db_read/db_search tools (Layer 1
#: CRM access). Emails and events are intentionally excluded: those are Layer 2
#: simulated services whose payload-realism contract (Phase 2 protocol,
#: Section 5) is enforced by the dedicated mail/calendar tools. Letting the
#: generic db_read return raw mailbox or calendar rows would bypass the
#: Gmail/Calendar response shape and bias the token-cost comparison.
ALLOWED_TABLES = {"accounts", "contacts", "agents", "cases", "opportunities"}

#: Tables that may be updated via ``db_update`` (write access for archetype F).
#: Mail and calendar use their dedicated tools rather than generic db_update,
#: keeping their domain semantics and synthetic latency in one place.
UPDATABLE_TABLES = {"accounts", "contacts", "agents", "cases", "opportunities"}

#: Columns that may be updated per table. Restricts writes to fields whose
#: change makes sense in F's action-execution tasks.
UPDATABLE_COLUMNS = {
    "cases": {"status", "priority", "agent_id", "transfer_count", "closed_at"},
    "opportunities": {"stage", "amount", "is_won", "owner_agent_id"},
    "contacts": {"email", "name"},
    "agents": {"team", "region"},
    "accounts": {"region", "industry", "type"},
}


def read_table(table: str, filters: dict[str, Any] | None = None) -> list[dict]:
    """Read rows from a table, optionally filtered by exact-match values.

    Direct (non-tool) reader used by deterministic workflow nodes and by the
    query executor. Returns all columns of all matching rows as dictionaries.

    Raises:
        ValueError: If the table name is not in the allowed set.
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table}")
    sql = f"SELECT * FROM {table}"
    params: list[Any] = []
    if filters:
        clauses = []
        for column, value in filters.items():
            clauses.append(f"{column} = ?")
            params.append(value)
        sql += " WHERE " + " AND ".join(clauses)
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@tool
def db_read(table: str, filters: dict[str, Any] | None = None) -> list[dict]:
    """Read rows from a CRM table, optionally filtered by exact-match columns.

    Available tables and columns:
        accounts(id, name, region, industry, type)
        contacts(id, account_id, name, email)
        agents(id, name, team, region)
        cases(id, account_id, agent_id, subject, issue_category, status,
              priority, created_at, closed_at, transfer_count)
        opportunities(id, account_id, owner_agent_id, name, amount, stage,
                      created_at, close_date, is_won)

    Args:
        table: One of the table names above.
        filters: Optional exact-match filters as column-value pairs, for
            example {"status": "Open"} or {"region": "EMEA"}.

    Returns:
        A list of matching rows as dictionaries.
    """
    return read_table(table, filters)


@tool
def db_search(table: str, column: str, query: str) -> list[dict]:
    """Search a table for rows where a column contains the query substring.

    Case-insensitive partial match. Use for free-text columns such as
    ``name`` or ``subject`` when an exact filter is not appropriate.

    Args:
        table: The table to search.
        column: The column to match against.
        query: The substring to look for.

    Returns:
        A list of matching rows as dictionaries.
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table}")
    sql = f"SELECT * FROM {table} WHERE {column} LIKE ? COLLATE NOCASE"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, [f"%{query}%"])
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@tool
def db_update(table: str, record_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    """Update one or more fields of a row identified by its id.

    Use this for archetype F tasks that change CRM state (case status, agent
    assignment, opportunity stage, contact email, etc.). Mail and calendar
    state changes use the dedicated mail/calendar tools.

    Args:
        table: One of ``cases``, ``opportunities``, ``contacts``, ``agents``,
            or ``accounts``.
        record_id: The primary-key id of the row to update.
        updates: Column-value pairs to set. Only columns in the table's
            updatable-columns whitelist are allowed.

    Returns:
        A dict ``{"id": ..., "updated_fields": [...]}`` describing the change,
        or ``{"error": "..."}`` if the row was not found or a column was
        disallowed.
    """
    if table not in UPDATABLE_TABLES:
        return {"error": f"table {table!r} not updatable"}
    allowed = UPDATABLE_COLUMNS.get(table, set())
    bad = [c for c in updates if c not in allowed]
    if bad:
        return {"error": f"columns not updatable on {table}: {bad}"}
    if not updates:
        return {"error": "no fields to update"}
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params: list[Any] = list(updates.values()) + [record_id]
    conn = get_connection()
    try:
        cursor = conn.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", params)
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"{table} id {record_id} not found"}
        return {"id": record_id, "table": table, "updated_fields": list(updates.keys())}
    finally:
        conn.close()


@tool
def attempt_close_case(case_id: int, resolution_summary: str) -> dict[str, Any]:
    """Attempt to close a case with a resolution summary.

    The close operation is subject to internal business rules (for example
    escalation policies tied to transfer history); the rules are enforced by
    the back-end and not exposed via a read tool. On success the case status
    is set to 'Closed' and the close timestamp is recorded; on a policy
    rejection the case state is unchanged.

    Args:
        case_id: The primary-key id of the case to close.
        resolution_summary: Short free-text describing how the case was
            resolved; recorded with the close for audit purposes.

    Returns:
        On success: ``{"closed": True, "id": case_id}``.
        On rejection by an internal rule:
            ``{"closed": False, "reason": "<policy reason>"}``.
        The reason is the only signal that the close was blocked; callers
        must read it to decide on a follow-up action.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, status, transfer_count FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
        if row is None:
            return {"closed": False, "reason": f"case {case_id} not found"}
        if row["status"] == "Closed":
            return {"closed": False, "reason": "case is already closed"}
        # Internal escalation policy (intentionally not documented in the
        # schema): cases with a high recent transfer count are routed to
        # manual review and cannot be closed via this tool.
        if (row["transfer_count"] or 0) > 3:
            return {
                "closed": False,
                "reason": "case escalated for manual review; automatic close is not permitted",
            }
        conn.execute(
            "UPDATE cases SET status = 'Closed', closed_at = datetime('now') WHERE id = ?",
            (case_id,),
        )
        conn.commit()
        return {"closed": True, "id": case_id, "resolution_summary": resolution_summary[:80]}
    finally:
        conn.close()
