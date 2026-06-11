"""Ground-truth evaluation for archetype F (outcome-centric, TCR).

For each instance, a Python predicate inspects the post-execution database
state and returns ``True`` if the task succeeded. The predicates live next to
the instance definitions in ``experiments/seed_actions.py`` (registered in
``PREDICATES`` by instance id) so that the gold and the test data are derived
together and stay consistent.

Following WorkBench (Styles et al., 2024): success is determined by what the
target system looks like after the run, not by which tool sequence the agent
or workflow used. Multiple correct execution paths therefore all score 1.
"""

from __future__ import annotations

from collections.abc import Callable
from sqlite3 import Connection

from src.core.db import get_connection

Predicate = Callable[[Connection], bool]


def score(instance_id: str, predicates: dict[str, Predicate]) -> tuple[float, str]:
    """Run the registered predicate against the live database state.

    Args:
        instance_id: The id of the F instance to evaluate.
        predicates: Mapping ``{instance_id: predicate(conn) -> bool}`` provided
            by ``experiments/seed_actions.py``.

    Returns:
        ``(1.0, "post-state predicate satisfied")`` if the predicate is True,
        ``(0.0, "post-state predicate not satisfied")`` if it is False, or
        ``(0.0, "no predicate registered for ...")`` if the instance id is
        unknown.
    """
    predicate = predicates.get(instance_id)
    if predicate is None:
        return 0.0, f"no predicate registered for {instance_id}"
    conn = get_connection()
    try:
        ok = bool(predicate(conn))
        return (1.0 if ok else 0.0), (
            "post-state predicate satisfied" if ok else "post-state predicate not satisfied"
        )
    finally:
        conn.close()
