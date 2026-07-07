"""Run the archetype-E robustness checks (perturbed inquiries) and score them.

Loads the five perturbed instances, runs both paradigms exactly as the main E
sweep does (``validate_e`` runners: decomposed workflow with verdict engine,
holistic agent), and scores against the UNCHANGED per-criterion gold and
expected label. Per-criterion attribution (workflow path) is recorded as in
the main sweep, so criterion-level robustness deltas are visible.

Run:
    PYTHONPATH=. python experiments/validate_e_robustness.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from experiments.validate_e import run_agent_instance, run_workflow_instance
from src.archetypes.e_output_verification.ground_truth import (
    extract_label,
    score,
    score_criteria,
)
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "e_output_verification" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["re-low-1", "re-low-2", "re-med-1", "re-med-2", "re-high-1"]
_FINAL_ANSWER_RE = re.compile(r"FINAL_ANSWER\s*:\s*\**\s*[A-Za-z_]+", re.IGNORECASE)


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':9} {'base':9} {'perturbation':24} {'paradigm':9} {'correct':7} {'crit_acc':>8} {'tok':>7}")
    print("-" * 84)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        gold = inst["expected_label"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row: dict = {
                "instance": rid, "base_instance": inst["base_instance"],
                "perturbation_type": inst["perturbation_type"],
                "difficulty": inst["difficulty"], "paradigm": name,
            }
            try:
                output, rec = runner(inst)
                crit_acc = None
                if name == "workflow":
                    predicted = output.get("label") if isinstance(output, dict) else None
                    if isinstance(output, dict) and "failed_criteria" in output:
                        crit_acc, false_fails, missed_fails = score_criteria(
                            output["failed_criteria"], inst.get("criterion_failures", [])
                        )
                        row.update({
                            "failed_criteria_predicted": output["failed_criteria"],
                            "failed_criteria_gold": inst.get("criterion_failures", []),
                            "criterion_accuracy": crit_acc,
                            "false_fails": false_fails, "missed_fails": missed_fails,
                        })
                else:
                    text = output if isinstance(output, str) else ""
                    predicted = extract_label(text)
                    row["final_answer_line_present"] = bool(_FINAL_ANSWER_RE.search(text))
                s, rationale = score(predicted, gold)
                ok = s >= 1.0
                row.update({"correct": ok, "predicted": predicted, "expected": gold,
                            "score_rationale": rationale, **rec})
                print(f"{rid:9} {inst['base_instance']:9} {inst['perturbation_type']:24} {name:9} "
                      f"{str(ok):7} {str(crit_acc):>8} {rec['total_tokens']:>7}")
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{rid:9} {inst['base_instance']:9} {inst['perturbation_type']:24} {name:9} ERROR {str(e)[:40]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"e_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Anchors: both-solved set of e_validation_20260702_180852 (gpt-5.4-nano, rebuilt E).")


if __name__ == "__main__":
    main()
