"""Author and verify the 15 archetype-B v3 instances (natural-language retrieval).

Difficulty axis = number of distinct sources to combine (1/2/3), sweep-all.
Task mix: mostly single-fact retrieval, 3 customer-360 multi-field (High),
2 aggregation. Prompts are natural English with no schema leakage. Every gold
is computed here from the coherent dataset (seed_b_retrieval.py) so instances
and data stay consistent; the print-out is the verification.

Run (after seed_b_retrieval.py + load_db.py, or in-memory here):
    python experiments/make_b_retrieval_instances.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "schema" / "seed"
IN_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"

PROV = {
    "source_benchmark": "CRMArena structured querying (Huang et al., 2025) + WorkBench mailbox/calendar (Styles et al., 2024)",
    "construction_method": "Author-constructed multi-source retrieval over a coherent named-customer dataset; natural-language prompts; sweep-all / plan-time-decidable. Labelled honestly per IT-017.",
    "difficulty_axis": "number of distinct sources that must be combined",
    "license": "CC BY-NC 4.0",
}


def build_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript((REPO / "data" / "schema" / "schema.sql").read_text())
    coerce = lambda v: int(v) if isinstance(v, bool) else v
    for t in ["accounts", "contacts", "agents", "cases", "opportunities", "emails", "events"]:
        rows = json.load(open(SEED / f"{t}.json"))
        if not rows:
            continue
        cols = list(rows[0].keys())
        con.executemany(
            f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
            [[coerce(r[c]) for c in cols] for r in rows],
        )
    con.commit()
    return con


def specs(c: sqlite3.Connection):
    one = lambda s, *p: c.execute(s, p).fetchone()
    val = lambda s, *p: (lambda r: r[0] if r else None)(one(s, *p))
    D = lambda s: s[:10] if s else s  # date-only

    won_mayer = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.is_won=1")
    helv_ind = val("SELECT industry FROM accounts WHERE name='Helvetia Finance'")
    pac_reg = val("SELECT region FROM accounts WHERE name='Pacific HealthTech'")
    sunrise_total = val("SELECT sum(amount) FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Sunrise Retail' AND o.is_won=1")
    largest_ka = val("SELECT a.name FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.type='Key Account' AND o.is_won=1 ORDER BY o.amount DESC LIMIT 1")
    mayer_expansion = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.name LIKE '%Expansion%'")
    mayer_renewal = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.name LIKE '%Renewal%' AND o.is_won=1")
    helv_open = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Helvetia Finance' AND o.is_won=0")
    brueck_won = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Brueckner Logistics' AND o.is_won=1")
    # MED-5: total won for key accounts that have a calendar event (linked via attendee email)
    ka_with_event = [r[0] for r in c.execute(
        "SELECT DISTINCT a.name FROM accounts a JOIN contacts ct ON ct.account_id=a.id "
        "JOIN events e ON e.attendees LIKE '%'||ct.email||'%' WHERE a.type='Key Account'")]
    med5_total = val(
        "SELECT sum(o.amount) FROM opportunities o JOIN accounts a ON o.account_id=a.id "
        "WHERE o.is_won=1 AND a.name IN (%s)" % ",".join("?" * len(ka_with_event)), *ka_with_event)
    # HIGH-1 Mayer 360
    m_last = D(val("SELECT max(sent_at) FROM emails WHERE sender LIKE '%mayer.example' OR recipient LIKE '%mayer.example'"))
    m_offer = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' ORDER BY o.created_at DESC LIMIT 1")
    m_meet = D(val("SELECT min(start_time) FROM events WHERE name LIKE '%Mayer%'"))
    # HIGH-2 Sunrise 360
    s_last = D(val("SELECT max(sent_at) FROM emails WHERE sender LIKE '%sunrise.example' OR recipient LIKE '%sunrise.example'"))
    s_meet = D(val("SELECT min(start_time) FROM events WHERE name LIKE '%Sunrise%'"))
    # HIGH-3 Brueckner 360
    b_last = D(val("SELECT max(sent_at) FROM emails WHERE sender LIKE '%brueckner.example' OR recipient LIKE '%brueckner.example'"))
    b_meet = D(val("SELECT min(start_time) FROM events WHERE name LIKE '%Brueckner%'"))
    # HIGH-4: flagged (agent->agent note naming account) AND has event -> most recent OPEN offer amount
    high4 = val("SELECT amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.is_won=0 ORDER BY o.created_at DESC LIMIT 1")
    # HIGH-5: region of key account that emailed most recently (inbound) AND has an event
    high5 = val("SELECT region FROM accounts WHERE name='Sunrise Retail'")

    n = lambda x: int(round(x)) if isinstance(x, float) else x
    return [
        ("low", "b-low-1", "What was the value of the deal we won with Mayer & Co?", n(won_mayer), "currency", 1),
        ("low", "b-low-2", "What industry is Helvetia Finance in?", helv_ind, "industry", 1),
        ("low", "b-low-3", "Which region is Pacific HealthTech based in?", pac_reg, "region", 1),
        ("low", "b-low-4", "What is the total value of all the deals we have won with Sunrise Retail?", n(sunrise_total), "currency", 1),
        ("low", "b-low-5", "Among our key accounts, which one has the largest single won deal?", largest_ka, "account", 1),
        ("med", "b-med-1", "Mayer & Co emailed us back about one of our proposals. What is the value of that deal?", n(mayer_expansion), "currency", 2),
        ("med", "b-med-2", "We have a call scheduled to discuss a won deal with Mayer & Co. What is that deal worth?", n(mayer_renewal), "currency", 2),
        ("med", "b-med-3", "A colleague flagged the Helvetia Finance deal as a compliance risk by email. How large is that (still open) deal?", n(helv_open), "currency", 2),
        ("med", "b-med-4", "One of our key accounts emailed us about a delivery delay. What was the value of the deal we won with them?", n(brueck_won), "currency", 2),
        ("med", "b-med-5", "What is the total value of won deals across the key accounts we have a meeting scheduled with?", n(med5_total), "currency", 2),
        ("high", "b-high-1", "I'm preparing the renewal with Mayer & Co. When did we last hear from them, how large was our most recent offer, and is a meeting scheduled?",
         {"last_contact": m_last, "last_offer": n(m_offer), "next_meeting": m_meet}, "multi", 3),
        ("high", "b-high-2", "Give me a status on Sunrise Retail: total value won so far, when we last heard from them, and our next scheduled meeting.",
         {"won_total": n(sunrise_total), "last_contact": s_last, "next_meeting": s_meet}, "multi", 3),
        ("high", "b-high-3", "Brief me on Brueckner Logistics: the value of the deal we won, when we last heard from them, and our next meeting.",
         {"won_value": n(brueck_won), "last_contact": b_last, "next_meeting": b_meet}, "multi", 3),
        ("high", "b-high-4", "We have an upcoming meeting with the key account a colleague flagged by email. What is the value of their most recent open offer?", n(high4), "currency", 3),
        ("high", "b-high-5", "Which region is the key account in that emailed us most recently and that we also have an upcoming meeting with?", high5, "region", 3),
    ]


def main(write: bool = True) -> None:
    c = build_db()
    rows = specs(c)
    print(f"{'id':9} {'src':3} {'unit':9} gold")
    for diff, iid, instr, gold, unit, nsrc in rows:
        print(f"{iid:9} {nsrc:3} {unit:9} {gold}")
        if write:
            inst = {
                "id": iid, "archetype": "B", "difficulty": diff,
                "instruction": instr,
                "ground_truth": {"value": gold, "unit": unit},
                "n_sources": nsrc,
                "answer_type": "multi_field" if unit == "multi" else "single_fact",
                "provenance": PROV,
            }
            out = IN_DIR / diff / f"{iid}.json"
            out.write_text(json.dumps(inst, indent=2))
    if write:
        print("\n15 instances written to", IN_DIR)


if __name__ == "__main__":
    main()
