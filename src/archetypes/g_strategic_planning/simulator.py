"""Deterministic plan simulator and goal checker for archetype G.

The simulator is the third member of the mechanical-validation family
(B query-executor, D policy-engine; protocol A.2, PlanBench principle). It
loads the seed CRM state as pure Python dictionaries, applies a plan's
steps in order under the same preconditions the F tools enforce, and then
evaluates the instance's declarative goal spec against the simulated final
state. The real database is never touched: G's deliverable is the plan,
not the state change (F/G boundary, Section 4.2.5).

Step semantics mirror ``src/core/tools/database.py`` / ``mail.py`` /
``calendar.py``:

- ``db_update(table, record_id, updates)`` — table and columns restricted
  by the same whitelists as the live tool; the record must exist.
- ``attempt_close_case(case_id, resolution_summary)`` — fails when the case
  does not exist, is already closed, or has ``transfer_count > 3`` (the
  escalation rule, documented in G's action-set doc because a planner
  cannot observe a rejection at plan time).
- ``send_email(recipient, subject, body)`` — appends an outbox record.
- ``create_event(name, start_time, end_time, attendees)`` — appends a
  calendar record.

Failure policy: a step whose preconditions fail makes the WHOLE plan
invalid (PlanBench convention — a plan containing an inapplicable action is
not a valid plan). This is deliberately stricter than F's record-and-
continue executor, because here the plan itself is the scored artefact.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from src.archetypes.g_strategic_planning.schemas import Plan, PlanStep
from src.core.tools.database import UPDATABLE_COLUMNS, UPDATABLE_TABLES

REPO = Path(__file__).resolve().parents[2].parent
SEED_DIR = REPO / "data" / "schema" / "seed"

_TABLES = ("accounts", "contacts", "agents", "cases", "opportunities")


def load_state() -> dict[str, Any]:
    """Load the deterministic seed as a fresh simulation state."""
    state: dict[str, Any] = {
        t: {row["id"]: dict(row) for row in json.loads((SEED_DIR / f"{t}.json").read_text())}
        for t in _TABLES
    }
    state["new_emails"] = []
    state["new_events"] = []
    return state


def _baseline() -> dict[str, Any]:
    return load_state()


def apply_step(state: dict, step: PlanStep) -> tuple[bool, str]:
    """Apply one plan step; returns (ok, reason)."""
    args = step.args or {}
    if step.tool == "db_update":
        table = args.get("table")
        record_id = args.get("record_id")
        updates = args.get("updates") or {}
        if table not in UPDATABLE_TABLES:
            return False, f"table {table!r} not updatable"
        allowed = UPDATABLE_COLUMNS.get(table, set())
        bad = [c for c in updates if c not in allowed]
        if bad:
            return False, f"columns not updatable on {table}: {bad}"
        if not updates:
            return False, "no fields to update"
        if not isinstance(record_id, int) or record_id not in state[table]:
            return False, f"{table} id {record_id!r} not found"
        state[table][record_id].update(updates)
        return True, "ok"

    if step.tool == "attempt_close_case":
        case_id = args.get("case_id")
        if not isinstance(case_id, int) or case_id not in state["cases"]:
            return False, f"case {case_id!r} not found"
        case = state["cases"][case_id]
        if case.get("status") == "Closed":
            return False, "case is already closed"
        if (case.get("transfer_count") or 0) > 3:
            return False, "close blocked: escalation rule (transfer_count > 3)"
        case["status"] = "Closed"
        case["closed_at"] = "SIMULATED"
        return True, "ok"

    if step.tool == "send_email":
        recipient = args.get("recipient")
        subject = args.get("subject")
        if not recipient or not subject or not args.get("body"):
            return False, "send_email requires recipient, subject, body"
        state["new_emails"].append({"recipient": recipient, "subject": subject})
        return True, "ok"

    if step.tool == "create_event":
        if not args.get("name") or not args.get("start_time") or not args.get("end_time"):
            return False, "create_event requires name, start_time, end_time"
        attendees = args.get("attendees") or []
        if isinstance(attendees, str):
            attendees = [a.strip() for a in attendees.split(",") if a.strip()]
        state["new_events"].append({"name": args["name"], "attendees": attendees})
        return True, "ok"

    return False, f"unknown tool {step.tool!r}"


def simulate(plan: Plan) -> dict[str, Any]:
    """Run the plan; returns a result dict with the final state and trace."""
    state = load_state()
    trace: list[dict] = []
    for i, step in enumerate(plan.steps, start=1):
        ok, reason = apply_step(state, step)
        trace.append({"n": i, "tool": step.tool, "ok": ok, "reason": reason})
        if not ok:
            return {"valid": False, "failed_step": i, "reason": reason, "state": state, "trace": trace}
    return {"valid": True, "failed_step": None, "reason": "all steps applied", "state": state, "trace": trace}


# ── Declarative goal checking ──


def check_goal(state: dict, plan: Plan, goal: dict) -> tuple[bool, dict]:
    """Evaluate a declarative goal spec against the simulated final state.

    Supported keys (all optional):
        cases_closed: [id, ...]           — status 'Closed' AND closed_at set
        case_fields: {id: {col: val}}     — exact field values on cases
        opp_fields: {id: {col: val}}      — exact field values on opportunities
        emails: [{recipient, subject}]    — exact multiset of new outbox mail
        emails_one_per_new_owner: {subject} — additionally expect exactly one
            email with that subject per agent that received >=1 reassigned
            case (recipients derived from the observed reassignments)
        events: [{name, attendees_contain?}] — exact count; names must match
        tc_incremented: [id, ...]         — transfer_count == baseline + 1
        cases_reassigned: [id, ...]       — agent_id differs from baseline
            and is one of agent_capacity.targets
        agent_capacity: {targets: [...], max_new: n} — newly assigned cases
            per target agent (vs baseline) must not exceed max_new
        closes_before_emails: true        — every case-closing step precedes
            every send_email step in the plan order
        no_other_changes: true            — cases/opportunities outside the
            ids referenced above are byte-identical to the seed
    Returns (passed, breakdown) with one boolean per check.
    """
    base = _baseline()
    bd: dict[str, Any] = {}

    touched_cases: set[int] = set(goal.get("cases_closed", []))
    touched_cases |= {int(k) for k in goal.get("case_fields", {})}
    touched_cases |= set(goal.get("tc_incremented", []))
    if "agent_capacity" in goal:
        touched_cases |= {
            cid for cid, c in state["cases"].items()
            if c.get("agent_id") != base["cases"][cid].get("agent_id")
        }
    touched_opps: set[int] = {int(k) for k in goal.get("opp_fields", {})}

    if "cases_closed" in goal:
        bd["cases_closed"] = all(
            state["cases"][cid].get("status") == "Closed"
            and state["cases"][cid].get("closed_at")
            for cid in goal["cases_closed"]
        )
    if "case_fields" in goal:
        bd["case_fields"] = all(
            state["cases"][int(cid)].get(col) == val
            for cid, fields in goal["case_fields"].items()
            for col, val in fields.items()
        )
    if "opp_fields" in goal:
        bd["opp_fields"] = all(
            state["opportunities"][int(oid)].get(col) == val
            for oid, fields in goal["opp_fields"].items()
            for col, val in fields.items()
        )
    if "emails" in goal or "emails_one_per_new_owner" in goal:
        expected = [(e["recipient"], e["subject"]) for e in goal.get("emails", [])]
        if "emails_one_per_new_owner" in goal:
            subject = goal["emails_one_per_new_owner"]["subject"]
            new_owners = sorted({
                c.get("agent_id") for cid, c in state["cases"].items()
                if c.get("agent_id") != base["cases"][cid].get("agent_id")
            })
            for owner in new_owners:
                owner_mail = state["agents"].get(owner, {}).get("email")
                expected.append((owner_mail, subject))
        observed = sorted((e["recipient"], e["subject"]) for e in state["new_emails"])
        bd["emails"] = sorted(expected) == observed
    if "events" in goal:
        specs = goal["events"]
        ok = len(state["new_events"]) == len(specs)
        if ok:
            names = sorted(e["name"] for e in state["new_events"])
            ok = names == sorted(s["name"] for s in specs)
        if ok:
            for s in specs:
                if "attendees_contain" in s:
                    ev = next(e for e in state["new_events"] if e["name"] == s["name"])
                    ok = ok and all(a in ev["attendees"] for a in s["attendees_contain"])
        bd["events"] = ok
    if "tc_incremented" in goal:
        bd["tc_incremented"] = all(
            state["cases"][cid].get("transfer_count")
            == (base["cases"][cid].get("transfer_count") or 0) + 1
            for cid in goal["tc_incremented"]
        )
    if "cases_reassigned" in goal:
        targets = set(goal.get("agent_capacity", {}).get("targets", []))
        bd["cases_reassigned"] = all(
            state["cases"][cid].get("agent_id") != base["cases"][cid].get("agent_id")
            and (not targets or state["cases"][cid].get("agent_id") in targets)
            for cid in goal["cases_reassigned"]
        )
    if "agent_capacity" in goal:
        cap = goal["agent_capacity"]
        counts = {t: 0 for t in cap["targets"]}
        valid_targets = True
        for cid, c in state["cases"].items():
            old, new = base["cases"][cid].get("agent_id"), c.get("agent_id")
            if old != new:
                if new in counts:
                    counts[new] += 1
                else:
                    valid_targets = False
        bd["agent_capacity"] = valid_targets and all(n <= cap["max_new"] for n in counts.values())
    if goal.get("closes_before_emails"):
        idx_close = [i for i, s in enumerate(plan.steps)
                     if s.tool == "attempt_close_case"
                     or (s.tool == "db_update" and "status" in (s.args.get("updates") or {}))]
        idx_mail = [i for i, s in enumerate(plan.steps) if s.tool == "send_email"]
        bd["closes_before_emails"] = (
            not idx_close or not idx_mail or max(idx_close) < min(idx_mail)
        )
    if goal.get("no_other_changes"):
        ok = True
        for cid, row in state["cases"].items():
            if cid not in touched_cases and row != base["cases"][cid]:
                ok = False
                break
        if ok:
            for oid, row in state["opportunities"].items():
                if oid not in touched_opps and row != base["opportunities"][oid]:
                    ok = False
                    break
        bd["no_other_changes"] = ok

    return all(bd.values()), bd


def score_plan(plan: Plan | None, goal: dict) -> tuple[float, dict]:
    """Full G scoring: simulate, then check the goal spec.

    Returns (score, rationale) where rationale records plan validity, the
    failing step if any, and the per-check goal breakdown.
    """
    if plan is None:
        return 0.0, {"plan_parsed": False}
    sim = simulate(plan)
    rationale: dict[str, Any] = {
        "plan_parsed": True,
        "n_steps": len(plan.steps),
        "sim_valid": sim["valid"],
        "failed_step": sim["failed_step"],
        "fail_reason": None if sim["valid"] else sim["reason"],
    }
    if not sim["valid"]:
        return 0.0, rationale
    passed, breakdown = check_goal(sim["state"], plan, goal)
    rationale["goal_breakdown"] = breakdown
    return (1.0 if passed else 0.0), rationale
