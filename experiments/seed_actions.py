"""Curated action-execution instances for archetype F.

Writes 15 task instances to ``data/test_inputs/f_action_execution/`` at three
difficulty levels (5 each). The set is quadrant-balanced along the empirically
supported routing axes of the IT-015 four-quadrant rule: plan-time-decidable
small sets (low tier plus f-med-2's read-conditional branch), enumeration
scale (f-med-3/4/5), in-context aggregation (f-high-4 argmax), one canonical
multi-step pattern (f-high-3), and THREE designed runtime-feedback instances
(f-high-1 chained two-outcome, f-high-2 no-action-on-failure, f-high-5 single
branch) so the agent-decisive quadrant no longer rests on n=2 with one
accidental member (f-low-2).

Each instance has a Python predicate registered in ``PREDICATES`` that
inspects the post-execution database state and returns True if the required
outcome holds. The predicate function is the single source of truth for
ground truth; the JSON instance file carries a human-readable description of
the expected post-state for documentation and reviewers.

Pre-execution state assumes the database has been reset to the seed via
``experiments/load_db.py``. The validator runs ``load_db.py`` before each task.

Run:
    python experiments/seed_actions.py
"""

from __future__ import annotations

import json
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "f_action_execution"
SEED_DIR = REPO / "data" / "schema" / "seed"

WORKBENCH = "WorkBench (Styles et al., 2024)"
WORKARENA = "WorkArena L1/L2 (Drouin et al., 2024)"

#: Provenance label for instances that have no direct counterpart in the
#: benchmark corpus. The novel High-stratum instances (argmax-then-act,
#: runtime-feedback branching) are author-constructed probes that
#: operationalize the bipolar sub-classes of archetype F (Table 3 of the
#: thesis); only their surface style (workplace action tasks over mail and
#: CRM) follows the benchmark sources. Labeling them as benchmark-adapted
#: would overclaim provenance.
AUTHOR_NOVEL = (
    "Author-constructed (no direct benchmark counterpart); surface style follows "
    "WorkBench (Styles et al., 2024) and WorkArena L1/L2 (Drouin et al., 2024)"
)

# "New row" detection is SEED-MEMBERSHIP based, not max-id based. The seed is
# no longer id-contiguous: the archetype-B dataset (IT-043) added mail rows
# with ids 1001+/2001+ and event rows with ids 1001+/2001+ to the shared seed,
# which silently broke the earlier `id > MAX_ID` detection (seed rows counted
# as task side-effects, so correct runs could never score correct). A row
# counts as task-created iff its id is absent from the seed export.

# Cache of the seed values per table, loaded lazily for predicate-time
# comparison so each side-effect check is O(table size) without a round trip
# to disk on every call.
_SEED_CACHE: dict[str, dict[int, dict]] = {}


def _seed_rows(table: str) -> dict[int, dict]:
    if table not in _SEED_CACHE:
        path = SEED_DIR / f"{table}.json"
        rows = json.loads(path.read_text())
        _SEED_CACHE[table] = {r["id"]: r for r in rows}
    return _SEED_CACHE[table]


def _new_outbox_rows(conn: Connection) -> list:
    """All task-created outbox emails (id not in the seed export)."""
    seed_ids = set(_seed_rows("emails"))
    rows = conn.execute(
        "SELECT id, recipient, subject FROM emails WHERE status='outbox'"
    ).fetchall()
    return [r for r in rows if r["id"] not in seed_ids]


def _new_event_rows(conn: Connection) -> list:
    """All task-created calendar events (id not in the seed export)."""
    seed_ids = set(_seed_rows("events"))
    rows = conn.execute(
        "SELECT id, name, start_time, end_time, attendees, status FROM events"
    ).fetchall()
    return [r for r in rows if r["id"] not in seed_ids]


def _provenance(source: str, sub_class: str | None) -> dict:
    if source is AUTHOR_NOVEL:
        note = (
            "Instance designed by the author to operationalize the novel sub-class of "
            "archetype F (runtime-feedback dependence / in-context aggregation), following "
            "the outcome-centric task construction principle of WorkBench (Styles et al., "
            "2024). No directly liftable counterpart exists in the benchmark corpus. "
            "Specific entities (account ids, agent emails, case ids) reference the "
            "deterministic seed in seed_crm.py for stable post-state predicates."
        )
        license_ = "Original work by the author (task design); benchmark style reference only"
    else:
        note = (
            "Action-task style adapted from the source benchmark; specific entities (account ids, "
            "agent emails, case ids) reference the deterministic seed in seed_crm.py for stable "
            "post-state predicates."
        )
        license_ = "Adapted under fair use for academic research"
    if sub_class:
        note += f" Sub-class: {sub_class}."
    return {
        "source_benchmark": source,
        "adaptation": note,
        "license": license_,
    }


# ── Predicate helpers ──

def _exists(conn: Connection, sql: str, params: tuple = ()) -> bool:
    return conn.execute(sql, params).fetchone() is not None


def _count(conn: Connection, sql: str, params: tuple = ()) -> int:
    return conn.execute(sql, params).fetchone()[0]


# ── Side-effect detection helpers ──
#
# Each predicate asserts both the positive post-condition (the required change
# happened) and the negative side-effect condition (no other relevant row was
# modified). Following WorkBench (Styles et al., 2024), an outcome-centric
# score that ignores spurious writes overstates correctness; these helpers
# add the negative half so unintended side-effects flip a "correct" run to
# "incorrect".


def _no_unintended_column_change(
    conn: Connection, table: str, column: str, target_ids: set[int]
) -> bool:
    """Verify that, in *table*, no row outside *target_ids* changed *column*
    from its seed value. Used for db_update side-effect detection on cases
    and opportunities."""
    seed = _seed_rows(table)
    rows = conn.execute(f"SELECT id, {column} FROM {table}").fetchall()
    for r in rows:
        if r["id"] in target_ids:
            continue
        baseline = seed.get(r["id"])
        if baseline is None:
            return False  # row appeared from nowhere
        if r[column] != baseline[column]:
            return False
    return True


def _no_unintended_email_status_change(
    conn: Connection, target_ids: set[int], allowed_new_status: str = "deleted"
) -> bool:
    """Verify that seed emails outside *target_ids* preserved their seed
    status. Targets are allowed to have *allowed_new_status* (default
    'deleted'). Used for delete_email side-effect detection."""
    seed = _seed_rows("emails")
    rows = conn.execute("SELECT id, status FROM emails").fetchall()
    for r in rows:
        baseline = seed.get(r["id"])
        if baseline is None:
            continue  # task-created row; outbox checks handle those
        if r["id"] in target_ids:
            if r["status"] != allowed_new_status:
                return False
        else:
            if r["status"] != baseline["status"]:
                return False
    return True


def _only_expected_new_outbox(
    conn: Connection, expected_subjects: set[str]
) -> bool:
    """Verify every task-created outbox email has a subject from
    *expected_subjects*. Catches spurious sends that would slip past a
    set-membership positive check."""
    return all(r["subject"] in expected_subjects for r in _new_outbox_rows(conn))


def _count_new_outbox_with_subject(conn: Connection, subject: str) -> int:
    return sum(1 for r in _new_outbox_rows(conn) if r["subject"] == subject)


def _count_new_outbox_to_with_subject(
    conn: Connection, recipient: str, subject: str
) -> int:
    return sum(
        1
        for r in _new_outbox_rows(conn)
        if r["recipient"] == recipient and r["subject"] == subject
    )


def _only_expected_new_events(
    conn: Connection, expected_names: set[str]
) -> bool:
    """Verify every task-created event has a name in *expected_names*."""
    return all(r["name"] in expected_names for r in _new_event_rows(conn))


def _no_existing_events_changed(conn: Connection) -> bool:
    """Verify that no event with a seed id had its core fields changed."""
    seed = _seed_rows("events")
    rows = conn.execute(
        "SELECT id, name, start_time, end_time, attendees, status FROM events"
    ).fetchall()
    for r in rows:
        baseline = seed.get(r["id"])
        if baseline is None:
            continue  # task-created row; _only_expected_new_events handles it
        for f in ("name", "start_time", "end_time", "attendees", "status"):
            if r[f] != baseline[f]:
                return False
    return True


# ── Instance definitions ──

INSTANCES: list[dict] = [
    # ── LOW: one step, one tool ──
    {
        "id": "f-low-1",
        "difficulty": "low",
        "instruction": "Send an email to contact005@example.com with the subject 'Q3 status update' and the body 'Hi, I wanted to share our Q3 status update for your account. This quarter we resolved the open billing issues, completed the integration handover, and have a few recommendations to discuss for next quarter. Let me know if you would like to set up a short call. Best regards, Account Team.'",
        "expected_post_state": "Exactly one new outbox row exists with recipient='contact005@example.com' and subject='Q3 status update'; no other outbox rows were added.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-low-2",
        "difficulty": "low",
        "instruction": "Update the status of case 6 to 'Closed'.",
        "expected_post_state": "cases.id=6 has status='Closed' (was 'In Progress' in the seed).",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-low-3",
        "difficulty": "low",
        "instruction": "Create a calendar event called 'Sales review' on 2026-06-15 from 10:00 to 11:00 with attendee contact010@example.com.",
        "expected_post_state": "An events row exists with name='Sales review', start_time='2026-06-15 10:00:00', and 'contact010@example.com' in attendees.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-low-4",
        "difficulty": "low",
        "instruction": "Delete the email with id 5.",
        "expected_post_state": "emails.id=5 has status='deleted'.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-low-5",
        "difficulty": "low",
        "instruction": "Set the priority of case 14 to 'High'.",
        "expected_post_state": "cases.id=14 has priority='High' (was 'Low' in the seed).",
        "sub_class": None,
        "source": WORKBENCH,
    },
    # ── MEDIUM: two to three steps, two tools ──
    {
        "id": "f-med-1",
        "difficulty": "med",
        "instruction": "For every case currently assigned to agent 3 that has status 'Open', set the status to 'In Progress'.",
        "expected_post_state": "Each of cases.id in {8, 57, 68, 89} (the open cases for agent 3 in the seed) has status='In Progress'.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-med-2",
        "difficulty": "med",
        "instruction": "Schedule a call named 'Contract sync' with contact010@example.com on 2025-12-23. The preferred slot is 18:00 to 18:45. First check their calendar for that date: if they already have an event that overlaps the preferred slot, book 20:00 to 20:45 instead. Create exactly one event, with contact010@example.com as attendee.",
        "expected_post_state": "Because contact010@example.com already has an event on 2025-12-23 from 18:00 to 18:45 in the seed (event 12, 'Product demo'), the preferred slot is taken: exactly one new events row exists with name='Contract sync' and start_time='2025-12-23 20:00:00' with contact010@example.com in attendees. No new event at 18:00 exists, no other events were created or modified, no emails were sent.",
        "sub_class": "read_conditional (plan-time-decidable branch on read results)",
        "source": AUTHOR_NOVEL,
    },
    {
        "id": "f-med-3",
        "difficulty": "med",
        "instruction": "Reassign all cases currently assigned to agent 5 to agent 8.",
        "expected_post_state": "No cases row has agent_id=5; all cases that were assigned to agent 5 in the seed (ids 31, 32, 33, 42, 48, 53, 78, 93, 98) now have agent_id=8.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-med-4",
        "difficulty": "med",
        "instruction": "Downgrade every opportunity currently in stage 'Negotiation' to stage 'Proposal'.",
        "expected_post_state": "No opportunities row has stage='Negotiation'; the 16 opportunities that were in 'Negotiation' in the seed now have stage='Proposal'.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    {
        "id": "f-med-5",
        "difficulty": "med",
        "instruction": "Send a follow-up email to the primary contact of each account in the 'APAC' region. Subject: 'APAC quarterly check-in'. Body: 'Hi, just touching base on your account this quarter. I would like to set up a short check-in to review progress and any open items on your side. Please reply with a time that works in the next two weeks. Best regards, APAC Team.'",
        "expected_post_state": "For each of the 7 APAC accounts (ids 1, 2, 4, 5, 8, 17, 18), exactly one new outbox row exists with recipient equal to the lowest-id contact's email and subject='APAC quarterly check-in'; no other outbox rows with this subject were added.",
        "sub_class": None,
        "source": WORKBENCH,
    },
    # ── HIGH novel: runtime-feedback sub-classes (chained, no-action) ──
    {
        "id": "f-high-1",
        "difficulty": "high",
        "instruction": "Please close out the two remaining open cases for account 10 -- that's case 47 and case 75 -- with the resolution 'Service credit applied', and make sure the customer and our ops team are informed as the support runbook requires.\n\nSupport runbook (excerpt):\n- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.\n- For every case that is successfully closed, notify the account's primary contact (the lowest-id contact at that account) by email: subject 'Case <id> closed' (substitute the actual case id), short confirmation body.\n- For every close the back-end refuses, leave the case untouched and escalate by email to ops@atlas.com: subject 'Escalation required: case <id>', body quoting the back-end's stated reason.",
        "expected_post_state": "Case 75 (transfer_count=0) closes: status='Closed'. Case 47 (transfer_count=4) is blocked by the escalation rule: status remains 'Open'. Exactly one outbox row to contact018@example.com (account 10's primary contact) with subject='Case 75 closed'; exactly one outbox row to ops@atlas.com with subject='Escalation required: case 47'. Zero rows with subject 'Case 47 closed' or 'Escalation required: case 75'. No other case changed.",
        "sub_class": "novel (runtime-feedback, chained: two independent action outcomes)",
        "source": AUTHOR_NOVEL,
    },
    {
        "id": "f-high-2",
        "difficulty": "high",
        "instruction": "Case 7 looks like a duplicate of case 12 -- please close it with the resolution 'Duplicate of case 12' and handle the follow-up as the support runbook requires.\n\nSupport runbook (excerpt):\n- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.\n- After a successful duplicate close, set the case's priority to 'Low' and confirm to ops@atlas.com by email: subject 'Case <id> closed'.\n- If the back-end refuses the close, the case is under escalation review: do not modify the case in any way (no status, priority, or assignment changes through any tool), and notify ops@atlas.com by email: subject 'Manual review required: case <id>', body quoting the back-end's stated reason.",
        "expected_post_state": "Case 7 (transfer_count=4) is blocked by the escalation rule: the case row is completely unchanged (status='Open', priority='High', agent_id=2). Exactly one outbox row to ops@atlas.com with subject='Manual review required: case 7'. Zero rows with subject 'Case 7 closed'. Forcing the closure or priority change via db_update fails the predicate.",
        "sub_class": "novel (runtime-feedback, no-action-on-failure)",
        "source": AUTHOR_NOVEL,
    },
    # ── HIGH canonical: familiar WorkBench-style multi-step pattern ──
    {
        "id": "f-high-3",
        "difficulty": "high",
        "instruction": "For every won opportunity (is_won=1) belonging to an account in the 'EMEA' region, create a calendar event named 'Quarterly review' on 2026-09-15 from 14:00 to 14:30 with the account's primary contact as an attendee.",
        "expected_post_state": "For each unique EMEA-won-account (accounts 3, 10, 6, 20, 9, 13), at least one new events row exists with name='Quarterly review', start_time='2026-09-15 14:00:00', and the account's primary-contact email in attendees. No newly created event has any other name; no existing seed event was modified.",
        "sub_class": "canonical",
        "source": WORKBENCH,
    },
    # ── HIGH novel: uncommon combinations (argmax-then-act, conditional branching) ──
    {
        "id": "f-high-4",
        "difficulty": "high",
        "instruction": "Among the agents on the EMEA team, find the one who currently has the most cases with status 'Open'. Send that agent an email with subject 'Workload review' and body 'Hi, a quick note that you currently have the highest open case load on the EMEA team. Please let me know if you would like to reprioritize or get backup on any of the active cases. Best regards, Operations.'",
        "expected_post_state": "Exactly one new outbox row exists with recipient='agent05@atlas.com' (agent 5 has the most Open cases among EMEA agents 1, 5, 7, 10) and subject='Workload review'; no outbox row with that subject went to any other recipient.",
        "sub_class": "novel",
        "source": AUTHOR_NOVEL,
    },
    {
        "id": "f-high-5",
        "difficulty": "high",
        "instruction": "The refund for case 47 has been processed on our side -- please get the case closed with the resolution 'Refund processed' and keep the customer in the loop as the support runbook requires.\n\nSupport runbook (excerpt):\n- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close.\n- If the case closes, email the account's primary contact (the lowest-id contact at that account): subject 'Case <id> resolved', brief body confirming the refund and the closure.\n- If the close is refused, email the same primary contact instead: subject 'Case <id> update', brief body explaining the case is still under review with a follow-up to come.\n- The customer receives exactly ONE of the two notifications, matching the actual outcome.",
        "expected_post_state": "Because case 47 has transfer_count=4 in the seed, the back-end's escalation rule blocks the close: case 47 status remains 'Open'. Exactly one new outbox row exists, addressed to the primary contact of account 10 (case 47's account), with subject='Case 47 update'. No outbox row with subject='Case 47 resolved' exists. No other outbox rows are added.",
        "sub_class": "novel",
        "source": AUTHOR_NOVEL,
    },
]


# ── Predicate implementations ──

def _p_low_1(conn: Connection) -> bool:
    """Send Q3 status email to contact005. No other outbox sends, no email status changes."""
    sent = _count_new_outbox_to_with_subject(
        conn, "contact005@example.com", "Q3 status update"
    )
    no_spurious = _only_expected_new_outbox(conn, {"Q3 status update"})
    no_email_changes = _no_unintended_email_status_change(conn, target_ids=set())
    return sent == 1 and no_spurious and no_email_changes


def _p_low_2(conn: Connection) -> bool:
    """Close case 6. No other case status changes."""
    row = conn.execute("SELECT status FROM cases WHERE id=6").fetchone()
    target_ok = row is not None and row["status"] == "Closed"
    no_other = _no_unintended_column_change(
        conn, "cases", "status", target_ids={6}
    )
    return target_ok and no_other


def _p_low_3(conn: Connection) -> bool:
    """Create 'Sales review' event. No other new events, no existing events modified."""
    matched = sum(
        1
        for r in _new_event_rows(conn)
        if r["name"] == "Sales review"
        and r["start_time"] == "2026-06-15 10:00:00"
        and "contact010@example.com" in r["attendees"]
        and r["status"] == "confirmed"
    )
    no_spurious_new = _only_expected_new_events(conn, {"Sales review"})
    no_existing_changed = _no_existing_events_changed(conn)
    return matched >= 1 and no_spurious_new and no_existing_changed


def _p_low_4(conn: Connection) -> bool:
    """Delete email 5. No other emails get status='deleted' or any other change."""
    row = conn.execute("SELECT status FROM emails WHERE id=5").fetchone()
    target_ok = row is not None and row["status"] == "deleted"
    no_other = _no_unintended_email_status_change(conn, target_ids={5})
    seed_ids = set(_seed_rows("emails"))
    all_ids = [r["id"] for r in conn.execute("SELECT id FROM emails").fetchall()]
    no_spurious_new = all(i in seed_ids for i in all_ids)
    return target_ok and no_other and no_spurious_new


def _p_low_5(conn: Connection) -> bool:
    """Set case 14 priority to High. No other case priority changes."""
    row = conn.execute("SELECT priority FROM cases WHERE id=14").fetchone()
    target_ok = row is not None and row["priority"] == "High"
    no_other = _no_unintended_column_change(
        conn, "cases", "priority", target_ids={14}
    )
    return target_ok and no_other


def _p_med_1(conn: Connection) -> bool:
    """Open cases of agent 3 → In Progress. No other case status changes."""
    targets = {8, 57, 68, 89}
    rows = conn.execute(
        f"SELECT status FROM cases WHERE id IN ({','.join('?' * len(targets))})",
        tuple(targets),
    ).fetchall()
    targets_ok = len(rows) == len(targets) and all(
        r["status"] == "In Progress" for r in rows
    )
    no_other = _no_unintended_column_change(conn, "cases", "status", targets)
    return targets_ok and no_other


def _p_med_2(conn: Connection) -> bool:
    """Read-conditional calendar booking: preferred slot is taken in the seed
    (event 12, contact010, 2025-12-23 18:00-18:45), so the correct outcome is
    exactly ONE new 'Contract sync' event at the 20:00 fallback slot. A plan
    that books the preferred slot without reading the calendar, or books both
    slots defensively, fails."""
    sync = [r for r in _new_event_rows(conn) if r["name"] == "Contract sync"]
    if len(sync) != 1:
        return False
    ev = sync[0]
    slot_ok = (
        ev["start_time"] == "2025-12-23 20:00:00"
        and "contact010@example.com" in ev["attendees"]
        and ev["status"] == "confirmed"
    )
    no_spurious_new = _only_expected_new_events(conn, {"Contract sync"})
    no_existing_changed = _no_existing_events_changed(conn)
    no_mail = len(_new_outbox_rows(conn)) == 0
    return slot_ok and no_spurious_new and no_existing_changed and no_mail


def _p_med_3(conn: Connection) -> bool:
    """Reassign agent 5's cases to agent 8. No other case reassignments."""
    targets = {31, 32, 33, 42, 48, 53, 78, 93, 98}
    no_more_5 = _count(conn, "SELECT COUNT(*) FROM cases WHERE agent_id=5") == 0
    moved = conn.execute(
        f"SELECT agent_id FROM cases WHERE id IN ({','.join('?' * len(targets))})",
        tuple(targets),
    ).fetchall()
    targets_ok = (
        no_more_5
        and len(moved) == len(targets)
        and all(r["agent_id"] == 8 for r in moved)
    )
    no_other = _no_unintended_column_change(conn, "cases", "agent_id", targets)
    return targets_ok and no_other


def _p_med_4(conn: Connection) -> bool:
    """Negotiation opps → Proposal. No other opportunity stage changes."""
    seed_opps = _seed_rows("opportunities")
    targets = {oid for oid, row in seed_opps.items() if row["stage"] == "Negotiation"}
    target_rows = conn.execute(
        f"SELECT stage FROM opportunities WHERE id IN ({','.join('?' * len(targets))})",
        tuple(targets),
    ).fetchall()
    targets_ok = len(target_rows) == len(targets) and all(
        r["stage"] == "Proposal" for r in target_rows
    )
    no_negotiation_left = (
        _count(conn, "SELECT COUNT(*) FROM opportunities WHERE stage='Negotiation'") == 0
    )
    no_other = _no_unintended_column_change(conn, "opportunities", "stage", targets)
    return targets_ok and no_negotiation_left and no_other


def _p_med_5(conn: Connection) -> bool:
    """APAC quarterly check-in to each APAC primary contact. No spurious sends."""
    apac_primaries = {
        "contact001@example.com",
        "contact003@example.com",
        "contact007@example.com",
        "contact010@example.com",
        "contact015@example.com",
        "contact036@example.com",
        "contact039@example.com",
    }
    each_received = all(
        _count_new_outbox_to_with_subject(conn, r, "APAC quarterly check-in") >= 1
        for r in apac_primaries
    )
    # No outbox with this subject went to anyone outside the APAC primaries.
    rows = [
        r for r in _new_outbox_rows(conn) if r["subject"] == "APAC quarterly check-in"
    ]
    no_off_target = all(r["recipient"] in apac_primaries for r in rows)
    no_spurious_subject = _only_expected_new_outbox(
        conn, {"APAC quarterly check-in"}
    )
    return each_received and no_off_target and no_spurious_subject


def _p_high_1(conn: Connection) -> bool:
    """Chained runtime feedback: two independent close attempts, one succeeds
    (case 75, transfer_count=0), one is blocked (case 47, transfer_count=4).
    The correct follow-up set exists only in the world the runtime outcomes
    select: 'Case 75 closed' to the primary contact AND 'Escalation required:
    case 47' to ops. Optimistic, defensive, or swapped plans fail."""
    c47 = conn.execute("SELECT status FROM cases WHERE id=47").fetchone()
    c75 = conn.execute("SELECT status FROM cases WHERE id=75").fetchone()
    if c47 is None or c75 is None:
        return False
    if c47["status"] != "Open" or c75["status"] != "Closed":
        return False
    # Only case 75 may have changed status (via the close tool).
    if not _no_unintended_column_change(conn, "cases", "status", target_ids={75}):
        return False
    closed_mail = _count_new_outbox_to_with_subject(
        conn, "contact018@example.com", "Case 75 closed"
    )
    escalation_mail = _count_new_outbox_to_with_subject(
        conn, "ops@atlas.com", "Escalation required: case 47"
    )
    wrong_branch = (
        _count_new_outbox_with_subject(conn, "Case 47 closed")
        + _count_new_outbox_with_subject(conn, "Escalation required: case 75")
    )
    only_expected = _only_expected_new_outbox(
        conn, {"Case 75 closed", "Escalation required: case 47"}
    )
    return (
        closed_mail == 1 and escalation_mail == 1 and wrong_branch == 0 and only_expected
    )


def _p_high_2(conn: Connection) -> bool:
    """Runtime feedback with a no-action obligation: case 7 (transfer_count=4)
    is blocked, and the correct behaviour is to leave the case COMPLETELY
    unchanged and escalate by email. Forcing the close or the priority change
    through db_update fails; so does sending the success-branch email."""
    row = conn.execute(
        "SELECT status, priority, agent_id FROM cases WHERE id=7"
    ).fetchone()
    if row is None:
        return False
    if row["status"] != "Open" or row["priority"] != "High" or row["agent_id"] != 2:
        return False
    # No case anywhere may have changed status, priority, or assignment.
    for col in ("status", "priority", "agent_id"):
        if not _no_unintended_column_change(conn, "cases", col, target_ids=set()):
            return False
    review_mail = _count_new_outbox_to_with_subject(
        conn, "ops@atlas.com", "Manual review required: case 7"
    )
    closed_mail = _count_new_outbox_with_subject(conn, "Case 7 closed")
    only_expected = _only_expected_new_outbox(conn, {"Manual review required: case 7"})
    return review_mail == 1 and closed_mail == 0 and only_expected


def _p_high_3(conn: Connection) -> bool:
    """Quarterly review events for each EMEA-won account's primary contact."""
    expected_attendees = {
        "contact005@example.com",  # account 3
        "contact018@example.com",  # account 10
        "contact012@example.com",  # account 6
        "contact043@example.com",  # account 20
        "contact017@example.com",  # account 9
        "contact026@example.com",  # account 13
    }
    # Each expected attendee appears in at least one new 'Quarterly review' event.
    new_reviews = [
        r
        for r in _new_event_rows(conn)
        if r["name"] == "Quarterly review"
        and r["start_time"] == "2026-09-15 14:00:00"
        and r["status"] == "confirmed"
    ]
    each_invited = all(
        any(attendee in r["attendees"] for r in new_reviews)
        for attendee in expected_attendees
    )
    no_spurious_new = _only_expected_new_events(conn, {"Quarterly review"})
    no_existing_changed = _no_existing_events_changed(conn)
    return each_invited and no_spurious_new and no_existing_changed


def _p_high_4(conn: Connection) -> bool:
    """Workload review email to argmax EMEA-team agent (agent05). No off-target."""
    sent = _count_new_outbox_to_with_subject(
        conn, "agent05@atlas.com", "Workload review"
    )
    no_spurious = _only_expected_new_outbox(conn, {"Workload review"})
    no_email_changes = _no_unintended_email_status_change(conn, target_ids=set())
    return sent == 1 and no_spurious and no_email_changes


def _p_high_5(conn: Connection) -> bool:
    """Runtime-feedback bipolar instance.

    Setup: case 47 has transfer_count=4 (seed override), so attempt_close_case
    is blocked by the back-end's escalation rule. The correct outcome is:
        - case 47 status is still 'Open' (close was blocked),
        - exactly one outbox email to account 10's primary contact (the lowest-
          id contact at that account) with subject='Case 47 update',
        - zero outbox emails with subject='Case 47 resolved',
        - no other side-effects.

    Defensive workflow plans that send both subjects fail the second clause;
    optimistic plans that only send 'Case 47 resolved' fail the third.
    """
    # 1. case 47 must not have been closed
    case = conn.execute("SELECT status, account_id FROM cases WHERE id=47").fetchone()
    if case is None or case["status"] == "Closed":
        return False
    # 2. no other case status changed (defensive plans must not mutate around)
    no_other_case_change = _no_unintended_column_change(
        conn, "cases", "status", target_ids={47}
    )
    if not no_other_case_change:
        return False
    # 3. find primary contact (lowest contact id at case 47's account)
    primary = conn.execute(
        "SELECT email FROM contacts WHERE account_id=? ORDER BY id LIMIT 1",
        (case["account_id"],),
    ).fetchone()
    if primary is None:
        return False
    target_contact = primary["email"]
    # 4. exactly one 'Case 47 update' email to that contact
    updates_sent = _count_new_outbox_to_with_subject(
        conn, target_contact, "Case 47 update"
    )
    if updates_sent != 1:
        return False
    # 5. zero 'Case 47 resolved' emails (anywhere)
    if _count_new_outbox_with_subject(conn, "Case 47 resolved") != 0:
        return False
    # 6. no other new outbox sends with off-target subjects
    no_spurious_subject = _only_expected_new_outbox(
        conn, {"Case 47 update"}
    )
    return no_spurious_subject


PREDICATES: dict[str, Callable[[Connection], bool]] = {
    "f-low-1": _p_low_1,
    "f-low-2": _p_low_2,
    "f-low-3": _p_low_3,
    "f-low-4": _p_low_4,
    "f-low-5": _p_low_5,
    "f-med-1": _p_med_1,
    "f-med-2": _p_med_2,
    "f-med-3": _p_med_3,
    "f-med-4": _p_med_4,
    "f-med-5": _p_med_5,
    "f-high-1": _p_high_1,
    "f-high-2": _p_high_2,
    "f-high-3": _p_high_3,
    "f-high-4": _p_high_4,
    "f-high-5": _p_high_5,
}


def main() -> None:
    for inst in INSTANCES:
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "F",
            "difficulty": inst["difficulty"],
            "sub_class": inst["sub_class"],
            "instruction": inst["instruction"],
            "expected_post_state": inst["expected_post_state"],
            "provenance": _provenance(inst["source"], inst["sub_class"]),
        }
        (directory / f"{inst['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"Wrote {len(INSTANCES)} instances under {INPUT_DIR.relative_to(REPO)}")
    print(f"Predicates registered: {len(PREDICATES)} (one per instance)")
    print("Run experiments/load_db.py before each validation task to reset DB to seed state.")


if __name__ == "__main__":
    main()
