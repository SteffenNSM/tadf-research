"""Generate the archetype-F robustness checks (perturbed action instructions).

Five checks (3 low, 2 med), each a SURFACE perturbation of a base instance
that BOTH paradigms solved in the clean dev sweep (`f_validation_20260703_140800`,
gpt-5.4-nano: both-solved set = f-low-1/3/4/5, f-med-1/4). The perturbation
rewrites the instruction's phrasing only; the required action values (recipient,
exact subject and body, ids, dates, stages) remain stated in the text, so the
post-state gold and the predicate are UNCHANGED and any drop is a robustness
delta, not a new task. The High tier has no both-solved anchor on the dev
model -- itself a finding, mirroring archetype B (IT-043 method note) -- so no
high check exists; re-anchor after the final-model clean run if the High tier
stabilizes there.

Perturbation types follow the discriminating patterns from D (IT-041/045):
colloquial wrappers with a buried ask, decision-critical values written as
words, a self-correction on the critical id, jargon synonyms for target
states, and redundant narrative noise.

Run:
    python experiments/make_f_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "f_action_execution"
OUT_DIR = IN_DIR / "robustness"

# (rid, base_id, subdir, difficulty, perturbation_type, perturbed instruction)
CHECKS = [
    (
        "rf-low-1", "f-low-1", "low", "low", "colloquial_buried",
        "hey, quick one -- been meaning to get this out all week. can you shoot "
        "contact005@example.com a note for me? subject line should be exactly "
        "'Q3 status update', and for the body just use this text as it is: 'Hi, I "
        "wanted to share our Q3 status update for your account. This quarter we "
        "resolved the open billing issues, completed the integration handover, and "
        "have a few recommendations to discuss for next quarter. Let me know if you "
        "would like to set up a short call. Best regards, Account Team.' thanks!!",
    ),
    (
        "rf-low-2", "f-low-3", "low", "low", "values_as_words",
        "please put a meeting called 'Sales review' into the calendar for the "
        "fifteenth of June twenty twenty-six, from ten to eleven in the morning, "
        "and invite contact010@example.com to it.",
    ),
    (
        "rf-low-3", "f-low-4", "low", "low", "self_correction_on_id",
        "we're cleaning the shared mailbox a bit. delete the email with id 4 -- "
        "hold on, wrong row, I mean the one with id 5. just that one, leave "
        "everything else as it is.",
    ),
    (
        "rf-med-1", "f-med-1", "med", "med", "jargon_synonym",
        "every open ticket currently sitting with agent #3 needs to move to WIP -- "
        "that's the 'In Progress' status in our CRM. only the ones still in 'Open', "
        "obviously; don't touch anything that's already moving.",
    ),
    (
        "rf-med-2", "f-med-4", "med", "med", "redundant_buried",
        "so the pricing committee met yesterday (long story, don't ask) and decided "
        "we're pulling back on all the deals we'd already pushed into contract "
        "talks. concretely, what I need in the system: every opportunity that is "
        "currently in stage 'Negotiation' goes back to stage 'Proposal'. nothing "
        "else changes, no emails to anyone, just the stage downgrades please.",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, diff, ptype, instruction in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {
            "id": rid,
            "archetype": "F",
            "difficulty": diff,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "instruction": instruction,
            "expected_post_state": base["expected_post_state"],  # unchanged
            "provenance": {
                "construction_method": (
                    f"Surface perturbation ({ptype}) of {base_id}'s instruction; all action "
                    "values remain stated in the text, post-state gold and predicate unchanged. "
                    "Robustness check, not a new task."
                ),
                "license": base["provenance"]["license"],
            },
        }
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:9} <- {base_id:8} [{ptype:20}] gold: {base['expected_post_state'][:70]}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
