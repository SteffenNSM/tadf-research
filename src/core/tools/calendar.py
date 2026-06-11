"""Simulated calendar tools for archetype F (and any archetype that needs calendar).

Mirrors the operations and payload shape of the Google Calendar API and the
WorkBench calendar sandbox (Styles et al., 2024), backed by the local SQLite
``events`` table. Each tool adds the protocol's synthetic latency
(Appendix A.5).

Status semantics: ``confirmed`` (active event), ``deleted`` (soft-deleted),
``tentative`` (placeholder). ``attendees`` is a comma-separated string of
email addresses for portability with the WorkBench representation.
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from src.core.db import get_connection
from src.core.tools._latency import synthetic_delay

DEFAULT_ORGANIZER = "user@atlas.com"


def _normalize_attendees(attendees: list[str] | str) -> str:
    if isinstance(attendees, list):
        return ",".join(a.strip() for a in attendees if a.strip())
    return attendees.strip()


@tool
def create_event(
    name: str,
    start_time: str,
    end_time: str,
    attendees: list[str] | str,
    organizer_email: str = DEFAULT_ORGANIZER,
) -> dict[str, Any]:
    """Create a calendar event.

    Args:
        name: Event title.
        start_time: ISO timestamp, format ``YYYY-MM-DD HH:MM:SS``.
        end_time: ISO timestamp, format ``YYYY-MM-DD HH:MM:SS``.
        attendees: List of email addresses, or a comma-separated string.
        organizer_email: Event organizer. Defaults to the current user.

    Returns:
        A dict describing the inserted event row.
    """
    args = {"name": name, "start_time": start_time, "end_time": end_time, "organizer_email": organizer_email}
    synthetic_delay("create_event", args)
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO events (name, organizer_email, attendees, start_time, end_time, status) "
            "VALUES (?, ?, ?, ?, ?, 'confirmed')",
            (name, organizer_email, _normalize_attendees(attendees), start_time, end_time),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "status": "confirmed"}
    finally:
        conn.close()


@tool
def search_events(
    query: str = "",
    date_min: str | None = None,
    date_max: str | None = None,
    attendee: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Search the calendar for events matching the filters.

    The query matches case-insensitively against the event name. ``attendee``
    matches any email substring in the attendees field.
    """
    args = {"query": query, "date_min": date_min, "date_max": date_max, "attendee": attendee, "status": status}
    synthetic_delay("search_events", args)
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        clauses.append("name LIKE ?")
        params.append(f"%{query}%")
    if date_min:
        clauses.append("start_time >= ?")
        params.append(date_min)
    if date_max:
        clauses.append("start_time <= ?")
        params.append(date_max + " 23:59:59")
    if attendee:
        clauses.append("attendees LIKE ?")
        params.append(f"%{attendee}%")
    if status:
        clauses.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY start_time ASC"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@tool
def update_event(
    event_id: int,
    name: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    attendees: list[str] | str | None = None,
) -> dict[str, Any]:
    """Update one or more fields of an existing event."""
    args = {"event_id": event_id, "name": name, "start_time": start_time, "end_time": end_time}
    synthetic_delay("update_event", args)
    updates: list[str] = []
    params: list[Any] = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if start_time is not None:
        updates.append("start_time = ?")
        params.append(start_time)
    if end_time is not None:
        updates.append("end_time = ?")
        params.append(end_time)
    if attendees is not None:
        updates.append("attendees = ?")
        params.append(_normalize_attendees(attendees))
    if not updates:
        return {"error": "no fields to update"}
    params.append(event_id)
    conn = get_connection()
    try:
        cursor = conn.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"event {event_id} not found"}
        return {"id": event_id, "updated_fields": [u.split(' =')[0] for u in updates]}
    finally:
        conn.close()


@tool
def delete_event(event_id: int) -> dict[str, Any]:
    """Soft-delete an event by setting its status to 'deleted'."""
    synthetic_delay("delete_event", {"event_id": event_id})
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE events SET status = 'deleted' WHERE id = ? AND status != 'deleted'",
            (event_id,),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"event {event_id} not found or already deleted"}
        return {"id": event_id, "status": "deleted"}
    finally:
        conn.close()
