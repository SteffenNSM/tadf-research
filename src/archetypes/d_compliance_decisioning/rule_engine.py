"""Deterministic rule engine for archetype D (framework-free).

Interprets the policy clauses fetched from the Policy Registry and applies
them to the extracted quote facts. This is the component that makes D a
genuine workflow-vs-agent paradigm test rather than a single-call collapse:
in the workflow the LLM only extracts the request fields, and *this engine* —
not the LLM — performs the rule application, exactly as a production rules
engine evaluates a decision table. The agent, by contrast, applies the same
fetched rules in-context.

The engine is intentionally generic: it evaluates whatever clauses it is
given, in the documented order (gates first, then bonus accumulation, then
decision rules by precedence). It does not hard-code the policy; swapping the
registry contents swaps the decision behaviour with no engine change. This is
what keeps information availability honest — the rules are data fetched at
runtime, not constants baked into the workflow.

Evaluation order:
    1. Gates (sorted by id). The first gate whose condition holds returns its
       decision immediately (no further evaluation). Gates encode the
       high-error-consequence no-action paths (DECLINE).
    2. Bonus accumulation. Each firing bonus adds ``add_pct`` to the base
       discount, yielding ``effective_discount``.
    3. Decision rules (sorted by precedence, then id). The first rule all of
       whose conditions hold returns its decision.

Facts is a flat dict with keys: ``lead_status``, ``region``, ``is_existing``,
``has_overdue_invoices``, ``has_credit_hold``, ``is_new_logo``, ``segment``,
``amount``, ``base_discount_pct``, ``term_months``. The engine derives
``effective_discount`` and exposes it to decision conditions. Missing fields
(e.g. the distractor policies' ``trip_cost``) fail closed via the ``None``
guard, so irrelevant clauses never fire.
"""

from __future__ import annotations

from typing import Any

#: Comparison operators usable in clause conditions. ``None`` operands never
#: satisfy an ordered comparison, so a missing extracted field fails closed
#: rather than raising.
_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "lt": lambda a, b: a is not None and a < b,
    "ge": lambda a, b: a is not None and a >= b,
    "le": lambda a, b: a is not None and a <= b,
}


def _holds(field: str, op: str, value: Any, facts: dict[str, Any]) -> bool:
    """Whether ``facts[field] <op> value`` holds."""
    return _OPS[op](facts.get(field), value)


def evaluate(clauses: list[dict[str, Any]], facts: dict[str, Any]) -> tuple[str, str]:
    """Apply the policy clauses to the facts and return ``(label, rationale)``.

    Raises ``ValueError`` only if no decision rule matches after the gates and
    bonuses — a malformed/incomplete clause set — which the verifier treats as
    a hard failure rather than a silent default.
    """
    gates = [c for c in clauses if c.get("kind") == "gate"]
    bonuses = [c for c in clauses if c.get("kind") == "bonus"]
    decisions = [c for c in clauses if c.get("kind") == "decision"]

    # 1. Gates — first firing gate wins, no further evaluation.
    for g in sorted(gates, key=lambda c: c["id"]):
        if _holds(g["field"], g["op"], g["value"], facts):
            return g["decision"], f"Gate {g['id']} fired: {g['decision']}."

    # 2. Bonus accumulation -> effective_discount.
    effective = facts.get("base_discount_pct", 0) or 0
    fired_bonuses: list[str] = []
    for b in sorted(bonuses, key=lambda c: c["id"]):
        if _holds(b["field"], b["op"], b["value"], facts):
            effective += b["add_pct"]
            fired_bonuses.append(b["id"])
    facts = {**facts, "effective_discount": effective}

    # 3. Decision rules — lowest precedence index that fully matches wins.
    for d in sorted(decisions, key=lambda c: (c["precedence"], c["id"])):
        if all(_holds(c["field"], c["op"], c["value"], facts) for c in d["conditions"]):
            bonus_note = (
                f" (bonuses {'+'.join(fired_bonuses)}, effective {effective}%)"
                if fired_bonuses
                else f" (effective {effective}%)"
            )
            return d["decision"], f"Rule {d['id']} fired: {d['decision']}{bonus_note}."

    raise ValueError(
        f"no decision rule matched for effective_discount={effective}; "
        "clause set is incomplete"
    )
