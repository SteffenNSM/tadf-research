"""End-to-end validation for archetype A with the real LLM and live web search.

Runs the workflow and the agent on a small set of research instances, captures
the execution telemetry, and scores the answers with the frozen-prompt LLM
judge. Web-search snippets are cached on disk on first call, so re-runs are
reproducible and both paradigms see identical snippets for identical queries.

Run:
    python experiments/seed_research.py            # generate instances first
    python experiments/validate_a.py               # one instance per difficulty
    python experiments/validate_a.py --all         # all 15 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from src.archetypes.a_exploratory_research.agent import run_agent
from src.archetypes.a_exploratory_research.ground_truth import score
from src.archetypes.a_exploratory_research.workflow import workflow
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "a_exploratory_research"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    picks = (
        [f"{lvl}/a-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
        if all_
        else ["low/a-low-1", "med/a-med-1", "high/a-high-1"]
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
    answer = state.get("output", {}).get("answer", "")
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
    print("-" * 100)
    for inst in instances:
        gt = inst["ground_truth"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {"instance": inst["id"], "difficulty": inst["difficulty"], "paradigm": name, "ground_truth": gt["value"]}
            try:
                answer, rec = runner(inst)
                s, rationale = score(answer, gt, inst["instruction"])
                ok = s >= 1.0
                row.update({"correct": ok, "answer": str(answer), "judge_rationale": rationale, **rec})
                print(f"{inst['id']:12} {name:9} {str(ok):7} {rec['total_tokens']:>8} "
                      f"{rec['tool_call_count']:>5} {rec['latency_s']:>6.1f}  {str(answer)[:50]!r} (gt={gt['value']!r})")
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:12} {name:9} ERROR  {str(e)[:80]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"a_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
