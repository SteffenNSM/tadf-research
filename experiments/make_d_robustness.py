"""Generate the archetype-D robustness checks (perturbed natural-language requests).

Six checks, two per difficulty tier, each a surface perturbation of a base
instance that was solved by BOTH paradigms in the clean run (d_validation
20260630_185002 — every instance except d-med-2). The gold label is copied
verbatim from the base instance, so the result is a robustness delta versus the
clean baseline: same decision, messier phrasing.

Each check applies ONE labelled, realistic perturbation, and every perturbation
targets a *decision-critical* fact — the field that, if mis-read, would flip the
label. This is deliberate: archetype D's workflow risk is the extraction step
(natural language -> QuoteFacts), and its engine is invariant once the facts are
right; the agent risk is extraction PLUS in-context rule application. Stressing a
gate/bonus/precedence-relevant fact therefore probes exactly where the two
paradigms can diverge. All six perturbed requests still contain every fact needed
to decide, so a failure is attributable to the perturbation, not to missing data.

Perturbation taxonomy (one per check):
    indirect_status      — the lead-qualification gate stated obliquely
    numeric_shorthand    — amounts as '250k' / 'a quarter-million' / '$4k'
    numeric_as_words     — amount and discount spelled out in words
    segment_paraphrase   — the segment (Strategic / Restricted) stated as prose,
                           not as a labelled field, with a distractor sentence

Run:
    python experiments/make_d_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "d_compliance_decisioning"
OUT_DIR = IN_DIR / "robustness"

INSTRUCTION = "Apply the approval policy to this quote request and return the required decision."

# (id, base_id, difficulty, perturbation_type, critical_fact, perturbed request_text)
# Re-anchored on instances both paradigms solved in d_validation_20260702_151746
# (workflow 15/15, agent 9/15). Every request_text carries ALL facts the engine
# needs -- including the new has_credit_hold / is_new_logo -- so the extract step
# can reproduce the gold; each applies one labelled perturbation to a
# decision-critical fact.
CHECKS = [
    (
        "rd-low-1", "d-low-1", "low", "indirect_status", "lead_status (gate G1)",
        "Subject: lead 5001 — policy call\n\n"
        "Hi team, before this goes any further: the lead (5001) hasn't cleared our "
        "qualification step — sales hasn't signed it off yet. The customer is a new "
        "(non-existing) account in the AMER region, Commercial segment, has no "
        "overdue invoices and is not on any credit hold, and this is not a new-logo "
        "acquisition. The deal is $50,000 over a 12-month term at a 5% base discount. "
        "What's the decision?",
    ),
    (
        "rd-low-2", "d-low-5", "low", "numeric_shorthand", "amount (rule P2)",
        "Subject: approval — lead 5005\n\n"
        "Quick one: qualified lead (5005), AMER region, new customer, Commercial "
        "segment, no overdue invoices, no credit hold, not a new-logo deal. It's a "
        "big one — a quarter-million-dollar deal (250k) on a 12-month term, and "
        "they're not even asking for a discount (0%). Where does it route?",
    ),
    (
        "rd-med-1", "d-med-1", "med", "numeric_as_words", "amount + discount",
        "Subject: policy check, lead 5006\n\n"
        "Hey — qualified lead five-thousand-and-six, handled out of our EMEA office, "
        "a brand-new (non-existing) customer in the Commercial segment, no invoices "
        "overdue and no credit hold, not a new-logo win. The deal is fifty thousand "
        "dollars over a twelve-month term with an eight-percent base discount. Let me "
        "know the decision.",
    ),
    (
        "rd-med-2", "d-med-3", "med", "numeric_shorthand", "amount (rule P3 threshold)",
        "Subject: tiny deal, lead 5008\n\n"
        "One of the little ones: qualified lead (5008), AMER, new account, Commercial "
        "segment, nothing overdue, no credit hold, not a new-logo deal. It's just a "
        "$4k deal, 12-month term, with a 6% discount requested. Still needs the policy "
        "run though — what's the verdict?",
    ),
    (
        "rd-high-1", "d-high-1", "high", "negated_and_indirect", "three bonuses at the cap boundary",
        "Subject: lead 5011\n\n"
        "Qualified lead (5011), EMEA region, an existing customer we've had for years "
        "(so not a new-logo). They have no overdue invoices anymore and are no longer "
        "on any credit hold. Commercial segment. The deal is $80,000 on a two-year "
        "term (that's 24 months) at an 18% base discount. What's the decision?",
    ),
    (
        "rd-high-2", "d-high-3", "high", "segment_paraphrase", "segment + new-logo (rule P2s, bonuses B4/B5)",
        "Subject: lead 5013\n\n"
        "Qualified lead (5013), APAC region, a brand-new customer — this is a new-logo "
        "win — with no overdue invoices and no credit hold. Heads up: this is one of "
        "our strategic named accounts. The deal is a hundred-and-fifty-thousand-dollar "
        "deal on a 24-month term with an 8% base discount. Where does it route?",
    ),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, diff, ptype, critical, text in CHECKS:
        base = json.loads((IN_DIR / diff / f"{base_id}.json").read_text())
        inst = {
            "id": rid,
            "archetype": "D",
            "difficulty": diff,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "critical_fact": critical,
            "instruction": INSTRUCTION,
            "request_text": text,
            "quote_request": base["quote_request"],          # reference / gold verifier
            "expected_label": base["expected_label"],         # copied verbatim
            "provenance": {
                "construction_method": (
                    f"Surface perturbation ({ptype}) of {base_id} targeting the "
                    f"decision-critical fact [{critical}]; gold label unchanged. "
                    "Robustness check, not a new task."
                ),
                "license": base["provenance"]["license"],
            },
        }
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:10} <- {base_id:9} [{ptype:18}] gold={base['expected_label']}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
