"""Curated batch-triage instances for archetype C: Support-Ticket Routing.

Writes 15 batch instances under ``data/test_inputs/c_ambiguous_classification/``
(5 per difficulty). Each instance is ONE triage task: a batch of customer
emails plus the (external) category document, producing ONE output list of
per-email labels (Section 2.2.3, a single task).

Difficulty scales on batch size AND per-email ambiguity:
- Low: 3 emails, each a clear single-signal case. Workflow -> 1 chunk.
- Med: 5 emails, each with genuinely competing category signals where one
  primary intent (the resolution the requester wants) decides. Workflow -> 1
  chunk (CHUNK_SIZE = 5), so no chunking overhead here.
- High: 8 emails, verbose and noisy with near-duplicate signals and a buried
  core ask; the larger, heavier context is meant to load a single call.
  Workflow -> 2 chunks (5 + 3), where the deterministic map-reduce keeps each
  call's context bounded against the agent's single-context handling.

Emails are composed from a labelled pool; the gold ``expected`` maps each
email id to its category. The primary-intent disambiguation rule (route to the
resolution the requester wants, not to keywords that merely appear) is what
makes the Med/High golds determinate despite the competing signals.

Run:
    python experiments/seed_classification.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "c_ambiguous_classification"

BENCHMARK = "CRMArena-Pro Case Routing / Activity Priority Understanding (Huang et al., 2025)"

# CLEAR (Low): one unambiguous signal.
CLEAR = [
    ("Billing", "Invoice question", "The September invoice total looks off. Could someone double-check the charges and tell me what's going on?"),
    ("Technical", "App keeps crashing", "Since this morning the dashboard crashes with a 500 error whenever I open the reports page. Please fix it."),
    ("Shipping", "Where is my package", "My order shipped five days ago but the tracking hasn't moved. Can you tell me where the package is?"),
    ("Account", "Add a seat", "Please add my new colleague Sara to our team account with editor permissions."),
    ("Product", "How do I export", "Is there a way to export a report to CSV? I couldn't find it in the docs."),
    ("Billing", "Refund not received", "You confirmed a refund two weeks ago but it still hasn't hit our card. Where is it?"),
]

# MIXED (Med, and part of High): competing signals, one subtle primary intent.
MIXED = [
    ("Account", "Access after role change", "Since you changed my role I can't see the billing section anymore. Pages load fine for my colleagues, so nothing is down — I just need my permissions put back so I can reach billing."),
    ("Billing", "Still charged for removed seats", "We removed three seats last month and the app reflects it correctly. The problem is only this invoice: it still bills the old seat count. Please correct the charge."),
    ("Technical", "Export: broken or intended?", "When we export a large report to CSV it fails every time with an error. Is that expected behaviour, or is it broken? For us it never completes — it just errors out."),
    ("Shipping", "Wrong SKU sent", "You shipped the wrong unit. I'd like the correct one sent out; once it arrives we can reconcile the price difference, but the priority is getting the right item delivered."),
    ("Product", "Totals look wrong", "Our weekly totals look wrong, so at first we thought it was a bug. After checking, the numbers are actually correct — we just don't understand how your 'week' is defined. Can you explain how the weekly rollup works?"),
    ("Account", "Contractor can't get in", "Our new contractor says the portal 'doesn't work'. But it loads fine for the rest of us, so it isn't an outage — they were simply never granted access. Please give them viewer access to the Atlas project."),
    ("Billing", "Double charge among praise", "Love the product and the team's been responsive. Minor: a docs gap on webhooks, for later. The thing I need now: our last invoice has two identical line items — we were double-charged and need one refunded."),
    ("Technical", "Sync failing, not the address", "Thanks for fixing our delivery address last week. Unrelated: finance had a charge question we've already resolved. The live problem: our nightly data sync via your API has failed with timeouts for three days and the reports are stale — please investigate."),
]

# HARD (High): verbose, near-duplicate signals, buried core ask.
HARD = [
    ("Billing", "Quarter recap, one real ask", "Hope you're well — busy quarter here. The team loved the new dashboard, though the export button took a while to find, and our admin had to re-add two seats after someone left (all sorted now). The reason I'm actually writing: our renewal invoice shows a mid-term price increase we never agreed to. Everything else is fine; we just need the pricing on that invoice explained and corrected."),
    ("Technical", "Several threads, one urgent", "A few things piled up this week. The hardware add-on shipped late (already resolved with the carrier). Someone also asked whether PDF export is supported — no rush on that. The urgent part: since Tuesday's release the login page throws an error for every one of our users, so nobody can get in. It's clearly on your side — please treat the outage as priority one."),
    ("Account", "Reorg with money and product noise", "We're splitting into two regional teams. I know that means new invoices for the split, and the new hires will probably want a product walkthrough at some point. But right now what I actually need is operational: move eight users from the EMEA org into a new APAC org and set their manager. It's purely an account-structure change."),
    ("Shipping", "Long complaint, real blocker", "Honestly a bit frustrated. Support was slow last week, the app logged me out twice (I got back in fine), and I still don't fully understand the new line on our bill. But the thing that's blocking us right now: the replacement device you promised for Monday still hasn't arrived — it's Thursday and there's no tracking update. Where is the shipment?"),
    ("Product", "Reads like a bug, is a how-to", "Our analysts flagged the reporting as 'broken' because the numbers 'don't add up'. I dug in: it's not a defect, the figures are correct. What we actually need is to understand how your rollups define a reporting week and when data is cut off — point us to the docs or explain the behaviour. No fix required."),
    ("Billing", "Praise, wishlist, buried refund", "Genuinely one of the better tools we use, and your team's been great. Two small things for later: the webhook docs are thin, and it'd be nice if the mobile app remembered my filters. The one thing I need handled now: we were charged twice for the same subscription on the latest invoice and need one of the duplicate charges refunded."),
    ("Account", "Access request dressed as an outage", "The project portal 'doesn't work' for our new contractor and it's holding up onboarding. To be precise, the pages load fine for everyone else on the team, so this isn't a service outage — the contractor was just never added. Please grant them viewer permissions on the Atlas project workspace."),
    ("Technical", "Delivery and billing noise, API is the issue", "Thanks again for sorting our delivery address the other week, and the charge question from finance is resolved on our end. The live problem I need eyes on: our nightly data synchronisation through your API has been failing with timeouts for three straight nights, so all of our dashboards are now showing stale figures. Please investigate the API failures."),
]


def _emails(pool_slice):
    emails, expected = [], {}
    for i, (label, subj, body) in enumerate(pool_slice, start=1):
        eid = f"e{i}"
        emails.append({"id": eid, "sender": f"user{i}@customer.example", "subject": subj, "body": body})
        expected[eid] = label
    return emails, expected


def _rot(pool, start, n):
    return [pool[(start + j) % len(pool)] for j in range(n)]


def build():
    out = []
    for k in range(5):
        low = _rot(CLEAR, k * 3, 3)                          # 3 clear -> 1 chunk
        med = _rot(MIXED, k * 5, 5)                           # 5 ambiguous -> 1 chunk
        high = _rot(MIXED, k * 3 + 2, 3) + _rot(HARD, k * 5, 5)  # 8 verbose/ambiguous -> 2 chunks
        for diff, pool_slice in (("low", low), ("med", med), ("high", high)):
            emails, expected = _emails(pool_slice)
            out.append({
                "id": f"c-{diff}-{k + 1}",
                "archetype": "C",
                "difficulty": diff,
                "instruction": "Triage this batch of customer support emails: assign each email to exactly one support category by its primary intent.",
                "emails": emails,
                "expected": expected,
                "provenance": {
                    "source_benchmark": BENCHMARK,
                    "construction_method": (
                        "Batch-triage task (single input batch -> single labelled output, Section 2.2.3). "
                        "Difficulty = batch size (3/5/8) x per-email ambiguity; Med/High emails carry competing "
                        "near-duplicate signals with one primary intent; High emails are verbose with a buried "
                        "core ask to load the context. Author-constructed from a labelled pool; no benchmark text reproduced."
                    ),
                    "license": "Original work by the author (email texts and task design); benchmark semantics reference only",
                },
            })
    return out


def main() -> None:
    written = 0
    for inst in build():
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{inst['id']}.json").write_text(json.dumps(inst, indent=2, ensure_ascii=False))
        written += 1
    print(f"Wrote {written} batch instances under {INPUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
