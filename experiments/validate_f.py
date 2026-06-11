"""End-to-end validation for archetype F with the real LLM.

Runs the workflow and the agent on a small set of action instances, captures
the execution telemetry, resets the database before each run, and scores the
outcome by querying the post-state of the database against the registered
predicate.

The DB reset uses ``experiments/load_db.load()`` to rebuild ``data/crm.db`` from
the seed JSON, restoring the schema and the baseline records. Each task
therefore runs against a clean, identical pre-state.

Run:
    python experiments/seed_crm.py        # if not yet generated
    python experiments/seed_actions.py    # if not yet generated
    python experiments/load_db.py         # build crm.db from seed
    python experiments/validate_f.py            # one instance per difficulty (low-1, med-1, high-1)
    python experiments/validate_f.py --all      # all 15 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_actions import PREDICATES
from src.archetypes.f_action_execution.agent import run_agent
from src.archetypes.f_action_execution.ground_truth import score
from src.archetypes.f_action_execution.workflow import workflow
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "f_action_execution"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    if all_:
        picks = [f"{lvl}/f-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
    else:
        picks = ["low/f-low-1", "med/f-med-1", "high/f-high-1"]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def run_workflow_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    output = state.get("output", {})
    return output, logger.to_record()


def run_agent_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(inst["instruction"], config={"callbacks": [logger]})
    logger.stop()
    summary = result["messages"][-1].content if result.get("messages") else ""
    return summary, logger.to_record()


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(f"{'instance':12} {'paradigm':9} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  summary")
    print("-" * 100)
    for inst in instances:
        for name, runner in (("workflow", _w := run_workflow_instance), ("agent", _a := run_agent_instance)):
            row: dict = {
                "instance": inst["id"],
                "difficulty": inst["difficulty"],
                "sub_class": inst.get("sub_class"),
                "paradigm": name,
            }
            try:
                # Reset DB to the clean seed before each paradigm run
                reset_database()
                output, rec = runner(inst)
                # Outcome-centric score against the post-state predicate
                s, rationale = score(inst["id"], PREDICATES)
                ok = s >= 1.0
                summary = (
                    output.get("summary", "") if isinstance(output, dict) else str(output)
                )
                row.update({"correct": ok, "summary": summary[:120], "predicate_rationale": rationale, **rec})
                print(
                    f"{inst['id']:12} {name:9} {str(ok):7} {rec['total_tokens']:>8} "
                    f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(summary)[:60]!r}"
                )
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:12} {name:9} ERROR  {str(e)[:80]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"f_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
