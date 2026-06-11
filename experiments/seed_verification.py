"""Curated verification instances for archetype E: Support Response Quality Review.

Writes 15 instance JSON files under ``data/test_inputs/e_output_verification/``
at three difficulty levels (5 each). Each instance contains:
    id, archetype, difficulty, sub_class, instruction, inquiry,
    candidate_response, expected_label, criterion_failures,
    rationale_hint, provenance

Each instance pairs a customer inquiry with a candidate support response;
the gold verdict is determined by counting violated rubric criteria (see
src/archetypes/e_output_verification/config.py for the rubric). Both the
workflow and the agent receive the inquiry and the candidate response
inline; the agent additionally has db_read / db_search exposed (per the
Phase-2 tool-symmetry invariant) but should not need them — every instance
is solvable from the two artefacts in the prompt.

Difficulty axis (Section 4.4 of the protocol, Table A.1 row E):
    Low    — clear cases. A single criterion failure (or zero failures) is
             obvious from a first reading of the candidate response.
    Medium — subtle cases. Failures hide in friendly phrasing
             (vague ETA disguised as concrete, scope creep wrapped in
             optimism, missing reference in a long response).
    High   — boundary cases. The failure count sits near the 1-2 / 3+
             cutoff, or the response looks critical (customer complaint
             plus a bug) but the rubric count says otherwise. These
             instances test whether the judge sticks to the mechanical
             count rule or applies extraneous standards.

Verdict mapping (deterministic; mirrors config.EVALUATION_RUBRIC):
    0 criterion failures      → PASS
    1 or 2 criterion failures → NEEDS_REVISION
    3 or more failures        → FAIL

The ``criterion_failures`` field is the per-instance list of failing
criteria (e.g. ["C2", "C3"]); its length determines the gold verdict
mechanically, and the self-test in this file's main path verifies that
each instance's expected_label agrees with the count.

Source attribution: the rubric and the inquiry/response pairs are
original author work; only the structural pattern of judge-prompts and
ternary quality verdicts is borrowed from the cited benchmarks (WONDERBREAD
SOP Ranking / Demo Validation, Kourani et al. self-improvement,
TheAgentCompany feedback subtasks).

Run:
    python experiments/seed_verification.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "e_output_verification"

BENCHMARK_REF = (
    "WONDERBREAD SOP Ranking and Demo Validation (Wornow et al., 2024); "
    "Kourani et al. (2025) self-improvement; "
    "TheAgentCompany feedback subtasks (Xu et al., 2024)"
)


def _provenance(sub_class: str | None) -> dict:
    note = (
        "Author-constructed inquiry / candidate-response pair and rubric; "
        "task semantics follow the LLM-as-Judge pattern of the cited "
        "benchmarks. No benchmark text or data is reproduced."
    )
    if sub_class:
        note += f" Sub-class: {sub_class}."
    return {
        "source_benchmark": BENCHMARK_REF,
        "adaptation": note,
        # IT-017 honesty rule: original author work; benchmark semantics
        # reference only, no text reuse.
        "license": "Original work by the author (rubric, inquiries, candidate responses); benchmark semantics reference only",
    }


def _verdict_from_failures(failures: list[str]) -> str:
    """Mechanical mapping from the failed-criterion list to the gold verdict.
    Mirrors EVALUATION_RUBRIC in config.py exactly."""
    n = len(failures)
    if n == 0:
        return "PASS"
    if n <= 2:
        return "NEEDS_REVISION"
    return "FAIL"


INSTANCES: list[dict] = [
    # ── LOW: a single criterion failure (or zero) is obvious ──
    {
        "id": "e-low-1",
        "difficulty": "low",
        "sub_class": None,
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "p.muller@acme-eu.example",
            "subject": "Case #42 — shipping delay",
            "body": (
                "Hi, I haven't received the parts from case #42 even though they should "
                "have arrived by now. Could you check on the shipment? Our team needs them "
                "by mid-March."
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #42 — shipping delay",
            "body": (
                "Hi, thanks for following up on case #42. I checked with the carrier and "
                "your shipment is currently delayed in transit due to weather routing — "
                "the new expected delivery date is March 15, 2026. I've attached the "
                "updated tracking link to case #42. If the package has not arrived by "
                "March 15, please reply to this email and we'll dispatch a replacement "
                "via expedited shipping. Best regards, Support."
            ),
        },
        "criterion_failures": [],
        "rationale_hint": (
            "All 5 criteria pass: acknowledges case #42 shipping delay (C1), gives a "
            "specific ETA March 15 with a fallback action (C2), no scope-creep "
            "commitments (C3), professional tone (C4), references case #42 correctly (C5)."
        ),
    },
    {
        "id": "e-low-2",
        "difficulty": "low",
        "sub_class": "vague_eta",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "ops@northwind.example",
            "subject": "Order #51234 not delivered",
            "body": (
                "Hi, order #51234 was supposed to arrive yesterday but it never came. "
                "Could you look into this?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Order #51234",
            "body": (
                "Hi, thanks for your message about order #51234. I'm looking into this "
                "with our shipping team and will get back to you soon. Best regards, "
                "Support."
            ),
        },
        "criterion_failures": ["C2"],
        "rationale_hint": (
            "C2 fails: 'soon' carries no concrete ETA and no actionable next step on the "
            "agent side. C1, C3, C4, C5 pass."
        ),
    },
    {
        "id": "e-low-3",
        "difficulty": "low",
        "sub_class": "wrong_reference",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "rin.takahashi@bluefin.example",
            "subject": "Case #87 — can't log in",
            "body": (
                "Hi, I can't log into my account since yesterday and the password reset "
                "email never arrived. My case number is 87. Could you reset my password "
                "manually?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #78",
            "body": (
                "Hi, thanks for reaching out about case #78. I've reset your password "
                "manually and a new reset email should be in your inbox within 5 minutes. "
                "If you don't see it, please check your spam folder and reply to this "
                "email. Best regards, Support."
            ),
        },
        "criterion_failures": ["C5"],
        "rationale_hint": (
            "C5 fails: response cites case #78 but the inquiry's case number is #87. "
            "C1, C2, C3, C4 pass (specific action, ETA, professional tone)."
        ),
    },
    {
        "id": "e-low-4",
        "difficulty": "low",
        "sub_class": "obvious_multi_fail",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "lila.okonkwo@summitpartners.example",
            "subject": "Account suspended without warning — urgent",
            "body": (
                "Hi, my account was suspended this morning with no warning or explanation. "
                "I need access urgently for a client meeting today. Account ID: 4477."
            ),
        },
        "candidate_response": {
            "subject": "Re: Account question",
            "body": (
                "Hello, looking at account 6601: suspensions usually happen when users "
                "violate the terms of service. You should have read the ToS more "
                "carefully before signing up. We'll look into it eventually."
            ),
        },
        "criterion_failures": ["C1", "C2", "C4", "C5"],
        "rationale_hint": (
            "Four criteria fail: C1 (doesn't address the urgency or the no-warning "
            "complaint, generic 'suspensions usually happen'), C2 ('eventually' no ETA), "
            "C4 ('should have read more carefully' is condescending), C5 (cites account "
            "6601 vs the customer's 4477). C3 passes."
        ),
    },
    {
        "id": "e-low-5",
        "difficulty": "low",
        "sub_class": None,
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "finance@halberd.example",
            "subject": "Annual invoice question — INV-9921",
            "body": (
                "Hi, our annual invoice INV-9921 shows the renewal at $48,000, but our "
                "signed purchase order is for $42,000. Could you check?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Annual invoice question — INV-9921",
            "body": (
                "Hi, thanks for catching this on invoice INV-9921. I've reviewed it "
                "against your purchase order and you're correct: the renewal should be "
                "billed at $42,000. I've initiated a corrected invoice and you'll receive "
                "the updated INV-9921 by end of business tomorrow, with the original "
                "voided in our system. Best regards, Billing Team."
            ),
        },
        "criterion_failures": [],
        "rationale_hint": (
            "All 5 criteria pass: addresses invoice mismatch (C1), concrete action and "
            "next-day ETA (C2), within scope (correction of an obvious billing error, "
            "C3), professional (C4), references INV-9921 correctly (C5)."
        ),
    },
    # ── MEDIUM: subtle violations hidden in friendly phrasing ──
    {
        "id": "e-med-1",
        "difficulty": "med",
        "sub_class": "no_eta_in_friendly_wrapping",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "alma.cordero@northstar.example",
            "subject": "Refund timeline for damaged order #20030",
            "body": (
                "Hi, my order #20030 arrived damaged last week. I was told a $200 refund "
                "would be processed. When will I see it on my card?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Order #20030 refund",
            "body": (
                "Hi, thanks for following up about order #20030. We've initiated the "
                "$200 refund for the damaged item and our finance team is processing it. "
                "We appreciate your patience and value your business. Best, Refunds Team."
            ),
        },
        "criterion_failures": ["C2"],
        "rationale_hint": (
            "C2 fails: response confirms the refund was initiated but gives no ETA on "
            "when the customer will actually see it on their card — which is the question "
            "the customer asked. C1, C3, C4, C5 pass."
        ),
    },
    {
        "id": "e-med-2",
        "difficulty": "med",
        "sub_class": "scope_creep_plus_vague",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "i.tran@quasar.example",
            "subject": "Help enabling SSO for our team",
            "body": (
                "Hi, we'd like to enable single sign-on for our team. Could you point us "
                "at the right setup guide?"
            ),
        },
        "candidate_response": {
            "subject": "Re: SSO setup",
            "body": (
                "Hi, thanks for asking about SSO. We're rolling out a major SSO upgrade "
                "later this year that will fully automate setup with one click — keep an "
                "eye out for that. For your current question, we'll have an engineer "
                "reach out in due course to walk you through the existing setup. Best, "
                "Customer Success."
            ),
        },
        "criterion_failures": ["C2", "C3"],
        "rationale_hint": (
            "Two failures: C2 ('in due course', no concrete pointer to docs or scheduled "
            "follow-up) and C3 (promises a 'major SSO upgrade later this year' as a "
            "future feature commitment, which the customer did not ask about). C1, C4, "
            "C5 pass."
        ),
    },
    {
        "id": "e-med-3",
        "difficulty": "med",
        "sub_class": "compact_compliance",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "controller@arclight.example",
            "subject": "Confirm renewal billing for April 1",
            "body": (
                "Could you confirm our renewal billing date and amount? Our records say "
                "April 1, 2026 for $24,000 but we want to double-check before the AP "
                "team locks the period."
            ),
        },
        "candidate_response": {
            "subject": "Re: Renewal billing confirmation",
            "body": (
                "Confirmed: your account will be charged $24,000 on April 1, 2026 per "
                "the contract you signed in January 2026. The amount and date match our "
                "records and your purchase order. If anything looks off before April 1, "
                "reply here and we'll review again. Best, Billing Team."
            ),
        },
        "criterion_failures": [],
        "rationale_hint": (
            "All 5 criteria pass even though the response is short: it confirms the "
            "specific date and amount (C1, C2), stays within scope (C3), is "
            "professional (C4), and implicitly references the existing arrangement (C5). "
            "Tests whether the judge over-classifies on length rather than rubric "
            "content."
        ),
    },
    {
        "id": "e-med-4",
        "difficulty": "med",
        "sub_class": "dismissive_plus_scope_creep",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "ana.morales@beacon.example",
            "subject": "Payment failed at checkout",
            "body": (
                "Hi, I tried to purchase the team plan today and the payment didn't go "
                "through — I just see a 'something went wrong' message. Could you help "
                "me complete the order?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Payment failed at checkout",
            "body": (
                "Hi, payment issues happen sometimes — just retry the checkout. We've "
                "heard from a few customers about payment problems lately and we're "
                "rebuilding the checkout flow which should fix it for everyone "
                "eventually. Cheers, Support."
            ),
        },
        "criterion_failures": ["C1", "C2", "C3"],
        "rationale_hint": (
            "Three failures: C1 ('payment issues happen sometimes' deflects from the "
            "specific case), C2 ('just retry' offers no diagnostic next step or ETA "
            "from the support side, and 'eventually' carries no ETA), C3 ('rebuilding "
            "the checkout flow' is a future-feature commitment the customer did not ask "
            "about). C4 and C5 pass (no inquiry case ID, tone is informal but not "
            "condescending)."
        ),
    },
    {
        "id": "e-med-5",
        "difficulty": "med",
        "sub_class": "stacked_subtle_fails",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "i.zubieta@aldebaran.example",
            "subject": "Case #103 — migration stuck for 2 weeks",
            "body": (
                "Hi, we started the data migration 2 weeks ago and it's still showing "
                "as 'in progress'. Our cutover deadline is Friday. Could someone please "
                "look at case #103 and unblock it?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #130",
            "body": (
                "Hi, thanks for your patience on case #130. Migrations can take a while "
                "depending on data volume — typically a few weeks. We're investigating "
                "and will get back to you. In the meantime, we're building a new "
                "migration dashboard that will give you better visibility into progress. "
                "Best, Migration Team."
            ),
        },
        "criterion_failures": ["C1", "C2", "C3", "C5"],
        "rationale_hint": (
            "Four failures: C1 ('migrations take a while' generic, ignores the 2-week "
            "stuck status and Friday deadline), C2 ('will get back to you' no ETA), "
            "C3 ('new migration dashboard' future feature commitment), C5 (cites case "
            "#130 vs the customer's case #103). C4 passes."
        ),
    },
    # ── HIGH: boundary cases at the failure-count cutoffs ──
    {
        "id": "e-high-1",
        "difficulty": "high",
        "sub_class": "boundary_pass_eta_window",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "casey.lin@waypoint.example",
            "subject": "Case #200 — chat sometimes drops messages",
            "body": (
                "Hi, our team has noticed that the in-app chat occasionally drops "
                "messages — they show as sent but the recipient never receives them. "
                "Case #200."
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #200 — chat drops",
            "body": (
                "Hi, thanks for the report on case #200. We're aware of intermittent "
                "message-dropping in the in-app chat and a fix is currently in QA — "
                "expected to be in production within the next 2 to 3 weeks. As a "
                "temporary workaround, you can use email for time-sensitive messages "
                "until the fix ships. I'll follow up on case #200 once the fix is live. "
                "Best, Support."
            ),
        },
        "criterion_failures": [],
        "rationale_hint": (
            "All 5 criteria pass. The boundary aspect: C2's '2 to 3 weeks' is a window "
            "rather than a fixed date, and C3 references a fix that is already in QA — "
            "this is acknowledging an in-flight effort, not promising a new feature. "
            "Tests whether the judge applies C2's window-ETA convention correctly and "
            "distinguishes in-flight from new commitments under C3."
        ),
    },
    {
        "id": "e-high-2",
        "difficulty": "high",
        "sub_class": "boundary_needs_revision_two_fails",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "logistics@stratos.example",
            "subject": "Case #88 — delayed parts shipment",
            "body": (
                "Hi, our case #88 was filed Monday about the delayed parts shipment. We "
                "still haven't heard back. The parts are needed for a production line "
                "that's currently idled. Could you give us an update?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #80",
            "body": (
                "Hi, thanks for following up on case #80. We're looking into the delayed "
                "shipment with our logistics team and will get back to you shortly. We "
                "understand this is impacting your operations and appreciate your "
                "patience. Best regards, Support."
            ),
        },
        "criterion_failures": ["C2", "C5"],
        "rationale_hint": (
            "Two failures: C2 ('shortly' no ETA) and C5 (cites case #80 vs the "
            "customer's case #88). C1, C3, C4 pass. Sits exactly at the 2-fail end of "
            "the NEEDS_REVISION band — one more failure would tip into FAIL. Tests "
            "whether the judge respects the count boundary."
        ),
    },
    {
        "id": "e-high-3",
        "difficulty": "high",
        "sub_class": "boundary_fail_three_fails",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "platform.team@meridian.example",
            "subject": "Case #155 — Salesforce integration intermittently fails",
            "body": (
                "Hi, our Salesforce integration fails intermittently — about once an "
                "hour the sync job errors out and we have to retry manually. Case #155."
            ),
        },
        "candidate_response": {
            "subject": "Re: Integration trouble",
            "body": (
                "Look, integrations sometimes don't work and our engineering team will "
                "get to your Salesforce issue at some point. We're also considering "
                "adding a new integration adapter that should help in the future. Maybe "
                "ping us back next month if you don't hear anything."
            ),
        },
        "criterion_failures": ["C1", "C2", "C3"],
        "rationale_hint": (
            "Three failures push this to FAIL: C1 ('integrations sometimes don't work' "
            "is generic and dismissive of the specific case), C2 ('at some point' / "
            "'next month if you don't hear' no ETA), C3 ('considering adding a new "
            "integration adapter' future feature). C4 and C5 are borderline but pass — "
            "no reference is required when the response omits one entirely (rubric C5 "
            "fails only on wrong or invented references)."
        ),
    },
    {
        "id": "e-high-4",
        "difficulty": "high",
        "sub_class": "soft_scope_creep_at_renewal",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "ops@parkwest.example",
            "subject": "Case #401 — renewal terms confirmation",
            "body": (
                "Hi, our contract renews soon. Could you confirm the renewal date and "
                "the amount? Case #401."
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #401 — renewal",
            "body": (
                "Hi, thanks for reaching out on case #401. Your current contract expires "
                "on December 31, 2026 and your renewal is processed automatically. The "
                "renewed annual fee will be $36,000, debited on January 1, 2027. We're "
                "also rolling out a new premium tier mid-2027 — if you'd like to upgrade "
                "by then, you'd get our new analytics suite free for the first year. "
                "You'll receive a renewal confirmation 30 days before the renewal date. "
                "Best, Account Services."
            ),
        },
        "criterion_failures": ["C3"],
        "rationale_hint": (
            "One failure: C3 ('new premium tier mid-2027' plus 'free analytics suite "
            "for the first year' is a future-feature commitment + financial concession "
            "the customer did not ask about). C1, C2, C4, C5 all pass. Tests whether "
            "the judge catches a soft upsell commitment buried inside an otherwise "
            "professional and accurate renewal confirmation."
        ),
    },
    {
        "id": "e-high-5",
        "difficulty": "high",
        "sub_class": "looks_critical_actually_pass",
        "instruction": "Apply the rubric to the candidate response and return the verdict.",
        "inquiry": {
            "sender": "kira.evans@spinnaker.example",
            "subject": "Case #500 — bug AND poor previous experience",
            "body": (
                "Hi, two things on case #500: (1) the dashboard widget bug is still "
                "happening — when I add more than 5 KPIs the page freezes, and (2) the "
                "last support agent we worked with on this just kept asking us to "
                "reproduce instead of actually looking. Could someone competent please "
                "look at the bug?"
            ),
        },
        "candidate_response": {
            "subject": "Re: Case #500",
            "body": (
                "Hi, thanks for the detailed report on case #500. Here's where we are: "
                "(1) On the bug — case #500 has been escalated to engineering this "
                "morning. They've reproduced the freeze locally with 6+ KPIs and "
                "expect a fix in production by March 20, 2026. (2) On the previous "
                "support experience — I'm sorry that happened; I'll personally own this "
                "case going forward and you can reach me at this address directly. "
                "Best, M. Devereaux, Support."
            ),
        },
        "criterion_failures": [],
        "rationale_hint": (
            "All 5 criteria pass: addresses both the bug and the experience complaint "
            "(C1), gives a concrete repro confirmation plus a date (C2), no out-of-"
            "scope commitments — taking personal ownership of an open case is within "
            "support's normal scope (C3), professional and empathetic without "
            "exaggeration (C4), references case #500 correctly (C5). Tests whether the "
            "judge over-classifies a response to a complaint-heavy inquiry as "
            "NEEDS_REVISION on emotional weight rather than rubric content."
        ),
    },
]


def main() -> None:
    written = 0
    for inst in INSTANCES:
        # Set the gold label deterministically from the per-instance
        # criterion_failures list. This keeps the data file editable in one
        # place — change the failure list and the gold updates with it,
        # eliminating drift between the failure list and the expected_label.
        inst["expected_label"] = _verdict_from_failures(inst["criterion_failures"])
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "E",
            "difficulty": inst["difficulty"],
            "sub_class": inst.get("sub_class"),
            "instruction": inst["instruction"],
            "inquiry": inst["inquiry"],
            "candidate_response": inst["candidate_response"],
            "criterion_failures": inst["criterion_failures"],
            "expected_label": inst["expected_label"],
            "rationale_hint": inst["rationale_hint"],
            "provenance": _provenance(inst.get("sub_class")),
        }
        (directory / f"{inst['id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False)
        )
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
