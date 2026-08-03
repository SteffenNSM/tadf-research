"""Curated staged-adaptivity instances for Phase 2b family S.

Family S ("Staged Adaptivity", IT-066) maps the boundary of COMPILED
conditional control flow: how much of the agent's adaptivity a state-machine
workflow (``src/archetypes/f_action_execution/state_machine.py``) can recover,
and where the loop is irreducible. Three variants:

- **s1_enumerated_switch** -- REUSES the family-X x1 instances verbatim
  (rule matrix on runtime outcomes, W 0/25 in the canonical form). Only the
  state machine is swept; canonical workflow/agent results join from the
  family-X grid at analysis time (identical instances, zero duplicate spend).
  H1: the SM carries the cell tier-invariantly at ~workflow cost -- the x1
  zero is a limit of the two-stage FORM, not of compiled control flow.
- **s2_bounded_until** -- REUSES the family-P p-b instances verbatim
  (repeat-until-refusal, W 0/25). Only the state machine is swept. H2: a
  deterministic until-edge with an iteration cap carries the cell -- an
  outcome-dependent COUNT is SM-compatible when the stop condition is
  deterministically checkable on the structured response.
- **s3_content_synthesis** -- NEW instances (defined here): the same
  oldest-first close batches, but the follow-up is a single run-report mail
  whose BODY lists exactly the cases that were actually closed in this run.
  The report's content depends on the runtime stop point; path selection
  cannot produce it and the SM's bounded placeholder vocabulary ({case_id},
  {reason} of the current step) deliberately carries no run aggregate. H3:
  the SM fails structurally wherever a refusal occurs; the agent carries the
  cell. s3-4 (account 8, no refusal in the batch) is the built-in CONTROL:
  with no refusal the closed set is plan-time derivable, so the SM (and the
  canonical workflow) should pass -- separating the content-synthesis
  mechanism from batch mechanics.

Design decisions logged in IT-066: the originally sketched uncovered-outcome
variant is DEFERRED -- injecting a genuinely non-enumerable outcome category
requires changing the frozen ``attempt_close_case`` response contract, which
the frozen-artifact discipline forbids; the executor's default-stop behavior
is exercised structurally instead. Content synthesis replaces it as the
sharper boundary (path vs. parameter vs. CONTENT).

Anchor discipline (IT-057): every batch order and refusal point is DERIVED
from the seed at import time (oldest-first over non-closed cases; first
transfer_count > 3 refuses) and asserted against the published family-P
literals, so s2 and s3 stay comparable cell by cell.

Run:
    PYTHONPATH=. python experiments/seed_s.py               # write s3 instances
    PYTHONPATH=. python experiments/seed_s.py --selfcheck   # verify predicates
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
INPUT_DIR = REPO / "data" / "test_inputs" / "s_staged_adaptivity"

USER = "user@atlas.com"
OPS = "ops@atlas.com"

PROVENANCE = {
    "source_benchmark": (
        "Author-constructed (Phase 2b family S, staged adaptivity); surface style "
        "follows WorkBench (Styles et al., 2024) and the family-P b-variant"
    ),
    "adaptation": (
        "Instance designed by the author to isolate runtime-dependent CONTENT "
        "synthesis (build decision IT-066): the close batch reuses the family-P "
        "outcome-dependent stop mechanism, and the required report body is a "
        "function of the run's own stop point. Batch orders and refusal points "
        "are derived from the deterministic seed with import-time assertions "
        "matching the published family-P literals. The canonical paradigm "
        "implementations are reused unchanged from archetype F; the state-machine "
        "form is defined in src/archetypes/f_action_execution/state_machine.py."
    ),
    "license": "Original work by the author (task design); benchmark style reference only",
}

Predicate = Callable[[Connection], bool]
Gold = Callable[[Connection], None]

_CASES = _seed_rows("cases")

# ── Instance reuse map (s1/s2) ──
#
# validate_s.py sweeps the state machine over these EXISTING instances; the
# canonical workflow/agent numbers for the same instances come from the
# family-X and family-P grids (join key: instance id).

S1_IDS = ["x1-1", "x1-2", "x1-3", "x1-4", "x1-5"]
S2_IDS = ["p-b-1", "p-b-2", "p-b-3", "p-b-4", "p-b-5"]


# ── Batch derivation (anchor-disciplined) ──


def _batch(account_id: int) -> tuple[list[int], int | None]:
    """Oldest-first non-closed cases of the account and the first refusal.

    Mirrors the runbook semantics: 'open casework' is every case that is not
    closed, processed oldest-first by creation date; the back-end refuses the
    first case with transfer_count > 3 (the undocumented escalation policy of
    ``attempt_close_case``).
    """
    batch = sorted(
        (c for c in _CASES.values() if c["account_id"] == account_id and c["status"] != "Closed"),
        key=lambda c: (c["created_at"], c["id"]),
    )
    order = [c["id"] for c in batch]
    refusal = next((c["id"] for c in batch if (c["transfer_count"] or 0) > 3), None)
    return order, refusal


#: (instance id, account, published family-P order, published refusal) -- the
#: literals are the family-P values; the assertions below guarantee the seed
#: still derives exactly these, keeping s2/s3 comparable cell by cell.
_S3 = [
    ("s3-1", 14, [62, 40, 63, 17, 118], 17),
    ("s3-2", 16, [54, 92, 104, 81, 16], 92),
    ("s3-3", 12, [38, 42, 76, 31, 8], 38),
    ("s3-4", 8, [56, 71, 98, 53], None),   # control: no refusal, content plan-time derivable
    ("s3-5", 19, [93, 99, 74, 51, 80], 99),
]

for _iid, _acct, _order, _ref in _S3:
    _derived_order, _derived_ref = _batch(_acct)
    assert _derived_order == _order, f"{_iid}: seed drift, order {_derived_order} != {_order}"
    assert _derived_ref == _ref, f"{_iid}: seed drift, refusal {_derived_ref} != {_ref}"


# ── Predicate / gold ──


def _report_body(conn: Connection, mail_id: int) -> str:
    row = conn.execute("SELECT body FROM emails WHERE id=?", (mail_id,)).fetchone()
    return (row["body"] if row and row["body"] else "")


def _mentions_case(body: str, rid: int) -> bool:
    """Whether the body names the case, accepting zero-padded ids (IT-057)."""
    return re.search(rf"case\s+0*{rid}\b", body, re.IGNORECASE) is not None


def make_s3(account_id: int, order: list[int], refusal: int | None) -> tuple[Predicate, Gold]:
    """Close oldest-first until refusal; ONE report mail naming exactly the closed set.

    Predicate: cases before the refusal are Closed (other mutable columns
    untouched); the refused case and everything after it fully untouched; no
    case outside the batch changed; no events; exactly one new outbox email to
    ops with subject 'Batch report: account <id>' whose body names every
    closed case (form 'case <id>', zero-padding accepted) and NO unclosed
    batch case. When nothing was closed the body must name no batch case and
    contain the phrase 'no cases closed'.
    """
    stop = order.index(refusal) if refusal is not None else len(order)
    closed, untouched = order[:stop], order[stop:]

    def predicate(conn: Connection) -> bool:
        seed = _seed_rows("cases")
        for rid in closed:
            r = dict(conn.execute("SELECT * FROM cases WHERE id=?", (rid,)).fetchone())
            if r["status"] != "Closed":
                return False
            for col in ("priority", "agent_id", "transfer_count"):
                if r[col] != seed[rid][col]:
                    return False
        for rid in untouched:
            r = dict(conn.execute("SELECT * FROM cases WHERE id=?", (rid,)).fetchone())
            for col in ("status", "priority", "agent_id", "transfer_count", "closed_at"):
                if r[col] != seed[rid][col]:
                    return False
        if not _cases_unchanged(conn, set(order)):
            return False
        if _new_event_rows(conn):
            return False
        new_mail = _new_outbox_rows(conn)
        if len(new_mail) != 1:
            return False
        m = new_mail[0]
        if m["recipient"] != OPS:
            return False
        if not re.fullmatch(
            _subject_pattern("Batch report: account {id}", account_id), m["subject"].strip()
        ):
            return False
        body = _report_body(conn, m["id"])
        for rid in closed:
            if not _mentions_case(body, rid):
                return False
        for rid in untouched:
            if _mentions_case(body, rid):
                return False
        if not closed and "no cases closed" not in body.lower():
            return False
        return True

    def gold(conn: Connection) -> None:
        for rid in closed:
            conn.execute(
                "UPDATE cases SET status='Closed', closed_at=datetime('now') WHERE id=?",
                (rid,),
            )
        body = "\n".join(f"case {rid}" for rid in closed) if closed else "no cases closed"
        conn.execute(
            "INSERT INTO emails (sender, recipient, subject, body, sent_at, status) "
            "VALUES (?, ?, ?, ?, datetime('now'), 'outbox')",
            (USER, OPS, f"Batch report: account {account_id}", body),
        )
        conn.commit()

    return predicate, gold


# ── Shared runbook (identical for all three execution forms) ──

RUNBOOK_S3 = """Support runbook (excerpt):
- 'Open casework' covers every case that is not closed (status Open or In Progress).
- Case closures go through the attempt_close_case tool; the back-end applies business rules and may refuse a close. Direct status edits to 'Closed' are not permitted.
- Work strictly oldest-first by creation date.
- Stop at the first refused close: leave that case and every case after it untouched. No escalation mail is needed; the batch report covers the outcome.
- After the batch (completed or stopped), send exactly ONE report email to ops@atlas.com, subject 'Batch report: account <id>' (substitute the account id).
- The report body names exactly the cases that were actually closed in THIS run, one line per case in the form 'case <id>'. Do not name any case that was not closed. If no case was closed, the body is the single line 'no cases closed'."""


# ── Instances ──

INSTANCES: list[dict] = []
PREDICATES: dict[str, Predicate] = {}
GOLD: dict[str, Gold] = {}


def _add(iid: str, instruction: str, expected: str, pred: Predicate, gold: Gold) -> None:
    INSTANCES.append({
        "id": iid, "archetype": "S", "family": "S (Phase 2b, staged adaptivity)",
        "variant": "s3_content_synthesis", "difficulty": "na",
        "sub_class": "s3_content_synthesis",
        "instruction": instruction, "expected_post_state": expected,
        "provenance": PROVENANCE,
    })
    PREDICATES[iid] = pred
    GOLD[iid] = gold


_RESOLUTIONS = {
    "s3-1": "Routine cleanup",
    "s3-2": "Batch review done",
    "s3-3": "Consolidated",
    "s3-4": "Quarterly cleanup",
    "s3-5": "Handover complete",
}

for iid, acct, order, refusal in _S3:
    pred, gold = make_s3(acct, order, refusal)
    stop = order.index(refusal) if refusal is not None else len(order)
    closed, untouched = order[:stop], order[stop:]
    closed_txt = ", ".join(str(r) for r in closed) if closed else "none"
    expected = (
        f"Oldest-first order is {', '.join(str(r) for r in order)}. "
        + (
            f"Case {refusal} (transfer_count > 3) is refused; cases {closed_txt} are Closed and "
            f"cases {', '.join(str(r) for r in untouched)} are untouched. "
            if refusal is not None
            else f"Every close succeeds; cases {closed_txt} are Closed. "
        )
        + f"Exactly one email to ops@atlas.com with subject 'Batch report: account {acct}' whose body "
        + (
            f"names exactly the closed cases ({closed_txt}) in the form 'case <id>' and no other case."
            if closed
            else "is the single line 'no cases closed' and names no case."
        )
    )
    _add(
        iid,
        f"Can you work through the open casework for account {acct}? Close what the back-end lets you "
        f"close, resolution '{_RESOLUTIONS[iid]}', and file the batch report as the runbook "
        f"requires.\n\n" + RUNBOOK_S3,
        expected,
        pred, gold,
    )


# ── Output / self-check ──

VARIANT_DIRS = {"s3_content_synthesis": "s3_content_synthesis"}


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
