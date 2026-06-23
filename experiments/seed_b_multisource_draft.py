"""Deterministic seed generator for the multi-source archetype-B worked example.

Produces the 'Contract countersigned' email rows that the worked instance
b-med-ms1 combines with the CRM opportunities table. Sweep-all design: the
two sources (CRM + Mail) are both knowable from the question.

The referenced opportunity set is chosen deterministically (seed=42) from the
current CRM seed: six WON opportunities (the answer set) plus three NOT-WON
opportunities (distractors that the CRM is_won filter must exclude). Eight
further won opportunities are intentionally left unreferenced so the mail
filter is also necessary.

This is a draft: it does not yet mutate seed_crm.py or crm.db. It emits the
email rows as JSON so they can be reviewed before promotion into the main seed.

Run:
    python experiments/seed_b_multisource_draft.py
"""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = REPO / "data" / "crm.db"
OUT = REPO / "data" / "test_inputs" / "b_structured_retrieval" / "_multisource_draft" / "countersigned_emails.json"

#: Stable internal-confirmation sender/recipient (agent mailbox).
SENDER = "legal@atlas.com"
RECIPIENT = "agent01@atlas.com"


def select_referenced(conn: sqlite3.Connection) -> tuple[list[int], list[int]]:
    """Deterministically pick referenced won opps (answer) and not-won distractors."""
    conn.row_factory = sqlite3.Row
    won = [r["id"] for r in conn.execute("SELECT id FROM opportunities WHERE is_won=1 ORDER BY id")]
    notwon = [r["id"] for r in conn.execute("SELECT id FROM opportunities WHERE is_won=0 ORDER BY id")]
    rng = random.Random(42)
    signed_won = sorted(rng.sample(won, 6))
    signed_distractor = sorted(rng.sample(notwon, 3))
    return signed_won, signed_distractor


def build_emails(conn: sqlite3.Connection) -> list[dict]:
    """Build the 'Contract countersigned' email rows referencing chosen opps."""
    conn.row_factory = sqlite3.Row
    names = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM opportunities")}
    signed_won, signed_distractor = select_referenced(conn)
    referenced = signed_won + signed_distractor
    emails = []
    # Draft id range 1001+ to avoid collision with the existing mailbox baseline.
    for offset, opp_id in enumerate(sorted(referenced)):
        emails.append(
            {
                "id": 1001 + offset,
                "sender": SENDER,
                "recipient": RECIPIENT,
                "subject": "Contract countersigned",
                "body": f"Contract countersigned for {names[opp_id]}. Fully executed copy is on file.",
                "sent_at": "2025-08-15T10:00:00",
                "status": "inbox",
            }
        )
    return emails


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        emails = build_emails(conn)
    finally:
        conn.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(emails, indent=2))
    print(f"wrote {len(emails)} countersigned emails to {OUT}")
    for e in emails:
        print(f"  id={e['id']} body={e['body']}")


if __name__ == "__main__":
    main()
