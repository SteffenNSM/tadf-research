"""Validate the archetype B query executor against the ground truth.

Hand-authored QuerySpecs for the 15 instances are executed against the seed
data and compared to the independently computed ground truth. Agreement here
confirms the deterministic executor is correct, independently of the LLM that
will produce these specs in the workflow plan node.

Run:
    python tests/test_b_executor.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.archetypes.b_structured_retrieval.schemas import FilterSpec, JoinSpec, QuerySpec
from src.archetypes.b_structured_retrieval.ground_truth import is_correct
from src.archetypes.b_structured_retrieval.query_executor import run_query

REPO = Path(__file__).resolve().parents[1]
SEED_DIR = REPO / "data" / "schema" / "seed"
INPUT_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"


def make_loader():
    cache: dict[str, list[dict]] = {}

    def load(table: str) -> list[dict]:
        if table not in cache:
            cache[table] = json.loads((SEED_DIR / f"{table}.json").read_text())
        return cache[table]

    return load


def F(column, op, value):
    return FilterSpec(column=column, op=op, value=value)


def J(table, local_key, prefix):
    return JoinSpec(table=table, local_key=local_key, prefix=prefix)


SPECS = {
    "b-low-1": QuerySpec(base_table="cases", filters=[F("status", "eq", "Open")], operation="count"),
    "b-low-2": QuerySpec(base_table="opportunities", filters=[F("is_won", "eq", True)], operation="sum", target_column="amount"),
    "b-low-3": QuerySpec(base_table="cases", filters=[F("priority", "eq", "High")], operation="count"),
    "b-low-4": QuerySpec(base_table="accounts", filters=[F("region", "eq", "EMEA")], operation="count"),
    "b-low-5": QuerySpec(base_table="opportunities", operation="avg", target_column="amount"),
    "b-med-1": QuerySpec(
        base_table="cases", joins=[J("agents", "agent_id", "agent_")],
        derive=["handle_time_hours"], filters=[F("agent_team", "eq", "EMEA"), F("status", "eq", "Closed")],
        operation="avg", target_column="handle_time_hours",
    ),
    "b-med-2": QuerySpec(
        base_table="opportunities", joins=[J("accounts", "account_id", "account_")],
        filters=[F("is_won", "eq", True), F("account_industry", "eq", "Technology")],
        operation="sum", target_column="amount",
    ),
    "b-med-3": QuerySpec(
        base_table="cases", joins=[J("agents", "agent_id", "agent_")],
        filters=[F("agent_team", "eq", "AMER")], operation="count",
    ),
    "b-med-4": QuerySpec(
        base_table="cases", joins=[J("accounts", "account_id", "account_")],
        filters=[F("account_type", "eq", "Partner")], operation="avg", target_column="transfer_count",
    ),
    "b-med-5": QuerySpec(
        base_table="opportunities", joins=[J("accounts", "account_id", "account_")],
        filters=[F("is_won", "eq", True), F("account_region", "eq", "APAC")], operation="count",
    ),
    "b-high-1": QuerySpec(
        base_table="opportunities", joins=[J("accounts", "account_id", "account_")],
        derive=["close_year", "close_quarter"],
        filters=[F("is_won", "eq", True), F("close_year", "eq", 2025), F("close_quarter", "eq", 3)],
        operation="argmax_group", group_by="account_region", group_metric="sum", target_column="amount",
    ),
    "b-high-2": QuerySpec(
        base_table="cases", joins=[J("agents", "agent_id", "agent_")],
        derive=["closed_year"],
        filters=[F("issue_category", "eq", "Billing"), F("status", "eq", "Closed"), F("closed_year", "eq", 2025)],
        operation="argmax_group", group_by="agent_team", group_metric="count",
    ),
    "b-high-3": QuerySpec(
        base_table="cases", joins=[J("agents", "agent_id", "agent_")],
        derive=["handle_time_hours"], filters=[F("agent_team", "eq", "EMEA"), F("status", "eq", "Closed")],
        operation="argmax_group", group_by="issue_category", group_metric="avg", target_column="handle_time_hours",
    ),
    "b-high-4": QuerySpec(
        base_table="opportunities", joins=[J("accounts", "account_id", "account_")],
        derive=["created_year", "created_month"],
        filters=[F("account_industry", "eq", "Technology"), F("created_year", "eq", 2025)],
        operation="argmax_group", group_by="created_month", group_metric="count",
    ),
    "b-high-5": QuerySpec(
        base_table="cases", joins=[J("accounts", "account_id", "account_")],
        filters=[F("priority", "eq", "High")],
        operation="argmax_group", group_by="account_region", group_metric="avg", target_column="transfer_count",
    ),
}


def main() -> None:
    load = make_loader()
    passed = 0
    for inst_id, spec in SPECS.items():
        level = inst_id.split("-")[1]
        gt = json.loads((INPUT_DIR / level / f"{inst_id}.json").read_text())["ground_truth"]
        result = run_query(spec, load)
        ok = is_correct(result, gt["value"])
        passed += ok
        flag = "OK " if ok else "FAIL"
        print(f"  [{flag}] {inst_id:10s} executor={result!r:>18}  gt={gt['value']!r}")
    print(f"\n{passed}/{len(SPECS)} executor specs match ground truth")


if __name__ == "__main__":
    main()
