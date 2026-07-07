"""Generate the archetype-A robustness checks (perturbed natural-language prompts).

Five checks (2 low, 2 med, 1 high), each a surface perturbation of a base
instance that was solved by BOTH paradigms in the clean run
(a_validation_20260701_131044) AND is non-memorized on the strongest model, with
the gold copied verbatim so the result is a robustness delta rather than a new
task. The High tier supports only one stable both-solved anchor (a-high-5), like
B's High tier. Each check applies one labelled, realistic perturbation so a
failure is attributable to a specific phenomenon.

Run:
    python experiments/make_a_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "a_exploratory_research"
OUT_DIR = IN_DIR / "robustness"

# (id, base_instance, base_subdir, difficulty, perturbation_type, perturbed instruction)
CHECKS = [
    ("ra-low-1", "a-low-2", "low", "low", "typos",
     "whats the name of the guy who foundd BCG (Boston Consluting Group), and the founder of Heidelberg Materials (ex HeidelbergCement)?"),
    ("ra-low-2", "a-low-4", "low", "low", "colloquial",
     "yo that farm-machine company with the double A in Harsewinkel — whats it called, and whats the big old monastery in that town?"),
    ("ra-med-1", "a-med-3", "med", "med", "jargon_synonym",
     "when did the automakers Toyota, VW and Porsche each get established? gimme the founding dates for each"),
    ("ra-med-2", "a-med-5", "med", "med", "redundant_selfcorrecting",
     "i need the street — sorry, street name and building number — of the HQ of RWE AG, of E.ON SE, and of the BMW Group Konzernzentrale"),
    ("ra-high-1", "a-high-5", "high", "high", "jargon_typos",
     "who was runing the town where VEKA AG sits as its mayor / Bürgermeistr back in 2022?"),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, diff, ptype, instr in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {
            "id": rid,
            "archetype": "A",
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
        print(f"{rid:10} <- {base_id:9} [{ptype:24}] gold={base['ground_truth']['value']}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR}")


if __name__ == "__main__":
    main()
