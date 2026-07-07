"""End-to-end validation for archetype C (batch email triage) with the real LLM.

Runs the workflow and the agent on each batch-triage instance, scores the
per-email labels against the curated gold, and persists per-run telemetry
(tokens, tool calls, latency, per-item accuracy, and the workflow's chunk
count) to a results JSON.

The workflow returns ``output['labels']`` as ``{email_id: label}`` via a
deterministic map-reduce over CHUNK_SIZE chunks; the agent returns free text
with one ``FINAL_ANSWER <email_id>: <label>`` line per email, parsed by the
ground-truth helper.

Run:
    python experiments/seed_classification.py     # generate batch instances
    python experiments/validate_c.py               # one instance per difficulty
    python experiments/validate_c.py --all         # all 15 instances
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from src.archetypes.c_ambiguous_classification.agent import run_agent
from src.archetypes.c_ambiguous_classification.ground_truth import (
    extract_batch_labels,
    score_batch,
)
from src.archetypes.c_ambiguous_classification.workflow import workflow
from src.core.llm import MODEL_NAME, results_dir
from src.core.logging import ExecutionLogger

REPO = Path(__file__).resolve().parents[1]
IN = REPO / "data" / "test_inputs" / "c_ambiguous_classification"
RESULTS = REPO / "data" / "results"


def load_instances(all_: bool) -> list[dict]:
    if all_:
        picks = [f"{lvl}/c-{lvl}-{n}" for lvl in ("low", "med", "high") for n in range(1, 6)]
    else:
        picks = ["low/c-low-1", "med/c-med-1", "high/c-high-1"]
    return [json.loads((IN / f"{p}.json").read_text()) for p in picks]


def run_workflow_instance(inst: dict) -> tuple[dict, dict]:
    logger = ExecutionLogger()
    logger.start()
    state = workflow.invoke(
        {"input_id": inst["id"], "instruction": inst["instruction"], "emails": inst["emails"]},
        config={"callbacks": [logger]},
    )
    logger.stop()
    return state.get("output", {}), logger.to_record()


def run_agent_instance(inst: dict) -> tuple[str, dict]:
    logger = ExecutionLogger()
    logger.start()
    result = run_agent(inst["instruction"], inst["emails"], config={"callbacks": [logger]})
    logger.stop()
    summary = result["messages"][-1].content if result.get("messages") else ""
    return summary, logger.to_record()


def main() -> None:
    all_ = "--all" in sys.argv
    instances = load_instances(all_)
    rows: list[dict] = []
    print(f"{'instance':10} {'para':9} {'acc':>7} {'n':>5} {'tok':>7} {'tools':>5} {'chunks':>6} {'lat_s':>6}")
    print("-" * 70)
    for inst in instances:
        expected = inst["expected"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {"instance": inst["id"], "difficulty": inst["difficulty"], "paradigm": name}
            try:
                output, rec = runner(inst)
                if name == "workflow":
                    predicted = output.get("labels", {}) if isinstance(output, dict) else {}
                    n_chunks = output.get("n_chunks") if isinstance(output, dict) else None
                else:
                    predicted = extract_batch_labels(output if isinstance(output, str) else "")
                    n_chunks = None
                acc, n_correct, n_total = score_batch(predicted, expected)
                row.update({
                    "accuracy": acc, "n_correct": n_correct, "n_total": n_total,
                    "all_correct": n_correct == n_total,
                    "predicted": predicted, "expected": expected,
                    "n_chunks": n_chunks, **rec,
                })
                print(f"{inst['id']:10} {name:9} {acc:>6.2f} {f'{n_correct}/{n_total}':>5} "
                      f"{rec['total_tokens']:>7} {rec['tool_call_count']:>5} {str(n_chunks):>6} {rec['latency_s']:>6.1f}")
            except Exception as e:
                row.update({"accuracy": 0.0, "error": str(e)[:200]})
                print(f"{inst['id']:10} {name:9} ERROR  {str(e)[:70]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"c_validation_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
