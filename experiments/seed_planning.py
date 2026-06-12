"""Curated planning instances for archetype G: CRM operations plans.

Writes 15 instance JSON files under ``data/test_inputs/g_strategic_planning/``
at three difficulty levels (5 each). Each instance contains:
    id, archetype, difficulty, sub_class, instruction, goal,
    optimal_length, rationale_hint, provenance

The deliverable per instance is a **plan** over the four-action vocabulary
(db_update, attempt_close_case, send_email, create_event) that the
deterministic simulator validates against the seed CRM state (precondition
checks per step, declarative goal spec on the final state). Information
Availability is moderate by construction: the instructions reference
accounts, cases, and conventions ("primary contact" = lowest contact id),
but the concrete ids, transfer counts, owner agents, and email addresses
live in the database and must be read before a concrete plan can exist.

Difficulty axis (protocol Table A.1 row G — optimal plan length):
    Low    — 3 steps. One precondition-aware chain (incl. one instance
             whose case is escalation-blocked, so the documented
             attempt_close_case precondition must be respected).
    Medium — 6–7 steps. Cross-entity chains with count discipline
             (exactly-one summary email) and ordering (closes before
             notifications).
    High   — 15–18 steps. Multi-account sweeps, capacity-constrained
             reassignment with transfer_count increments (state tracking),
             blocked-case handling at scale, strict side-effect discipline.

Every goal is machine-checkable (simulator.check_goal); every instance
ships with a REFERENCE_PLANS entry whose simulated execution must satisfy
the goal — the solvability proof exercised by tests/test_g_simulator.py.

Source attribution: scenarios are author-constructed over the local CRM
seed; the mechanical-validation principle, the plan-length difficulty axis,
and temperature 0 follow PlanBench (Valmeekam et al., 2023); plan-
generation framing follows FlowBench (Xiao et al., 2024) and WorkArena L2
(Boisvert et al., 2024). No benchmark text or data is reproduced.

Run:
    python experiments/seed_planning.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "g_strategic_planning"
SEED_DIR = REPO / "data" / "schema" / "seed"

BENCHMARK_REF = (
    "PlanBench (Valmeekam et al., 2023); "
    "FlowBench plan-generation variant (Xiao et al., 2024); "
    "WorkArena L2 compositional (Boisvert et al., 2024)"
)

# ── Seed lookups (deterministic; the instances reference these values) ──

_CONTACTS = json.loads((SEED_DIR / "contacts.json").read_text())
_AGENTS = {a["id"]: a for a in json.loads((SEED_DIR / "agents.json").read_text())}
_CASES = {c["id"]: c for c in json.loads((SEED_DIR / "cases.json").read_text())}


def pc(account_id: int) -> str:
    """Primary contact email of an account (lowest contact id)."""
    cands = [c for c in _CONTACTS if c["account_id"] == account_id]
    return min(cands, key=lambda c: c["id"])["email"]


def am(agent_id: int) -> str:
    """Agent email."""
    return _AGENTS[agent_id]["email"]


def _close_step(case_id: int) -> dict:
    """Reference-plan close step choosing the precondition-safe path."""
    if (_CASES[case_id].get("transfer_count") or 0) > 3:
        return {"tool": "db_update", "args": {"table": "cases", "record_id": case_id,
                "updates": {"status": "Closed", "closed_at": "2026-06-12 12:00:00"}}}
    return {"tool": "attempt_close_case",
            "args": {"case_id": case_id, "resolution_summary": "Resolved per plan"}}


def _mail(recipient: str, subject: str) -> dict:
    return {"tool": "send_email", "args": {"recipient": recipient, "subject": subject,
            "body": "Please see the update regarding this item."}}


def _event(name: str, attendees: list[str], day: str = "2026-06-25") -> dict:
    return {"tool": "create_event", "args": {"name": name, "start_time": f"{day} 10:00:00",
            "end_time": f"{day} 10:30:00", "attendees": attendees}}


def _provenance(sub_class: str | None) -> dict:
    note = (
        "Author-constructed scenario over the local CRM seed; mechanical plan "
        "validation, plan-length difficulty, and temperature 0 follow PlanBench; "
        "plan-generation framing follows FlowBench and WorkArena L2. No benchmark "
        "text or data is reproduced."
    )
    if sub_class:
        note += f" Sub-class: {sub_class}."
    return {
        "source_benchmark": BENCHMARK_REF,
        "adaptation": note,
        "license": "Original work by the author (scenarios, goal specs, action doc); benchmark semantics reference only",
    }


INSTANCES: list[dict] = [
    # ── LOW: optimal 3 steps ──
    {
        "id": "g-low-1", "difficulty": "low", "sub_class": "close_notify",
        "instruction": (
            "Plan the resolution of case 5: close it (resolution summary 'Issue resolved'), "
            "set its priority to 'Low' once closed, and notify the primary contact of the "
            "case's account by email with subject 'Case 5 closed' and a brief body."
        ),
        "goal": {"cases_closed": [5], "case_fields": {"5": {"priority": "Low"}},
                 "emails": [{"recipient": pc(4), "subject": "Case 5 closed"}],
                 "events": [], "no_other_changes": True},
        "optimal_length": 3,
        "rationale_hint": "Case 5 has transfer_count 2, so attempt_close_case is permitted; priority needs a separate db_update; one notification email to the primary contact of account 4.",
    },
    {
        "id": "g-low-2", "difficulty": "low", "sub_class": "blocked_close",
        "instruction": (
            "Plan the closure of case 7. Mind its transfer history when choosing the closing "
            "action, and make sure the closure timestamp is recorded. Notify the primary "
            "contact of the case's account by email with subject 'Case 7 closed' and a brief "
            "body, and schedule a 30-minute review event named 'Case 7 review' on 2026-06-25 "
            "with the case's owning agent as attendee."
        ),
        "goal": {"cases_closed": [7],
                 "emails": [{"recipient": pc(17), "subject": "Case 7 closed"}],
                 "events": [{"name": "Case 7 review", "attendees_contain": [am(2)]}],
                 "no_other_changes": True},
        "optimal_length": 3,
        "rationale_hint": "Case 7 has transfer_count 4 — attempt_close_case is rejected; the plan must use db_update with status AND closed_at. Owning agent is agent 2.",
    },
    {
        "id": "g-low-3", "difficulty": "low", "sub_class": "reassign_handover",
        "instruction": (
            "Plan the handover of case 8: reassign it to agent 2 and set its priority to "
            "'Medium' in the same update, then email the receiving agent with subject "
            "'Case 8 reassigned' and the previous owning agent with subject 'Case 8 handed "
            "over' (brief bodies). Do not close the case."
        ),
        "goal": {"case_fields": {"8": {"agent_id": 2, "priority": "Medium", "status": "Open"}},
                 "emails": [{"recipient": am(2), "subject": "Case 8 reassigned"},
                            {"recipient": am(3), "subject": "Case 8 handed over"}],
                 "events": [], "no_other_changes": True},
        "optimal_length": 3,
        "rationale_hint": "Bundled two-field db_update plus two emails; previous owner is agent 3 (must be read from the case row).",
    },
    {
        "id": "g-low-4", "difficulty": "low", "sub_class": "opportunity_win",
        "instruction": (
            "Plan the win booking of opportunity 3: set its stage to 'Closed Won' and is_won "
            "to true in one update, email the primary contact of its account with subject "
            "'Opportunity 3 won' and a brief body, and schedule an event named 'Win review "
            "Account 16' on 2026-06-26 with agent 7 as attendee."
        ),
        "goal": {"opp_fields": {"3": {"stage": "Closed Won", "is_won": True}},
                 "emails": [{"recipient": pc(16), "subject": "Opportunity 3 won"}],
                 "events": [{"name": "Win review Account 16", "attendees_contain": [am(7)]}],
                 "no_other_changes": True},
        "optimal_length": 3,
        "rationale_hint": "Opportunity 3 belongs to account 16; both fields in one db_update.",
    },
    {
        "id": "g-low-5", "difficulty": "low", "sub_class": "kickoff",
        "instruction": (
            "Plan the kickoff for account 6: schedule an event named 'Kickoff Account 6' on "
            "2026-06-22 with agent 7 and the account's primary contact as attendees, email "
            "that contact with subject 'Kickoff scheduled' and a brief body, and raise the "
            "priority of account 6's open case 21 to 'High'."
        ),
        "goal": {"case_fields": {"21": {"priority": "High", "status": "Open"}},
                 "emails": [{"recipient": pc(6), "subject": "Kickoff scheduled"}],
                 "events": [{"name": "Kickoff Account 6", "attendees_contain": [am(7), pc(6)]}],
                 "no_other_changes": True},
        "optimal_length": 3,
        "rationale_hint": "Primary contact of account 6 must be resolved via the lowest-contact-id convention.",
    },
    # ── MEDIUM: optimal 6–7 steps ──
    {
        "id": "g-med-1", "difficulty": "med", "sub_class": "account_sweep",
        "instruction": (
            "Plan the cleanup of account 13: close its open cases 18, 22 and 67, email the "
            "account's primary contact once per closed case with subject 'Case <id> closed' "
            "(e.g. 'Case 18 closed') and brief bodies, sending the notifications only after "
            "all closes, and finish with an event named 'Account 13 wrap-up' on 2026-06-29 "
            "with agent 1 as attendee."
        ),
        "goal": {"cases_closed": [18, 22, 67],
                 "emails": [{"recipient": pc(13), "subject": f"Case {i} closed"} for i in (18, 22, 67)],
                 "events": [{"name": "Account 13 wrap-up", "attendees_contain": [am(1)]}],
                 "closes_before_emails": True, "no_other_changes": True},
        "optimal_length": 7,
        "rationale_hint": "All three cases have transfer_count <= 3 (attempt_close_case permitted); ordering constraint: closes strictly before notifications.",
    },
    {
        "id": "g-med-2", "difficulty": "med", "sub_class": "bulk_reassign",
        "instruction": (
            "Plan the rebalancing of account 14: reassign its open cases 40, 62, 63 and 118 "
            "to agent 8, setting each case's priority to 'Medium' in the same update, then "
            "email agent 8 once with subject 'Account 14 cases reassigned' and a brief body, "
            "and finish with an event named 'Handover sync' on 2026-06-30 with agent 8 as "
            "attendee. Do not close any case."
        ),
        "goal": {"case_fields": {str(i): {"agent_id": 8, "priority": "Medium", "status": "Open"}
                                  for i in (40, 62, 63, 118)},
                 "emails": [{"recipient": am(8), "subject": "Account 14 cases reassigned"}],
                 "events": [{"name": "Handover sync", "attendees_contain": [am(8)]}],
                 "no_other_changes": True},
        "optimal_length": 6,
        "rationale_hint": "Four bundled two-field updates; exactly one email despite four cases (count discipline).",
    },
    {
        "id": "g-med-3", "difficulty": "med", "sub_class": "mixed_blocked",
        "instruction": (
            "Plan the closure of agent 5's open cases 31, 32 and 53, recording a closure "
            "timestamp for every one and minding each case's transfer history when choosing "
            "the closing action. Email the primary contact of each case's account with "
            "subject 'Case <id> resolved' and a brief body, and email agent 5 once with "
            "subject 'Case load resolved'."
        ),
        "goal": {"cases_closed": [31, 32, 53],
                 "emails": [{"recipient": pc(12), "subject": "Case 31 resolved"},
                            {"recipient": pc(18), "subject": "Case 32 resolved"},
                            {"recipient": pc(8), "subject": "Case 53 resolved"},
                            {"recipient": am(5), "subject": "Case load resolved"}],
                 "events": [], "no_other_changes": True},
        "optimal_length": 7,
        "rationale_hint": "Case 31 has transfer_count 4 (blocked: db_update path with closed_at); 32 and 53 are closable via attempt_close_case. Account mapping 31->12, 32->18, 53->8 must be read.",
    },
    {
        "id": "g-med-4", "difficulty": "med", "sub_class": "pipeline_update",
        "instruction": (
            "Plan the account 8 pipeline review: move opportunities 4 and 17 to stage "
            "'Proposal', close the account's open cases 71 and 98, email the account's "
            "primary contact exactly once with subject 'Account 8 update' and a brief body, "
            "and finish with an event named 'Pipeline review Account 8' on 2026-07-01 with "
            "agent 5 as attendee."
        ),
        "goal": {"cases_closed": [71, 98],
                 "opp_fields": {"4": {"stage": "Proposal"}, "17": {"stage": "Proposal"}},
                 "emails": [{"recipient": pc(8), "subject": "Account 8 update"}],
                 "events": [{"name": "Pipeline review Account 8", "attendees_contain": [am(5)]}],
                 "no_other_changes": True},
        "optimal_length": 6,
        "rationale_hint": "Exactly one customer email despite two closed cases and two moved opportunities; both cases are closable (transfer_count <= 3).",
    },
    {
        "id": "g-med-5", "difficulty": "med", "sub_class": "blocked_in_sweep",
        "instruction": (
            "Plan the resolution of account 10's open cases 75, 110 and 47, recording a "
            "closure timestamp for every one and minding each case's transfer history when "
            "choosing the closing actions. After all closes, email the account's primary "
            "contact exactly once with subject 'All account 10 cases resolved', and email "
            "the owning agent of case 47 with subject 'Case 47 closed after review' (brief "
            "bodies)."
        ),
        "goal": {"cases_closed": [75, 110, 47],
                 "emails": [{"recipient": pc(10), "subject": "All account 10 cases resolved"},
                            {"recipient": am(1), "subject": "Case 47 closed after review"}],
                 "events": [], "closes_before_emails": True, "no_other_changes": True},
        "optimal_length": 5,
        "rationale_hint": "Case 47 has transfer_count 4 (db_update path); 75 and 110 are closable. Owning agent of case 47 is agent 1. Exactly two emails, after all closes.",
    },
    # ── HIGH: optimal 15–18 steps ──
    {
        "id": "g-high-1", "difficulty": "high", "sub_class": "two_account_sweep",
        "instruction": (
            "Plan the Q2 cleanup of accounts 14 and 16: close every open case of these two "
            "accounts that is NOT escalation-blocked — that is cases 40, 62, 63 and 118 "
            "(account 14) and 16, 54, 81 and 104 (account 16). Email the respective "
            "account's primary contact once per closed case with subject 'Case <id> closed' "
            "and brief bodies, only after all closes. Move opportunity 3 to stage "
            "'Closed Lost'. Finish with an event named 'Q2 cleanup review' on 2026-07-02 "
            "with agents 7 and 8 as attendees."
        ),
        "goal": {"cases_closed": [40, 62, 63, 118, 16, 54, 81, 104],
                 "emails": ([{"recipient": pc(14), "subject": f"Case {i} closed"} for i in (40, 62, 63, 118)]
                            + [{"recipient": pc(16), "subject": f"Case {i} closed"} for i in (16, 54, 81, 104)]),
                 "opp_fields": {"3": {"stage": "Closed Lost"}},
                 "events": [{"name": "Q2 cleanup review", "attendees_contain": [am(7), am(8)]}],
                 "closes_before_emails": True, "no_other_changes": True},
        "optimal_length": 18,
        "rationale_hint": "Eight closable cases (all transfer_count <= 3), eight per-case emails to two different primary contacts, one opportunity move, one event — 18 steps with a global ordering constraint.",
    },
    {
        "id": "g-high-2", "difficulty": "high", "sub_class": "capacity_rebalance",
        "instruction": (
            "Plan the rebalancing of agent 5's six open cases (31, 32, 53, 78, 93, 98): "
            "reassign every one to one of agents 2, 6 or 8, with AT MOST two cases per "
            "receiving agent, and increment each case's transfer_count by exactly 1 in the "
            "same update. Email the primary contact of each case's account with subject "
            "'Case <id> reassigned' and a brief body. Email each receiving agent exactly "
            "once with subject 'Cases reassigned to you'. Finish with an event named "
            "'Rebalance review' on 2026-07-03 with agent 5 as attendee."
        ),
        "goal": {"cases_reassigned": [31, 32, 53, 78, 93, 98],
                 "tc_incremented": [31, 32, 53, 78, 93, 98],
                 "agent_capacity": {"targets": [2, 6, 8], "max_new": 2},
                 "emails": [{"recipient": pc(12), "subject": "Case 31 reassigned"},
                            {"recipient": pc(18), "subject": "Case 32 reassigned"},
                            {"recipient": pc(8), "subject": "Case 53 reassigned"},
                            {"recipient": pc(17), "subject": "Case 78 reassigned"},
                            {"recipient": pc(19), "subject": "Case 93 reassigned"},
                            {"recipient": pc(8), "subject": "Case 98 reassigned"}],
                 "emails_one_per_new_owner": {"subject": "Cases reassigned to you"},
                 "events": [{"name": "Rebalance review", "attendees_contain": [am(5)]}],
                 "no_other_changes": True},
        "optimal_length": 16,
        "rationale_hint": "Six cases over three targets at capacity 2 forces an exact 2/2/2 split; transfer_count increments require reading the current values (31->5, 32->3, 53->2, 78->4, 93->1, 98->4); six contact emails plus exactly one email per receiving agent.",
    },
    {
        "id": "g-high-3", "difficulty": "high", "sub_class": "mixed_discipline",
        "instruction": (
            "Plan the dual-account consolidation: close account 15's open cases 68, 116 and "
            "120 and email the account's primary contact once per closed case with subject "
            "'Case <id> closed'. Close account 18's open cases 30 and 89 and email that "
            "account's primary contact exactly once with subject 'Account 18 cases "
            "resolved'. Email the owning agent of each account-18 case with subject "
            "'Handover complete' (one email per case). Move opportunities 10 and 13 to "
            "stage 'Proposal'. Schedule two events: 'Account 15 phase 2 kickoff' on "
            "2026-07-06 with account 15's primary contact, and 'Account 18 retro' on "
            "2026-07-07 with agent 4 as attendee. All emails use brief bodies."
        ),
        "goal": {"cases_closed": [68, 116, 120, 30, 89],
                 "emails": ([{"recipient": pc(15), "subject": f"Case {i} closed"} for i in (68, 116, 120)]
                            + [{"recipient": pc(18), "subject": "Account 18 cases resolved"},
                               {"recipient": am(4), "subject": "Handover complete"},
                               {"recipient": am(3), "subject": "Handover complete"}]),
                 "opp_fields": {"10": {"stage": "Proposal"}, "13": {"stage": "Proposal"}},
                 "events": [{"name": "Account 15 phase 2 kickoff", "attendees_contain": [pc(15)]},
                            {"name": "Account 18 retro", "attendees_contain": [am(4)]}],
                 "no_other_changes": True},
        "optimal_length": 15,
        "rationale_hint": "Mixed notification discipline: per-case emails for account 15, exactly one summary for account 18, plus per-case agent handovers (case 30 -> agent 4, case 89 -> agent 3, must be read). All five cases closable.",
    },
    {
        "id": "g-high-4", "difficulty": "high", "sub_class": "escalated_at_scale",
        "instruction": (
            "Plan the resolution of the five escalated cases 7, 13, 31, 45 and 47. Every "
            "one of them has a transfer history that blocks the standard closing action — "
            "choose the closing path accordingly, record a closure timestamp, and set each "
            "case's priority to 'Low' in the same update. After all closes, email the "
            "primary contact of each case's account with subject 'Case <id> closed after "
            "review', and email each case's owning agent with subject 'Escalated case <id> "
            "resolved' (brief bodies). Move opportunities 12 and 26 to stage 'Proposal'. "
            "Finish with an event named 'Escalation retrospective' on 2026-07-08 with "
            "agents 1 and 2 as attendees."
        ),
        "goal": {"cases_closed": [7, 13, 31, 45, 47],
                 "case_fields": {str(i): {"priority": "Low"} for i in (7, 13, 31, 45, 47)},
                 "emails": ([{"recipient": pc(a), "subject": f"Case {c} closed after review"}
                             for c, a in ((7, 17), (13, 3), (31, 12), (45, 4), (47, 10))]
                            + [{"recipient": am(g), "subject": f"Escalated case {c} resolved"}
                               for c, g in ((7, 2), (13, 6), (31, 5), (45, 10), (47, 1))]),
                 "opp_fields": {"12": {"stage": "Proposal"}, "26": {"stage": "Proposal"}},
                 "events": [{"name": "Escalation retrospective", "attendees_contain": [am(1), am(2)]}],
                 "closes_before_emails": True, "no_other_changes": True},
        "optimal_length": 18,
        "rationale_hint": "All five cases have transfer_count > 3: attempt_close_case is rejected for every one; the optimal path bundles status, closed_at, and priority into one db_update per case. Ten emails with per-case account and agent resolution, two opportunity moves, one event.",
    },
    {
        "id": "g-high-5", "difficulty": "high", "sub_class": "account_cycle",
        "instruction": (
            "Plan the full account 16 cycle: close its open cases 16, 54, 81 and 104, "
            "setting case 16's priority to 'Low' after its close, and email the account's "
            "primary contact once per closed case with subject 'Case <id> closed' (brief "
            "bodies, only after all closes). Mark opportunity 3 as won (stage 'Closed Won', "
            "is_won true, one update). Email agents 7 and 10 one message each with subject "
            "'Account 16 cycle complete'. Schedule three events: 'Account 16 kickoff EU' on "
            "2026-07-09 with agent 7, 'Account 16 retro' on 2026-07-10 with agent 10, and "
            "'Account 16 exec review' on 2026-07-11 with agent 7 as attendees."
        ),
        "goal": {"cases_closed": [16, 54, 81, 104],
                 "case_fields": {"16": {"priority": "Low"}},
                 "opp_fields": {"3": {"stage": "Closed Won", "is_won": True}},
                 "emails": ([{"recipient": pc(16), "subject": f"Case {i} closed"} for i in (16, 54, 81, 104)]
                            + [{"recipient": am(7), "subject": "Account 16 cycle complete"},
                               {"recipient": am(10), "subject": "Account 16 cycle complete"}]),
                 "events": [{"name": "Account 16 kickoff EU", "attendees_contain": [am(7)]},
                            {"name": "Account 16 retro", "attendees_contain": [am(10)]},
                            {"name": "Account 16 exec review", "attendees_contain": [am(7)]}],
                 "closes_before_emails": True, "no_other_changes": True},
        "optimal_length": 15,
        "rationale_hint": "Four closable cases, one extra priority update on case 16, one bundled opportunity win, six emails, three events — 15 steps with closes-before-emails ordering.",
    },
]


# ── Reference plans: the solvability proof (tests/test_g_simulator.py) ──

def _ref(inst_id: str) -> list[dict]:
    g = {i["id"]: i for i in INSTANCES}[inst_id]["goal"]
    steps: list[dict] = []
    if inst_id == "g-low-1":
        steps = [_close_step(5),
                 {"tool": "db_update", "args": {"table": "cases", "record_id": 5, "updates": {"priority": "Low"}}},
                 _mail(pc(4), "Case 5 closed")]
    elif inst_id == "g-low-2":
        steps = [_close_step(7), _mail(pc(17), "Case 7 closed"),
                 _event("Case 7 review", [am(2)])]
    elif inst_id == "g-low-3":
        steps = [{"tool": "db_update", "args": {"table": "cases", "record_id": 8,
                  "updates": {"agent_id": 2, "priority": "Medium"}}},
                 _mail(am(2), "Case 8 reassigned"), _mail(am(3), "Case 8 handed over")]
    elif inst_id == "g-low-4":
        steps = [{"tool": "db_update", "args": {"table": "opportunities", "record_id": 3,
                  "updates": {"stage": "Closed Won", "is_won": True}}},
                 _mail(pc(16), "Opportunity 3 won"), _event("Win review Account 16", [am(7)])]
    elif inst_id == "g-low-5":
        steps = [_event("Kickoff Account 6", [am(7), pc(6)]), _mail(pc(6), "Kickoff scheduled"),
                 {"tool": "db_update", "args": {"table": "cases", "record_id": 21, "updates": {"priority": "High"}}}]
    elif inst_id == "g-med-1":
        steps = [_close_step(i) for i in (18, 22, 67)]
        steps += [_mail(pc(13), f"Case {i} closed") for i in (18, 22, 67)]
        steps += [_event("Account 13 wrap-up", [am(1)])]
    elif inst_id == "g-med-2":
        steps = [{"tool": "db_update", "args": {"table": "cases", "record_id": i,
                  "updates": {"agent_id": 8, "priority": "Medium"}}} for i in (40, 62, 63, 118)]
        steps += [_mail(am(8), "Account 14 cases reassigned"), _event("Handover sync", [am(8)])]
    elif inst_id == "g-med-3":
        steps = [_close_step(i) for i in (31, 32, 53)]
        steps += [_mail(pc(12), "Case 31 resolved"), _mail(pc(18), "Case 32 resolved"),
                  _mail(pc(8), "Case 53 resolved"), _mail(am(5), "Case load resolved")]
    elif inst_id == "g-med-4":
        steps = [{"tool": "db_update", "args": {"table": "opportunities", "record_id": i,
                  "updates": {"stage": "Proposal"}}} for i in (4, 17)]
        steps += [_close_step(71), _close_step(98), _mail(pc(8), "Account 8 update"),
                  _event("Pipeline review Account 8", [am(5)])]
    elif inst_id == "g-med-5":
        steps = [_close_step(i) for i in (75, 110, 47)]
        steps += [_mail(pc(10), "All account 10 cases resolved"),
                  _mail(am(1), "Case 47 closed after review")]
    elif inst_id == "g-high-1":
        steps = [_close_step(i) for i in (40, 62, 63, 118, 16, 54, 81, 104)]
        steps += [_mail(pc(14), f"Case {i} closed") for i in (40, 62, 63, 118)]
        steps += [_mail(pc(16), f"Case {i} closed") for i in (16, 54, 81, 104)]
        steps += [{"tool": "db_update", "args": {"table": "opportunities", "record_id": 3,
                   "updates": {"stage": "Closed Lost"}}},
                  _event("Q2 cleanup review", [am(7), am(8)])]
    elif inst_id == "g-high-2":
        assign = {31: 2, 32: 2, 53: 6, 78: 6, 93: 8, 98: 8}
        steps = [{"tool": "db_update", "args": {"table": "cases", "record_id": cid,
                  "updates": {"agent_id": tgt,
                              "transfer_count": (_CASES[cid].get("transfer_count") or 0) + 1}}}
                 for cid, tgt in assign.items()]
        steps += [_mail(pc(_CASES[cid]["account_id"]), f"Case {cid} reassigned") for cid in assign]
        steps += [_mail(am(t), "Cases reassigned to you") for t in (2, 6, 8)]
        steps += [_event("Rebalance review", [am(5)])]
    elif inst_id == "g-high-3":
        steps = [_close_step(i) for i in (68, 116, 120, 30, 89)]
        steps += [_mail(pc(15), f"Case {i} closed") for i in (68, 116, 120)]
        steps += [_mail(pc(18), "Account 18 cases resolved"),
                  _mail(am(4), "Handover complete"), _mail(am(3), "Handover complete")]
        steps += [{"tool": "db_update", "args": {"table": "opportunities", "record_id": i,
                   "updates": {"stage": "Proposal"}}} for i in (10, 13)]
        steps += [_event("Account 15 phase 2 kickoff", [pc(15)]),
                  _event("Account 18 retro", [am(4)])]
    elif inst_id == "g-high-4":
        steps = [{"tool": "db_update", "args": {"table": "cases", "record_id": i,
                  "updates": {"status": "Closed", "closed_at": "2026-06-12 12:00:00", "priority": "Low"}}}
                 for i in (7, 13, 31, 45, 47)]
        steps += [_mail(pc(a), f"Case {c} closed after review")
                  for c, a in ((7, 17), (13, 3), (31, 12), (45, 4), (47, 10))]
        steps += [_mail(am(g), f"Escalated case {c} resolved")
                  for c, g in ((7, 2), (13, 6), (31, 5), (45, 10), (47, 1))]
        steps += [{"tool": "db_update", "args": {"table": "opportunities", "record_id": i,
                   "updates": {"stage": "Proposal"}}} for i in (12, 26)]
        steps += [_event("Escalation retrospective", [am(1), am(2)])]
    elif inst_id == "g-high-5":
        steps = [_close_step(i) for i in (16, 54, 81, 104)]
        steps += [{"tool": "db_update", "args": {"table": "cases", "record_id": 16, "updates": {"priority": "Low"}}}]
        steps += [_mail(pc(16), f"Case {i} closed") for i in (16, 54, 81, 104)]
        steps += [{"tool": "db_update", "args": {"table": "opportunities", "record_id": 3,
                   "updates": {"stage": "Closed Won", "is_won": True}}},
                  _mail(am(7), "Account 16 cycle complete"), _mail(am(10), "Account 16 cycle complete")]
        steps += [_event("Account 16 kickoff EU", [am(7)]), _event("Account 16 retro", [am(10)]),
                  _event("Account 16 exec review", [am(7)])]
    return steps


REFERENCE_PLANS: dict[str, list[dict]] = {i["id"]: _ref(i["id"]) for i in INSTANCES}


def main() -> None:
    written = 0
    for inst in INSTANCES:
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        record = {
            "id": inst["id"],
            "archetype": "G",
            "difficulty": inst["difficulty"],
            "sub_class": inst.get("sub_class"),
            "instruction": inst["instruction"],
            "goal": inst["goal"],
            "optimal_length": inst["optimal_length"],
            "rationale_hint": inst["rationale_hint"],
            "provenance": _provenance(inst.get("sub_class")),
        }
        (directory / f"{inst['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")
    print("Reference plans registered:", len(REFERENCE_PLANS))


if __name__ == "__main__":
    main()
