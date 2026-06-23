"""Deterministic verification of the multi-source archetype-B worked example.

Mirrors what the WORKFLOW's deterministic execute node would do for b-med-ms1:
combine a CRM structured aggregate with a mail-derived set (sweep-all). The
LLM-facing plan node and the ReAct agent are not exercised here (no API egress
in the sandbox); this proves the deterministic core and the gold, exactly as
IT-004 did for single-source B.

Pipeline (the deterministic execute node):
  source CRM  : opportunities WHERE is_won = 1            -> {name: amount}
  source Mail : emails WHERE subject = 'Contract countersigned'
                -> parse body for 'Opportunity NNN'        -> {referenced names}
  combine     : sum amount over (won names INTERSECT referenced names)

The result is checked against an independent gold computed directly from the
known referenced-id set, so the executor is not graded against itself.

Run:
    python experiments/seed_b_multisource_draft.py   # writes the email rows
    python experiments/verify_b_multisource_draft.py
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = REPO / "data" / "crm.db"
DRAFT = REPO / "data" / "test_inputs" / "b_structured_retrieval" / "_multisource_draft"
EMAILS = DRAFT / "countersigned_emails.json"
INSTANCE = DRAFT / "b-med-ms1.json"

_OPP_RE = re.compile(r"Opportunity\s+\d+")


def load_emails(conn: sqlite3.Connection) -> list[dict]:
    """Return the mailbox the run sees: CRM baseline emails plus the draft rows."""
    conn.row_factory = sqlite3.Row
    base = [dict(r) for r in conn.execute("SELECT * FROM emails")]
    draft = json.loads(EMAILS.read_text()) if EMAILS.exists() else []
    return base + draft


def multisource_execute(conn: sqlite3.Connection) -> float:
    """The deterministic combine the workflow execute node performs."""
    conn.row_factory = sqlite3.Row
    # Source 1: CRM structured aggregate input — won opportunities.
    won = {r["name"]: r["amount"] for r in conn.execute(
        "SELECT name, amount FROM opportunities WHERE is_won = 1"
    )}
    # Source 2: Mail — names referenced by 'Contract countersigned' emails.
    referenced: set[str] = set()
    for e in load_emails(conn):
        if (e.get("subject") or "").strip().lower() == "contract countersigned":
            referenced.update(_OPP_RE.findall(e.get("body") or ""))
    # Combine: intersection, then sum amount.
    return float(sum(amt for name, amt in won.items() if name in referenced))


def independent_gold(conn: sqlite3.Connection) -> float:
    """Gold computed from the known referenced-id set, independent of the executor."""
    conn.row_factory = sqlite3.Row
    draft = json.loads(EMAILS.read_text())
    ids = []
    name_to_id = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM opportunities")}
    for e in draft:
        for m in _OPP_RE.findall(e["body"]):
            ids.append(name_to_id[m])
    rows = conn.execute(
        f"SELECT amount FROM opportunities WHERE is_won = 1 AND id IN ({','.join('?' * len(ids))})",
        ids,
    ).fetchall()
    return float(sum(r["amount"] for r in rows))


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        execed = multisource_execute(conn)
        gold = independent_gold(conn)
        stated = json.loads(INSTANCE.read_text())["ground_truth"]["value"]
    finally:
        conn.close()
    print(f"multi-source executor result : {execed:.0f}")
    print(f"independent gold (id-based)  : {gold:.0f}")
    print(f"instance stated gold         : {stated}")
    ok = execed == gold == float(stated)
    print(f"\n{'PASS' if ok else 'FAIL'}: executor == independent gold == stated gold")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
