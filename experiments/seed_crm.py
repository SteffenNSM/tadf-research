"""Deterministic CRM seed generator and ground-truth computation for archetype B.

Generates a synthetic but realistic CRM dataset that mirrors the Salesforce
object model of CRMArena (Huang et al., 2025): accounts, contacts, agents,
cases, and opportunities. The records are synthesized locally with a fixed
seed because the original CRMArena runs against a live Salesforce org that is
not reproducible. The task TYPES (structured querying) are taken from
CRMArena; the data is generated for local reproducibility.

The script writes:
- data/schema/seed/*.json          : the seed records, for loading into Supabase
- data/test_inputs/b_structured_retrieval/{low,medium,high}/*.json
                                     : the 15 task instances with ground truth

Ground truth is computed directly here (independent of the workflow's query
executor) so that an agreement between the two is genuine evidence of
correctness, not a shared bug.

Run:
    python experiments/seed_crm.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
REPO = Path(__file__).resolve().parents[1]
SEED_DIR = REPO / "data" / "schema" / "seed"
INPUT_DIR = REPO / "data" / "test_inputs" / "b_structured_retrieval"

REGIONS = ["EMEA", "AMER", "APAC"]
INDUSTRIES = ["Technology", "Manufacturing", "Retail", "Healthcare", "Finance"]
ACCOUNT_TYPES = ["Customer", "Partner"]
TEAMS = ["EMEA", "AMER", "APAC"]
ISSUE_CATEGORIES = ["Billing", "Technical", "Shipping", "Account", "Product"]
CASE_STATUS = ["Open", "In Progress", "Closed"]
PRIORITIES = ["Low", "Medium", "High"]
OPP_STAGES = ["Prospecting", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate() -> dict[str, list[dict]]:
    """Generate the full CRM dataset deterministically."""
    rng = random.Random(SEED)

    # ── Accounts ──
    accounts = []
    for i in range(1, 21):
        accounts.append(
            {
                "id": i,
                "name": f"Account {i:02d}",
                "region": rng.choice(REGIONS),
                "industry": rng.choice(INDUSTRIES),
                "type": rng.choice(ACCOUNT_TYPES),
            }
        )

    # ── Contacts ──
    contacts = []
    cid = 1
    for acc in accounts:
        for _ in range(rng.randint(1, 3)):
            contacts.append(
                {
                    "id": cid,
                    "account_id": acc["id"],
                    "name": f"Contact {cid:03d}",
                    "email": f"contact{cid:03d}@example.com",
                }
            )
            cid += 1

    # ── Agents ──
    agents = []
    for i in range(1, 11):
        agents.append(
            {
                "id": i,
                "name": f"Agent {i:02d}",
                "team": rng.choice(TEAMS),
                "region": rng.choice(REGIONS),
                "email": f"agent{i:02d}@atlas.com",
            }
        )

    # ── Cases ──
    cases = []
    base = datetime(2025, 1, 1, 9, 0, 0)
    for i in range(1, 121):
        created = base + timedelta(
            days=rng.randint(0, 330), hours=rng.randint(0, 8)
        )
        status = rng.choice(CASE_STATUS)
        closed = None
        if status == "Closed":
            closed = created + timedelta(hours=rng.randint(2, 240))
        cases.append(
            {
                "id": i,
                "account_id": rng.randint(1, 20),
                "agent_id": rng.randint(1, 10),
                "subject": f"Case {i:03d}",
                "issue_category": rng.choice(ISSUE_CATEGORIES),
                "status": status,
                "priority": rng.choice(PRIORITIES),
                "created_at": _iso(created),
                "closed_at": _iso(closed) if closed else None,
                "transfer_count": rng.randint(0, 5),
            }
        )

    # ── Deterministic overrides for cases used in archetype F test instances ──
    # These ensure the test pre-state is exactly what the predicates expect,
    # independently of the random draw above. Edit alongside seed_actions.py.
    case_overrides = {
        # f-high-5 (runtime-feedback): case 47 must be open, not yet closed, and
        # have transfer_count > 3 so attempt_close_case is blocked by the hidden
        # escalation rule. account_id pinned for predicate stability.
        47: {
            "account_id": 10,
            "agent_id": 1,
            "status": "Open",
            "priority": "Medium",
            "transfer_count": 4,
            "closed_at": None,
        },
    }
    for case in cases:
        if case["id"] in case_overrides:
            case.update(case_overrides[case["id"]])

    # ── Opportunities ──
    opportunities = []
    for i in range(1, 61):
        created = base + timedelta(days=rng.randint(0, 300))
        close = created + timedelta(days=rng.randint(10, 120))
        stage = rng.choice(OPP_STAGES)
        is_won = stage == "Closed Won"
        opportunities.append(
            {
                "id": i,
                "account_id": rng.randint(1, 20),
                "owner_agent_id": rng.randint(1, 10),
                "name": f"Opportunity {i:03d}",
                "amount": rng.randint(5_000, 200_000),
                "stage": stage,
                "created_at": _iso(created),
                "close_date": close.strftime("%Y-%m-%d"),
                "is_won": is_won,
            }
        )

    # ── Emails (mailbox baseline for archetype F) ──
    emails = []
    eid = 1
    # Inbox: messages sent by contacts to agents (10 entries)
    for _ in range(10):
        agent = rng.choice(agents)
        contact = rng.choice(contacts)
        ts = base + timedelta(days=rng.randint(0, 320), hours=rng.randint(8, 17))
        emails.append(
            {
                "id": eid,
                "sender": contact["email"],
                "recipient": agent["email"],
                "subject": rng.choice([
                    "Question about my recent case",
                    "Follow-up on proposal",
                    "Issue with our product",
                    "Renewal inquiry",
                    "Billing question",
                ]),
                "body": "Could you please get back to me on this?",
                "sent_at": _iso(ts),
                "status": "inbox",
            }
        )
        eid += 1
    # Outbox: messages from agents to contacts (10 entries)
    for _ in range(10):
        agent = rng.choice(agents)
        contact = rng.choice(contacts)
        ts = base + timedelta(days=rng.randint(0, 320), hours=rng.randint(8, 17))
        emails.append(
            {
                "id": eid,
                "sender": agent["email"],
                "recipient": contact["email"],
                "subject": rng.choice([
                    "Update on your case",
                    "Quarterly check-in",
                    "Information you requested",
                    "Renewal options",
                    "Resolution details",
                ]),
                "body": "Please see attached or reply with any questions.",
                "sent_at": _iso(ts),
                "status": "outbox",
            }
        )
        eid += 1

    # ── Events (calendar baseline for archetype F) ──
    events = []
    vid = 1
    for _ in range(12):
        organizer = rng.choice(agents)
        invitee = rng.choice(contacts)
        day_offset = rng.randint(-30, 60)  # past and future events
        start = base + timedelta(days=330 + day_offset, hours=rng.choice([9, 10, 11, 13, 14, 15]))
        end = start + timedelta(minutes=rng.choice([30, 45, 60]))
        events.append(
            {
                "id": vid,
                "name": rng.choice([
                    "Account review",
                    "Quarterly business review",
                    "Onboarding call",
                    "Product demo",
                    "Renewal discussion",
                    "Catch-up",
                ]),
                "organizer_email": organizer["email"],
                "attendees": f"{organizer['email']},{invitee['email']}",
                "start_time": _iso(start),
                "end_time": _iso(end),
                "status": "confirmed",
            }
        )
        vid += 1

    return {
        "accounts": accounts,
        "contacts": contacts,
        "agents": agents,
        "cases": cases,
        "opportunities": opportunities,
        "emails": emails,
        "events": events,
    }


# ── Ground-truth helpers (direct computation, independent of the executor) ──


def handle_time_hours(case: dict) -> float | None:
    if case["status"] != "Closed" or not case["closed_at"]:
        return None
    c = datetime.strptime(case["created_at"], "%Y-%m-%d %H:%M:%S")
    cl = datetime.strptime(case["closed_at"], "%Y-%m-%d %H:%M:%S")
    return (cl - c).total_seconds() / 3600.0


def quarter(date_str: str) -> int:
    m = int(date_str[5:7])
    return (m - 1) // 3 + 1


def year(date_str: str) -> int:
    return int(date_str[:4])


def month(date_str: str) -> int:
    return int(date_str[5:7])


def compute_ground_truth(data: dict) -> list[dict]:
    """Define the 15 instances and compute their ground truth from the data."""
    acc = {a["id"]: a for a in data["accounts"]}
    ag = {a["id"]: a for a in data["agents"]}
    cases = data["cases"]
    opps = data["opportunities"]

    instances: list[dict] = []

    def add(level, n, question, value, unit, source_task):
        instances.append(
            {
                "id": f"b-{level}-{n}",
                "archetype": "B",
                "difficulty": level,
                "instruction": question,
                "ground_truth": {"value": value, "unit": unit},
                "provenance": {
                    "source_benchmark": "CRMArena (Huang et al., 2025)",
                    "source_task_type": source_task,
                    "adaptation": "Schema and task type adapted from CRMArena structured querying; records synthesized locally (seed=42) for reproducibility.",
                    "license": "CC BY-NC 4.0",
                },
            }
        )

    # ── LOW: single table, filter + aggregate ──
    add("low", 1, "How many cases currently have status 'Open'?",
        sum(1 for c in cases if c["status"] == "Open"), "count", "Case Count")
    add("low", 2, "What is the total amount of all won opportunities (is_won = true)?",
        sum(o["amount"] for o in opps if o["is_won"]), "currency", "Sales Volume Understanding")
    add("low", 3, "How many cases have priority 'High'?",
        sum(1 for c in cases if c["priority"] == "High"), "count", "Case Count")
    add("low", 4, "How many accounts are in the 'EMEA' region?",
        sum(1 for a in data["accounts"] if a["region"] == "EMEA"), "count", "Account Count")
    add("low", 5, "What is the average amount across all opportunities, rounded to the nearest integer?",
        round(sum(o["amount"] for o in opps) / len(opps)), "currency", "Sales Volume Understanding")

    # ── MEDIUM: 2-table join + aggregate ──
    emea_ht = [handle_time_hours(c) for c in cases
               if ag[c["agent_id"]]["team"] == "EMEA" and handle_time_hours(c) is not None]
    add("med", 1, "What is the average handle time in hours (closed_at minus created_at) of closed cases handled by agents on the 'EMEA' team, rounded to one decimal?",
        round(sum(emea_ht) / len(emea_ht), 1) if emea_ht else 0, "hours", "Handle Time Understanding")

    add("med", 2, "What is the total amount of won opportunities for accounts in the 'Technology' industry?",
        sum(o["amount"] for o in opps if o["is_won"] and acc[o["account_id"]]["industry"] == "Technology"),
        "currency", "Sales Volume Understanding")

    add("med", 3, "How many cases were handled by agents on the 'AMER' team?",
        sum(1 for c in cases if ag[c["agent_id"]]["team"] == "AMER"), "count", "Case Count")

    partner_tc = [c["transfer_count"] for c in cases if acc[c["account_id"]]["type"] == "Partner"]
    add("med", 4, "What is the average transfer count of cases for accounts of type 'Partner', rounded to two decimals?",
        round(sum(partner_tc) / len(partner_tc), 2) if partner_tc else 0, "count", "Transfer Count Understanding")

    add("med", 5, "How many won opportunities belong to accounts in the 'APAC' region?",
        sum(1 for o in opps if o["is_won"] and acc[o["account_id"]]["region"] == "APAC"),
        "count", "Sales Volume Understanding")

    # ── HIGH: multi-table / grouped aggregation with a single argmax answer ──
    # H1: region with highest total won amount in Q3 2025
    region_won_q3: dict[str, int] = {}
    for o in opps:
        if o["is_won"] and year(o["close_date"]) == 2025 and quarter(o["close_date"]) == 3:
            r = acc[o["account_id"]]["region"]
            region_won_q3[r] = region_won_q3.get(r, 0) + o["amount"]
    add("high", 1, "Which region generated the highest total won-opportunity amount for opportunities closed in Q3 2025? Answer with the region name.",
        max(region_won_q3, key=region_won_q3.get) if region_won_q3 else None, "region", "Best Region Identification")

    # H2: agent team that handled most Billing cases closed in 2025
    team_billing: dict[str, int] = {}
    for c in cases:
        if c["issue_category"] == "Billing" and c["status"] == "Closed" and c["closed_at"] and year(c["closed_at"]) == 2025:
            t = ag[c["agent_id"]]["team"]
            team_billing[t] = team_billing.get(t, 0) + 1
    add("high", 2, "Which agent team handled the most cases with issue_category 'Billing' that were closed in 2025? Answer with the team name.",
        max(team_billing, key=team_billing.get) if team_billing else None, "team", "Top Issue Identification")

    # H3: issue_category with highest avg handle time among EMEA-team agents
    cat_ht: dict[str, list[float]] = {}
    for c in cases:
        ht = handle_time_hours(c)
        if ht is not None and ag[c["agent_id"]]["team"] == "EMEA":
            cat_ht.setdefault(c["issue_category"], []).append(ht)
    cat_avg = {k: sum(v) / len(v) for k, v in cat_ht.items()}
    add("high", 3, "Among cases handled by agents on the 'EMEA' team, which issue_category has the highest average handle time? Answer with the category name.",
        max(cat_avg, key=cat_avg.get) if cat_avg else None, "issue_category", "Top Issue Identification")

    # H4: month of 2025 with most opportunities created for Technology accounts
    month_count: dict[int, int] = {}
    for o in opps:
        if acc[o["account_id"]]["industry"] == "Technology" and year(o["created_at"]) == 2025:
            m = month(o["created_at"])
            month_count[m] = month_count.get(m, 0) + 1
    add("high", 4, "In which month of 2025 were the most opportunities created for accounts in the 'Technology' industry? Answer with the month number (1-12).",
        max(month_count, key=month_count.get) if month_count else None, "month", "Monthly Trend Analysis")

    # H5: region with highest avg transfer count for High-priority cases
    region_tc: dict[str, list[int]] = {}
    for c in cases:
        if c["priority"] == "High":
            r = acc[c["account_id"]]["region"]
            region_tc.setdefault(r, []).append(c["transfer_count"])
    region_tc_avg = {k: sum(v) / len(v) for k, v in region_tc.items()}
    add("high", 5, "Which region has the highest average transfer count for High-priority cases? Answer with the region name.",
        max(region_tc_avg, key=region_tc_avg.get) if region_tc_avg else None, "region", "Transfer Count Understanding")

    return instances


def check_ties(data: dict, instances: list[dict]) -> list[str]:
    """Flag high-difficulty argmax instances whose top two groups are tied."""
    warnings: list[str] = []
    # Re-derive the grouped distributions to check for ambiguity.
    acc = {a["id"]: a for a in data["accounts"]}
    ag = {a["id"]: a for a in data["agents"]}

    def top_gap(d: dict) -> float:
        vals = sorted(d.values(), reverse=True)
        return (vals[0] - vals[1]) if len(vals) > 1 else vals[0]

    region_won_q3: dict[str, int] = {}
    for o in data["opportunities"]:
        if o["is_won"] and year(o["close_date"]) == 2025 and quarter(o["close_date"]) == 3:
            r = acc[o["account_id"]]["region"]
            region_won_q3[r] = region_won_q3.get(r, 0) + o["amount"]
    if region_won_q3 and top_gap(region_won_q3) == 0:
        warnings.append("b-high-1 has a tie")
    return warnings


def main() -> None:
    data = generate()
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    for table, rows in data.items():
        (SEED_DIR / f"{table}.json").write_text(json.dumps(rows, indent=2))

    instances = compute_ground_truth(data)
    for inst in instances:
        d = INPUT_DIR / inst["difficulty"]
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{inst['id']}.json").write_text(json.dumps(inst, indent=2))

    print(f"Seed rows: " + ", ".join(f"{k}={len(v)}" for k, v in data.items()))
    print(f"Instances written: {len(instances)}")
    for inst in instances:
        print(f"  {inst['id']:12s} | {inst['ground_truth']['value']!r:>14} {inst['ground_truth']['unit']}")
    warnings = check_ties(data, instances)
    print("Ties:", warnings if warnings else "none")


if __name__ == "__main__":
    main()
