"""Generate the archetype-G robustness checks (perturbed planning instructions).

Six checks (2 low, 2 med, 2 high), each a SURFACE perturbation of a base
instance that BOTH paradigms solved in the clean gpt-5.2 sweep (IT-024,
`g_validation_20260612_170811`: the workflow missed g-low-1, g-med-3,
g-high-2/3/4; the agent solved 15/15, so the both-solved set is
g-low-2/3/4/5, g-med-1/2/4/5, g-high-1/5). G is the only developed archetype
whose High tier HAS both-solved anchors, so unlike F the suite covers all
three tiers. The `goal` spec and `optimal_length` are copied verbatim from
the base instance; only the instruction's phrasing changes, with every id,
subject, date, and value still stated in the text, so any drop is a
robustness delta rather than a new task.

Perturbation types follow the cross-archetype battery (C/D/F): colloquial and
indirect phrasing, values written as words, self-corrections on decision-
critical ids, jargon synonyms for CRM states, and redundant narrative noise.

Run:
    python experiments/make_g_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

from experiments.seed_planning import RUNBOOK

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "g_strategic_planning"
OUT_DIR = IN_DIR / "robustness"

# (rid, base_id, subdir, perturbation_type, perturbed REQUEST part)
# Only the human request is perturbed; the shared RUNBOOK block (a stable
# organizational document) is appended verbatim, exactly as in the bases.
CHECKS = [
    (
        "rg-low-1", "g-low-2", "low", "colloquial_indirect",
        "ugh, case 7... that thing has been open forever. can you finally plan "
        "getting it off the books? heads up, it has been bounced around a lot, so "
        "pick a closing path that actually works. the customer gets the usual note "
        "once it's done, and stick a 30-minute review into the calendar -- call it "
        "'Case 7 review' -- on 2026-06-25, with whoever owns the case attending.",
    ),
    (
        "rg-low-2", "g-low-5", "low", "values_as_words",
        "please set up the kickoff for account six: an event named 'Kickoff "
        "Account 6' on the twenty-second of June twenty twenty-six, attendees are "
        "agent seven and the account's primary contact, and that contact also gets "
        "an email with subject 'Kickoff scheduled'. while you are at it, their open "
        "case twenty-one moves up to 'High' priority.",
    ),
    (
        "rg-med-1", "g-med-1", "med", "redundant_buried",
        "quick context: account 13 has been quiet for months, the CSM changed "
        "twice, and after a long thread (not important here) support agreed we "
        "finally wrap it up. so: their open cases 18, 22 and 67 get closed, the "
        "customer hears about it the usual way, and to round things off there is an "
        "event named 'Account 13 wrap-up' on 2026-06-29 with agent 1 attending.",
    ),
    (
        "rg-med-2", "g-med-2", "med", "self_correction_on_ids",
        "plan the account 14 rebalancing please: their open cases 40, 62, 63 and "
        "117 -- sorry, 118, not 117 -- all move to agent 7... no, wait, agent 8, "
        "that was the final call. each one gets 'Medium' priority in the same "
        "update. agent 8 then gets one mail, subject 'Account 14 cases reassigned', "
        "and there is an event named 'Handover sync' on 2026-06-30 with agent 8 as "
        "attendee. nothing gets closed.",
    ),
    (
        "rg-high-1", "g-high-1", "high", "jargon_synonym",
        "time for the Q2 hygiene sweep on accounts 14 and 16: every open ticket on "
        "those two that isn't escalation-blocked gets resolved -- concretely cases "
        "40, 62, 63 and 118 on account 14 and cases 16, 54, 81 and 104 on account "
        "16 ('resolved' meaning closed in the CRM) -- and the customers hear about "
        "it per the usual routine. opp 3 sadly goes to stage 'Closed Lost'. wrap "
        "with a calendar entry named 'Q2 cleanup review' on 2026-07-02, agents 7 "
        "and 8 attending.",
    ),
    (
        "rg-high-2", "g-high-5", "high", "colloquial_buried",
        "honestly account 16 has dragged on forever, so let's run the full cycle "
        "and be done. their open cases 16, 54, 81 and 104 get closed (case 16 "
        "drops to 'Low' priority after its close), the customer hears about it the "
        "usual way. oh, and opportunity 3 actually came through -- stage 'Closed "
        "Won', is_won true, in a single update. agents 7 and 10 each get one mail, "
        "subject 'Account 16 cycle complete'. plus three events please: 'Account 16 "
        "kickoff EU' on 2026-07-09 with agent 7, 'Account 16 retro' on 2026-07-10 "
        "with agent 10, and 'Account 16 exec review' on 2026-07-11 with agent 7 as "
        "attendees.",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, ptype, instruction in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        inst = {
            "id": rid,
            "archetype": "G",
            "difficulty": base["difficulty"],
            "base_instance": base_id,
            "perturbation_type": ptype,
            "instruction": instruction + RUNBOOK,
            "goal": base["goal"],                    # copied verbatim
            "optimal_length": base["optimal_length"],  # copied verbatim
            "provenance": {
                "construction_method": (
                    f"Surface perturbation ({ptype}) of {base_id}'s instruction; every id, "
                    "subject, date, and value remains stated in the text; goal spec and "
                    "optimal length copied verbatim. Robustness check, not a new task."
                ),
                "license": base["provenance"]["license"],
            },
        }
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:10} <- {base_id:9} [{ptype:22}] optimum={base['optimal_length']}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
