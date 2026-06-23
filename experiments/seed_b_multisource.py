"""Master generator for the multi-source archetype-B corpus (15 instances).

Single source of truth. Reads the CRM seed, deterministically (seed=42) defines
four cross-source signals, emits the supporting Mail/Calendar rows into the seed
JSON, builds the 15 instance files, and computes every gold from the same
reference sets so instances and seeds are consistent by construction.

Difficulty axis = number of distinct sources that must be combined (sweep-all,
plan-time-decidable):
    Low  = 1 source  (CRM only)
    Med  = 2 sources (CRM + Mail, or CRM + Calendar)
    High = 3 sources (CRM + Mail + Calendar)

Signals (each references opportunities by name 'Opportunity NNN'):
    MC = Mail     subject 'Contract countersigned'
    MP = Mail     subject 'Payment received'
    CC = Calendar event   'Closing call'
    CK = Calendar event   'Kickoff scheduled'
Each signal references a subset of WON opportunities (answer-relevant) plus a
few NOT-WON opportunities (distractors the CRM is_won filter must exclude).

Run:
    python experiments/seed_b_multisource.py
    python experiments/load_db.py            # rebuild crm.db incl. the new rows
    python experiments/verify_b_multisource.py
"""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB_PATH = REPO / "data" / "crm.db"
SEED_DIR = REPO / "data" / "schema" / "seed"
IN_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"

ID_BASE = 1001  # B-signal rows live at id >= 1001, kept disjoint from the baseline

PROV = {
    "source_benchmark": "CRMArena structured querying (Huang et al., 2025) + WorkBench mailbox/calendar (Styles et al., 2024)",
    "construction_method": "Author-constructed multi-source sweep-all: a CRM structured set intersected with Mail/Calendar-derived sets; all sources knowable from the question (plan-time-decidable). Labelled honestly per IT-017.",
    "difficulty_axis": "number of distinct sources that must be combined",
    "license": "CC BY-NC 4.0",
}


def _opps(conn: sqlite3.Connection) -> tuple[list[dict], list[int], list[int], dict, dict]:
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT id, name, amount, is_won FROM opportunities ORDER BY id")]
    won = [r["id"] for r in rows if r["is_won"] == 1]
    notwon = [r["id"] for r in rows if r["is_won"] == 0]
    name = {r["id"]: r["name"] for r in rows}
    amount = {r["id"]: r["amount"] for r in rows}
    return rows, won, notwon, name, amount


def build_signals(won: list[int], notwon: list[int]) -> dict[str, set[int]]:
    """Deterministic reference sets per signal: won subset + not-won distractors."""
    rng = random.Random(42)
    def pick(pool: list[int], k: int) -> list[int]:
        return sorted(rng.sample(pool, k))
    return {
        "MC": set(pick(won, 8) + pick(notwon, 3)),
        "MP": set(pick(won, 8) + pick(notwon, 3)),
        "CC": set(pick(won, 7) + pick(notwon, 2)),
        "CK": set(pick(won, 6) + pick(notwon, 2)),
    }


def emit_seed_rows(signals: dict[str, set[int]], name: dict[int, str]) -> tuple[list[dict], list[dict]]:
    """Build Mail rows (MC, MP) and Calendar rows (CC, CK) referencing opp names.

    The mail reference lives in the body (search_emails matches subject/body and
    returns it in the snippet). The calendar reference must live in the event
    NAME, because search_events matches only the name and the events table has
    no free-text field. Datetimes use the canonical 'YYYY-MM-DD HH:MM:SS' form
    the mail/calendar tools parse.
    """
    emails, events, eid, vid = [], [], ID_BASE, ID_BASE
    mail_subject = {"MC": "Contract countersigned", "MP": "Payment received"}
    cal_name = {"CC": "Closing call", "CK": "Kickoff scheduled"}
    for sig, subject in mail_subject.items():
        for opp_id in sorted(signals[sig]):
            emails.append({
                "id": eid, "sender": "legal@atlas.com", "recipient": "agent01@atlas.com",
                "subject": subject,
                "body": f"{subject} for {name[opp_id]}. Reference on file.",
                "sent_at": "2025-08-15 10:00:00", "status": "inbox",
            })
            eid += 1
    for sig, evname in cal_name.items():
        for opp_id in sorted(signals[sig]):
            events.append({
                "id": vid, "name": f"{evname}: {name[opp_id]}",
                "organizer_email": "agent01@atlas.com",
                "attendees": "agent01@atlas.com,legal@atlas.com",
                "start_time": "2025-09-01 09:00:00", "end_time": "2025-09-01 09:30:00",
                "status": "confirmed",
            })
            vid += 1
    return emails, events


# ── Instance specifications (gold computed below from CRM + signals) ──
# Each spec: id, difficulty, instruction, and a `compute` callable returning gold.

def specs(won, notwon, name, amount, signals, crm_counts):
    won_s, notwon_s = set(won), set(notwon)
    def crm_won_sum(keys):  # sum amount over won opps in keys
        return float(sum(amount[i] for i in keys if i in won_s))
    def inter(*sigs):
        s = won_s
        for g in sigs:
            s = s & signals[g]
        return s

    return [
        # ── LOW: 1 source (CRM only) ──
        ("low", "b-low-1", "How many cases currently have status 'Open'? Answer with the count.",
         crm_counts["open_cases"], "count", ["CRM.cases"]),
        ("low", "b-low-2", "How many accounts are in the 'EMEA' region? Answer with the count.",
         crm_counts["emea_accounts"], "count", ["CRM.accounts"]),
        ("low", "b-low-3", "How many opportunities have been won (is_won = 1)? Answer with the count.",
         crm_counts["won_count"], "count", ["CRM.opportunities"]),
        ("low", "b-low-4", "What is the total amount (sum of 'amount') of all won opportunities (is_won = 1)? Answer with the number.",
         crm_counts["won_sum"], "sum", ["CRM.opportunities"]),
        ("low", "b-low-5", "How many agents are on the 'EMEA' team? Answer with the count.",
         crm_counts["emea_agents"], "count", ["CRM.agents"]),

        # ── MED: 2 sources ──
        ("med", "b-med-1",
         "What is the total amount (sum of 'amount') of WON opportunities (is_won = 1) whose contract was countersigned? "
         "A contract is countersigned only if an email with subject 'Contract countersigned' names the opportunity as 'Opportunity NNN' in its body. "
         "Answer with the total amount.",
         crm_won_sum(inter("MC")), "sum", ["CRM.opportunities", "Mail"]),
        ("med", "b-med-2",
         "How many WON opportunities (is_won = 1) have a 'Closing call' calendar event? "
         "An opportunity has one only if a calendar event named 'Closing call' names it as 'Opportunity NNN'. "
         "Answer with the count.",
         len(inter("CC")), "count", ["CRM.opportunities", "Calendar"]),
        ("med", "b-med-3",
         "What is the total amount (sum of 'amount') of WON opportunities (is_won = 1) for which a payment was received? "
         "A payment was received only if an email with subject 'Payment received' names the opportunity as 'Opportunity NNN'. "
         "Answer with the total amount.",
         crm_won_sum(inter("MP")), "sum", ["CRM.opportunities", "Mail"]),
        ("med", "b-med-4",
         "How many NOT-won opportunities (is_won = 0) have a 'Kickoff scheduled' calendar event? "
         "An opportunity has one only if a calendar event named 'Kickoff scheduled' names it as 'Opportunity NNN'. "
         "Answer with the count.",
         len((notwon_s) & signals["CK"]), "count", ["CRM.opportunities", "Calendar"]),
        ("med", "b-med-5",
         "How many WON opportunities (is_won = 1) had a payment received (email subject 'Payment received' naming them as 'Opportunity NNN')? "
         "Answer with the count.",
         len(inter("MP")), "count", ["CRM.opportunities", "Mail"]),

        # ── HIGH: 3 sources (CRM + Mail + Calendar) ──
        ("high", "b-high-1",
         "What is the total amount (sum of 'amount') of WON opportunities (is_won = 1) that were BOTH countersigned by email "
         "(subject 'Contract countersigned') AND have a 'Closing call' calendar event, each naming the opportunity as 'Opportunity NNN'? "
         "Answer with the total amount.",
         crm_won_sum(inter("MC", "CC")), "sum", ["CRM.opportunities", "Mail", "Calendar"]),
        ("high", "b-high-2",
         "How many WON opportunities (is_won = 1) were BOTH countersigned by email (subject 'Contract countersigned') "
         "AND have a 'Closing call' calendar event, each naming the opportunity as 'Opportunity NNN'? Answer with the count.",
         len(inter("MC", "CC")), "count", ["CRM.opportunities", "Mail", "Calendar"]),
        ("high", "b-high-3",
         "What is the total amount (sum of 'amount') of WON opportunities (is_won = 1) that had a payment received "
         "(email subject 'Payment received') AND a 'Kickoff scheduled' calendar event, each naming the opportunity as 'Opportunity NNN'? "
         "Answer with the total amount.",
         crm_won_sum(inter("MP", "CK")), "sum", ["CRM.opportunities", "Mail", "Calendar"]),
        ("high", "b-high-4",
         "How many WON opportunities (is_won = 1) were countersigned by email (subject 'Contract countersigned') "
         "AND have a 'Kickoff scheduled' calendar event, each naming the opportunity as 'Opportunity NNN'? Answer with the count.",
         len(inter("MC", "CK")), "count", ["CRM.opportunities", "Mail", "Calendar"]),
        ("high", "b-high-5",
         "What is the total amount (sum of 'amount') of WON opportunities (is_won = 1) that had a payment received "
         "(email subject 'Payment received') AND a 'Closing call' calendar event, each naming the opportunity as 'Opportunity NNN'? "
         "Answer with the total amount.",
         crm_won_sum(inter("MP", "CC")), "sum", ["CRM.opportunities", "Mail", "Calendar"]),
    ]


def _round_gold(value, op):
    return int(round(value)) if op == "sum" else int(value)


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows, won, notwon, name, amount = _opps(conn)
        conn.row_factory = sqlite3.Row
        crm_counts = {
            "open_cases": conn.execute("SELECT count(*) FROM cases WHERE status='Open'").fetchone()[0],
            "emea_accounts": conn.execute("SELECT count(*) FROM accounts WHERE region='EMEA'").fetchone()[0],
            "won_count": len(won),
            "won_sum": float(sum(amount[i] for i in won)),
            "emea_agents": conn.execute("SELECT count(*) FROM agents WHERE team='EMEA'").fetchone()[0],
        }
    finally:
        conn.close()

    signals = build_signals(won, notwon)
    emails, events = emit_seed_rows(signals, name)

    # 1) Append B-signal rows to the seed JSON (idempotent: drop prior id>=ID_BASE).
    for fname, new_rows in (("emails", emails), ("events", events)):
        path = SEED_DIR / f"{fname}.json"
        base = json.loads(path.read_text()) if path.exists() else []
        base = [r for r in base if r.get("id", 0) < ID_BASE]
        path.write_text(json.dumps(base + new_rows, indent=2))
        print(f"seed {fname}.json: {len(base)} baseline + {len(new_rows)} B-signal rows")

    # 2) Write the 15 instances with computed golds.
    units = {"sum": "currency", "count": "count"}
    written = []
    for diff, iid, instr, gold_raw, op, sources in specs(won, notwon, name, amount, signals, crm_counts):
        gold = _round_gold(gold_raw, op)
        inst = {
            "id": iid, "archetype": "B", "difficulty": diff,
            "instruction": instr,
            "ground_truth": {"value": gold, "unit": units[op]},
            "sources_required": sources,
            "n_sources": len(sources),
            "operation": op,
            "provenance": PROV,
        }
        out = IN_DIR / diff / f"{iid}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inst, indent=2))
        written.append((iid, len(sources), op, gold))

    print("\n15 instances written:")
    for iid, ns, op, gold in written:
        print(f"  {iid:9} sources={ns} {op:5} gold={gold}")


if __name__ == "__main__":
    main()
