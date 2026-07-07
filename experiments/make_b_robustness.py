"""Generate the archetype-B robustness checks (perturbed natural-language prompts).

Five checks, each a surface perturbation of a base instance that is STABLY
solved by BOTH paradigms across the recent tool-router runs
(b_validation_20260701_151022 + 152452), with the gold copied verbatim so the
result is a robustness delta rather than a new task. The stable both-solved set
is b-low-1..4 plus b-med-2; the High tier has no stable both-solved anchor (its
customer-360 instances flip between runs), so b-high-2 is the single High check
and its result is read with that caveat. Each check applies one labelled,
realistic perturbation so a failure is attributable to a specific phenomenon.

Run:
    python experiments/make_b_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"
OUT_DIR = IN_DIR / "robustness"

# (id, base_instance, base_subdir, difficulty, perturbation_type, perturbed instruction)
CHECKS = [
    ("r-low-1", "b-low-1", "low", "low", "typos",
     "whats the valeu of the deal we wonn with Mayer & Co?"),
    ("r-low-2", "b-low-4", "low", "low", "colloquial",
     "yo how much have we bagged in total from Sunrise Retail deals we actually closed / won?"),
    ("r-low-3", "b-low-2", "low", "low", "jargon_synonym",
     "which sector or vertical does Helvetia Finance operate in?"),
    ("r-med-1", "b-med-2", "med", "med", "redundant_selfcorrecting",
     "there's a call on the calendar about a deal we won — with Mayer, i mean Mayer & Co — how much is that won deal worth again?"),
    ("r-high-1", "b-high-2", "high", "high", "jargon_typos",
     "quick rundown on Sunrise Retail pls — total $ we've clsoed, when they last pinged us, n whats our next mtg?"),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, diff, ptype, instr in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {
            "id": rid,
            "archetype": "B",
            "difficulty": diff,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "instruction": instr,
            "ground_truth": base["ground_truth"],          # copied verbatim
            "provenance": {
                "construction_method": f"Surface perturbation ({ptype}) of {base_id}; gold unchanged. Robustness check, not a new task.",
                "license": base["provenance"]["license"],
            },
        }
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:9} <- {base_id:9} [{ptype:24}] gold={base['ground_truth']['value']}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
