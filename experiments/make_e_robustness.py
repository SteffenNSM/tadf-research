"""Generate the archetype-E robustness checks (perturbed customer inquiries).

Five checks (2 low, 2 med, 1 high), each a SURFACE perturbation of a base
instance that BOTH paradigms solved in the rebuilt-E clean dev run
(`e_validation_20260702_180852`, gpt-5.4-nano: both-solved = e-low-2/3/4/5,
e-med-1/3/5, e-high-3/4 -- unlike F and H, E has High-tier anchors).

E's robustness lever is the INQUIRY: the artefact under judgment (the
candidate response) and hence the per-criterion gold (`criterion_failures`)
are copied verbatim; only the customer's message is rewritten in a messy
style, with every issue, identifier, amount, and date still stated. The
criterion outcomes are invariant to the inquiry's phrasing by construction
(C1/C5 depend on WHAT the inquiry states, which is preserved), so any drop
is a robustness delta of the judgment under noisy input, not a new task.

Run:
    python experiments/make_e_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "e_output_verification"
OUT_DIR = IN_DIR / "robustness"

# (rid, base_id, subdir, perturbation_type, perturbed inquiry BODY)
CHECKS = [
    (
        "re-low-1", "e-low-2", "low", "colloquial_typos",
        "hey so order #51234 was meant to show up yesterday n it never came?? can "
        "someone plz check whats going on, we kinda need that stuff",
    ),
    (
        "re-low-2", "e-low-4", "low", "angry_rambling",
        "honestly, what is going on over there. logged in this morning and boom, "
        "account suspended, zero warning, zero explanation, nothing. i have a "
        "client meeting TODAY and i need access urgently. account id is 4477 by "
        "the way. this keeps getting better and better.",
    ),
    (
        "re-med-1", "e-med-1", "med", "redundant_selfcorrecting",
        "hi, quick one about my order #20030 -- it arrived damaged last week (the "
        "box was fine actually, the item inside wasn't, anyway). support told me a "
        "refund of $200 would be processed... i think it was $200, yes, $200. when "
        "will i actually see that on my card?",
    ),
    (
        "re-med-2", "e-med-3", "med", "jargon_indirect",
        "before our AP team locks the period we would like to sanity-check the "
        "renewal cadence: our records show the renewal billing hitting April 1, "
        "2026 at $24,000 -- can you confirm both the date and the amount?",
    ),
    (
        "re-high-1", "e-high-3", "high", "buried_noise",
        "hi -- a few things, mostly one big thing. we rolled the new build last "
        "week (fine), the dashboards are fine too. the actual problem: our "
        "Salesforce integration keeps failing intermittently, roughly once an "
        "hour the sync job errors out and we retry by hand, which is getting old "
        "fast. it's case #155. please look at that one.",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, ptype, body in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {**base}  # candidate_response, criterion_failures, expected_label verbatim
        inst["inquiry"] = {**base["inquiry"], "body": body}
        inst.update({
            "id": rid,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "provenance": {
                "construction_method": (
                    f"Surface perturbation ({ptype}) of {base_id}'s inquiry body; the candidate "
                    "response, the criterion-failure gold, and the expected label are copied "
                    "verbatim, and every issue, identifier, amount, and date remains stated. "
                    "Robustness check, not a new task."
                ),
                "license": base["provenance"]["license"] if isinstance(base.get("provenance"), dict) else "Original work by the author",
            },
        })
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:9} <- {base_id:9} [{ptype:24}] gold={base['expected_label']} ({base['criterion_failures']})")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
