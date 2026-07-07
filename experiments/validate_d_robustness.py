"""Run the archetype-D robustness checks (perturbed requests) and score them.

Loads the six perturbed instances, runs both paradigms exactly as the main D
sweep does (``validate_d`` runners), and scores the predicted decision against
the (unchanged) base gold. All six base instances were solved by BOTH paradigms
in the clean run, so any failure here is a robustness loss attributable to the
labelled perturbation. Results are written to the model-stamped results
directory (dev models -> results/dev/).

Run:
    PYTHONPATH=. TADF_MODEL=gpt-5.4-nano-2026-03-17 python experiments/validate_d_robustness.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from experiments.validate_d import run_agent_instance, run_workflow_instance
from src.archetypes.d_compliance_decisioning.ground_truth import extract_label, score
from src.core.llm import MODEL_NAME, results_dir

REPO = Path(__file__).resolve().parents[1]
ROBUST_DIR = REPO / "data" / "test_inputs" / "d_compliance_decisioning" / "robustness"
RESULTS = REPO / "data" / "results"

ORDER = ["rd-low-1", "rd-low-2", "rd-med-1", "rd-med-2", "rd-high-1", "rd-high-2"]

_FINAL_ANSWER_RE = re.compile(r"FINAL_ANSWER\s*:\s*\**\s*[A-Za-z_]+", re.IGNORECASE)


def main() -> None:
    rows: list[dict] = []
    print(
        f"{'id':10} {'base':9} {'perturbation':18} {'paradigm':9} {'correct':7} "
        f"{'tokens':>7} {'tools':>5}  predicted -> expected"
    )
    print("-" * 96)
    for rid in ORDER:
        inst = json.loads((ROBUST_DIR / f"{rid}.json").read_text())
        gold = inst["expected_label"]
        for name, runner in (
            ("workflow", run_workflow_instance),
            ("agent", run_agent_instance),
        ):
            row = {
                "instance": rid,
                "base_instance": inst["base_instance"],
                "perturbation_type": inst["perturbation_type"],
                "critical_fact": inst.get("critical_fact"),
                "difficulty": inst["difficulty"],
                "paradigm": name,
                "expected": gold,
            }
            try:
                output, rec = runner(inst)
                if name == "workflow":
                    predicted = output.get("label") if isinstance(output, dict) else None
                else:
                    summary_text = output if isinstance(output, str) else ""
                    predicted = extract_label(summary_text)
                    row["final_answer_line_present"] = bool(_FINAL_ANSWER_RE.search(summary_text))
                s, rationale = score(predicted, gold)
                ok = s >= 1.0
                row.update({"correct": ok, "predicted": predicted, "score_rationale": rationale, **rec})
                print(
                    f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:18} "
                    f"{name:9} {str(ok):7} {rec['total_tokens']:>7} {rec['tool_call_count']:>5}  "
                    f"{predicted!r} -> {gold!r}"
                )
            except Exception as e:
                row.update({"correct": False, "error": str(e)[:200]})
                print(f"{rid:10} {inst['base_instance']:9} {inst['perturbation_type']:18} {name:9} ERROR  {str(e)[:50]}")
            rows.append(row)

    out_dir = results_dir(RESULTS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"d_robustness_{stamp}.json"
    out.write_text(json.dumps({"timestamp": stamp, "model": MODEL_NAME, "runs": rows}, indent=2, default=str))
    print(f"\nResults written to {out.relative_to(REPO)}")
    print("Baseline: all six base instances were solved by both paradigms in the clean run.")


if __name__ == "__main__":
    main()
