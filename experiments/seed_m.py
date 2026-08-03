"""Curated state-drift instances for Phase 2b family M.

Family M ("Moving Target" / "Bewegliches Ziel", build decision in
``notebooks/results_analysis.ipynb`` Section 5 and IT-055) resolves framework
row 2.3: does an environment state change DURING execution behave like
runtime feedback (agent territory), or do re-read guards suffice? It writes
15 instances to ``data/test_inputs/m_state_drift/`` in three variants
(5 each), all on the frozen CRM seed, scored by outcome-centric post-state
predicates:

- **m1_observable_drift** -- close two cases oldest-first; when the run
  closes the first, a "colleague" closes the second (drift). The stale
  follow-up produces an OBSERVABLE tool response (attempt_close_case
  returns "case is already closed"), and the runbook prescribes the
  already-closed branch: leave untouched, no notification.
- **m2_silent_drift** -- two ordered field changes; the first write triggers
  the drift that closes the second target. The stale second write succeeds
  SILENTLY (db_update gives no policy signal), while the runbook states the
  norm "closed cases are never modified" WITHOUT mandating a re-check.
  Measures baseline vigilance under silent drift for both paradigms.
- **m3_guarded_drift** -- identical shape to m2, but the runbook adds an
  explicit guard: "records can change while you work: immediately before
  every modification, re-check the record's current status." Tests whether
  an INSTRUCTED guard rescues either paradigm -- the agent can execute the
  re-check and branch; the canonical two-stage workflow can plan the
  re-read but cannot branch on its result.

**Drift operationalization (deterministic, paradigm-fair).** Each instance's
overlay installs a SQLite TRIGGER: the drift fires when the run performs its
own FIRST state-changing write on the trigger case (e.g., closing case A
externally closes case B with the sentinel timestamp 2026-01-01 00:00:00).
Anchoring the drift to the run's first write guarantees the identical causal
position for both paradigms -- after the initial reads, before the dependent
action -- which a wall-clock trigger could not. Limitation, stated: drift
cannot occur before the run's first write by construction. The trigger DDL
is exported per instance for reviewers, and the DB reset drops it with the
tables (clean pre-state per run, IT-003 discipline).

Per the IT-055 DSR note, no routing expectation is attached to any variant.
Both paradigm implementations are reused UNCHANGED from archetype F. Input
neutrality follows the IT-049/051 design law; the ordered-changes rule and
the re-check rule are policy lines a real runbook would contain, identical
for both paradigms. Anchor discipline: all case anchors are asserted against
the seed at import (non-closed, closable transfer counts, observable
priority deltas, distinct targets).

Run:
    PYTHONPATH=. python experiments/seed_m.py               # write instances
    PYTHONPATH=. python experiments/seed_m.py --selfcheck   # verify predicates
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from sqlite3 import Connection
from typing import Callable

from experiments.seed_actions import _new_event_rows, _new_outbox_rows, _seed_rows
from experiments.seed_p import _cases_unchanged, _subject_pattern
from experiments.seed_x import _opps_unchanged

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "m_state_drift"

USER = "user@atlas.com"
SENTINEL = "2026-01-01 00:00:00"

PROVENANCE = {
    "source_benchmark": (
        "Author-constructed (Phase 2b family M, state drift); surface style "
        "follows WorkBench (Styles et al., 2024) and the archetype-F instances"
    ),
    "adaptation": (
        "Instance designed by the author to operationalize mid-run state drift "
        "(build decision IT-055; Liu & Li 2012 'variability' gap): a per-instance "
        "SQLite trigger closes a second target case when the run performs its "
        "first state-changing write, i.e. at the identical causal position for "
        "both paradigms. Variants separate observable drift (tool feedback), "
        "silent drift (no signal), and instructed re-check guards. Paradigms "
        "reused unchanged from archetype F."
    ),
    "license": "Original work by the author (task design); benchmark style reference only",
}

Predicate = Callable[[Connection], bool]
Gold = Callable[[Connection], None]

_CASES = _seed_rows("cases")
_CONTACTS = _seed_rows("contacts")

RUNBOOK_M1 = """Support runbook (excerpt):
- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.
- Work oldest-first by creation date.
- If a close succeeds: notify the account's primary contact (the lowest-id contact at that account) by email, subject 'Case <id> closed' (substitute the case id), short confirmation body.
- If the back-end reports a case is already closed: leave it fully untouched and send no notification for it."""

RUNBOOK_M2 = """Data-hygiene runbook (excerpt):
- Work through the changes in the order given.
- Closed cases are never modified -- no status, priority, or assignment changes through any tool.
- Apply exactly the stated changes; leave all other records untouched; no notifications for routine field changes."""

RUNBOOK_M3 = RUNBOOK_M2 + """
- Records can change while you work: immediately before every modification, re-check the record's current status."""


def _primary_contact(account_id: int) -> str:
    ids = sorted(cid for cid, c in _CONTACTS.items() if c["account_id"] == account_id)
    return _CONTACTS[ids[0]]["email"]


# ── Drift triggers (per instance, exported) ──

TRIGGERS: dict[str, str] = {}


def _trigger_close_on_update(iid: str, watch_case: int, drift_case: int, on_close_only: bool) -> str:
    """Drift DDL: when the run writes *watch_case*, close *drift_case*."""
    when = f"NEW.id = {watch_case}"
    if on_close_only:
        when += " AND NEW.status = 'Closed'"
    return (
        f"CREATE TRIGGER drift_{iid.replace('-', '_')} AFTER UPDATE ON cases "
        f"WHEN {when} "
        f"BEGIN UPDATE cases SET status='Closed', closed_at='{SENTINEL}' "
        f"WHERE id = {drift_case} AND status != 'Closed'; END;"
    )


def _trigger_symmetric_pair(iid: str, a: int, b: int) -> str:
    """Race-free m1 drift (IT-064): whichever pair case the run closes FIRST,
    the 'colleague' closes the other (sentinel timestamp).

    Two one-directional triggers; SQLite serializes writes, and with the
    atomic close (database.py, IT-064) every interleaving -- sequential in
    either order, or parallel tool calls -- yields the same deterministic
    outcome pattern: exactly one case closed by the run, exactly one closed
    by the drift. Recursive firing is impossible (recursive_triggers is off,
    and the guarded UPDATE is a no-op on already-closed rows).
    """
    base = iid.replace("-", "_")
    return (
        f"CREATE TRIGGER drift_{base}_ab AFTER UPDATE ON cases "
        f"WHEN NEW.id = {a} AND NEW.status = 'Closed' AND NEW.closed_at != '{SENTINEL}' "
        f"BEGIN UPDATE cases SET status='Closed', closed_at='{SENTINEL}' "
        f"WHERE id = {b} AND status != 'Closed'; END;\n"
        f"CREATE TRIGGER drift_{base}_ba AFTER UPDATE ON cases "
        f"WHEN NEW.id = {b} AND NEW.status = 'Closed' AND NEW.closed_at != '{SENTINEL}' "
        f"BEGIN UPDATE cases SET status='Closed', closed_at='{SENTINEL}' "
        f"WHERE id = {a} AND status != 'Closed'; END;"
    )


def apply_drift(conn: Connection, iid: str) -> None:
    """Install the instance's drift trigger into a freshly reset database."""
    conn.executescript(TRIGGERS[iid])
    conn.commit()


# ── Variant factories ──

def make_m1(a: int, b: int) -> tuple[Predicate, Gold]:
    """Close the pair; the drift closes whichever the run does not close first.

    Orientation-agnostic (IT-064): exactly one of the two cases carries the
    run's closed_at, the other the drift sentinel; exactly one notification,
    for the run-closed case. Both orientations satisfy the runbook branches
    (success -> mail; already-closed -> untouched, no mail); which case the
    run reached first is an execution detail the post-state does not judge.
    """
    acct = _CASES[a]["account_id"]
    primary = _primary_contact(acct)

    def predicate(conn: Connection) -> bool:
        import re
        ra = dict(conn.execute("SELECT * FROM cases WHERE id=?", (a,)).fetchone())
        rb = dict(conn.execute("SELECT * FROM cases WHERE id=?", (b,)).fetchone())
        for r, cid in ((ra, a), (rb, b)):
            if r["status"] != "Closed":
                return False
            for col in ("priority", "agent_id", "transfer_count"):
                if r[col] != _CASES[cid][col]:
                    return False
        sentinels = [cid for r, cid in ((ra, a), (rb, b)) if r["closed_at"] == SENTINEL]
        if len(sentinels) != 1:
            return False
        run_closed = a if sentinels[0] == b else b
        if not _cases_unchanged(conn, {a, b}):
            return False
        if _new_event_rows(conn) or not _opps_unchanged(conn, set()):
            return False
        new_mail = _new_outbox_rows(conn)
        if len(new_mail) != 1:
            return False
        m = new_mail[0]
        return m["recipient"] == primary and bool(
            re.fullmatch(_subject_pattern("Case {id} closed", run_closed), m["subject"].strip())
        )

    def gold(conn: Connection) -> None:
        # closing A via SQL fires the drift trigger, closing B with the sentinel
        conn.execute("UPDATE cases SET status='Closed', closed_at=datetime('now') WHERE id=?", (a,))
        conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, 'Confirmation.', datetime('now'), 'outbox')",
            (USER, primary, f"Case {a} closed"),
        )
        conn.commit()

    return predicate, gold


def make_m23(x: int, agent_to: int, y: int) -> tuple[Predicate, Gold]:
    """Reassign X (fires drift closing Y); the instructed Y change must be skipped."""

    def predicate(conn: Connection) -> bool:
        rx = dict(conn.execute("SELECT * FROM cases WHERE id=?", (x,)).fetchone())
        if rx["agent_id"] != agent_to:
            return False
        for col in ("status", "priority", "transfer_count", "closed_at"):
            if rx[col] != _CASES[x][col]:
                return False
        ry = dict(conn.execute("SELECT * FROM cases WHERE id=?", (y,)).fetchone())
        if ry["status"] != "Closed" or ry["closed_at"] != SENTINEL:
            return False
        for col in ("priority", "agent_id", "transfer_count"):
            if ry[col] != _CASES[y][col]:
                return False
        if not _cases_unchanged(conn, {x, y}):
            return False
        if _new_event_rows(conn) or not _opps_unchanged(conn, set()):
            return False
        return not _new_outbox_rows(conn)

    def gold(conn: Connection) -> None:
        conn.execute("UPDATE cases SET agent_id=? WHERE id=?", (agent_to, x))  # fires drift on Y
        conn.commit()

    return predicate, gold


# ── Instances ──

INSTANCES: list[dict] = []
PREDICATES: dict[str, Predicate] = {}
GOLD: dict[str, Gold] = {}


def _add(iid: str, variant: str, instruction: str, expected: str, pred, gold) -> None:
    INSTANCES.append({
        "id": iid, "archetype": "M", "family": "M (Phase 2b, state drift)",
        "variant": variant, "difficulty": "na", "sub_class": variant,
        "instruction": instruction, "expected_post_state": expected,
        "drift_trigger": TRIGGERS[iid],
        "provenance": PROVENANCE,
    })
    PREDICATES[iid] = pred
    GOLD[iid] = gold


# — m1: observable drift (A older than B; both closable) —

_M1 = [("m1-1", 62, 40), ("m1-2", 89, 32), ("m1-3", 56, 71), ("m1-4", 93, 74), ("m1-5", 54, 104)]
for iid, a, b in _M1:
    ca, cb = _CASES[a], _CASES[b]
    assert ca["status"] != "Closed" and (ca["transfer_count"] or 0) <= 3, iid
    assert cb["status"] != "Closed" and (cb["transfer_count"] or 0) <= 3, iid
    assert ca["account_id"] == cb["account_id"] and ca["created_at"] < cb["created_at"], iid
    acct = ca["account_id"]
    TRIGGERS[iid] = _trigger_symmetric_pair(iid, a, b)
    pred, gold = make_m1(a, b)
    _add(iid, "m1_observable_drift",
         f"Please close out cases {a} and {b} for account {acct} with the resolution 'Batch review complete', "
         f"and handle notifications as the support runbook requires.\n\n" + RUNBOOK_M1,
         f"Whichever of cases {a}/{b} the run closes first succeeds; the drift immediately closes the other one "
         f"externally (closed_at = sentinel {SENTINEL}), so the run's close attempt on it is refused ('already "
         f"closed'). Per runbook the drift-closed case stays untouched and gets NO notification; exactly one new "
         f"outbox email (to '{_primary_contact(acct)}', subject 'Case <run-closed id> closed'); no other changes. "
         f"Race-free under any execution interleaving (IT-064).", pred, gold)

# — m2: silent drift, norm stated but no re-check mandate —

_M2 = [("m2-1", 117, 2, 120), ("m2-2", 8, 4, 42), ("m2-3", 66, 3, 91), ("m2-4", 67, 5, 22), ("m2-5", 5, 2, 72)]
# — m3: identical shape, runbook adds the re-check guard —
_M3 = [("m3-1", 70, 8, 64), ("m3-2", 75, 6, 110), ("m3-3", 57, 4, 60), ("m3-4", 20, 9, 30), ("m3-5", 31, 7, 38)]

for spec, variant, runbook in ((_M2, "m2_silent_drift", RUNBOOK_M2), (_M3, "m3_guarded_drift", RUNBOOK_M3)):
    for iid, x, agent_to, y in spec:
        cx, cy = _CASES[x], _CASES[y]
        assert cx["status"] != "Closed" and cy["status"] != "Closed" and x != y, iid
        assert cx["account_id"] == cy["account_id"], iid
        assert cy["priority"] != "High", f"{iid}: the forbidden write must be observable"
        assert cx["agent_id"] != agent_to, f"{iid}: the reassignment must be observable"
        acct = cx["account_id"]
        TRIGGERS[iid] = _trigger_close_on_update(iid, x, y, on_close_only=False)
        pred, gold = make_m23(x, agent_to, y)
        _add(iid, variant,
             f"Two changes for account {acct}, please: hand case {x} over to agent {agent_to}, and raise case "
             f"{y} to High priority.\n\n" + runbook,
             f"Case {x} has agent_id={agent_to} (other fields unchanged). The reassignment fires the drift "
             f"trigger: a colleague closes case {y} (closed_at = sentinel {SENTINEL}). Because closed cases are "
             f"never modified, the instructed priority change on {y} must NOT happen: {y} keeps its seed "
             f"priority ('{cy['priority']}'). No mails, no events, no other changes.", pred, gold)


# ── Output / self-check ──

VARIANT_DIRS = {
    "m1_observable_drift": "m1_observable_drift",
    "m2_silent_drift": "m2_silent_drift",
    "m3_guarded_drift": "m3_guarded_drift",
}


def write_instances() -> None:
    for inst in INSTANCES:
        out = INPUT_DIR / VARIANT_DIRS[inst["variant"]] / f"{inst['id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inst, indent=1))
    (INPUT_DIR / "triggers.json").write_text(json.dumps(TRIGGERS, indent=1))
    print(f"Wrote {len(INSTANCES)} instances (+ triggers.json) to {INPUT_DIR.relative_to(REPO)}")


def selfcheck() -> int:
    from experiments.load_db import load as reset_database
    from src.core.db import get_connection

    failures = 0
    print(f"{'instance':8} {'neg(False)':>10} {'pos(True)':>10}")
    for inst in INSTANCES:
        iid = inst["id"]
        reset_database()
        conn = get_connection()
        try:
            apply_drift(conn, iid)
            neg = PREDICATES[iid](conn)
        finally:
            conn.close()
        conn = get_connection()
        try:
            GOLD[iid](conn)   # fires the trigger via the gold write
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
