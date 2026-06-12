"""End-to-end validation for archetype G with the real LLM.

Runs the workflow and the agent on each planning instance, scores the plan
via the deterministic simulator (precondition checks per step, declarative
goal spec on the simulated final state), and persists a per-run telemetry
record to a results JSON. Nothing is executed against the database — the
plan is the deliverable, so no DB reset is needed between runs.

Per-run audit fields:
    plan_parse_ok      — the agent's FINAL_PLAN JSON parsed and validated
                         (workflow plans are schema-valid by construction)
    iteration_overflow — the agent exceeded the per-difficulty step limit
                         (protocol A.6; recorded as failure, OFFICEBENCH
                         convention; resolves D-007 for G)
    n_steps / optimal_length — plan length vs documented optimum
    sim rationale      — failing step + per-check goal breakdown

Run:
    python experiments/seed_planning.py     # generate instances
    python experiments/validate_g.py         # one instance per difficulty
    python experiments/validate_g.py --all   # all 15 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from langgraph.errors import GraphRecursionError

from src.archetypes.g_strategic_planning.agent import run_agent
from src.archetypes.g_strategic_planning.config import MAX_AGENT_STEPS
from src.archetypes.g_strategic_planning.ground_truth import extract_plan, score_plan
from src.archetypes.g_strategic_planning.schemas import Plan
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "g_strategic_planning"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    if all_:
        picks = [f"{lvl}/g-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
    else:
        picks = ["low/g-low-1", "med/g-med-1", "high/g-high-1"]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def run_workflow_instance(inst: dict) -> tuple[Plan | None, dict, bool]:
    from src.archetypes.g_strategic_planning.workflow import workflow

    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    output = state.get("output")
    plan = Plan.model_validate(output) if output else None
    return plan, logger.to_record(), False


def run_agent_instance(inst: dict) -> tuple[Plan | None, dict, bool]:
    logger = ExecutionLogger()
    logger.start()
    limit = MAX_AGENT_STEPS[inst["difficulty"]]
    overflow = False
    text = ""
    try:
        result = run_agent(
            inst["instruction"],
            config={"callbacks": [logger], "recursion_limit": 2 * limit + 1},
        )
        text = result["messages"][-1].content if result.get("messages") else ""
    except GraphRecursionError:
        overflow = True
    logger.stop()
    return extract_plan(text), logger.to_record(), overflow


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(f"{'instance':11} {'paradigm':9} {'correct':7} {'steps':>5} {'opt':>4} "
          f"{'tokens':>8} {'tools':>5} {'lat_s':>6}  detail")
    print("-" * 100)
    for inst in instances:
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {
                "instance": inst["id"],
                "difficulty": inst["difficulty"],
                "sub_class": inst.get("sub_class"),
                "paradigm": name,
                "optimal_length": inst["optimal_length"],
            }
            try:
                plan, rec, overflow = runner(inst)
                s, rationale = (0.0, {"plan_parsed": plan is not None}) if overflow \
                    else score_plan(plan, inst["goal"])
                ok = s >= 1.0
                detail = "iteration_overflow" if overflow else (
                    "ok" if ok else (rationale.get("fail_reason")
                                     or str({k: v for k, v in (rationale.get("goal_breakdown") or {}).items() if not v})))
                row.update({
                    "correct": ok,
                    "plan_parse_ok": plan is not None,
                    "iteration_overflow": overflow,
                    "n_steps": rationale.get("n_steps", 0),
                    "score_rationale": rationale,
                    # Full plan persisted for failure forensics (IT-024):
                    # distinguishes read-stage under-fetch from mis-resolution.
                    "plan_steps": [s.model_dump() for s in plan.steps] if plan else None,
                    **rec,
                })
                print(f"{inst['id']:11} {name:9} {str(ok):7} {rationale.get('n_steps', 0):>5} "
                      f"{inst['optimal_length']:>4} {rec['total_tokens']:>8} "
                      f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(detail)[:60]}")
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:11} {name:9} ERROR  {str(e)[:80]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"g_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
