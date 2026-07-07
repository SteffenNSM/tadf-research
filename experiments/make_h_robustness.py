"""Generate the archetype-H robustness checks (perturbed drafting briefs).

Five checks (3 low, 2 med), each a SURFACE perturbation of a base instance
that BOTH paradigms passed on the deterministic compliance layer in the clean
gpt-5.2 sweep (`h_validation_20260616_111547_rescored`: both-passed set =
h-low-1/2/3/5, h-med-1/2; the High tier has NO both-passed anchor -- the agent
passed none -- the same anchor gap as archetype F, itself a finding).

H's gold-relevant content lives in STRUCTURED fields (constraints, table,
feedback_rounds, allowed_numbers), which are copied verbatim; only the free-
text `instruction` is perturbed. Any compliance drop is therefore a
robustness delta of the brief's phrasing, not a changed task. The scripted
feedback rounds are untouched: they model a stable reviewer, and both
paradigms receive them identically.

Run:
    python experiments/make_h_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "h_content_drafting"
OUT_DIR = IN_DIR / "robustness"

# (rid, base_id, subdir, perturbation_type, perturbed instruction)
CHECKS = [
    (
        "rh-low-1", "h-low-1", "low", "colloquial_buried",
        "hey, marketing pinged me about this twice already -- can you whip up a "
        "short LinkedIn post announcing this quarter's product revenue? nothing "
        "fancy, the numbers are in the table below.",
    ),
    (
        "rh-low-2", "h-low-3", "low", "indirect_request",
        "we finally hit that customer milestone everyone has been waiting for -- "
        "would be great if something celebratory went out about it. a post, you "
        "know the drill.",
    ),
    (
        "rh-low-3", "h-low-5", "low", "redundant_noise",
        "so the CSAT results landed yesterday, took forever this time (the survey "
        "tool acted up again, different story). anyway -- write a brief post "
        "sharing the latest customer satisfaction score, please.",
    ),
    (
        "rh-med-1", "h-med-1", "med", "colloquial_indirect",
        "the sales director wants to know how Q3 went across our three product "
        "lines -- can you put that into an email for her? summary style, she "
        "reads fast.",
    ),
    (
        "rh-med-2", "h-med-2", "med", "redundant_buried",
        "the leadership offsite is coming up and they asked for pre-reads (agenda "
        "chaos as usual, not your problem). what I need from you: a one-page "
        "report on the quarter's hiring funnel for the leadership team.",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, ptype, instruction in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {**base}  # constraints, table, feedback, allowed_numbers verbatim
        inst.update({
            "id": rid,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "instruction": instruction,
            "provenance": {
                "construction_method": (
                    f"Surface perturbation ({ptype}) of {base_id}'s brief instruction; the "
                    "structured constraint, table, feedback, and allowed-number fields are "
                    "copied verbatim. Robustness check, not a new task."
                ),
                "license": base["provenance"]["license"],
            },
        })
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:9} <- {base_id:8} [{ptype:19}] format={base['format']}, fb={len(base['feedback_rounds'])}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
