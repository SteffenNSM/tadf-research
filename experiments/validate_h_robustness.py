"""Run the archetype-H robustness checks (perturbed drafting briefs).

Loads the five perturbed instances and runs both paradigms through the main
sweep's ``run_one`` (deterministic compliance layer plus frozen-prompt judge).
Constraints, table, feedback rounds, and allowed numbers are verbatim copies
of the both-passed base instances, so any compliance drop is attributable to
the perturbed brief phrasing. Compliance is the binding robustness signal;
OQS is recorded alongside as the soft secondary metric, as in the main sweep.

Run:
    PYTHONPATH=. python experiments/validate_h_robustness.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.validate_h import run_one
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "h_content_drafting" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["rh-low-1", "rh-low-2", "rh-low-3", "rh-med-1", "rh-med-2"]


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':9} {'base':8} {'perturbation':19} {'paradigm':9} {'compl':6} {'rate':>5} {'oqs':>4} {'tok':>7}")
    print("-" * 84)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        for paradigm in ("workflow", "agent"):
            try:
                row = run_one(inst, paradigm)
                row.update({
                    "base_instance": inst["base_instance"],
                    "perturbation_type": inst["perturbation_type"],
                })
                print(f"{rid:9} {inst['base_instance']:8} {inst['perturbation_type']:19} {paradigm:9} "
                      f"{str(row['compliance_all_pass']):6} {row['compliance_rate']:>5} "
                      f"{row['oqs']:>4} {row['total_tokens']:>7}")
            except Exception as e:  # noqa: BLE001
                row = {"instance": rid, "base_instance": inst["base_instance"],
                       "perturbation_type": inst["perturbation_type"],
                       "paradigm": paradigm, "compliance_all_pass": False,
                       "error": str(e)[:200]}
                print(f"{rid:9} {inst['base_instance']:8} {inst['perturbation_type']:19} {paradigm:9} ERROR {str(e)[:40]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"h_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Anchors: compliance both-passed set of h_validation_20260616_111547_rescored (gpt-5.2); no High anchor exists.")


if __name__ == "__main__":
    main()
