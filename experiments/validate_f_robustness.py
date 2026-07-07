"""Run the archetype-F robustness checks (perturbed instructions) and score them.

Loads the five perturbed instances, runs both paradigms exactly as the main F
sweep does (``validate_f`` runners, DB reset to the seed before every run),
and scores the post-state with the BASE instance's predicate -- the gold is
unchanged by construction, so any drop against the clean run is a robustness
loss attributable to the labelled surface perturbation.

Run:
    PYTHONPATH=. python experiments/validate_f_robustness.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from experiments.load_db import load as reset_database
from experiments.seed_actions import PREDICATES
from experiments.validate_f import run_agent_instance, run_workflow_instance
from src.archetypes.f_action_execution.ground_truth import score
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "f_action_execution" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["rf-low-1", "rf-low-2", "rf-low-3", "rf-med-1", "rf-med-2"]


def main() -> None:
    rows: list[dict] = []
    print(f"{'id':9} {'base':8} {'perturbation':20} {'paradigm':9} {'correct':7} {'tokens':>8} {'tools':>5}")
    print("-" * 84)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        base_id = inst["base_instance"]
        for name, runner in (("workflow", run_workflow_instance), ("agent", run_agent_instance)):
            row = {
                "instance": rid,
                "base_instance": base_id,
                "perturbation_type": inst["perturbation_type"],
                "difficulty": inst["difficulty"],
                "paradigm": name,
            }
            try:
                reset_database()
                output, rec = runner(inst)
                s, rationale = score(base_id, PREDICATES)  # base predicate, gold unchanged
                ok = s >= 1.0
                summary = (
                    output.get("summary", "") if isinstance(output, dict) else str(output)
                )
                row.update({"correct": ok, "summary": summary[:120], "predicate_rationale": rationale, **rec})
                print(
                    f"{rid:9} {base_id:8} {inst['perturbation_type']:20} {name:9} {str(ok):7} "
                    f"{rec['total_tokens']:>8} {rec['tool_call_count']:>5}"
                )
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{rid:9} {base_id:8} {inst['perturbation_type']:20} {name:9} ERROR  {str(e)[:50]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"f_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Anchors: both-solved set of the clean dev run f_validation_20260703_140800 (no High anchor exists).")


if __name__ == "__main__":
    main()
