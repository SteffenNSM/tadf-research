"""Curated plan-uncertainty instances for Phase 2b family P.

Family P ("Plan Uncertainty", build decision in ``notebooks/
results_analysis.ipynb`` Section 5 and IT-055) isolates WHERE plan-time
decidability breaks. It writes 20 task instances to
``data/test_inputs/p_plan_uncertainty/`` in four variants (5 each), all on
the frozen CRM seed and scored by outcome-centric post-state predicates:

- **a_count_read** — the number of required actions is not stated in the
  instruction but is fully derivable from one read (homogeneous update per
  matching record; matching counts vary 2-4). Control axis: count unknown
  at plan time, data-bounded.
- **b_count_outcome** — the number of required actions depends on each
  action's runtime outcome: close non-closed cases oldest-first and stop at
  the first back-end refusal (the refusal rule, ``transfer_count > 3``, is
  intentionally undocumented and not stated anywhere in the input).
- **c_source_unknown** — WHICH tool holds the needed fact is unknown: the
  item lives in exactly one of mailbox / calendar / CRM cases, and the
  requester says so naturally ("I don't remember where it ended up").
- **d_derived_order** — the required ordering of the actions is not stated
  as a sequence but must be derived from record data (creation date,
  priority, amount). Order is verified through the send order of the
  notification emails (outbox ids are monotone). Control axis: ordering
  derivable at plan time after a read.

Per the IT-055 DSR note, no routing expectation is attached to any variant;
which paradigm carries a variant is decided from the sweep results. Both
paradigm implementations are reused UNCHANGED from archetype F (frozen
artifact state), so differences attribute to the task properties.

Input-neutrality rules (design law, IT-049/IT-051): every instruction is a
natural colleague request plus a short shared runbook excerpt, identical for
both paradigms; no procedural hints, no step counts, no output-format
directives beyond what a requester would write. The only tool named in any
input is ``attempt_close_case`` inside the support-runbook excerpt, following
the archetype-F precedent (closure policy is routed through that tool).

Each instance registers a Python predicate in ``PREDICATES`` (positive
post-condition AND negative side-effect condition) and a gold simulation in
``GOLD`` used by the deterministic self-check.

Run:
    PYTHONPATH=. python experiments/seed_p.py               # write instances
    PYTHONPATH=. python experiments/seed_p.py --selfcheck   # verify predicates
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

from experiments.seed_actions import (
    _new_event_rows,
    _new_outbox_rows,
    _no_unintended_column_change,
    _seed_rows,
)

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "p_plan_uncertainty"

USER = "user@atlas.com"
OPS = "ops@atlas.com"

PROVENANCE = {
    "source_benchmark": (
        "Author-constructed (Phase 2b family P, plan uncertainty); surface style "
        "follows WorkBench (Styles et al., 2024) and the archetype-F instances"
    ),
    "adaptation": (
        "Instance designed by the author to isolate one plan-uncertainty axis "
        "(build decision IT-055): action count derivable from a read (a), action "
        "count dependent on runtime outcomes (b), unknown source tool (c), or "
        "ordering derived from record data (d). Entities reference the "
        "deterministic seed in seed_crm.py for stable post-state predicates. "
        "Paradigm implementations are reused unchanged from archetype F."
    ),
    "license": "Original work by the author (task design); benchmark style reference only",
}

# ── Shared runbook excerpts (identical for both paradigms) ──

RUNBOOK_HYGIENE = """Data-hygiene runbook (excerpt):
- Apply the change to every record that matches the stated condition -- no more, no fewer.
- Leave all other records untouched, and do not send any notifications for routine field changes."""

RUNBOOK_CLOSE = """Support runbook (excerpt):
- 'Open casework' covers every case that is not closed (status Open or In Progress).
- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.
- Work strictly oldest-first by creation date.
- Stop at the first refused close: leave that case and every case after it untouched, and notify ops@atlas.com by email: subject 'Manual review required: case <id>' (substitute the case id), body quoting the back-end's stated reason.
- If no close is refused, the batch is complete and no notification is needed."""

RUNBOOK_LOOKUP = """Workspace note:
- Customer touchpoints end up in different places -- some in the shared mailbox, some on the team calendar, some as CRM cases. Where a given item landed is not always known.
- Notes state dates in YYYY-MM-DD format."""

RUNBOOK_NOTIFY = """Notification runbook (excerpt):
- One email per record, addressed to the responsible agent (the record's assigned agent; agent addresses follow the agentNN@atlas.com pattern and are listed in the agents table).
- Send the notifications one at a time in the required order, so the audit trail reflects the sequence.
- Do not modify any records while notifying."""


# ── Predicate / gold helpers ──

Predicate = Callable[[Connection], bool]
Gold = Callable[[Connection], None]

_AGENT_EMAILS = {a["id"]: a["email"] for a in json.loads((REPO / "data/schema/seed/agents.json").read_text())}


def _cases_unchanged(conn: Connection, exclude: set[int]) -> bool:
    """All cases outside *exclude* still match the seed on the mutable columns."""
    seed = _seed_rows("cases")
    for r in conn.execute(
        "SELECT id, status, priority, agent_id, transfer_count, closed_at FROM cases"
    ).fetchall():
        if r["id"] in exclude:
            continue
        s = seed.get(r["id"])
        if s is None:
            return False  # a task-created case row would be a side effect
        for col in ("status", "priority", "agent_id", "transfer_count", "closed_at"):
            if r[col] != s[col]:
                return False
    return True


def _row(conn: Connection, table: str, rid: int) -> dict:
    return dict(conn.execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone())


def _subject_pattern(fmt: str, rid: int) -> str:
    """Regex accepting the record id with optional zero padding.

    Seed record labels are zero-padded ('Case 089'), so a model that copies
    the label writes 'Case 089 reminder' while the instruction's literal form
    is 'Case 89 reminder'. Both name the same record; per the IT-005/IT-027
    extraction-robustness precedent the predicate accepts both. Scoring
    stays on the construct (which record, which recipient, which order), not
    on padding style.
    """
    return "^" + re.escape(fmt).replace(re.escape("{id}"), f"0*{rid}") + "$"


# ── Variant a: count derivable from one read ──

def make_pa(table: str, targets: dict[int, dict], column: str) -> tuple[Predicate, Gold]:
    """Homogeneous update on *targets* (id -> {column: new_value}); nothing else.

    Predicate: every target row carries the new value; no other row in the
    table changed *column* from its seed value; no mails, no events.
    """

    def predicate(conn: Connection) -> bool:
        for rid, upd in targets.items():
            if _row(conn, table, rid)[column] != upd[column]:
                return False
        if not _no_unintended_column_change(conn, table, column, set(targets)):
            return False
        return not _new_outbox_rows(conn) and not _new_event_rows(conn)

    def gold(conn: Connection) -> None:
        for rid, upd in targets.items():
            conn.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (upd[column], rid))
        conn.commit()

    return predicate, gold


# ── Variant b: count dependent on runtime outcomes ──

def make_pb(order: list[int], refusal: int | None) -> tuple[Predicate, Gold]:
    """Close *order* (oldest-first ids) until *refusal*; then stop and escalate.

    Predicate: every case before *refusal* is Closed (other columns
    untouched); *refusal* and every later case fully untouched; exactly one
    new outbox email to ops with subject 'Manual review required: case <id>'
    (zero emails when *refusal* is None); no other new emails, no events; no
    case outside the batch changed.
    """
    stop_index = order.index(refusal) if refusal is not None else len(order)
    to_close = order[:stop_index]
    untouched = order[stop_index:]

    def predicate(conn: Connection) -> bool:
        seed = _seed_rows("cases")
        for rid in to_close:
            r = _row(conn, "cases", rid)
            if r["status"] != "Closed":
                return False
            for col in ("priority", "agent_id", "transfer_count"):
                if r[col] != seed[rid][col]:
                    return False
        for rid in untouched:
            r = _row(conn, "cases", rid)
            for col in ("status", "priority", "agent_id", "transfer_count", "closed_at"):
                if r[col] != seed[rid][col]:
                    return False
        if not _cases_unchanged(conn, set(order)):
            return False
        if _new_event_rows(conn):
            return False
        new_mail = _new_outbox_rows(conn)
        if refusal is None:
            return not new_mail
        if len(new_mail) != 1:
            return False
        m = new_mail[0]
        return m["recipient"] == OPS and bool(
            re.fullmatch(
                _subject_pattern("Manual review required: case {id}", refusal),
                m["subject"].strip(),
            )
        )

    def gold(conn: Connection) -> None:
        for rid in to_close:
            conn.execute(
                "UPDATE cases SET status='Closed', closed_at=datetime('now') WHERE id=?",
                (rid,),
            )
        if refusal is not None:
            conn.execute(
                "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
                "VALUES (?, ?, ?, ?, datetime('now'), 'outbox')",
                (
                    USER,
                    OPS,
                    f"Manual review required: case {refusal}",
                    "case escalated for manual review; automatic close is not permitted",
                ),
            )
        conn.commit()

    return predicate, gold


# ── Variant c: unknown source tool ──

def make_pc(recipient: str, subject: str, date_token: str) -> tuple[Predicate, Gold]:
    """One notification email whose body carries the fact found elsewhere.

    Predicate: exactly one new outbox email with the exact recipient and
    subject, body containing *date_token*; no CRM case changed; no events.
    """

    def predicate(conn: Connection) -> bool:
        if not _cases_unchanged(conn, set()):
            return False
        if _new_event_rows(conn):
            return False
        new_mail = _new_outbox_rows(conn)
        if len(new_mail) != 1:
            return False
        m = new_mail[0]
        if m["recipient"] != recipient or m["subject"].strip() != subject:
            return False
        body = conn.execute("SELECT body FROM emails WHERE id=?", (m["id"],)).fetchone()["body"]
        return date_token in (body or "")

    def gold(conn: Connection) -> None:
        conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, datetime('now'), 'outbox')",
            (USER, recipient, subject, f"It came in on {date_token}.", ),
        )
        conn.commit()

    return predicate, gold


# ── Variant d: ordering derived from record data ──

def make_pd(sequence: list[tuple[str, str, str]]) -> tuple[Predicate, Gold]:
    """Ordered notifications: *sequence* of (recipient, subject_pattern, example).

    Predicate: the new outbox rows, sorted by id (= send order), match the
    expected (recipient, subject regex) sequence exactly (zero-padded record
    ids accepted, see ``_subject_pattern``); no CRM case changed; no events.
    """

    def predicate(conn: Connection) -> bool:
        if not _cases_unchanged(conn, set()):
            return False
        if _new_event_rows(conn):
            return False
        new_mail = sorted(_new_outbox_rows(conn), key=lambda m: m["id"])
        if len(new_mail) != len(sequence):
            return False
        for m, (rcpt, pat, _example) in zip(new_mail, sequence):
            if m["recipient"] != rcpt or not re.fullmatch(pat, m["subject"].strip()):
                return False
        return True

    def gold(conn: Connection) -> None:
        for rcpt, _pat, example in sequence:
            conn.execute(
                "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
                "VALUES (?, ?, ?, ?, datetime('now'), 'outbox')",
                (USER, rcpt, example, "Please take a look."),
            )
        conn.commit()

    return predicate, gold


def _seq_from_cases(case_ids: list[int], subject_fmt: str) -> list[tuple[str, str, str]]:
    seed = _seed_rows("cases")
    return [
        (
            _AGENT_EMAILS[seed[cid]["agent_id"]],
            _subject_pattern(subject_fmt, cid),
            subject_fmt.format(id=cid),
        )
        for cid in case_ids
    ]


# p-d-5 target order computed from the seed: Open+Medium cases of account 15,
# newest first (documented in the instance; the instruction states the rule,
# not the ids).
_PD5_IDS = [
    c["id"]
    for c in sorted(
        (
            c for c in _seed_rows("cases").values()
            if c["account_id"] == 15 and c["status"] == "Open" and c["priority"] == "Medium"
        ),
        key=lambda c: c["created_at"],
        reverse=True,
    )
]


# ── Instance definitions ──

def _inst(iid: str, variant: str, instruction: str, expected: str) -> dict:
    return {
        "id": iid,
        "archetype": "P",
        "family": "P (Phase 2b, plan uncertainty)",
        "variant": variant,
        "difficulty": "na",
        "sub_class": variant,
        "instruction": instruction,
        "expected_post_state": expected,
        "provenance": PROVENANCE,
    }


INSTANCES: list[dict] = []
PREDICATES: dict[str, Predicate] = {}
GOLD: dict[str, Gold] = {}


def _add(iid: str, variant: str, instruction: str, expected: str, pred: Predicate, gold: Gold) -> None:
    INSTANCES.append(_inst(iid, variant, instruction, expected))
    PREDICATES[iid] = pred
    GOLD[iid] = gold


# — a_count_read (counts 4, 3, 3, 2, 4; never stated in the instruction) —

p, g = make_pa("cases", {68: {"priority": "High"}, 112: {"priority": "High"}, 116: {"priority": "High"}, 120: {"priority": "High"}}, "priority")
_add("p-a-1", "a_count_read",
     "Quick cleanup for account 15, please: every case there that is still marked Open and currently sits at "
     "Medium priority should be raised to High.\n\n" + RUNBOOK_HYGIENE,
     "Cases 68, 112, 116, 120 (the four Open+Medium cases of account 15) have priority 'High'; no other case "
     "changed priority; no emails sent, no events created.", p, g)

p, g = make_pa("cases", {89: {"agent_id": 2}, 32: {"agent_id": 2}, 30: {"agent_id": 2}}, "agent_id")
_add("p-a-2", "a_count_read",
     "All cases for account 18 that are still marked Open should be handed over to agent 2, who is covering "
     "that queue this quarter.\n\n" + RUNBOOK_HYGIENE,
     "Cases 89, 32, 30 (the three Open cases of account 18) have agent_id=2; the In-Progress cases 20 and 39 "
     "are untouched; no other agent_id changed; no emails, no events.", p, g)

p, g = make_pa("cases", {38: {"priority": "Medium"}, 42: {"priority": "Medium"}, 76: {"priority": "Medium"}}, "priority")
_add("p-a-3", "a_count_read",
     "For the triage review, set every case of account 12 that is currently In Progress to Medium "
     "priority.\n\n" + RUNBOOK_HYGIENE,
     "Cases 38, 42, 76 (the three In-Progress cases of account 12) have priority 'Medium'; the Open cases 31 "
     "and 8 are untouched; no other priority changed; no emails, no events.", p, g)

p, g = make_pa("opportunities", {16: {"owner_agent_id": 5}, 59: {"owner_agent_id": 5}}, "owner_agent_id")
_add("p-a-4", "a_count_read",
     "The opportunities for account 19 that are still in the Prospecting stage move to agent 5 as their new "
     "owner, please.\n\n" + RUNBOOK_HYGIENE,
     "Opportunities 16 and 59 (the two Prospecting-stage opportunities of account 19) have owner_agent_id=5; "
     "opportunity 38 (Proposal) is untouched; no other owner changed; no emails, no events.", p, g)

p, g = make_pa("cases", {54: {"priority": "High"}, 104: {"priority": "High"}, 81: {"priority": "High"}, 16: {"priority": "High"}}, "priority")
_add("p-a-5", "a_count_read",
     "Account 16 escalation: raise every case there that is still marked Open to High priority.\n\n" + RUNBOOK_HYGIENE,
     "Cases 54, 104, 81, 16 (the four Open cases of account 16) have priority 'High'; the In-Progress case 92 "
     "is untouched; no other priority changed; no emails, no events.", p, g)

# — b_count_outcome (stop points: after 3, after 1, immediately, never, after 1) —

p, g = make_pb([62, 40, 63, 17, 118], refusal=17)
_add("p-b-1", "b_count_outcome",
     "Can you clear out the open casework for account 14? Close what the back-end lets you close, resolution "
     "'Routine cleanup', and follow the runbook.\n\n" + RUNBOOK_CLOSE,
     "Oldest-first order is 62, 40, 63, 17, 118. Cases 62, 40, 63 are Closed; case 17 (transfer_count 5) is "
     "refused and untouched; case 118 is untouched because processing stops at the refusal; exactly one email "
     "to ops@atlas.com with subject 'Manual review required: case 17'.", p, g)

p, g = make_pb([54, 92, 104, 81, 16], refusal=92)
_add("p-b-2", "b_count_outcome",
     "Please work through the open casework for account 16 and close it with the resolution 'Batch review "
     "done', following the runbook.\n\n" + RUNBOOK_CLOSE,
     "Oldest-first order is 54, 92, 104, 81, 16. Case 54 is Closed; case 92 (transfer_count 5) is refused and "
     "untouched; cases 104, 81, 16 are untouched; exactly one email to ops@atlas.com with subject 'Manual "
     "review required: case 92'.", p, g)

p, g = make_pb([38, 42, 76, 31, 8], refusal=38)
_add("p-b-3", "b_count_outcome",
     "Time to tidy up account 12: close out its open casework with the resolution 'Consolidated', per the "
     "runbook.\n\n" + RUNBOOK_CLOSE,
     "Oldest-first order is 38, 42, 76, 31, 8. Case 38 (transfer_count 5) is refused immediately: no case is "
     "closed, all five are untouched; exactly one email to ops@atlas.com with subject 'Manual review "
     "required: case 38'.", p, g)

p, g = make_pb([56, 71, 98, 53], refusal=None)
_add("p-b-4", "b_count_outcome",
     "Please close out the open casework for account 8 with the resolution 'Quarterly cleanup', following the "
     "runbook.\n\n" + RUNBOOK_CLOSE,
     "Oldest-first order is 56, 71, 98, 53; every close succeeds (all transfer counts <= 3). All four cases "
     "are Closed and NO notification email is sent.", p, g)

p, g = make_pb([93, 99, 74, 51, 80], refusal=99)
_add("p-b-5", "b_count_outcome",
     "Account 19's open casework needs closing -- resolution 'Handover complete', runbook applies.\n\n" + RUNBOOK_CLOSE,
     "Oldest-first order is 93, 99, 74, 51, 80. Case 93 is Closed; case 99 (transfer_count 4) is refused and "
     "untouched; cases 74, 51, 80 are untouched; exactly one email to ops@atlas.com with subject 'Manual "
     "review required: case 99'.", p, g)

# — c_source_unknown (source rotates: mail, calendar, CRM, mail, calendar) —

p, g = make_pc("agent05@atlas.com", "Renewal inquiry timing", "2025-03-16")
_add("p-c-1", "c_source_unknown",
     "I'm trying to pin down when the renewal inquiry from contact012@example.com reached us -- it might be "
     "sitting in the mailbox, or it ended up on the calendar, or it was logged as a case, I honestly don't "
     "remember. Once you've found it, send a short note to agent05@atlas.com, subject 'Renewal inquiry "
     "timing', with the date it came in.\n\n" + RUNBOOK_LOOKUP,
     "The item is email 5 (inbox, sent 2025-03-16). Exactly one new outbox email to agent05@atlas.com with "
     "subject 'Renewal inquiry timing' and a body containing '2025-03-16'; no CRM changes, no events.", p, g)

p, g = make_pc("agent06@atlas.com", "Product demo timing", "2025-12-23")
_add("p-c-2", "c_source_unknown",
     "When is the product demo with contact010@example.com happening? I couldn't say whether it's on the "
     "calendar or only mentioned in an email or a case somewhere. Please find it and send a note to "
     "agent06@atlas.com, subject 'Product demo timing', with the date.\n\n" + RUNBOOK_LOOKUP,
     "The item is calendar event 12 ('Product demo', 2025-12-23 18:00). Exactly one new outbox email to "
     "agent06@atlas.com with subject 'Product demo timing' and a body containing '2025-12-23'; no CRM "
     "changes, no events created or modified.", p, g)

p, g = make_pc("agent10@atlas.com", "Account 13 escalation timing", "2025-11-15")
_add("p-c-3", "c_source_unknown",
     "Sometime in November someone raised a high-priority issue for account 13 -- I can't tell you whether it "
     "was logged as a case, arrived by email, or was put on the calendar. Find out when it was opened and "
     "send a note to agent10@atlas.com, subject 'Account 13 escalation timing', with the date.\n\n" + RUNBOOK_LOOKUP,
     "The item is case 67 (account 13, High, created 2025-11-15). Exactly one new outbox email to "
     "agent10@atlas.com with subject 'Account 13 escalation timing' and a body containing '2025-11-15'; no "
     "CRM changes, no events.", p, g)

p, g = make_pc("agent09@atlas.com", "Proposal follow-up timing", "2025-01-27")
_add("p-c-4", "c_source_unknown",
     "There was a follow-up on a proposal from contact006@example.com at some point -- mailbox, calendar, or "
     "case, no idea where it landed. Please locate it and send a short note to agent09@atlas.com, subject "
     "'Proposal follow-up timing', with the date it reached us.\n\n" + RUNBOOK_LOOKUP,
     "The item is email 9 (inbox, 'Follow-up on proposal', sent 2025-01-27). Exactly one new outbox email to "
     "agent09@atlas.com with subject 'Proposal follow-up timing' and a body containing '2025-01-27'; no CRM "
     "changes, no events.", p, g)

p, g = make_pc("agent03@atlas.com", "QBR timing contact016", "2025-11-10")
_add("p-c-5", "c_source_unknown",
     "I need the date of the quarterly business review with contact016@example.com -- might be a calendar "
     "entry, might only exist in the mailbox or as a case note. Find it and send a note to agent03@atlas.com, "
     "subject 'QBR timing contact016', with the date.\n\n" + RUNBOOK_LOOKUP,
     "The item is calendar event 8 ('Quarterly business review' with contact016, 2025-11-10). Exactly one new "
     "outbox email to agent03@atlas.com with subject 'QBR timing contact016' and a body containing "
     "'2025-11-10'; no CRM changes, no events created or modified.", p, g)

# — d_derived_order (order derived from created_at, priority, or amount) —

p, g = make_pd(_seq_from_cases([89, 32, 30], "Case {id} reminder"))
_add("p-d-1", "d_derived_order",
     "The Open cases for account 18 need a reminder to whoever is responsible -- one mail per case, subject "
     "'Case <id> reminder' (with the case id filled in), and please work through them oldest first so the "
     "audit trail is in order.\n\n" + RUNBOOK_NOTIFY,
     "Three new outbox emails, in send order: case 89 (agent 3), case 32 (agent 5), case 30 (agent 4) -- the "
     "creation-date order 2025-04-02, 2025-06-04, 2025-10-16. Recipients are the assigned agents; subjects "
     "'Case <id> reminder'; no records modified.", p, g)

p, g = make_pd(_seq_from_cases([84, 67, 22, 18], "Case {id} escalation check"))
_add("p-d-2", "d_derived_order",
     "Please ping the owners of the non-closed cases for account 13, subject 'Case <id> escalation check' -- "
     "highest priority first, and where the priority is the same, the older case goes first.\n\n" + RUNBOOK_NOTIFY,
     "Four new outbox emails, in send order: case 84 (High, 2025-02-17), case 67 (High, 2025-11-15), case 22 "
     "(Medium), case 18 (Low), each to its assigned agent; no records modified.", p, g)

# Account 19's not-yet-won-or-lost opportunities are 12 (Negotiation), 16, 59,
# 38 -- FOUR records. The first release of this instance omitted opportunity 12
# (anchor query had filtered on Prospecting/Proposal only); gold corrected on
# 2026-07-16 before analysis, affected cells re-run (IT-057).
_PD3_SEQ = [
    (_AGENT_EMAILS[oid_owner], _subject_pattern("Opportunity {id} review", oid), f"Opportunity {oid} review")
    for oid, oid_owner in ((12, 5), (16, 1), (59, 9), (38, 4))
]
p, g = make_pd(_PD3_SEQ)
_add("p-d-3", "d_derived_order",
     "For the pipeline review, notify the owners of account 19's opportunities that are not yet won or lost "
     "-- one email each, subject 'Opportunity <id> review', biggest deal first.\n\n" + RUNBOOK_NOTIFY,
     "Four new outbox emails, in send order by amount descending: opportunity 12 (172,493, agent 5), "
     "opportunity 16 (163,965, agent 1), opportunity 59 (60,768, agent 9), opportunity 38 (22,985, agent 4); "
     "no records modified.", p, g)

p, g = make_pd(_seq_from_cases([54, 104, 81, 16], "Case {id} reminder"))
_add("p-d-4", "d_derived_order",
     "Account 16 still has cases marked Open -- please remind the responsible agents, one email per case with "
     "subject 'Case <id> reminder', starting with the case that has been open the longest.\n\n" + RUNBOOK_NOTIFY,
     "Four new outbox emails, in send order: case 54 (2025-01-13, agent 10), case 104 (2025-05-18, agent 9), "
     "case 81 (2025-09-11, agent 4), case 16 (2025-10-20, agent 7); no records modified.", p, g)

p, g = make_pd(_seq_from_cases(_PD5_IDS, "Case {id} status ping"))
_add("p-d-5", "d_derived_order",
     "Please send a status ping for account 15's Open cases that sit at Medium priority -- one mail per case "
     "to its agent, subject 'Case <id> status ping', newest case first.\n\n" + RUNBOOK_NOTIFY,
     f"Four new outbox emails for cases {_PD5_IDS} in that send order (creation date descending), each to its "
     "assigned agent; no records modified.", p, g)


# ── Output / self-check ──

VARIANT_DIRS = {
    "a_count_read": "a_count_read",
    "b_count_outcome": "b_count_outcome",
    "c_source_unknown": "c_source_unknown",
    "d_derived_order": "d_derived_order",
}


def write_instances() -> None:
    for inst in INSTANCES:
        out = INPUT_DIR / VARIANT_DIRS[inst["variant"]] / f"{inst['id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inst, indent=1))
    print(f"Wrote {len(INSTANCES)} instances to {INPUT_DIR.relative_to(REPO)}")


def selfcheck() -> int:
    """Negative + positive control for every predicate against a fresh DB."""
    from experiments.load_db import load as reset_database
    from src.core.db import get_connection

    failures = 0
    print(f"{'instance':8} {'neg(False)':>10} {'pos(True)':>10}")
    for inst in INSTANCES:
        iid = inst["id"]
        reset_database()
        conn = get_connection()
        try:
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
        print(f"{iid:8} {str(not neg):>10} {str(pos):>10}" + ("" if ok else "   <-- FAIL"))
    print("SELF-CHECK " + ("PASSED" if failures == 0 else f"FAILED ({failures})"))
    return failures


def main() -> None:
    write_instances()
    if "--selfcheck" in sys.argv:
        sys.exit(1 if selfcheck() else 0)


if __name__ == "__main__":
    main()
