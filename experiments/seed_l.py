"""Curated payload-scaling instances for Phase 2b family L.

Family L ("Payload Scaling" / "Lastprobe", build decision in ``notebooks/
results_analysis.ipynb`` Section 5 and IT-055) calibrates the placeholder
numbers of framework row 1.2: at which input volume does each paradigm
degrade, and where do batching recommendations start? It writes 18 instances
to ``data/test_inputs/l_payload_scaling/`` -- three task shapes x three
payload levels (x1 / x5 / x20) x two instances -- scored by outcome-centric
post-state predicates:

- **scan_scaling** -- in-context DB aggregation: "raise the account's
  longest-open case to High" over 8 / 40 / 160 cases. One action; the input
  volume is the only stressor. Aggregation (argmax over created_at) cannot
  be shortcut by exact-match filters, so the rows MUST pass through the
  model context in both paradigms.
- **action_scaling** -- bulk output: "every Open+Low case moves to Medium"
  with 2 / 10 / 40 matching cases inside 8 / 40 / 160. Homogeneous updates
  (family-P control axis), so the action count, not decidability, scales.
- **mail_scaling** -- mailbox aggregation: "send the date of the OLDEST
  '<topic>' mail" over 10 / 50 / 200 inbox mails with 3 / 15 / 60 topic
  matches. Gmail-shaped tool payloads make this the context-heaviest shape.

**Payload overlay, not seed change.** The shared seed stays untouched (B's
whole-table golds and the P/X/F target sets depend on it). Each instance
carries its own deterministic overlay (account id 900+, case ids 9000+,
email ids 90000+) that ``apply_overlay(conn, iid)`` inserts AFTER the
standard DB reset, identically for both paradigms -- a controlled pre-state
detail behind the tool boundary (the IT-003 argument). Instruction texts are
identical across payload levels within a shape (only account / topic /
recipient tokens differ), so the payload level is the only varied factor.

Tasks are deliberately gate-free (plan-time decidable, homogeneous, single
source): family L measures whether VOLUME alone degrades success or only
cost/latency -- the row-1.2 question. Per the IT-055 DSR note, no routing or
threshold expectation is attached. Paradigms reused unchanged from archetype
F. Anchor discipline: overlays are generated, not hand-picked; uniqueness of
every argmax target is asserted at import time.

Run:
    PYTHONPATH=. python experiments/seed_l.py               # write instances
    PYTHONPATH=. python experiments/seed_l.py --selfcheck   # verify predicates
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

from experiments.seed_actions import _new_event_rows, _seed_rows

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "l_payload_scaling"

USER = "user@atlas.com"

PROVENANCE = {
    "source_benchmark": (
        "Author-constructed (Phase 2b family L, payload scaling); surface style "
        "follows WorkBench (Styles et al., 2024) and the archetype-B/F instances"
    ),
    "adaptation": (
        "Instance designed by the author to scale input volume at constant task "
        "content (build decision IT-055): identical instruction templates across "
        "payload levels x1/x5/x20; per-instance deterministic overlay (fresh id "
        "ranges) inserted after the standard DB reset, identical for both "
        "paradigms; aggregation targets (argmax) so payload cannot be bypassed "
        "by exact-match filters. Paradigms reused unchanged from archetype F."
    ),
    "license": "Original work by the author (task design); benchmark style reference only",
}

RUNBOOK_HYGIENE = """Data-hygiene runbook (excerpt):
- Apply the change to every record that matches the stated condition -- no more, no fewer.
- Leave all other records untouched, and do not send any notifications for routine field changes."""

NOTE_DATES = """Workspace note:
- Notes state dates in YYYY-MM-DD format."""

LEVELS = {1: 1, 5: 5, 20: 20}
SCAN_N = {1: 8, 5: 40, 20: 160}
ACT_N = {1: 8, 5: 40, 20: 160}
ACT_MATCH = {1: 2, 5: 10, 20: 40}
MAIL_N = {1: 10, 5: 50, 20: 200}
MAIL_MATCH = {1: 3, 5: 15, 20: 60}

_TOPICS = ["Invoice reminder", "Shipping delay", "Contract renewal",
           "Onboarding documents", "Downtime notice", "Pricing question"]
_DISTRACT = ["Weekly digest", "Meeting notes", "System notification", "Survey invitation"]
_MAIL_AGENTS = ["agent02@atlas.com", "agent04@atlas.com", "agent06@atlas.com",
                "agent08@atlas.com", "agent01@atlas.com", "agent03@atlas.com"]

Predicate = Callable[[Connection], bool]
Gold = Callable[[Connection], None]

_SEED_CASES = _seed_rows("cases")
_SEED_EMAILS = _seed_rows("emails")


def _dt(base: datetime, i: int) -> str:
    return (base + timedelta(days=i, hours=(i * 7) % 24)).strftime("%Y-%m-%d %H:%M:%S")


# ── Overlay generation (deterministic, per instance) ──

OVERLAYS: dict[str, dict] = {}


def _mk_case(cid: int, aid: int, status: str, priority: str, created: str) -> dict:
    return {"id": cid, "account_id": aid, "agent_id": 1 + cid % 9, "subject": f"Case {cid}",
            "issue_category": "General", "status": status, "priority": priority,
            "created_at": created, "closed_at": None, "transfer_count": cid % 3}


def _build_scan(iid: str, k: int, level: int) -> dict:
    aid = 900 + k
    n = SCAN_N[level]
    base = datetime(2025, 1, 10, 9, 0)
    cases = []
    statuses = ["Open", "In Progress", "Closed"]
    for i in range(n):
        cid = 9000 + k * 300 + i
        status = statuses[i % 3] if i > 0 else "Open"  # index 0: the oldest, Open
        prio = ["Low", "Medium"][i % 2]
        cases.append(_mk_case(cid, aid, status, prio, _dt(base, i)))
    target = cases[0]
    assert target["status"] == "Open" and target["priority"] != "High"
    opens = [c for c in cases if c["status"] == "Open"]
    assert min(opens, key=lambda c: c["created_at"])["id"] == target["id"], iid
    return {"account": {"id": aid, "name": f"Overlay Account {aid}", "region": "EMEA",
                       "industry": "Logistics", "type": "Customer"},
            "cases": cases, "emails": [], "target_case": target["id"], "level": level}


def _build_act(iid: str, k: int, level: int) -> dict:
    aid = 900 + k
    n, m = ACT_N[level], ACT_MATCH[level]
    base = datetime(2025, 2, 3, 8, 0)
    cases = []
    for i in range(n):
        cid = 9000 + k * 300 + i
        if i < m:
            status, prio = "Open", "Low"
        else:
            status, prio = ["Open", "In Progress", "Closed"][i % 3], ["Medium", "High"][i % 2]
        cases.append(_mk_case(cid, aid, status, prio, _dt(base, i)))
    matches = [c["id"] for c in cases if c["status"] == "Open" and c["priority"] == "Low"]
    assert len(matches) == m, iid
    return {"account": {"id": aid, "name": f"Overlay Account {aid}", "region": "AMER",
                       "industry": "Retail", "type": "Customer"},
            "cases": cases, "emails": [], "match_cases": matches, "level": level}


def _build_mail(iid: str, k: int, level: int, topic: str) -> dict:
    n, m = MAIL_N[level], MAIL_MATCH[level]
    base = datetime(2025, 3, 2, 10, 0)
    emails = []
    for i in range(n):
        eid = 90000 + k * 400 + i
        is_topic = i < m
        subj = topic if is_topic else _DISTRACT[i % len(_DISTRACT)]
        emails.append({"id": eid, "sender": f"contact{900 + k:03d}@example.com",
                       "recipient": USER,
                       "subject": subj,
                       "body": f"Regarding {subj.lower()}, please see the details attached (ref {eid}).",
                       "sent_at": _dt(base, i), "status": "inbox"})
    topic_mails = [e for e in emails if e["subject"] == topic]
    oldest = min(topic_mails, key=lambda e: e["sent_at"])
    assert oldest["id"] == topic_mails[0]["id"] and len(topic_mails) == m, iid
    return {"account": None, "cases": [], "emails": emails,
            "topic": topic, "gold_date": oldest["sent_at"][:10], "level": level}


def apply_overlay(conn: Connection, iid: str) -> None:
    """Insert the instance's payload overlay into a freshly reset database."""
    ov = OVERLAYS[iid]
    if ov.get("account"):
        a = ov["account"]
        conn.execute("INSERT INTO accounts (id, name, region, industry, type) VALUES (?,?,?,?,?)",
                     (a["id"], a["name"], a["region"], a["industry"], a["type"]))
    for c in ov["cases"]:
        conn.execute(
            "INSERT INTO cases (id, account_id, agent_id, subject, issue_category, status, priority, created_at, closed_at, transfer_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (c["id"], c["account_id"], c["agent_id"], c["subject"], c["issue_category"],
             c["status"], c["priority"], c["created_at"], c["closed_at"], c["transfer_count"]))
    for e in ov["emails"]:
        conn.execute(
            "INSERT INTO emails (id, sender, recipient, subject, body, sent_at, status) VALUES (?,?,?,?,?,?,?)",
            (e["id"], e["sender"], e["recipient"], e["subject"], e["body"], e["sent_at"], e["status"]))
    conn.commit()


# ── Overlay-aware predicate helpers ──

def _known_email_ids(iid: str) -> set[int]:
    return set(_SEED_EMAILS) | {e["id"] for e in OVERLAYS[iid]["emails"]}


def _new_outbox(conn: Connection, iid: str) -> list:
    known = _known_email_ids(iid)
    rows = conn.execute("SELECT id, recipient, subject, body FROM emails WHERE status='outbox'").fetchall()
    return [r for r in rows if r["id"] not in known]


def _cases_ok(conn: Connection, iid: str, expected_changes: dict[int, dict]) -> bool:
    """Every case equals seed/overlay baseline except *expected_changes*."""
    ov = {c["id"]: c for c in OVERLAYS[iid]["cases"]}
    for r in conn.execute("SELECT id, status, priority, agent_id, transfer_count, closed_at FROM cases").fetchall():
        base = _SEED_CASES.get(r["id"]) or ov.get(r["id"])
        if base is None:
            return False  # task-created case row
        expect = {**{k: base[k] for k in ("status", "priority", "agent_id", "transfer_count", "closed_at")},
                  **expected_changes.get(r["id"], {})}
        for col, val in expect.items():
            if r[col] != val:
                return False
    return True


# ── Shape factories ──

def make_scan(iid: str) -> tuple[Predicate, Gold]:
    target = OVERLAYS[iid]["target_case"]

    def predicate(conn: Connection) -> bool:
        if not _cases_ok(conn, iid, {target: {"priority": "High"}}):
            return False
        return not _new_outbox(conn, iid) and not _new_event_rows(conn)

    def gold(conn: Connection) -> None:
        conn.execute("UPDATE cases SET priority='High' WHERE id=?", (target,))
        conn.commit()

    return predicate, gold


def make_act(iid: str) -> tuple[Predicate, Gold]:
    matches = OVERLAYS[iid]["match_cases"]

    def predicate(conn: Connection) -> bool:
        if not _cases_ok(conn, iid, {cid: {"priority": "Medium"} for cid in matches}):
            return False
        return not _new_outbox(conn, iid) and not _new_event_rows(conn)

    def gold(conn: Connection) -> None:
        for cid in matches:
            conn.execute("UPDATE cases SET priority='Medium' WHERE id=?", (cid,))
        conn.commit()

    return predicate, gold


def make_mail(iid: str, recipient: str, subject: str) -> tuple[Predicate, Gold]:
    gold_date = OVERLAYS[iid]["gold_date"]

    def predicate(conn: Connection) -> bool:
        if not _cases_ok(conn, iid, {}):
            return False
        if _new_event_rows(conn):
            return False
        new = _new_outbox(conn, iid)
        if len(new) != 1:
            return False
        m = new[0]
        return (m["recipient"] == recipient and m["subject"].strip() == subject
                and gold_date in (m["body"] or ""))

    def gold(conn: Connection) -> None:
        conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, datetime('now'), 'outbox')",
            (USER, recipient, subject, f"The oldest one came in on {gold_date}."))
        conn.commit()

    return predicate, gold


# ── Instances (identical templates across levels within a shape) ──

INSTANCES: list[dict] = []
PREDICATES: dict[str, Predicate] = {}
GOLD: dict[str, Gold] = {}


def _add(iid: str, variant: str, level: int, instruction: str, expected: str, pred, gold) -> None:
    INSTANCES.append({
        "id": iid, "archetype": "L", "family": "L (Phase 2b, payload scaling)",
        "variant": variant, "level": level, "difficulty": "na", "sub_class": f"{variant}_x{level}",
        "instruction": instruction, "expected_post_state": expected,
        "provenance": PROVENANCE,
    })
    PREDICATES[iid] = pred
    GOLD[iid] = gold


k = 0
for level in (1, 5, 20):
    for n in (1, 2):
        iid = f"l-s{level}-{n}"
        OVERLAYS[iid] = _build_scan(iid, k, level)
        aid = OVERLAYS[iid]["account"]["id"]
        pred, gold = make_scan(iid)
        _add(iid, "scan_scaling", level,
             f"Please take a look at account {aid}'s cases: the one that is still Open and has been open the "
             f"longest should be raised to High priority -- just that one.\n\n" + RUNBOOK_HYGIENE,
             f"Case {OVERLAYS[iid]['target_case']} (the oldest Open case of overlay account {aid}, "
             f"{SCAN_N[level]} cases total) has priority 'High'; every other record unchanged; no mails, no events.",
             pred, gold)
        k += 1

for level in (1, 5, 20):
    for n in (1, 2):
        iid = f"l-a{level}-{n}"
        OVERLAYS[iid] = _build_act(iid, k, level)
        aid = OVERLAYS[iid]["account"]["id"]
        pred, gold = make_act(iid)
        _add(iid, "action_scaling", level,
             f"Quick cleanup for account {aid}, please: every case there that is still Open and sits at Low "
             f"priority moves up to Medium.\n\n" + RUNBOOK_HYGIENE,
             f"The {ACT_MATCH[level]} Open+Low cases of overlay account {aid} ({ACT_N[level]} cases total) have "
             f"priority 'Medium'; every other record unchanged; no mails, no events.",
             pred, gold)
        k += 1

mi = 0
for level in (1, 5, 20):
    for n in (1, 2):
        iid = f"l-m{level}-{n}"
        topic = _TOPICS[mi]
        OVERLAYS[iid] = _build_mail(iid, k, level, topic)
        recipient = _MAIL_AGENTS[mi]
        subject = f"Oldest {topic.lower()}"
        pred, gold = make_mail(iid, recipient, subject)
        _add(iid, "mail_scaling", level,
             f"Somewhere in the mailbox are the '{topic}' mails -- find the oldest one and send a short note to "
             f"{recipient}, subject '{subject}', with the date it came in.\n\n" + NOTE_DATES,
             f"Exactly one new outbox email to {recipient} with subject '{subject}' and a body containing "
             f"'{OVERLAYS[iid]['gold_date']}' (oldest of {MAIL_MATCH[level]} '{topic}' mails among "
             f"{MAIL_N[level]} overlay mails); no record changes, no events.",
             pred, gold)
        k += 1
        mi += 1


# ── Output / self-check ──

VARIANT_DIRS = {"scan_scaling": "scan_scaling", "action_scaling": "action_scaling", "mail_scaling": "mail_scaling"}


def write_instances() -> None:
    for inst in INSTANCES:
        out = INPUT_DIR / VARIANT_DIRS[inst["variant"]] / f"{inst['id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inst, indent=1))
    ov_out = INPUT_DIR / "overlays.json"
    ov_out.write_text(json.dumps(OVERLAYS, indent=1))
    print(f"Wrote {len(INSTANCES)} instances (+ overlays.json) to {INPUT_DIR.relative_to(REPO)}")


def selfcheck() -> int:
    from experiments.load_db import load as reset_database
    from src.core.db import get_connection

    failures = 0
    print(f"{'instance':9} {'neg(False)':>10} {'pos(True)':>10}")
    for inst in INSTANCES:
        iid = inst["id"]
        reset_database()
        conn = get_connection()
        try:
            apply_overlay(conn, iid)
            neg = PREDICATES[iid](conn)
        finally:
            conn.close()
        conn = get_connection()
        try:
            GOLD[iid](conn)
            pos = PREDICATES[iid](conn)
        finally:
            conn.close()
        ok = (neg is False) and (pos is True)
        failures += 0 if ok else 1
        print(f"{iid:9} {str(not neg):>10} {str(pos):>10}" + ("" if ok else "   <-- FAIL"))
    print("SELF-CHECK " + ("PASSED" if failures == 0 else f"FAILED ({failures})"))
    return failures


def main() -> None:
    write_instances()
    if "--selfcheck" in sys.argv:
        sys.exit(1 if selfcheck() else 0)


if __name__ == "__main__":
    main()
