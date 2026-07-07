"""Coherent named-customer dataset for the archetype-B retrieval redesign (v3).

Adds a small set of realistically named customers with COHERENT facts spread
across CRM, Mail (used as the conversation / colleague-note log), and Calendar,
so the v3 tasks can be natural-language information-retrieval questions about a
named customer rather than schema-leaking aggregation prompts.

Additive and idempotent: rows live at high id ranges (accounts/contacts/opps at
id >= 101, emails/events at id >= 2001) and are appended to the seed JSON; the
existing generic data (used by the other archetypes) is untouched. Re-running
drops the prior high-id rows first.

Run:
    python experiments/seed_b_retrieval.py
    python experiments/load_db.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "data" / "schema" / "seed"
ACC_BASE, EMAIL_BASE = 101, 2001  # high id ranges for the coherent customers

# ── Coherent customers. Each carries cross-source facts referenced by the tasks. ──
# account: (id, name, region, industry, type)
# contacts: [(id, name, email)]
# opps: [(id, name, amount, stage, created_at, close_date, is_won, owner_agent_id)]
# emails: [(id, sender, recipient, subject, body, sent_at)]   (the conversation/colleague log)
# events: [(id, name, attendees, start_time, end_time)]

CUSTOMERS = [
    {
        "account": (101, "Mayer & Co", "EMEA", "Manufacturing", "Key Account"),
        "contacts": [(101, "Anna Brandt", "anna.brandt@mayer.example")],
        "opps": [
            (101, "Mayer Renewal 2025", 120000, "Closed Won", "2025-03-04", "2025-08-20", True, 1),
            (102, "Mayer Expansion", 80000, "Proposal", "2025-09-02", "2025-12-01", False, 1),
        ],
        "emails": [
            (2001, "anna.brandt@mayer.example", "agent01@atlas.com", "Re: Expansion proposal",
             "Thanks for the proposal, we are reviewing it internally.", "2025-09-12 09:30:00"),
            (2002, "agent03@atlas.com", "agent01@atlas.com", "Mayer & Co - assessment",
             "Heads-up: Mayer is very price-sensitive; the renewal was hard-fought on price.", "2025-09-05 14:00:00"),
        ],
        "events": [
            (2001, "Renewal call Mayer & Co", "agent01@atlas.com,anna.brandt@mayer.example",
             "2025-10-03 10:00:00", "2025-10-03 10:30:00"),
        ],
    },
    {
        "account": (102, "Brueckner Logistics", "EMEA", "Logistics", "Key Account"),
        "contacts": [(102, "Tom Keller", "tom.keller@brueckner.example")],
        "opps": [
            (103, "Brueckner Fleet Deal", 45000, "Closed Won", "2025-02-10", "2025-05-15", True, 2),
        ],
        "emails": [
            (2003, "tom.keller@brueckner.example", "agent02@atlas.com", "Delivery delay",
             "We had a delivery delay last week, please get back to us.", "2025-07-21 11:15:00"),
        ],
        "events": [
            (2002, "Quarterly review Brueckner", "agent02@atlas.com,tom.keller@brueckner.example",
             "2025-09-18 13:00:00", "2025-09-18 14:00:00"),
        ],
    },
    {
        "account": (103, "Sunrise Retail", "AMER", "Retail", "Key Account"),
        "contacts": [(103, "Maria Lopez", "maria.lopez@sunrise.example")],
        "opps": [
            (104, "Sunrise POS Rollout", 95000, "Closed Won", "2025-01-20", "2025-04-30", True, 3),
            (105, "Sunrise Loyalty Add-on", 30000, "Closed Won", "2025-05-02", "2025-07-10", True, 3),
            (106, "Sunrise Analytics", 60000, "Negotiation", "2025-08-15", "2025-11-30", False, 3),
        ],
        "emails": [
            (2004, "maria.lopez@sunrise.example", "agent03@atlas.com", "Re: Analytics proposal",
             "Looks good, we still need sign-off from the board.", "2025-09-25 16:40:00"),
        ],
        "events": [
            (2003, "Analytics demo Sunrise", "agent03@atlas.com,maria.lopez@sunrise.example",
             "2025-10-10 15:00:00", "2025-10-10 16:00:00"),
        ],
    },
    {
        "account": (104, "Helvetia Finance", "EMEA", "Finance", "Key Account"),
        "contacts": [(104, "Lukas Frei", "lukas.frei@helvetia.example")],
        "opps": [
            (107, "Helvetia Compliance Suite", 150000, "Proposal", "2025-09-10", "2025-12-20", False, 4),
        ],
        "emails": [
            (2005, "agent04@atlas.com", "agent01@atlas.com", "Helvetia - risk note",
             "Caution: Helvetia has a long compliance approval; close no earlier than Q1.", "2025-09-15 08:50:00"),
        ],
        "events": [],
    },
    {
        "account": (105, "Pacific HealthTech", "APAC", "Healthcare", "Key Account"),
        "contacts": [(105, "Hiro Tanaka", "hiro.tanaka@pacificht.example")],
        "opps": [
            (108, "Pacific Pilot", 25000, "Closed Won", "2025-03-30", "2025-06-12", True, 5),
        ],
        "emails": [
            (2006, "hiro.tanaka@pacificht.example", "agent05@atlas.com", "Pilot feedback",
             "The pilot is going well, we are considering an expansion.", "2025-08-08 10:05:00"),
        ],
        "events": [
            (2004, "Pilot review Pacific", "agent05@atlas.com,hiro.tanaka@pacificht.example",
             "2025-09-05 09:00:00", "2025-09-05 09:45:00"),
        ],
    },
]


def build_rows():
    accounts, contacts, opps, emails, events = [], [], [], [], []
    for c in CUSTOMERS:
        aid, name, region, industry, atype = c["account"]
        accounts.append({"id": aid, "name": name, "region": region, "industry": industry, "type": atype})
        for cid, cname, cemail in c["contacts"]:
            contacts.append({"id": cid, "account_id": aid, "name": cname, "email": cemail})
        for oid, oname, amt, stage, created, close, won, owner in c["opps"]:
            opps.append({"id": oid, "account_id": aid, "owner_agent_id": owner, "name": oname,
                         "amount": amt, "stage": stage, "created_at": created,
                         "close_date": close, "is_won": won})
        for eid, snd, rcv, subj, body, ts in c["emails"]:
            emails.append({"id": eid, "sender": snd, "recipient": rcv, "subject": subj,
                           "body": body, "sent_at": ts, "status": "inbox"})
        for vid, vname, att, start, end in c["events"]:
            events.append({"id": vid, "name": vname, "organizer_email": att.split(",")[0],
                           "attendees": att, "start_time": start, "end_time": end, "status": "confirmed"})
    return accounts, contacts, opps, emails, events


def _merge(fname: str, new_rows: list[dict], base_floor: int) -> None:
    path = SEED / f"{fname}.json"
    base = json.loads(path.read_text()) if path.exists() else []
    base = [r for r in base if r.get("id", 0) < base_floor]
    path.write_text(json.dumps(base + new_rows, indent=2))
    print(f"seed {fname}.json: {len(base)} kept (< {base_floor}) + {len(new_rows)} coherent-customer rows")


def main() -> None:
    accounts, contacts, opps, emails, events = build_rows()
    _merge("accounts", accounts, ACC_BASE)
    _merge("contacts", contacts, ACC_BASE)
    _merge("opportunities", opps, ACC_BASE)
    # emails/events keep the IT-033 signal rows (1001..) AND append the coherent log (2001..)
    for fname, rows in (("emails", emails), ("events", events)):
        path = SEED / f"{fname}.json"
        base = json.loads(path.read_text()) if path.exists() else []
        base = [r for r in base if r.get("id", 0) < EMAIL_BASE]
        path.write_text(json.dumps(base + rows, indent=2))
        print(f"seed {fname}.json: {len(base)} kept (< {EMAIL_BASE}) + {len(rows)} coherent-customer rows")
    print(f"\nAdded {len(accounts)} customers, {len(opps)} opportunities, {len(emails)} emails, {len(events)} events.")


if __name__ == "__main__":
    main()
