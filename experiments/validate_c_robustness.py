"""Run the archetype-C robustness checks (perturbed batch triage) and score them.

Loads the five perturbed batch instances, runs both paradigms exactly as the
main C sweep does (``validate_c`` runners), and scores the per-email labels
against the (unchanged) base gold. All base instances were solved 100/100 by
both paradigms in the clean run, so any drop here is a robustness loss
attributable to the labelled perturbation of the email bodies.

Run:
    PYTHONPATH=. TADF_MODEL=gpt-5.4-nano-2026-03-17 python experiments/validate_c_robustness.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.validate_c import run_agent_instance, run_workflow_instance
from src.archetypes.c_ambiguous_classification.ground_truth import (
    extract_batch_labels,
    score_batch,
)
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "c_ambiguous_classification" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["rc-low-1", "rc-low-2", "rc-med-1", "rc-med-2", "rc-high-1"]


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':10} {'base':9} {'perturbation':22} {'para':9} {'acc':>6} {'n':>5} {'tok':>7} {'chunks':>6}")
    print("-" * 82)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        expected = inst["expected"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row = {"instance": rid, "base_instance": inst["base_instance"],
                   "perturbation_type": inst["perturbation_type"], "difficulty": inst["difficulty"],
                   "paradigm": name, "expected": expected}
            try:
                output, rec = runner(inst)
                if name == "workflow":
                    predicted = output.get("labels", {}) if isinstance(output, dict) else {}
                    n_chunks = output.get("n_chunks") if isinstance(output, dict) else None
                else:
                    predicted = extract_batch_labels(output if isinstance(output, str) else "")
                    n_chunks = None
                acc, n_correct, n_total = score_batch(predicted, expected)
                row.update({"accuracy": acc, "n_correct": n_correct, "n_total": n_total,
                            "predicted": predicted, "n_chunks": n_chunks, **rec})
                print(f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:22} {name:9} "
                      f"{acc:>6.2f} {f'{n_correct}/{n_total}':>5} {rec['total_tokens']:>7} {str(n_chunks):>6}")
            except Exception as e:
                row.update({"accuracy": 0.0, "error": str(e)[:200]})
                print(f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:22} {name:9} ERROR {str(e)[:50]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"c_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Baseline: all base instances scored 100/100 for both paradigms in the clean run.")


if __name__ == "__main__":
    main()
