"""Run the archetype-B robustness checks (perturbed prompts) and score them.

Loads the six perturbed instances, runs both paradigms exactly as the main
sweep does, and scores against the (unchanged) base gold. All six base
instances were solved by BOTH paradigms in the clean run, so any failure here
is a robustness loss attributable to the labelled perturbation. Results are
written to the model-stamped results directory (dev models -> results/dev/).

Run:
    PYTHONPATH=. TADF_MODEL=gpt-5.4-nano-2026-03-17 python experiments/validate_b_robustness.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.validate_b import run_agent_instance, run_workflow_instance
from src.archetypes.b_structured_retrieval.ground_truth import is_correct
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["r-low-1", "r-low-2", "r-low-3", "r-med-1", "r-high-1"]


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':9} {'base':9} {'perturbation':24} {'paradigm':9} {'correct':7} {'tokens':>8}  answer")
    print("-" * 100)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        gt = inst["ground_truth"]["value"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row = {"instance": rid, "base_instance": inst["base_instance"],
                   "perturbation_type": inst["perturbation_type"],
                   "difficulty": inst["difficulty"], "paradigm": name, "ground_truth": gt}
            try:
                answer, rec = runner(inst)
                ok = is_correct(answer, gt)
                row.update({"correct": ok, "answer": str(answer), **rec})
                print(f"{rid:9} {inst['base_instance']:9} {inst['perturbation_type']:24} {name:9} "
                      f"{str(ok):7} {rec['total_tokens']:>8}  {str(answer)[:34]!r}")
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{rid:9} {inst['base_instance']:9} {inst['perturbation_type']:24} {name:9} ERROR  {str(e)[:60]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"b_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Baseline: all six base instances were solved by both paradigms in the clean run.")


if __name__ == "__main__":
    main()
