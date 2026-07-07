"""Read-only SQL executor for the archetype-B v3 retrieval workflow.

Runs the read-only SELECT carried by each field of a RetrievalPlan and assembles
the answer. The LLM writes the SQL (translation); this executor runs it
deterministically against the store, which is the defining property of the
workflow paradigm: computation and cross-source joins happen in the database
engine, never in the LLM.

A guard restricts execution to a single read-only SELECT (no writes, no DDL,
no multiple statements), so an LLM-written query cannot mutate the store.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from src.archetypes.b_structured_retrieval.schemas import RetrievalPlan

#: Query runner: maps a SQL string to the first result row (a tuple) or None.
Runner = Callable[[str], Any]

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|replace|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


def is_read_only(sql: str) -> bool:
    """True if the SQL is a single read-only SELECT/WITH statement."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:  # no multiple statements
        return False
    if not re.match(r"(?is)^\s*(select|with)\b", s):
        return False
    if _FORBIDDEN.search(s):
        return False
    return True


def _scalar(row: Any) -> Any:
    """First column of a result row, or None."""
    if row is None:
        return None
    return row[0]


def run_retrieval_plan(plan: RetrievalPlan, runner: Runner) -> Any:
    """Execute each field's SELECT and assemble the answer.

    Returns a single scalar for a single-fact plan (one field named 'answer'),
    otherwise a dict mapping field name to value.

    Per-field failures are handled gracefully: a field whose SQL is rejected by
    the read-only guard or raises an execution error yields ``None`` for that
    field instead of aborting the whole task, so one malformed field does not
    discard the others. A malformed answer simply scores as incorrect, which is
    the honest outcome for an LLM-authored query.
    """
    results: dict[str, Any] = {}
    for f in plan.fields:
        try:
            if not is_read_only(f.sql):
                results[f.name] = None
                continue
            results[f.name] = _scalar(runner(f.sql))
        except Exception:
            results[f.name] = None
    if len(plan.fields) == 1 and plan.fields[0].name == "answer":
        return results.get("answer")
    return results
