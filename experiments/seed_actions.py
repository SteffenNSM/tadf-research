"""Curated action-execution instances for archetype F.

Writes 15 task instances to ``data/test_inputs/f_action_execution/`` at three
difficulty levels (5 each). The high stratum splits explicitly into three
canonical (familiar WorkBench-style multi-step patterns) and two novel
(uncommon combinations such as argmax-then-act or conditional branching)
sub-classes, so the bipolar Step Predictability of F can be observed directly
in the data.

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

# Highest ids in the freshly generated seed; any row with a larger id was
# created by the task and counts as a candidate side-effect. Tied to
# experiments/seed_crm.py.
SEED_EMAIL_MAX_ID = 20
SEED_EVENT_MAX_ID = 12

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
    rows = conn.execute(
        "SELECT id, status FROM emails WHERE id <= ?", (SEED_EMAIL_MAX_ID,)
    ).fetchall()
    for r in rows:
        baseline = seed.get(r["id"])
        if baseline is None:
            return False
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
    """Verify every new outbox email (id > SEED_EMAIL_MAX_ID) has a subject
    from *expected_subjects*. Catches spurious sends that would slip past a
    set-membership positive check."""
    rows = conn.execute(
        "SELECT subject FROM emails WHERE id > ? AND status='outbox'",
        (SEED_EMAIL_MAX_ID,),
    ).fetchall()
    return all(r["subject"] in expected_subjects for r in rows)


def _count_new_outbox_with_subject(conn: Connection, subject: str) -> int:
    return _count(
        conn,
        "SELECT COUNT(*) FROM emails WHERE id > ? AND subject = ? AND status='outbox'",
        (SEED_EMAIL_MAX_ID, subject),
    )


def _count_new_outbox_to_with_subject(
    conn: Connection, recipient: str, subject: str
) -> int:
    return _count(
        conn,
        "SELECT COUNT(*) FROM emails WHERE id > ? AND recipient = ? AND subject = ? AND status='outbox'",
        (SEED_EMAIL_MAX_ID, recipient, subject),
    )


def _only_expected_new_events(
    conn: Connection, expected_names: set[str]
) -> bool:
    """Verify every newly created event has a name in *expected_names*."""
    rows = conn.execute(
        "SELECT name FROM events WHERE id > ?",
        (SEED_EVENT_MAX_ID,),
    ).fetchall()
    return all(r["name"] in expected_names for r in rows)


def _no_existing_events_changed(conn: Connection) -> bool:
    """Verify that no event with a seed id had its core fields changed."""
    seed = _seed_rows("events")
    rows = conn.execute(
        "SELECT id, name, start_time, end_time, attendees, status FROM events WHERE id <= ?",
        (SEED_EVENT_MAX_ID,),
    ).fetchall()
    for r in rows:
        baseline = seed.get(r["id"])
        if baseline is None:
            return False
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
        "instruction": "Find the primary contact of account 7 (the contact at that account with the lowest id) and send them an email with subject 'Renewal discussion' and body 'Hi, your renewal is coming up and I would like to find a time next week to walk through the options together. Could you let me know which days work for you? Best regards, Renewals Team.'",
        "expected_post_state": "Exactly one new outbox row exists with recipient='contact013@example.com' (account 7's lowest-id contact) and subject='Renewal discussion'; no other outbox rows were added.",
        "sub_class": None,
        "source": WORKBENCH,
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
    # ── HIGH canonical: familiar WorkBench-style multi-step patterns ──
    {
        "id": "f-high-1",
        "difficulty": "high",
        "instruction": "Find every High-priority case currently assigned to agent 1 that is still Open. For each such case, send the agent (agent01@atlas.com) an email with subject 'High-priority case <case_id>' (substitute the actual case id) and a body asking them to provide a status update and an expected resolution date for the case.",
        "expected_post_state": "Exactly two new outbox rows exist with recipient='agent01@atlas.com' and subjects {'High-priority case 40', 'High-priority case 118'}; no other outbox rows with that recipient and 'High-priority case' subject prefix.",
        "sub_class": "canonical",
        "source": WORKBENCH,
    },
    {
        "id": "f-high-2",
        "difficulty": "high",
        "instruction": "For every opportunity in stage 'Proposal' that belongs to an account in the 'Technology' industry, send an email to the account's primary contact (the contact with the lowest id at that account). Subject: 'Proposal follow-up'. Body: 'Hi, following up on the proposal we sent over. I would like to schedule a short call to discuss any questions and the next steps on your side. Please share a time that works in the coming week. Best regards, Sales Team.'",
        "expected_post_state": "At least one new outbox row per unique primary contact of the Technology+Proposal accounts (recipients are contact012@example.com and contact033@example.com) with subject='Proposal follow-up'. No outbox row with that subject was sent to any other recipient.",
        "sub_class": "canonical",
        "source": WORKBENCH,
    },
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
        "instruction": "Use the attempt_close_case tool to try to close case 47 with the resolution summary 'Refund processed'. If the close succeeds, send the primary contact of case 47's account (the lowest-id contact at that account) an email with subject 'Case 47 resolved' and a brief body confirming that the refund is being processed and that the case is now closed. If the close is blocked by a business rule (the tool returns closed=false), send the same primary contact an email with subject 'Case 47 update' and a brief body explaining that the case is still under review and that you will follow up once it is resolved. Send exactly one of the two emails depending on the outcome of the close attempt.",
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
    matched = _count(
        conn,
        "SELECT COUNT(*) FROM events WHERE name='Sales review' AND start_time='2026-06-15 10:00:00' AND attendees LIKE '%contact010@example.com%' AND status='confirmed' AND id > ?",
        (SEED_EVENT_MAX_ID,),
    )
    no_spurious_new = _only_expected_new_events(conn, {"Sales review"})
    no_existing_changed = _no_existing_events_changed(conn)
    return matched >= 1 and no_spurious_new and no_existing_changed


def _p_low_4(conn: Connection) -> bool:
    """Delete email 5. No other emails get status='deleted' or any other change."""
    row = conn.execute("SELECT status FROM emails WHERE id=5").fetchone()
    target_ok = row is not None and row["status"] == "deleted"
    no_other = _no_unintended_email_status_change(conn, target_ids={5})
    no_spurious_new = (
        _count(conn, "SELECT COUNT(*) FROM emails WHERE id > ?", (SEED_EMAIL_MAX_ID,)) == 0
    )
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
    """Renewal discussion email to account 7's primary contact. No spurious sends."""
    sent = _count_new_outbox_to_with_subject(
        conn, "contact013@example.com", "Renewal discussion"
    )
    no_spurious = _only_expected_new_outbox(conn, {"Renewal discussion"})
    no_email_changes = _no_unintended_email_status_change(conn, target_ids=set())
    return sent == 1 and no_spurious and no_email_changes


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
    rows = conn.execute(
        "SELECT recipient FROM emails WHERE id > ? AND status='outbox' AND subject='APAC quarterly check-in'",
        (SEED_EMAIL_MAX_ID,),
    ).fetchall()
    no_off_target = all(r["recipient"] in apac_primaries for r in rows)
    no_spurious_subject = _only_expected_new_outbox(
        conn, {"APAC quarterly check-in"}
    )
    return each_received and no_off_target and no_spurious_subject


def _p_high_1(conn: Connection) -> bool:
    """Two high-priority case alerts to agent 1. No off-target sends."""
    expected_subjects = {"High-priority case 40", "High-priority case 118"}
    each_sent = all(
        _count_new_outbox_to_with_subject(conn, "agent01@atlas.com", s) >= 1
        for s in expected_subjects
    )
    # No outbox with a 'High-priority case' subject prefix went anywhere unexpected.
    rows = conn.execute(
        "SELECT recipient, subject FROM emails WHERE id > ? AND status='outbox' AND subject LIKE 'High-priority case%'",
        (SEED_EMAIL_MAX_ID,),
    ).fetchall()
    no_off_target = all(
        r["recipient"] == "agent01@atlas.com" and r["subject"] in expected_subjects
        for r in rows
    )
    no_spurious_subject = _only_expected_new_outbox(conn, expected_subjects)
    return each_sent and no_off_target and no_spurious_subject


def _p_high_2(conn: Connection) -> bool:
    """Proposal follow-up to Technology+Proposal primary contacts. No off-target."""
    expected_recipients = {"contact012@example.com", "contact033@example.com"}
    each_received = all(
        _count_new_outbox_to_with_subject(conn, r, "Proposal follow-up") >= 1
        for r in expected_recipients
    )
    rows = conn.execute(
        "SELECT recipient FROM emails WHERE id > ? AND status='outbox' AND subject='Proposal follow-up'",
        (SEED_EMAIL_MAX_ID,),
    ).fetchall()
    no_off_target = all(r["recipient"] in expected_recipients for r in rows)
    no_spurious_subject = _only_expected_new_outbox(conn, {"Proposal follow-up"})
    return each_received and no_off_target and no_spurious_subject


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
    each_invited = True
    for attendee in expected_attendees:
        n = _count(
            conn,
            "SELECT COUNT(*) FROM events WHERE id > ? AND name='Quarterly review' AND start_time='2026-09-15 14:00:00' AND status='confirmed' AND attendees LIKE ?",
            (SEED_EVENT_MAX_ID, f"%{attendee}%"),
        )
        if n < 1:
            each_invited = False
            break
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
    resolved_sent = _count(
        conn,
        "SELECT COUNT(*) FROM emails WHERE id > ? AND status='outbox' AND subject='Case 47 resolved'",
        (SEED_EMAIL_MAX_ID,),
    )
    if resolved_sent != 0:
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
