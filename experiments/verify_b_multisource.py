"""Independent verification of the multi-source archetype-B corpus.

Rebuilds the four signal sets by PARSING the persisted Mail/Calendar rows in
crm.db (subject/body for mail, event name for calendar), recomputes every gold
with the same spec logic, and checks it against the gold written into each
instance file. This catches seeding, datetime-format, and parse bugs, because
the signals are reconstructed from the database the tools actually read, not
from the in-memory sets the seeder used.

Run (after seed + load_db):
    python experiments/seed_b_multisource.py
    python experiments/load_db.py
    python experiments/verify_b_multisource.py
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from experiments.seed_b_multisource import specs

REPO = Path(__file__).resolve().parents[1]
DB_PATH = REPO / "data" / "crm.db"
IN_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"

_OPP_RE = re.compile(r"Opportunity\s+\d+")
_SUBJECT_TO_SIG = {"Contract countersigned": "MC", "Payment received": "MP"}
_EVENT_TO_SIG = {"Closing call": "CC", "Kickoff scheduled": "CK"}


def parse_signals_from_db(conn: sqlite3.Connection) -> dict[str, set[int]]:
    """Reconstruct signal -> {opportunity id} by parsing emails and events."""
    conn.row_factory = sqlite3.Row
    name_to_id = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM opportunities")}
    sig: dict[str, set[int]] = {"MC": set(), "MP": set(), "CC": set(), "CK": set()}
    for r in conn.execute("SELECT subject, body FROM emails"):
        s = _SUBJECT_TO_SIG.get((r["subject"] or "").strip())
        if s:
            for m in _OPP_RE.findall(r["body"] or ""):
                sig[s].add(name_to_id[m])
    for r in conn.execute("SELECT name FROM events"):
        nm = r["name"] or ""
        for prefix, s in _EVENT_TO_SIG.items():
            if nm.startswith(prefix):
                for m in _OPP_RE.findall(nm):
                    sig[s].add(name_to_id[m])
    return sig


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT id, name, amount, is_won FROM opportunities ORDER BY id")]
    won = [r["id"] for r in rows if r["is_won"] == 1]
    notwon = [r["id"] for r in rows if r["is_won"] == 0]
    name = {r["id"]: r["name"] for r in rows}
    amount = {r["id"]: r["amount"] for r in rows}
    crm_counts = {
        "open_cases": conn.execute("SELECT count(*) FROM cases WHERE status='Open'").fetchone()[0],
        "emea_accounts": conn.execute("SELECT count(*) FROM accounts WHERE region='EMEA'").fetchone()[0],
        "won_count": len(won),
        "won_sum": float(sum(amount[i] for i in won)),
        "emea_agents": conn.execute("SELECT count(*) FROM agents WHERE team='EMEA'").fetchone()[0],
    }
    signals = parse_signals_from_db(conn)
    conn.close()

    rebuilt = specs(won, notwon, name, amount, signals, crm_counts)
    ok = True
    print(f"{'id':9} {'src':3} {'op':5} {'recomputed':>11} {'instance':>10}  ok")
    for diff, iid, _instr, gold_raw, op, sources in rebuilt:
        recomputed = int(round(gold_raw)) if op == "sum" else int(gold_raw)
        stated = json.loads((IN_DIR / diff / f"{iid}.json").read_text())["ground_truth"]["value"]
        match = recomputed == stated
        ok &= match
        print(f"{iid:9} {len(sources):3} {op:5} {recomputed:11} {stated:10}  {'OK' if match else 'MISMATCH'}")
    print(f"\n{'PASS' if ok else 'FAIL'}: all 15 instance golds reproduced from the database")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
