"""Deterministic query executor for archetype B.

Executes a ``QuerySpec`` against CRM rows and returns the computed answer. The
executor is a pure function parameterized by a ``load`` callable, so it can run
against Supabase in production and against seed JSON in tests. The workflow uses
this executor in its deterministic ``execute`` node; the LLM never performs the
aggregation, which is the defining property of the workflow paradigm for B.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.archetypes.b_structured_retrieval.schemas import FilterSpec, QuerySpec

Loader = Callable[[str], list[dict]]

_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "lt": lambda a, b: a is not None and a < b,
    "ge": lambda a, b: a is not None and a >= b,
    "le": lambda a, b: a is not None and a <= b,
}


def _parse_dt(value: str) -> datetime:
    """Parse an ISO datetime or date string."""
    fmt = "%Y-%m-%d %H:%M:%S" if len(value) > 10 else "%Y-%m-%d"
    return datetime.strptime(value, fmt)


def _derive(row: dict, columns: list[str]) -> None:
    """Add computed columns to a row in place."""
    for col in columns:
        if col == "handle_time_hours":
            if row.get("status") == "Closed" and row.get("closed_at"):
                delta = _parse_dt(row["closed_at"]) - _parse_dt(row["created_at"])
                row[col] = delta.total_seconds() / 3600.0
            else:
                row[col] = None
        elif col == "created_year":
            row[col] = _parse_dt(row["created_at"]).year
        elif col == "created_month":
            row[col] = _parse_dt(row["created_at"]).month
        elif col == "closed_year":
            row[col] = _parse_dt(row["closed_at"]).year if row.get("closed_at") else None
        elif col == "close_year":
            row[col] = _parse_dt(row["close_date"]).year
        elif col == "close_quarter":
            row[col] = (_parse_dt(row["close_date"]).month - 1) // 3 + 1
        elif col == "close_month":
            row[col] = _parse_dt(row["close_date"]).month


def _apply_filters(rows: list[dict], filters: list[FilterSpec]) -> list[dict]:
    """Return the rows that satisfy all filter conditions."""
    out = []
    for row in rows:
        keep = True
        for f in filters:
            if not _OPS[f.op](row.get(f.column), f.value):
                keep = False
                break
        if keep:
            out.append(row)
    return out


def run_query(spec: QuerySpec, load: Loader) -> Any:
    """Execute the query specification and return the computed answer.

    Args:
        spec: The declarative query specification.
        load: A callable mapping a table name to its rows.

    Returns:
        The aggregation result: an int/float for numeric operations, or the
        group key (a string) for ``argmax_group``.
    """
    rows = [dict(r) for r in load(spec.base_table)]

    # Joins: enrich each base row with prefixed parent attributes.
    for join in spec.joins:
        parent_index = {p[join.foreign_key]: p for p in load(join.table)}
        for row in rows:
            parent = parent_index.get(row.get(join.local_key))
            if parent:
                for key, val in parent.items():
                    row[f"{join.prefix}{key}"] = val

    # Derived columns.
    for row in rows:
        _derive(row, spec.derive)

    rows = _apply_filters(rows, spec.filters)

    op = spec.operation
    if op == "count":
        return len(rows)

    if op in ("sum", "avg", "min", "max"):
        vals = [r[spec.target_column] for r in rows if r.get(spec.target_column) is not None]
        if not vals:
            return 0
        if op == "sum":
            return sum(vals)
        if op == "avg":
            return sum(vals) / len(vals)
        if op == "min":
            return min(vals)
        return max(vals)

    if op == "argmax_group":
        groups: dict[Any, list[dict]] = {}
        for r in rows:
            groups.setdefault(r.get(spec.group_by), []).append(r)
        scores: dict[Any, float] = {}
        for key, members in groups.items():
            if spec.group_metric == "count":
                scores[key] = len(members)
            else:
                vals = [m[spec.target_column] for m in members if m.get(spec.target_column) is not None]
                if not vals:
                    continue
                scores[key] = sum(vals) if spec.group_metric == "sum" else sum(vals) / len(vals)
        return max(scores, key=scores.get) if scores else None

    raise ValueError(f"Unknown operation: {op}")
