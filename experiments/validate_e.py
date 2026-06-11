"""End-to-end validation for archetype E with the real LLM.

Runs the workflow and the agent on each verification instance, scores the
predicted verdict against the curated gold, and persists a per-run
telemetry record (tokens, tool calls, latency, predicted vs expected
label, FINAL_ANSWER format compliance for the agent) to a results JSON.

The workflow returns its label via the QualityVerdict schema (the label is
constrained to the Literal); the agent returns free text and the label is
extracted by the ground-truth helper from the final message content.

Run:
    python experiments/seed_verification.py     # generate instances
    python experiments/validate_e.py             # one instance per difficulty
    python experiments/validate_e.py --all       # all 15 instances
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from src.archetypes.e_output_verification.agent import run_agent
from src.archetypes.e_output_verification.ground_truth import (
    extract_label,
    score,
)
from src.archetypes.e_output_verification.workflow import workflow
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "e_output_verification"
RESULTS = REPO / "data" / "results"

_FINAL_ANSWER_RE = re.compile(r"FINAL_ANSWER\s*:\s*\**\s*[A-Za-z_]+", re.IGNORECASE)


def load_instances(all_: bool) -> list[dict]:
    if all_:
        picks = [
            f"{lvl}/e-{lvl}-{n}"
            for lvl in ("low", "med", "high")
            for n in range(1, 6)
        ]
    else:
        picks = ["low/e-low-1", "med/e-med-1", "high/e-high-1"]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def run_workflow_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {
            "input_id": inst["id"],
            "instruction": inst["instruction"],
            "inquiry": inst["inquiry"],
            "candidate_response": inst["candidate_response"],
        },
        config={"callbacks": [logger]},
    )
    logger.stop()
    output = state.get("output", {})
    return output, logger.to_record()


def run_agent_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(
        inst["instruction"],
        inst["inquiry"],
        inst["candidate_response"],
        config={"callbacks": [logger]},
    )
    logger.stop()
    summary = result["messages"][-1].content if result.get("messages") else ""
    return summary, logger.to_record()


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(
        f"{'instance':12} {'paradigm':9} {'correct':7} "
        f"{'tokens':>8} {'tools':>5} {'lat_s':>6}  predicted -> expected"
    )
    print("-" * 100)
    for inst in instances:
        gold = inst["expected_label"]
        for name, runner in (
            ("workflow", run_workflow_instance),
            ("agent", run_agent_instance),
        ):
            row: dict = {
                "instance": inst["id"],
                "difficulty": inst["difficulty"],
                "sub_class": inst.get("sub_class"),
                "paradigm": name,
            }
            try:
                output, rec = runner(inst)
                if name == "workflow":
                    predicted = (
                        output.get("label") if isinstance(output, dict) else None
                    )
                    summary_text = (
                        output.get("rationale", "")
                        if isinstance(output, dict)
                        else str(output)
                    )
                else:
                    summary_text = output if isinstance(output, str) else ""
                    predicted = extract_label(summary_text)
                    row["final_answer_line_present"] = bool(
                        _FINAL_ANSWER_RE.search(summary_text)
                    )
                s, rationale = score(predicted, gold)
                ok = s >= 1.0
                row.update(
                    {
                        "correct": ok,
                        "predicted": predicted,
                        "expected": gold,
                        "score_rationale": rationale,
                        "summary": summary_text[:200],
                        **rec,
                    }
                )
                print(
                    f"{inst['id']:12} {name:9} {str(ok):7} "
                    f"{rec['total_tokens']:>8} {rec['tool_call_count']:>5} "
                    f"{rec['latency_s']:>6.1f}  {predicted!r} -> {gold!r}"
                )
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{inst['id']:12} {name:9} ERROR  {str(e)[:80]}")
            rows.append(row)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS / f"e_validation_{stamp}.json"
    out.write_text(
        json.dumps({"timestamp": stamp, "runs": rows}, indent=2, default=str)
    )
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
