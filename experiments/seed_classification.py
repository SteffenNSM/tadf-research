"""Curated classification instances for archetype C: Support-Ticket Routing.

Writes 15 instance JSON files under ``data/test_inputs/c_ambiguous_classification/``
at three difficulty levels (5 each). Each instance contains:
    id, archetype, difficulty, sub_class, instruction, email, expected_label,
    rationale_hint, provenance

The email texts are author-constructed and stored inline in the instance
JSON. They are NOT inserted into the shared CRM mailbox, so they cannot
interact with archetype F's mail-state predicates. Both the workflow and the
agent receive the same email JSON in the prompt; the agent additionally has
``db_read`` / ``db_search`` exposed (per the Phase-2 tool-symmetry invariant)
but should not need them — every instance is designed to be solvable from
the email text alone.

Difficulty axis (Section 4.4 of the protocol, Table A.1 row C, updated under
deviation D-010):
    Low    — a single clear signal cluster; the email's primary intent
             maps unambiguously to one category.
    Medium — two signal clusters, one dominant; a side mention or a
             contextual reference touches a second category, but the
             requester's primary action ask falls in exactly one.
    High   — near-duplicate categories within the label set, vague or
             paraphrase-only language without obvious keywords, or a buried
             core ask under a dominant side topic. These are the analogues
             of CRMArena-Pro Named Entity Disambiguation, applied to
             categories rather than named entities.

The gold label for every instance — including the High ones — is
determinate under the CATEGORY_DEFINITIONS in config.py: exactly one
category captures the requester's primary intent. The rationale_hint field
documents the per-instance disambiguation reasoning for reviewer
transparency (analogous to archetype A's gold-rationale documentation).

Source: CRMArena-Pro Case Routing / Activity Priority Understanding (Huang
et al., 2025) — task semantics. The five-category label set mirrors
``cases.issue_category`` from ``experiments/seed_crm.py``. Email texts are
author-constructed.

Run:
    python experiments/seed_classification.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "c_ambiguous_classification"

CRMARENA = "CRMArena-Pro Case Routing / Activity Priority Understanding (Huang et al., 2025)"


def _provenance(sub_class: str | None) -> dict:
    note = (
        "Author-constructed email texts; task semantics follow the CRMArena-Pro "
        "routing/disambiguation pattern. The five-category label set is mirrored "
        "from cases.issue_category in experiments/seed_crm.py so the routing "
        "decision is consistent with the local CRM schema."
    )
    if sub_class:
        note += f" High-stratum sub-class: {sub_class}."
    return {
        "source_benchmark": CRMARENA,
        "adaptation": note,
        # IT-017 honesty rule: the email texts are original author work, not
        # lifted benchmark material; only the task semantics follow the source.
        "license": "Original work by the author (email texts and task design); benchmark semantics reference only",
    }


INSTANCES: list[dict] = [
    # ── LOW: a single clear signal cluster ──
    {
        "id": "c-low-1",
        "difficulty": "low",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "marco.weber@northwind.example",
            "subject": "Invoice question — September",
            "body": (
                "Hi support team, I just received the invoice for September and the total looks off. "
                "Could someone double-check the charges and let me know what's going on? Thanks, Marco."
            ),
        },
        "expected_label": "Billing",
        "rationale_hint": (
            "Single-cluster signal: the requester is asking for a review of an invoice amount, which "
            "is the textbook Billing case."
        ),
    },
    {
        "id": "c-low-2",
        "difficulty": "low",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "lia.chen@bluespruce.example",
            "subject": "Reporting module crashes on open",
            "body": (
                "The reporting module crashes every single time I try to open it. Started this morning around 9 AM. "
                "Browser console shows a 500 error. Could you look into it?"
            ),
        },
        "expected_label": "Technical",
        "rationale_hint": (
            "Single-cluster signal: the requester is reporting a defect (crash + 500 error) and "
            "expecting it to be fixed."
        ),
    },
    {
        "id": "c-low-3",
        "difficulty": "low",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "ops@ridgeway-partners.example",
            "subject": "Tracking stuck since Monday — order #45821",
            "body": (
                "Hi, order #45821 has been showing 'in transit' since Monday and the tracking number hasn't "
                "updated since. Could you check with the carrier? We need it on site by Friday."
            ),
        },
        "expected_label": "Shipping",
        "rationale_hint": (
            "Single-cluster signal: the requester wants information on a physical delivery and asks for "
            "carrier follow-up."
        ),
    },
    {
        "id": "c-low-4",
        "difficulty": "low",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "j.farrell@halberd.example",
            "subject": "Promote teammate to admin",
            "body": (
                "Could you change Sarah Klein (sarah.k@halberd.example) to an admin role? She's currently a "
                "viewer but needs admin access to manage our new project workspace."
            ),
        },
        "expected_label": "Account",
        "rationale_hint": (
            "Single-cluster signal: the requester is asking for a role change on a teammate, which is an "
            "account-level structural change."
        ),
    },
    {
        "id": "c-low-5",
        "difficulty": "low",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "kavi.patel@meridian.example",
            "subject": "Scheduling reports?",
            "body": (
                "Quick question — is there a way to schedule reports to be emailed out on a recurring basis? "
                "I looked through the docs but couldn't find anything on it."
            ),
        },
        "expected_label": "Product",
        "rationale_hint": (
            "Single-cluster signal: a how-to question about whether a product feature exists, with a docs "
            "gap acknowledgement."
        ),
    },
    # ── MEDIUM: two signal clusters, one dominant ──
    {
        "id": "c-med-1",
        "difficulty": "med",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "remy.ohara@thalia-co.example",
            "subject": "Error downloading invoice",
            "body": (
                "I keep hitting a 500 error every time I try to download my latest invoice from the Billing tab. "
                "Worked fine last week. Could you look at the page?"
            ),
        },
        "expected_label": "Technical",
        "rationale_hint": (
            "Side signal: 'invoice' and 'Billing tab' (Billing surface). Dominant signal: the user is "
            "reporting a 500 error on a page that previously worked — defect report → Technical. The "
            "billing context describes where the bug appears, not what the user wants resolved."
        ),
    },
    {
        "id": "c-med-2",
        "difficulty": "med",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "ops-team@northwind.example",
            "subject": "Onboarding 3 more users",
            "body": (
                "We're adding three more team members to our plan. Their emails are listed below. Please assign "
                "them to the Analytics group with the same role Sarah K. got last week. We ran into a few "
                "permission issues during Sarah's onboarding so please make sure access is set correctly from "
                "the start.\n\nnew.starter1@northwind.example\nnew.starter2@northwind.example\n"
                "new.starter3@northwind.example"
            ),
        },
        "expected_label": "Account",
        "rationale_hint": (
            "Side signal: 'permission issues' during a previous onboarding (Technical-adjacent). Dominant "
            "signal: the requester is asking for three new seats to be added with role assignment — an "
            "account-level operational change. The mention of past issues is context, not the ask."
        ),
    },
    {
        "id": "c-med-3",
        "difficulty": "med",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "denise.k@harborstone.example",
            "subject": "Bulk export panel — where is it?",
            "body": (
                "I'm trying to find the bulk export feature — the docs reference a 'bulk operations' panel "
                "under Settings, but I don't see it in our admin view. Is this a permissions thing or did "
                "the feature move?"
            ),
        },
        "expected_label": "Product",
        "rationale_hint": (
            "Side signal: 'permissions thing' (Account-adjacent). Dominant signal: a how-to / 'where is "
            "this feature' question. The user is asking about product behaviour, not requesting an "
            "account change."
        ),
    },
    {
        "id": "c-med-4",
        "difficulty": "med",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "cfo@arclight.example",
            "subject": "Renewal invoice — amount mismatch",
            "body": (
                "Quick follow-up on our renewal. The new contract total shows our enterprise discount "
                "applied as 10%, but the signed proposal had it at 15%. Could the team re-check the invoice "
                "math and send a corrected version?"
            ),
        },
        "expected_label": "Billing",
        "rationale_hint": (
            "Side signal: 'renewal' and 'contract' (Account/contract-adjacent surface). Dominant signal: "
            "the requester is asking for an invoice correction tied to a specific discount calculation — "
            "the ask is about money on an invoice → Billing."
        ),
    },
    {
        "id": "c-med-5",
        "difficulty": "med",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "warehouse@coastline-supply.example",
            "subject": "Order #52481 — delivered but not received",
            "body": (
                "Our last three orders showed up fine, but order #52481 is showing 'delivered' on the "
                "tracking page and we never received it. Could you check with the carrier and reissue if "
                "needed? Happy to cover any reshipping fees."
            ),
        },
        "expected_label": "Shipping",
        "rationale_hint": (
            "Side signal: 'happy to cover any reshipping fees' (Billing-adjacent). Dominant signal: a "
            "delivery discrepancy plus a request to chase the carrier and reissue — the ask is about "
            "tracking down the missing package → Shipping."
        ),
    },
    # ── HIGH: near-duplicate categories, buried core ask, or paraphrase without keywords ──
    {
        "id": "c-high-1",
        "difficulty": "high",
        "sub_class": "near_duplicate",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "h.bryant@summitline.example",
            "subject": "Friday's seat addition — invoice rate",
            "body": (
                "Last Friday I added 15 new analytics seats through your admin portal. The portal showed the "
                "new tier price, I confirmed, and the seats were activated immediately. Today the invoice "
                "arrived and it's billed at the old per-seat rate, not the tiered enterprise rate we agreed "
                "in last quarter's QBR. Could you adjust the invoice to match the agreed pricing?"
            ),
        },
        "expected_label": "Billing",
        "rationale_hint": (
            "Near-duplicate distractor: heavy Account surface ('added 15 seats', 'admin portal'). The "
            "requester is NOT asking for a seat-addition change — that already happened correctly. The "
            "primary ask is 'adjust the invoice' to reflect agreed pricing → Billing."
        ),
    },
    {
        "id": "c-high-2",
        "difficulty": "high",
        "sub_class": "buried_under_compliment",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "ananya@beacon-partners.example",
            "subject": "Loving the new dashboard — one quick thing",
            "body": (
                "Big fan of the new dashboard layout — feels way cleaner than before. Quick thing though: "
                "every time I try to export the Q3 numbers to CSV, the download starts and I end up with "
                "a 0-byte file. Worked fine before the rollout. Could one of the engineers take a look?"
            ),
        },
        "expected_label": "Technical",
        "rationale_hint": (
            "Buried-core distractor: opens with strong product praise that looks like Product feedback. "
            "The actual ask is at the bottom — a defect report on the CSV export feature, with a "
            "regression marker ('worked fine before the rollout'). The product compliment is social "
            "framing; the request is to fix a bug → Technical."
        ),
    },
    {
        "id": "c-high-3",
        "difficulty": "high",
        "sub_class": "paraphrase_no_keywords",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "d.morley@parkwest.example",
            "subject": "We've grown — need to extend our setup",
            "body": (
                "We've grown a lot this quarter and the original setup from when we onboarded a year ago "
                "doesn't quite fit anymore. I'd like to bring our European office team into the account "
                "and make sure the regional split shows up properly in our views. Who do I talk to about "
                "extending what we have?"
            ),
        },
        "expected_label": "Account",
        "rationale_hint": (
            "Paraphrase without keywords: no occurrence of 'users', 'seats', 'permissions', 'roles', or "
            "'team members'. The requester is describing organic growth and asking to bring an additional "
            "team into the account with structural changes (regional split). That is an account-level "
            "expansion → Account."
        ),
    },
    {
        "id": "c-high-4",
        "difficulty": "high",
        "sub_class": "near_duplicate",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "yusuf.mehta@quasar-labs.example",
            "subject": "Group-level alert rules?",
            "body": (
                "Trying to set up alerts for the regional managers as a group. I see the 'Notifications' panel "
                "under each individual profile, but I want one rule applied across the whole regional cohort. "
                "Is that supported, or do I have to configure each person separately?"
            ),
        },
        "expected_label": "Product",
        "rationale_hint": (
            "Near-duplicate distractors: 'individual profiles' and 'regional cohort' read as Account; "
            "'Notifications panel' reads as Technical. The actual ask is 'is this supported, or do I "
            "have to do it the long way' — a how-to / feature-capability question → Product. The user "
            "has not been blocked by a defect and is not asking for a structural change."
        ),
    },
    {
        "id": "c-high-5",
        "difficulty": "high",
        "sub_class": "paraphrase_no_keywords",
        "instruction": "Route this email to the correct support category.",
        "email": {
            "sender": "events@beacon-partners.example",
            "subject": "Order 71034 — follow-up",
            "body": (
                "Hi! Following up on order 71034. The status update Monday said the package was 'received at "
                "the regional facility', but the next-day delivery window we paid extra for has come and "
                "gone. Hoping someone can chase this down before our launch event tomorrow morning."
            ),
        },
        "expected_label": "Shipping",
        "rationale_hint": (
            "Paraphrase without obvious keywords ('shipping', 'tracking', 'delay' don't appear). The "
            "requester paraphrases a missed next-day delivery window after a regional-facility receipt "
            "stop, and asks for someone to chase the delivery. A side mention of paid-extra shipping "
            "doesn't shift the ask to Billing — the request is to locate the package → Shipping."
        ),
    },
]


def main() -> None:
    written = 0
    for inst in INSTANCES:
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "C",
            "difficulty": inst["difficulty"],
            "sub_class": inst.get("sub_class"),
            "instruction": inst["instruction"],
            "email": inst["email"],
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
