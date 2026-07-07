"""Verify the archetype-B v4 ETL workflow end-to-end (deterministic part).

Builds the store in-memory, and for each of the 15 instances: simulates the
fetch step (the same matching the Mail/Calendar APIs perform) into the staging
tables fetched_emails / fetched_events, then runs a reference RetrievalPlan
(read-only SQL per field over CRM + staging) through the production
run_retrieval_plan, and checks the result against the gold. This proves that the
ETL staging + SQL-combine mechanism answers every task. The LLM fetch-plan and
query nodes are exercised on the author's machine.

Run:
    python -m experiments.verify_b_retrieval
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.archetypes.b_structured_retrieval.schemas import RetrievalField, RetrievalPlan
from src.archetypes.b_structured_retrieval.sql_executor import run_retrieval_plan

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "schema" / "seed"
IN_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"


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


def stage(con: sqlite3.Connection, mail_qs: list[str], cal_qs: list[str]) -> None:
    """Simulate the fetch step: run the API-equivalent searches into staging."""
    con.execute("DROP TABLE IF EXISTS fetched_emails")
    con.execute("CREATE TEMP TABLE fetched_emails (sender, recipient, subject, body, sent_at)")
    for q in mail_qs:
        like = f"%{q}%"
        con.execute(
            "INSERT INTO fetched_emails SELECT sender, recipient, subject, body, sent_at FROM emails "
            "WHERE subject LIKE ? OR body LIKE ? OR sender LIKE ?", (like, like, like))
    con.execute("DROP TABLE IF EXISTS fetched_events")
    con.execute("CREATE TEMP TABLE fetched_events (name, attendees, start_time, end_time)")
    for q in cal_qs:
        con.execute(
            "INSERT INTO fetched_events SELECT name, attendees, start_time, end_time FROM events WHERE name LIKE ?",
            (f"%{q}%",))


def F(name, sql):
    return RetrievalField(name=name, sql=sql)


# (mail_queries, calendar_queries, [fields])
REF = {
    "b-low-1": ([], [], [F("answer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.is_won=1")]),
    "b-low-2": ([], [], [F("answer", "SELECT industry FROM accounts WHERE name='Helvetia Finance'")]),
    "b-low-3": ([], [], [F("answer", "SELECT region FROM accounts WHERE name='Pacific HealthTech'")]),
    "b-low-4": ([], [], [F("answer", "SELECT sum(o.amount) FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Sunrise Retail' AND o.is_won=1")]),
    "b-low-5": ([], [], [F("answer", "SELECT a.name FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.type='Key Account' AND o.is_won=1 ORDER BY o.amount DESC LIMIT 1")]),
    "b-med-1": (["Expansion"], [], [F("answer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.name LIKE '%Expansion%' AND EXISTS(SELECT 1 FROM fetched_emails fe WHERE fe.subject LIKE '%Expansion%')")]),
    "b-med-2": ([], ["Mayer"], [F("answer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' AND o.name LIKE '%Renewal%' AND o.is_won=1 AND EXISTS(SELECT 1 FROM fetched_events fv WHERE fv.name LIKE '%Renewal%')")]),
    "b-med-3": (["Helvetia"], [], [F("answer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Helvetia Finance' AND o.is_won=0 AND EXISTS(SELECT 1 FROM fetched_emails fe WHERE fe.subject LIKE '%Helvetia%' OR fe.body LIKE '%Helvetia%')")]),
    "b-med-4": (["delivery delay"], [], [F("answer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Brueckner Logistics' AND o.is_won=1 AND EXISTS(SELECT 1 FROM fetched_emails fe WHERE fe.subject LIKE '%delivery delay%' OR fe.body LIKE '%delivery delay%')")]),
    "b-med-5": ([], [""], [F("answer", "SELECT sum(o.amount) FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE o.is_won=1 AND a.type='Key Account' AND a.id IN (SELECT DISTINCT ct.account_id FROM contacts ct JOIN fetched_events fv ON fv.attendees LIKE '%'||ct.email||'%')")]),
    "b-high-1": (["mayer.example"], ["Mayer"], [
        F("last_contact", "SELECT date(max(sent_at)) FROM fetched_emails WHERE sender LIKE '%mayer.example' OR recipient LIKE '%mayer.example'"),
        F("last_offer", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Mayer & Co' ORDER BY o.created_at DESC LIMIT 1"),
        F("next_meeting", "SELECT date(min(start_time)) FROM fetched_events WHERE name LIKE '%Mayer%'")]),
    "b-high-2": (["sunrise.example"], ["Sunrise"], [
        F("won_total", "SELECT sum(o.amount) FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Sunrise Retail' AND o.is_won=1"),
        F("last_contact", "SELECT date(max(sent_at)) FROM fetched_emails WHERE sender LIKE '%sunrise.example' OR recipient LIKE '%sunrise.example'"),
        F("next_meeting", "SELECT date(min(start_time)) FROM fetched_events WHERE name LIKE '%Sunrise%'")]),
    "b-high-3": (["brueckner.example"], ["Brueckner"], [
        F("won_value", "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id WHERE a.name='Brueckner Logistics' AND o.is_won=1"),
        F("last_contact", "SELECT date(max(sent_at)) FROM fetched_emails WHERE sender LIKE '%brueckner.example' OR recipient LIKE '%brueckner.example'"),
        F("next_meeting", "SELECT date(min(start_time)) FROM fetched_events WHERE name LIKE '%Brueckner%'")]),
    "b-high-4": ([""], [""], [F("answer",
        "SELECT o.amount FROM opportunities o JOIN accounts a ON o.account_id=a.id "
        "WHERE o.is_won=0 AND a.type='Key Account' AND EXISTS("
        "SELECT 1 FROM fetched_emails fe WHERE fe.sender LIKE '%@atlas.com' AND fe.recipient LIKE '%@atlas.com' "
        "AND (fe.subject LIKE '%'||a.name||'%' OR fe.body LIKE '%'||a.name||'%')) AND EXISTS("
        "SELECT 1 FROM contacts ct JOIN fetched_events fv ON fv.attendees LIKE '%'||ct.email||'%' WHERE ct.account_id=a.id) "
        "ORDER BY o.created_at DESC LIMIT 1")]),
    "b-high-5": ([""], [""], [F("answer",
        "SELECT a.region FROM accounts a WHERE a.id=("
        "SELECT ct.account_id FROM fetched_emails fe JOIN contacts ct ON fe.sender=ct.email "
        "JOIN accounts a2 ON ct.account_id=a2.id WHERE a2.type='Key Account' "
        "AND EXISTS(SELECT 1 FROM fetched_events fv WHERE fv.attendees LIKE '%'||ct.email||'%') "
        "ORDER BY fe.sent_at DESC LIMIT 1)")]),
}


def norm(v):
    return int(round(v)) if isinstance(v, float) else v


def main() -> None:
    con = build_db()
    ok = True
    for diff in ["low", "med", "high"]:
        for n in range(1, 6):
            iid = f"b-{diff}-{n}"
            mail_qs, cal_qs, fields = REF[iid]
            stage(con, mail_qs, cal_qs)
            gold = json.loads((IN_DIR / diff / f"{iid}.json").read_text())["ground_truth"]["value"]
            res = run_retrieval_plan(RetrievalPlan(fields=fields), lambda sql: con.execute(sql).fetchone())
            res = {k: norm(v) for k, v in res.items()} if isinstance(res, dict) else norm(res)
            match = res == gold
            ok &= match
            print(f"{iid:9} {'OK' if match else 'MISMATCH':8} exec={res}  gold={gold}")
    print(f"\n{'PASS' if ok else 'FAIL'}: ETL staging + SQL combine reproduces all 15 golds")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
