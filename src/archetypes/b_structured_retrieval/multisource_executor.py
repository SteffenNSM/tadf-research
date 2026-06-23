"""Deterministic multi-source executor for archetype B.

Executes a ``MultiSourcePlan`` and returns the computed answer. The aggregation
and the cross-source intersection are performed here deterministically; the LLM
never computes them, which is the defining property of the workflow paradigm.

Parameterized by three loaders so the same function runs against the live tools
(workflow execute node) and against plain readers (tests):
    crm_loader(table)   -> list[dict]                       (rows of a CRM table)
    mail_loader(query)  -> list[str]                        (text bodies of matching emails)
    cal_loader(query)   -> list[str]                        (names of matching events)

Single source (crm only): the operation is applied to the filtered CRM rows.
Multi source: the answer is computed over the INTERSECTION of the per-source
key sets, keyed by ``crm.key_column`` and matched against the opportunity names
('Opportunity NNN') extracted from the Mail/Calendar text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from src.archetypes.b_structured_retrieval.schemas import FilterSpec, MultiSourcePlan

CrmLoader = Callable[[str], list[dict]]
TextLoader = Callable[[str], list[str]]

_OPP_RE = re.compile(r"Opportunity\s+\d+")

_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "lt": lambda a, b: a is not None and a < b,
    "ge": lambda a, b: a is not None and a >= b,
    "le": lambda a, b: a is not None and a <= b,
}


def _apply_filters(rows: list[dict], filters: list[FilterSpec]) -> list[dict]:
    """Return rows satisfying all AND-combined filter conditions."""
    out = []
    for row in rows:
        if all(_OPS[f.op](row.get(f.column), f.value) for f in filters):
            out.append(row)
    return out


def _extract_opps(texts: list[str]) -> set[str]:
    """Extract the set of 'Opportunity NNN' references from a list of text blobs."""
    keys: set[str] = set()
    for t in texts:
        keys.update(_OPP_RE.findall(t or ""))
    return keys


def run_plan(
    plan: MultiSourcePlan,
    crm_loader: CrmLoader,
    mail_loader: TextLoader,
    cal_loader: TextLoader,
) -> Any:
    """Execute the multi-source plan and return the computed answer."""
    rows = [dict(r) for r in crm_loader(plan.crm.table)]
    rows = _apply_filters(rows, plan.crm.filters)

    use_mail = plan.mail is not None
    use_cal = plan.calendar is not None

    # Single source: aggregate the filtered CRM rows directly.
    if not use_mail and not use_cal:
        if plan.operation == "count":
            return len(rows)
        vals = [r[plan.crm.value_column] for r in rows if r.get(plan.crm.value_column) is not None]
        return float(sum(vals))

    # Multi source: intersect key sets keyed by crm.key_column.
    key_col = plan.crm.key_column or "name"
    crm_keys = {r.get(key_col) for r in rows if r.get(key_col) is not None}
    value_map = {r.get(key_col): r.get(plan.crm.value_column) for r in rows}

    keys = set(crm_keys)
    if use_mail:
        keys &= _extract_opps(mail_loader(plan.mail.query))
    if use_cal:
        keys &= _extract_opps(cal_loader(plan.calendar.query))

    if plan.operation == "count":
        return len(keys)
    return float(sum(value_map[k] for k in keys if value_map.get(k) is not None))
