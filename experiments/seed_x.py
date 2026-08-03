"""Curated crossed-gates instances for Phase 2b family X.

Family X ("Crossed Gates", build decision in ``notebooks/results_analysis.ipynb``
Section 5 and IT-055) tests what happens when TWO routing mechanisms fire in
the same task -- the evidence the cascade's first-match order and the
hierarchical form (Section 4.1) need. It writes 15 instances to
``data/test_inputs/x_crossed_gates/`` in three variants (5 each), all on the
frozen CRM seed, scored by outcome-centric post-state predicates:

- **x1_rule_on_outcome (D4 x D1)** -- a codifiable notification/escalation
  matrix whose INPUT is an action's runtime outcome: close two cases; the
  back-end's response (success / manual-review refusal / already closed)
  selects the rule to apply. Codifiability says workflow, runtime feedback
  says agent; the cascade puts G1 first.
- **x2_chain_heterogeneous (D2 x D3)** -- a two-hop chain (contact -> account
  -> that account's open opportunities) feeding HETEROGENEOUS per-record
  updates (stage by amount threshold, owner above a second threshold). Both
  gates point to the agent; the cell checks whether the mechanisms compound
  into saturation.
- **x3_rules_heterogeneous (D4 x D3)** -- a fully plan-time-decidable triage
  matrix (priority -> different action per case: reassign / raise priority /
  both) that forces a heterogeneous plan object. The v1 cascade (G2 before
  G4) and the v2 hierarchy (D3 before D4) route this cell DIFFERENTLY --
  x3 is the discriminating cell between the two forms.

Per the IT-055 DSR note, no routing expectation is attached to any variant.
Both paradigm implementations are reused UNCHANGED from archetype F. Note for
interpretation: the codifiable rules live in the shared runbook excerpt and
are applied by the planner LLM (canonical F forms); the deterministic rule
ENGINE of archetype D is a build response, not the paradigm baseline, so x1/x3
test gate ordering under the canonical forms.

Anchor discipline (lesson of IT-057/p-d-3): every target set is computed FROM
the seed at import time and guarded by assertions; nothing is hand-filtered.

Input neutrality follows the IT-049/051 design law (natural colleague request
+ shared runbook excerpt, identical for both paradigms; the only named tool is
attempt_close_case inside the support runbook, F precedent).

Run:
    PYTHONPATH=. python experiments/seed_x.py               # write instances
    PYTHONPATH=. python experiments/seed_x.py --selfcheck   # verify predicates
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
    _seed_rows,
)
from experiments.seed_p import _cases_unchanged, _subject_pattern

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "x_crossed_gates"

USER = "user@atlas.com"
OPS = "ops@atlas.com"

PROVENANCE = {
    "source_benchmark": (
        "Author-constructed (Phase 2b family X, crossed gates); surface style "
        "follows WorkBench (Styles et al., 2024) and the archetype-D/F instances"
    ),
    "adaptation": (
        "Instance designed by the author to cross exactly two routing mechanisms "
        "(build decision IT-055): rule matrix on runtime outcomes (x1, D4xD1), "
        "read chain into heterogeneous updates (x2, D2xD3), plan-time rule matrix "
        "forcing a heterogeneous plan object (x3, D4xD3). Target sets are computed "
        "from the deterministic seed with import-time assertions. Paradigm "
        "implementations are reused unchanged from archetype F."
    ),
    "license": "Original work by the author (task design); benchmark style reference only",
}

Predicate = Callable[[Connection], bool]
Gold = Callable[[Connection], None]

_CASES = _seed_rows("cases")
_OPPS = _seed_rows("opportunities")
_CONTACTS = _seed_rows("contacts")


def _primary_contact(account_id: int) -> str:
    ids = sorted(cid for cid, c in _CONTACTS.items() if c["account_id"] == account_id)
    return _CONTACTS[ids[0]]["email"]


def _open_opps(account_id: int) -> list[dict]:
    """Every opportunity of the account that is not yet won or lost."""
    return sorted(
        (o for o in _OPPS.values()
         if o["account_id"] == account_id and o["stage"] not in ("Closed Won", "Closed Lost")),
        key=lambda o: o["id"],
    )


def _non_closed_cases(account_id: int) -> list[dict]:
    return sorted(
        (c for c in _CASES.values() if c["account_id"] == account_id and c["status"] != "Closed"),
        key=lambda c: c["id"],
    )


def _mail_multiset_ok(new_mail: list, expected: list[tuple[str, str]]) -> bool:
    """Exact multiset match: every expected (recipient, pattern) consumed once."""
    if len(new_mail) != len(expected):
        return False
    pool = list(new_mail)
    for rcpt, pat in expected:
        hit = next((m for m in pool if m["recipient"] == rcpt and re.fullmatch(pat, m["subject"].strip())), None)
        if hit is None:
            return False
        pool.remove(hit)
    return True


def _opps_unchanged(conn: Connection, exclude: set[int]) -> bool:
    for r in conn.execute("SELECT id, stage, amount, is_won, owner_agent_id FROM opportunities").fetchall():
        if r["id"] in exclude:
            continue
        s = _OPPS.get(r["id"])
        if s is None:
            return False
        for col in ("stage", "amount", "is_won", "owner_agent_id"):
            if r[col] != s[col]:
                return False
    return True


# ── x1: codifiable matrix on runtime outcomes (D4 x D1) ──

def make_x1(succeed_id: int, other_id: int, other_kind: str) -> tuple[Predicate, Gold]:
    """One case closes, the other is refused ('review') or already closed ('closed').

    Rules (shared runbook): success -> mail the account's primary contact
    'Case <id> closed'; manual-review refusal -> mail ops 'Manual review
    required: case <id>' AND set that case's priority to 'High'; already
    closed -> leave untouched, no mail.
    """
    acct = _CASES[succeed_id]["account_id"]
    primary = _primary_contact(acct)
    expected_mails = [(primary, _subject_pattern("Case {id} closed", succeed_id))]
    if other_kind == "review":
        expected_mails.append((OPS, _subject_pattern("Manual review required: case {id}", other_id)))

    def predicate(conn: Connection) -> bool:
        r = dict(conn.execute("SELECT * FROM cases WHERE id=?", (succeed_id,)).fetchone())
        if r["status"] != "Closed" or r["priority"] != _CASES[succeed_id]["priority"]:
            return False
        o = dict(conn.execute("SELECT * FROM cases WHERE id=?", (other_id,)).fetchone())
        if other_kind == "review":
            if o["status"] != _CASES[other_id]["status"] or o["priority"] != "High":
                return False
        else:  # already closed: fully untouched
            for col in ("status", "priority", "agent_id", "transfer_count", "closed_at"):
                if o[col] != _CASES[other_id][col]:
                    return False
        if not _cases_unchanged(conn, {succeed_id, other_id}):
            return False
        if _new_event_rows(conn) or not _opps_unchanged(conn, set()):
            return False
        return _mail_multiset_ok(_new_outbox_rows(conn), expected_mails)

    def gold(conn: Connection) -> None:
        conn.execute("UPDATE cases SET status='Closed', closed_at=datetime('now') WHERE id=?", (succeed_id,))
        conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, 'Confirmation.', datetime('now'), 'outbox')",
            (USER, primary, f"Case {succeed_id} closed"),
        )
        if other_kind == "review":
            conn.execute("UPDATE cases SET priority='High' WHERE id=?", (other_id,))
            conn.execute(
                "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
                "VALUES (?, ?, ?, 'Back-end reason quoted.', datetime('now'), 'outbox')",
                (USER, OPS, f"Manual review required: case {other_id}"),
            )
        conn.commit()

    return predicate, gold


# ── x2: chain into heterogeneous updates (D2 x D3) ──

def make_x2(account_id: int, t_stage: int, t_owner: int, owner: int) -> tuple[Predicate, Gold]:
    """Touch-up rule over the account's open opportunities.

    stage = 'Negotiation' if amount >= t_stage else 'Proposal';
    owner_agent_id = *owner* additionally where amount >= t_owner.
    """
    targets = {}
    for o in _open_opps(account_id):
        upd = {"stage": "Negotiation" if o["amount"] >= t_stage else "Proposal"}
        if o["amount"] >= t_owner:
            upd["owner_agent_id"] = owner
        targets[o["id"]] = upd
    assert len(targets) >= 2, f"account {account_id}: expected >=2 open opportunities"

    def predicate(conn: Connection) -> bool:
        for oid, upd in targets.items():
            r = dict(conn.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone())
            for col, val in upd.items():
                if r[col] != val:
                    return False
            if "owner_agent_id" not in upd and r["owner_agent_id"] != _OPPS[oid]["owner_agent_id"]:
                return False
            if r["amount"] != _OPPS[oid]["amount"] or r["is_won"] != _OPPS[oid]["is_won"]:
                return False
        if not _opps_unchanged(conn, set(targets)):
            return False
        if not _cases_unchanged(conn, set()):
            return False
        return not _new_outbox_rows(conn) and not _new_event_rows(conn)

    def gold(conn: Connection) -> None:
        for oid, upd in targets.items():
            sets = ", ".join(f"{c}=?" for c in upd)
            conn.execute(f"UPDATE opportunities SET {sets} WHERE id=?", (*upd.values(), oid))
        conn.commit()

    return predicate, gold, targets  # type: ignore[return-value]


# ── x3: plan-time rule matrix forcing heterogeneous actions (D4 x D3) ──

def make_x3(account_id: int, agent_high: int, agent_low: int) -> tuple[Predicate, Gold]:
    """Triage matrix over the account's non-closed cases.

    High -> agent_high (priority kept); Medium -> priority 'High' (owner
    kept); Low -> priority 'Medium' AND agent_low.
    """
    targets = {}
    for c in _non_closed_cases(account_id):
        if c["priority"] == "High":
            targets[c["id"]] = {"agent_id": agent_high}
        elif c["priority"] == "Medium":
            targets[c["id"]] = {"priority": "High"}
        else:
            targets[c["id"]] = {"priority": "Medium", "agent_id": agent_low}
    prios = {_CASES[cid]["priority"] for cid in targets}
    assert prios == {"High", "Medium", "Low"}, f"account {account_id}: matrix needs all three priorities, got {prios}"

    def predicate(conn: Connection) -> bool:
        for cid, upd in targets.items():
            r = dict(conn.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone())
            expect = {**{k: _CASES[cid][k] for k in ("status", "priority", "agent_id", "transfer_count", "closed_at")}, **upd}
            for col, val in expect.items():
                if r[col] != val:
                    return False
        if not _cases_unchanged(conn, set(targets)):
            return False
        if not _opps_unchanged(conn, set()):
            return False
        return not _new_outbox_rows(conn) and not _new_event_rows(conn)

    def gold(conn: Connection) -> None:
        for cid, upd in targets.items():
            sets = ", ".join(f"{c}=?" for c in upd)
            conn.execute(f"UPDATE cases SET {sets} WHERE id=?", (*upd.values(), cid))
        conn.commit()

    return predicate, gold, targets  # type: ignore[return-value]


# ── Shared runbooks ──

RUNBOOK_X1 = """Support runbook (excerpt):
- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.
- If a close succeeds: notify the account's primary contact (the lowest-id contact at that account) by email, subject 'Case <id> closed' (substitute the case id), short confirmation body.
- If a close is refused for manual review: leave the case status untouched, raise the case's priority to 'High', and notify ops@atlas.com by email, subject 'Manual review required: case <id>', body quoting the back-end's stated reason.
- If the back-end reports the case is already closed: leave it fully untouched and send no notification for it."""

RUNBOOK_X2 = """Pipeline runbook (excerpt):
- The touch-up covers every opportunity of that account that is not yet won or lost.
- Opportunities at {t_stage:,} or above move to stage 'Negotiation'; those below move to stage 'Proposal'.
- Opportunities at {t_owner:,} or above additionally get agent {owner} as their new owner.
- Change nothing else, and send no notifications for routine field changes."""

RUNBOOK_X3 = """Triage runbook (excerpt):
- High-priority cases are handed to agent {agent_high} (assignment only; the priority stays).
- Medium-priority cases are raised to High priority (the assigned agent stays).
- Low-priority cases are raised to Medium priority AND handed to agent {agent_low}.
- Apply the matching rule to every non-closed case of the account; change nothing else; no notifications."""


# ── Instances ──

INSTANCES: list[dict] = []
PREDICATES: dict[str, Predicate] = {}
GOLD: dict[str, Gold] = {}


def _add(iid: str, variant: str, instruction: str, expected: str, pred, gold) -> None:
    INSTANCES.append({
        "id": iid, "archetype": "X", "family": "X (Phase 2b, crossed gates)",
        "variant": variant, "difficulty": "na", "sub_class": variant,
        "instruction": instruction, "expected_post_state": expected,
        "provenance": PROVENANCE,
    })
    PREDICATES[iid] = pred
    GOLD[iid] = gold


# — x1 (anchor guards: succeed closable, other refused/closed) —

_X1 = [
    ("x1-1", 120, 112, "review"),
    ("x1-2", 5, 45, "review"),
    ("x1-3", 8, 31, "review"),
    ("x1-4", 66, 29, "review"),
    ("x1-5", 67, 12, "closed"),
]
for iid, sid, oid, kind in _X1:
    assert _CASES[sid]["status"] != "Closed" and (_CASES[sid]["transfer_count"] or 0) <= 3, iid
    if kind == "review":
        assert _CASES[oid]["status"] != "Closed" and (_CASES[oid]["transfer_count"] or 0) > 3, iid
        assert _CASES[oid]["priority"] != "High", f"{iid}: refusal priority change must be observable"
    else:
        assert _CASES[oid]["status"] == "Closed", iid
    assert _CASES[sid]["account_id"] == _CASES[oid]["account_id"], iid
    acct = _CASES[sid]["account_id"]
    pred, gold = make_x1(sid, oid, kind)
    _add(iid, "x1_rule_on_outcome",
         f"Please close out cases {sid} and {oid} for account {acct} with the resolution 'Reviewed and resolved', "
         f"and handle the follow-ups as the support runbook requires.\n\n" + RUNBOOK_X1,
         f"Case {sid} closes (transfer_count <= 3): status 'Closed', one email to the account's primary contact "
         f"('{_primary_contact(acct)}') with subject 'Case {sid} closed'. Case {oid}: "
         + ("refused for manual review (transfer_count > 3): status unchanged, priority set to 'High', one email to "
            f"ops@atlas.com with subject 'Manual review required: case {oid}'."
            if kind == "review" else
            "the back-end reports it is already closed: fully untouched, no notification for it.")
         + " No other mails, no events, no other case or opportunity changes.",
         pred, gold)

# — x2 (thresholds vary; targets computed from seed incl. Negotiation stage) —

_X2 = [
    ("x2-1", 19, 100_000, 150_000, 5),
    ("x2-2", 9, 100_000, 150_000, 2),
    ("x2-3", 16, 40_000, 160_000, 7),
    ("x2-4", 20, 100_000, 150_000, 9),
    ("x2-5", 3, 100_000, 120_000, 3),
]
for iid, acct, t1, t2, owner in _X2:
    pred, gold, targets = make_x2(acct, t1, t2, owner)
    contact = _primary_contact(acct)
    desc = "; ".join(
        f"opp {oid}: " + ", ".join(f"{k}={v}" for k, v in upd.items()) for oid, upd in sorted(targets.items())
    )
    _add(iid, "x2_chain_heterogeneous",
         f"Could you run the quarterly pipeline touch-up for the account that {contact} belongs to? "
         f"The runbook rules apply.\n\n" + RUNBOOK_X2.format(t_stage=t1, t_owner=t2, owner=owner),
         f"The account is {acct} (via contact {contact}). Expected updates over its not-won-or-lost opportunities: "
         f"{desc}. All other opportunity fields and records unchanged; no mails, no events.",
         pred, gold)

# — x3 (matrix accounts carry all three priorities; agents vary) —

_X3 = [
    ("x3-1", 15, 1, 9),
    ("x3-2", 16, 3, 6),
    ("x3-3", 18, 8, 1),
    ("x3-4", 12, 6, 10),
    ("x3-5", 19, 2, 3),
]
for iid, acct, a_hi, a_lo in _X3:
    pred, gold, targets = make_x3(acct, a_hi, a_lo)
    desc = "; ".join(
        f"case {cid}: " + ", ".join(f"{k}={v}" for k, v in upd.items()) for cid, upd in sorted(targets.items())
    )
    _add(iid, "x3_rules_heterogeneous",
         f"Please run the triage matrix over account {acct}'s open casework (every case that is not closed).\n\n"
         + RUNBOOK_X3.format(agent_high=a_hi, agent_low=a_lo),
         f"Expected per the matrix: {desc}. Closed cases and all other records untouched; no mails, no events.",
         pred, gold)


# ── Output / self-check ──

VARIANT_DIRS = {
    "x1_rule_on_outcome": "x1_rule_on_outcome",
    "x2_chain_heterogeneous": "x2_chain_heterogeneous",
    "x3_rules_heterogeneous": "x3_rules_heterogeneous",
}


def write_instances() -> None:
    for inst in INSTANCES:
        out = INPUT_DIR / VARIANT_DIRS[inst["variant"]] / f"{inst['id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(inst, indent=1))
    print(f"Wrote {len(INSTANCES)} instances to {INPUT_DIR.relative_to(REPO)}")


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
