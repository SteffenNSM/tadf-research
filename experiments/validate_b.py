"""End-to-end validation for archetype B with the real LLM.

Runs the workflow and the agent on a small set of instances, captures the
execution telemetry, and scores the answers against the ground truth. This
validates the full pipeline (LLM -> QuerySpec -> executor for the workflow;
LLM -> tool calls -> answer for the agent) and shows the paradigm metric
contrast. It is a smoke test, not the full Phase 2 sweep.

Run:
    python experiments/validate_b.py            # one instance per difficulty
    python experiments/validate_b.py --all      # all 15 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from src.archetypes.b_structured_retrieval.agent import run_agent
from src.archetypes.b_structured_retrieval.ground_truth import is_correct
from src.archetypes.b_structured_retrieval.workflow import workflow
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "b_structured_retrieval"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    picks = (
        [f"{lvl}/b-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
        if all_
        else ["low/b-low-1", "med/b-med-1", "high/b-high-1"]
    )
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def run_workflow_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    answer = state.get("output", {}).get("value", "")
    return answer, logger.to_record()


def run_agent_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(inst["instruction"], config={"callbacks": [logger]})
    logger.stop()
    answer = result["messages"][-1].content if result.get("messages") else ""
    return answer, logger.to_record()


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(f"{'instance':12} {'paradigm':9} {'correct':7} {'tokens':>8} {'tools':>5} {'lat_s':>6}  answer")
    print("-" * 80)
    for inst in instances:
        gt = inst["ground_truth"]["value"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {"instance": inst["id"], "difficulty": inst["difficulty"], "paradigm": name, "ground_truth": gt}
            try:
                answer, rec = runner(inst)
                ok = is_correct(answer, gt)
                row.update({"correct": ok, "answer": str(answer), **rec})
                print(f"{inst['id']:12} {name:9} {str(ok):7} {rec['total_tokens']:>8} "
                      f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(answer)[:40]!r} (gt={gt!r})")
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:12} {name:9} ERROR  {str(e)[:80]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"b_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
