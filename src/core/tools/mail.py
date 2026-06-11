"""Simulated mail tools for archetype F (and any archetype that needs mail).

Mirrors the operations and payload shape of the Gmail API and the WorkBench
mailbox sandbox (Styles et al., 2024), backed by the local SQLite ``emails``
table. Each tool adds the protocol's synthetic latency (Appendix A.5) so the
wall-clock latency reflects the order of magnitude of real-API round trips.

Storage semantics on the underlying SQLite row:
    status='inbox'   → Gmail labelIds: ['INBOX', 'UNREAD']
    status='outbox'  → Gmail labelIds: ['SENT']
    status='deleted' → Gmail labelIds: ['TRASH']

Payload-realism note (Phase 2 protocol, Section 5 / Layer 2): tool responses
are shaped as Gmail message resources (Gmail API v1) rather than as raw
mailbox rows, so the per-call payload verbosity reflects what a production
Mail integration would emit and the token-cost comparison between paradigms
is not biased by sparse outputs. Body data is base64url-encoded as in Gmail;
``snippet`` carries the first 200 plaintext characters for searchability.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any

from langchain_core.tools import tool

from src.core.db import get_connection
from src.core.tools._latency import synthetic_delay

#: Default sender for ``send_email`` if no sender is specified. The "current
#: user" of the simulated mailbox. F instances that send on behalf of a
#: specific agent pass the ``sender`` argument explicitly.
DEFAULT_SENDER = "user@atlas.com"

#: Maximum length of the plain-text ``snippet`` field in a Gmail message,
#: matching Gmail's documented behavior (~200 chars).
_SNIPPET_LEN = 200


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _labels_for(status: str) -> list[str]:
    if status == "inbox":
        return ["INBOX", "UNREAD"]
    if status == "outbox":
        return ["SENT"]
    if status == "deleted":
        return ["TRASH"]
    return []


def _parse_sql_dt(s: str | None) -> datetime:
    """Parse a SQLite ``YYYY-MM-DD HH:MM:SS`` timestamp as a UTC datetime."""
    if not s:
        return datetime.now(timezone.utc)
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _to_gmail_message(row: dict[str, Any]) -> dict[str, Any]:
    """Wrap a SQLite ``emails`` row as a Gmail API message resource.

    The shape mirrors the Gmail API v1 ``users.messages`` resource so the
    LLM-facing payload verbosity is comparable to a real Gmail tool call
    (protocol Section 5, payload-realism requirement).
    """
    body_text = row.get("body") or ""
    body_bytes = body_text.encode("utf-8")
    body_b64 = base64.urlsafe_b64encode(body_bytes).decode("ascii").rstrip("=")
    sent_dt = _parse_sql_dt(row.get("sent_at"))
    internal_date_ms = str(int(sent_dt.timestamp() * 1000))
    msg_id = row["id"]
    return {
        "id": str(msg_id),
        "threadId": str(msg_id),
        "labelIds": _labels_for(row.get("status", "")),
        "snippet": body_text[:_SNIPPET_LEN],
        "historyId": str(msg_id),
        "internalDate": internal_date_ms,
        "payload": {
            "partId": "",
            "mimeType": "text/plain",
            "filename": "",
            "headers": [
                {"name": "From", "value": row.get("sender", "")},
                {"name": "To", "value": row.get("recipient", "")},
                {"name": "Subject", "value": row.get("subject", "")},
                {"name": "Date", "value": format_datetime(sent_dt)},
                {"name": "Message-ID", "value": f"<{msg_id}@atlas.local>"},
            ],
            "body": {
                "size": len(body_bytes),
                "data": body_b64,
            },
        },
        "sizeEstimate": len(body_bytes) + 300,
    }


def _fetch_row(conn, email_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, sender, recipient, subject, body, sent_at, status FROM emails WHERE id = ?",
        (email_id,),
    ).fetchone()
    return dict(row) if row is not None else None


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
        A Gmail API ``users.messages`` resource describing the sent message:
        ``{id, threadId, labelIds=['SENT'], snippet, payload{headers, body}, internalDate, sizeEstimate}``.
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
        row = _fetch_row(conn, cursor.lastrowid)
        return _to_gmail_message(row) if row else {"error": "insert failed"}
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
        A list of Gmail-shaped message resources, one per match. Each entry has
        the same shape as ``send_email``'s return value: ``{id, threadId,
        labelIds, snippet, historyId, internalDate, payload{partId, mimeType,
        filename, headers[5], body{size, data}}, sizeEstimate}``.
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
    sql = "SELECT id, sender, recipient, subject, body, sent_at, status FROM emails"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY sent_at DESC"
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        return [_to_gmail_message(dict(row)) for row in cursor.fetchall()]
    finally:
        conn.close()


@tool
def forward_email(email_id: int, recipient: str, sender: str = DEFAULT_SENDER) -> dict[str, Any]:
    """Forward an existing email to a new recipient.

    The original email is preserved; a new ``outbox`` row is created whose
    subject is the original prefixed with ``Fwd:`` and whose body is the
    original body.

    Returns:
        A Gmail-shaped message resource describing the forwarded copy.
    """
    synthetic_delay("forward_email", {"email_id": email_id, "recipient": recipient, "sender": sender})
    conn = get_connection()
    try:
        original = conn.execute(
            "SELECT id, sender, recipient, subject, body, sent_at, status FROM emails WHERE id = ?",
            (email_id,),
        ).fetchone()
        if original is None:
            return {"error": f"email {email_id} not found"}
        original = dict(original)
        subject = f"Fwd: {original['subject']}"
        sent_at = _now_iso()
        cursor = conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'outbox')",
            (sender, recipient, subject, original["body"], sent_at),
        )
        conn.commit()
        row = _fetch_row(conn, cursor.lastrowid)
        return _to_gmail_message(row) if row else {"error": "insert failed"}
    finally:
        conn.close()


@tool
def delete_email(email_id: int) -> dict[str, Any]:
    """Soft-delete an email by setting its status to 'deleted' (label TRASH).

    Returns:
        A minimal acknowledgement dict ``{"id": "...", "labelIds": ["TRASH"]}``
        matching Gmail's trash-operation response shape.
    """
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
        return {"id": str(email_id), "labelIds": ["TRASH"]}
    finally:
        conn.close()
