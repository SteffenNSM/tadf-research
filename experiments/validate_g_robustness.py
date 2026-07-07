"""Run the archetype-G robustness checks (perturbed planning instructions).

Loads the six perturbed instances, runs both paradigms exactly as the main G
sweep does (``validate_g`` runners, simulator scoring against the base goal
spec), and persists the same telemetry. The goal specs are copied verbatim
from the both-solved base instances, so any drop against the clean run is a
robustness loss attributable to the labelled surface perturbation.

Run:
    PYTHONPATH=. python experiments/validate_g_robustness.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.validate_g import run_agent_instance, run_workflow_instance
from src.archetypes.g_strategic_planning.ground_truth import score_plan
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "g_strategic_planning" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["rg-low-1", "rg-low-2", "rg-med-1", "rg-med-2", "rg-high-1", "rg-high-2"]


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':10} {'base':9} {'perturbation':22} {'paradigm':9} {'correct':7} {'steps':>5} {'tokens':>8}")
    print("-" * 90)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row = {
                "instance": rid,
                "base_instance": inst["base_instance"],
                "perturbation_type": inst["perturbation_type"],
                "difficulty": inst["difficulty"],
                "paradigm": name,
                "optimal_length": inst["optimal_length"],
            }
            try:
                plan, rec, overflow = runner(inst)
                s, rationale = (0.0, {"plan_parsed": plan is not None}) if overflow \
                    else score_plan(plan, inst["goal"])
                ok = s >= 1.0
                row.update({
                    "correct": ok,
                    "plan_parse_ok": plan is not None,
                    "iteration_overflow": overflow,
                    "n_steps": rationale.get("n_steps", 0),
                    "score_rationale": rationale,
                    "plan_steps": [st.model_dump() for st in plan.steps] if plan else None,
                    **rec,
                })
                print(f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:22} {name:9} "
                      f"{str(ok):7} {rationale.get('n_steps', 0):>5} {rec['total_tokens']:>8}")
            except Exception as e:  # noqa: BLE001
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:22} {name:9} ERROR {str(e)[:40]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"g_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Anchors: both-solved set of the clean gpt-5.2 run g_validation_20260612_170811 (IT-024).")


if __name__ == "__main__":
    main()
