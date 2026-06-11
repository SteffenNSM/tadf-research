"""Simulated mail tools for archetype F (and any archetype that needs mail).

Mirrors the operations and payload shape of the Gmail API and the WorkBench
mailbox sandbox (Styles et al., 2024), backed by the local SQLite ``emails``
table. Each tool adds the protocol's synthetic latency (Appendix A.5) so the
wall-clock latency reflects the order of magnitude of real-API round trips.

Status semantics: ``inbox`` (received messages), ``outbox`` (sent messages),
``deleted`` (soft-deleted, kept for auditability). ``send_email`` creates an
``outbox`` row.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from src.core.db import get_connection
from src.core.tools._latency import synthetic_delay

#: Default sender for ``send_email`` if no sender is specified. The "current
#: user" of the simulated mailbox. F instances that send on behalf of a
#: specific agent pass the ``sender`` argument explicitly.
DEFAULT_SENDER = "user@atlas.com"


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def send_email(
    recipient: str,
    subject: str,
    body: str,
    sender: str = DEFAULT_SENDER,
) -> dict[str, Any]:
    """Send an email. Creates a new row in the mailbox with status 'outbox'.

    Args:
        recipient: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        sender: Sender email address. Defaults to the current user.

    Returns:
        A dict ``{"id": ..., "status": "outbox", "sent_at": "..."}`` describing
        the inserted row.
    """
    synthetic_delay("send_email", {"recipient": recipient, "subject": subject, "sender": sender})
    conn = get_connection()
    try:
        sent_at = _now_iso()
        cursor = conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'outbox')",
            (sender, recipient, subject, body, sent_at),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "status": "outbox", "sent_at": sent_at}
    finally:
        conn.close()


@tool
def search_emails(
    query: str = "",
    date_min: str | None = None,
    date_max: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Search the mailbox for emails matching the query and date range.

    The query is matched case-insensitively against the subject, body, and
    sender columns. All filters are AND-combined.

    Args:
        query: Substring to match in subject/body/sender. Empty matches all.
        date_min: Inclusive lower bound on ``sent_at`` (format ``YYYY-MM-DD``).
        date_max: Inclusive upper bound on ``sent_at``.
        status: Optional filter on status (``inbox``, ``outbox``, ``deleted``).

    Returns:
        A list of matching email rows as dictionaries.
    """
    synthetic_delay("search_emails", {"query": query, "date_min": date_min, "date_max": date_max, "status": status})
    clauses: list[str] = []
    params: list[Any] = []
    if query:
        like = f"%{query}%"
        clauses.append("(subject LIKE ? OR body LIKE ? OR sender LIKE ?)")
        params.extend([like, like, like])
    if date_min:
        clauses.append("sent_at >= ?")
        params.append(date_min)
    if date_max:
        clauses.append("sent_at <= ?")
        params.append(date_max + " 23:59:59")
    if status:
        clauses.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM emails"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY sent_at DESC"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@tool
def forward_email(email_id: int, recipient: str, sender: str = DEFAULT_SENDER) -> dict[str, Any]:
    """Forward an existing email to a new recipient.

    The original email is preserved; a new ``outbox`` row is created whose
    subject is the original prefixed with ``Fwd:`` and whose body is the
    original body.
    """
    synthetic_delay("forward_email", {"email_id": email_id, "recipient": recipient, "sender": sender})
    conn = get_connection()
    try:
        original = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
        if original is None:
            return {"error": f"email {email_id} not found"}
        subject = f"Fwd: {original['subject']}"
        sent_at = _now_iso()
        cursor = conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'outbox')",
            (sender, recipient, subject, original["body"], sent_at),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "status": "outbox", "sent_at": sent_at}
    finally:
        conn.close()


@tool
def delete_email(email_id: int) -> dict[str, Any]:
    """Soft-delete an email by setting its status to 'deleted'."""
    synthetic_delay("delete_email", {"email_id": email_id})
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE emails SET status = 'deleted' WHERE id = ? AND status != 'deleted'",
            (email_id,),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"email {email_id} not found or already deleted"}
        return {"id": email_id, "status": "deleted"}
    finally:
        conn.close()
