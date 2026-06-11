"""Simulated calendar tools for archetype F (and any archetype that needs calendar).

Mirrors the operations and payload shape of the Google Calendar API v3 and
the WorkBench calendar sandbox (Styles et al., 2024), backed by the local
SQLite ``events`` table. Each tool adds the protocol's synthetic latency
(Appendix A.5).

Storage semantics on the underlying SQLite row:
    status='confirmed' | 'tentative' | 'cancelled'/'deleted'

Payload-realism note (Phase 2 protocol, Section 5 / Layer 2): tool responses
are shaped as Google Calendar event resources rather than as raw event rows,
so the per-call payload verbosity reflects what a production Calendar
integration would emit and the token-cost comparison between paradigms is
not biased by sparse outputs. Attendees are exposed as a list of objects with
``email`` and ``responseStatus`` fields rather than as a comma-separated
string.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from src.core.db import get_connection
from src.core.tools._latency import synthetic_delay

DEFAULT_ORGANIZER = "user@atlas.com"


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _parse_sql_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _to_rfc3339(s: str | None) -> str:
    dt = _parse_sql_dt(s)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00") if dt else ""


def _normalize_attendees(attendees: list[str] | str) -> str:
    if isinstance(attendees, list):
        return ",".join(a.strip() for a in attendees if a.strip())
    return attendees.strip()


def _attendees_objects(attendees_csv: str | None) -> list[dict[str, Any]]:
    """Convert the stored comma-separated string to a list of attendee objects."""
    if not attendees_csv:
        return []
    out: list[dict[str, Any]] = []
    for a in attendees_csv.split(","):
        a = a.strip()
        if a:
            out.append({"email": a, "responseStatus": "needsAction"})
    return out


#: Map internal SQLite status to Google Calendar API status terminology.
_STATUS_API_MAP = {"deleted": "cancelled"}


def _to_calendar_event(row: dict[str, Any]) -> dict[str, Any]:
    """Wrap a SQLite ``events`` row as a Google Calendar event resource.

    The shape mirrors the Google Calendar API v3 ``events`` resource so the
    LLM-facing payload verbosity is comparable to a real Calendar tool call
    (protocol Section 5, payload-realism requirement). Storage status
    ``'deleted'`` is translated to the API value ``'cancelled'``.
    """
    event_id = row["id"]
    organizer = row.get("organizer_email") or DEFAULT_ORGANIZER
    storage_status = row.get("status", "confirmed")
    api_status = _STATUS_API_MAP.get(storage_status, storage_status)
    return {
        "kind": "calendar#event",
        "etag": f'"{event_id}-1"',
        "id": str(event_id),
        "status": api_status,
        "htmlLink": f"https://calendar.atlas.local/event?eid={event_id}",
        "created": _now_iso_utc(),
        "updated": _now_iso_utc(),
        "summary": row.get("name", ""),
        "creator": {"email": organizer, "self": True},
        "organizer": {"email": organizer, "self": True},
        "start": {"dateTime": _to_rfc3339(row.get("start_time")), "timeZone": "UTC"},
        "end": {"dateTime": _to_rfc3339(row.get("end_time")), "timeZone": "UTC"},
        "iCalUID": f"{event_id}-atlas.local",
        "sequence": 0,
        "attendees": _attendees_objects(row.get("attendees")),
        "recurringEventId": None,
        "eventType": "default",
    }


def _fetch_event(conn, event_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, name, organizer_email, attendees, start_time, end_time, status FROM events WHERE id = ?",
        (event_id,),
    ).fetchone()
    return dict(row) if row is not None else None


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
        A Google Calendar event resource describing the created event:
        ``{kind, etag, id, status, htmlLink, created, updated, summary,
        creator, organizer, start{dateTime, timeZone}, end{...}, iCalUID,
        sequence, attendees[{email, responseStatus}], recurringEventId,
        eventType}``.
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
        row = _fetch_event(conn, cursor.lastrowid)
        return _to_calendar_event(row) if row else {"error": "insert failed"}
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

    Returns:
        A list of Google Calendar event resources (same shape as the return
        value of ``create_event``), one per match.
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
    sql = "SELECT id, name, organizer_email, attendees, start_time, end_time, status FROM events"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY start_time ASC"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [_to_calendar_event(dict(row)) for row in cursor.fetchall()]
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
    """Update one or more fields of an existing event.

    Returns:
        The updated Google Calendar event resource, or ``{"error": ...}`` if
        the event was not found or no fields were specified.
    """
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
        row = _fetch_event(conn, event_id)
        return _to_calendar_event(row) if row else {"error": "fetch after update failed"}
    finally:
        conn.close()


@tool
def delete_event(event_id: int) -> dict[str, Any]:
    """Soft-delete an event by setting its status to 'cancelled'.

    Returns:
        A minimal acknowledgement dict ``{"id": "...", "status": "cancelled"}``
        matching the Google Calendar delete-operation response shape.
    """
    synthetic_delay("delete_event", {"event_id": event_id})
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE events SET status = 'deleted' WHERE id = ? AND status != 'deleted'",
            (event_id,),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"event {event_id} not found or already cancelled"}
        return {"id": str(event_id), "status": "cancelled"}
    finally:
        conn.close()
