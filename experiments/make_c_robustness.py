"""Generate the archetype-C robustness checks (perturbed batch triage).

Five checks (2 low, 2 med, 1 high), each a surface perturbation of a base batch
instance that BOTH paradigms solved cleanly (all 15 C instances score 100/100
on the clean run). The perturbation rewrites the email bodies in a messy style;
the email ids, subjects, and the per-email gold (`expected`) are copied verbatim
so the result is a robustness delta rather than a new task. Each check applies
one labelled perturbation to the whole batch.

Run:
    python experiments/make_c_robustness.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IN_DIR = REPO / "data" / "test_inputs" / "c_ambiguous_classification"
OUT_DIR = IN_DIR / "robustness"

# (rid, base_id, subdir, difficulty, perturbation_type, [perturbed body per email in order])
CHECKS = [
    ("rc-low-1", "c-low-1", "low", "low", "typos", [
        "the sept invoce total looks wrong — can someone doublecheck the charges n tell me whats going on?",
        "since this mornin the dashbaord crashes w a 500 error whenver i open the reprots page. pls fix",
        "my ordr shiped 5 days ago but the trackign hasnt moved. can u tell me where the packge is?",
    ]),
    ("rc-low-2", "c-low-2", "low", "low", "colloquial", [
        "hey can u add my new coworker Sara onto our team acct with editor access? thx",
        "yo quick one — any way to export a report to csv? couldnt find it in the docs",
        "soo that refund u confirmed like 2 weeks ago still hasnt hit our card. wheres it at?",
    ]),
    ("rc-med-1", "c-med-1", "med", "med", "jargon_synonym", [
        "post the role change i've lost visibility into the billing module — my peers can see it fine so it's not an outage, just need my entitlements reinstated",
        "we de-provisioned three seats last cycle and the app reflects it, but this statement still bills the old seat count — please true up the charge",
        "our CSV egress on large reports errors out every run — is that by design or a defect? for us it never completes",
        "you dispatched the wrong SKU; kindly ship the correct unit — we can reconcile the price delta afterwards, the priority is the right item",
        "our weekly aggregates looked off so we suspected a bug; turns out the figures are right, we just don't grok how your 'week' is bucketed — can you explain the rollup?",
    ]),
    ("rc-med-2", "c-med-2", "med", "med", "redundant_selfcorrecting", [
        "our new contractor — well, contractor-to-be — says the portal doesn't work, but it works for the rest of us, so i mean it's not down, they just never got added; pls give viewer access to the Atlas project",
        "love the tool, anyway — small thing, the webhook docs are thin, for later — the thing i need now, sorry: our last invoice has two identical line items, we got double-charged, refund one pls",
        "thanks for the address fix last week; separate thing, that charge question is resolved on our side — the actual live issue: nightly data sync via your API has timed out for 3 nights, reports are stale, pls look",
        "after you changed my role, or updated it i guess, i can't reach billing anymore — colleagues can, so not an outage — just restore my perms",
        "we removed seats last month, that part's done, but the invoice, this one, still charges the old count — fix the charge pls",
    ]),
    ("rc-high-1", "c-high-1", "high", "high", "jargon_typos", [
        "csv egress on big reprots errrors out evry time — intended or broke? never completes for us",
        "you shiped the wrong unit, pls send the corect one — can sort the price diff after, priority is the right item",
        "weekly totals lookd wrong so we thot bug, but the numbrs r right — we jst dont get how yr 'week' is defined, explain the rollup?",
        "busy qtr, team loved the dashbaord, admin re-added 2 seats (sorted) — real ask: our renewal invoce has a mid-term price hike we never agreed to, pls explain n correct the pricing",
        "hw add-on shiped late (resolved), someone askd about pdf export (no rush) — URGENT: since tues release the login page errors for ALL our users, nobody can get in, its on yr side, P1 pls",
        "splitting into 2 regional teams, ill get new invoces n the new hires want a walkthru later — rn what i need: move 8 users from the EMEA org to a new APAC org n set their manager, pure acct-structure change",
        "support was slow, app logged me out twice (back in fine), still dont get the new bill line — but whats blocking us: the replacment device promised for mon still isnt here, its thurs no trackign, where is it?",
        "analysts flagd reporting as 'broken' cuz numbers dont add up — dug in, not a defect, figures r correct — we jst need to understand how yr rollups define a week n the cutoff, no fix needed",
    ]),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rid, base_id, subdir, diff, ptype, bodies in CHECKS:
        base = json.loads((IN_DIR / subdir / f"{base_id}.json").read_text())
        assert len(bodies) == len(base["emails"]), f"{rid}: {len(bodies)} bodies vs {len(base['emails'])} emails"
        emails = []
        for e, body in zip(base["emails"], bodies):
            emails.append({"id": e["id"], "sender": e["sender"], "subject": e["subject"], "body": body})
        inst = {
            "id": rid,
            "archetype": "C",
            "difficulty": diff,
            "base_instance": base_id,
            "perturbation_type": ptype,
            "instruction": base["instruction"],
            "emails": emails,
            "expected": base["expected"],          # copied verbatim
            "provenance": {
                "construction_method": f"Surface perturbation ({ptype}) of {base_id}'s email bodies; ids/subjects/gold unchanged. Robustness check, not a new task.",
                "license": base["provenance"]["license"],
            },
        }
        (OUT_DIR / f"{rid}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        print(f"{rid:10} <- {base_id:9} [{ptype:22}] {len(emails)} emails, gold={list(base['expected'].values())}")
    print(f"\n{len(CHECKS)} robustness instances written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
