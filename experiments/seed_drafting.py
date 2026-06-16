"""Curated drafting instances for archetype H: data-to-text business writing.

Writes 15 instance JSON files under ``data/test_inputs/h_content_drafting/``
at three difficulty levels (5 each). Each instance pairs an inline data
table with a writing brief (format, audience, tonality, length window,
framing, required data points), zero to two scripted feedback rounds, and
the deterministic constraint set used by the compliance layer.

Difficulty axis = CONSTRAINT LOAD + feedback rounds (deviation D-014):
    Low  — 1–2 constraints, 0 feedback rounds.
    Med  — 3–4 constraints, 1 feedback round (adds a data-bound requirement).
    High — 5+ constraints, 2 feedback rounds, one of them a TENSION revision
           (e.g. "shorten it but add the regional breakdown") that forces
           re-prioritization.

Formats are MIXED across tiers (post / email / report) so format is not
confounded with length; the workflow-vs-agent comparison is per-instance
paired, so format variety does not bias the contrast.

Faithfulness anchor: ``allowed_numbers`` is computed from the table cells
plus a per-instance ``extra_allowed`` list of legitimate derived values
(totals, growth percentages, the year). The compliance layer flags any
significant number in the artefact not within tolerance of this set as a
fabrication.

Source: WONDERBREAD SOP Generation / Improvement (Wornow et al., 2024);
TheAgentCompany report drafting (Xu et al., 2024). Tables, briefs, and
constraints are author-constructed over synthetic figures (IT-017 rule).

Run:
    python experiments/seed_drafting.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "h_content_drafting"

BENCHMARK_REF = (
    "WONDERBREAD SOP Generation / SOP Improvement (Wornow et al., 2024); "
    "TheAgentCompany report drafting (Xu et al., 2024)"
)

_NUM = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def _nums_from_table(table: dict) -> list[float]:
    vals: list[float] = []
    for row in table["rows"]:
        for cell in row:
            for m in _NUM.findall(str(cell)):
                try:
                    vals.append(float(m.replace(",", "")))
                except ValueError:
                    pass
    return vals


def _provenance(sub_class: str | None) -> dict:
    note = (
        "Author-constructed table, brief, and constraints over synthetic "
        "figures; data-to-text drafting with scripted feedback follows the "
        "SOP-generation/improvement and report-drafting pattern of the cited "
        "benchmarks. No benchmark text or data is reproduced."
    )
    if sub_class:
        note += f" Sub-class: {sub_class}."
    return {
        "source_benchmark": BENCHMARK_REF,
        "adaptation": note,
        "license": "Original work by the author (tables, briefs, constraints, judge rubric); benchmark semantics reference only",
    }


# ── Instances ──────────────────────────────────────────────────────────────
# Each: id, difficulty, sub_class, format, instruction, table, constraints,
# feedback_rounds, feedback_requirements, extra_allowed, rationale_hint.

INSTANCES: list[dict] = [
    # ===== LOW: 1–2 constraints, 0 feedback rounds =====
    {
        "id": "h-low-1", "difficulty": "low", "sub_class": "social_post",
        "format": "LinkedIn post",
        "instruction": "Write a short LinkedIn post announcing this quarter's product revenue.",
        "table": {"caption": "Q3 2025 revenue by product line (EUR)",
                  "columns": ["Product line", "Q3 revenue"],
                  "rows": [["Core", 1240000], ["Analytics", 880000], ["Connect", 410000]]},
        "constraints": {"audience": "LinkedIn followers and prospects", "tonality": "upbeat and confident",
                        "min_words": 30, "max_words": 70,
                        "required_points": [{"desc": "Core revenue 1,240,000", "keywords": ["1,240,000", "1.24 million", "1.24m", "1,24"]}]},
        "feedback_rounds": [], "feedback_requirements": [], "extra_allowed": [2530000, 2025, 3],
        "rationale_hint": "Two constraints (tone, length) + one required figure; no feedback. Near-parity expected.",
    },
    {
        "id": "h-low-2", "difficulty": "low", "sub_class": "short_email",
        "format": "internal email",
        "instruction": "Write a brief internal email summarizing last month's growth metrics for the team.",
        "table": {"caption": "October 2025 growth metrics",
                  "columns": ["Metric", "Value"],
                  "rows": [["New signups", 3420], ["Churned accounts", 215]]},
        "constraints": {"audience": "the internal growth team", "tonality": "concise and professional",
                        "min_words": 40, "max_words": 90,
                        "required_points": [{"desc": "signups 3420", "keywords": ["3,420", "3420"]},
                                            {"desc": "churn 215", "keywords": ["215"]}]},
        "feedback_rounds": [], "feedback_requirements": [], "extra_allowed": [2025],
        "rationale_hint": "Two required figures, tone + length. Single-shot.",
    },
    {
        "id": "h-low-3", "difficulty": "low", "sub_class": "social_post",
        "format": "company-update post",
        "instruction": "Write a celebratory post about reaching a customer milestone.",
        "table": {"caption": "Customer milestone",
                  "columns": ["Metric", "Value"], "rows": [["Total customers", 10000], ["Countries served", 42]]},
        "constraints": {"audience": "customers and the public", "tonality": "celebratory and warm",
                        "min_words": 30, "max_words": 60,
                        "required_points": [{"desc": "10,000 customers", "keywords": ["10,000", "10000", "10k"]}]},
        "feedback_rounds": [], "feedback_requirements": [], "extra_allowed": [42, 2025],
        "rationale_hint": "Milestone post; one mandatory figure, celebratory tone.",
    },
    {
        "id": "h-low-4", "difficulty": "low", "sub_class": "short_email",
        "format": "status email",
        "instruction": "Write a short status email to the support lead summarizing this week's ticket throughput.",
        "table": {"caption": "Support week 45",
                  "columns": ["Metric", "Value"], "rows": [["Tickets resolved", 612], ["Median response (h)", 4.2]]},
        "constraints": {"audience": "the support team lead", "tonality": "factual and brief",
                        "min_words": 35, "max_words": 80,
                        "required_points": [{"desc": "612 resolved", "keywords": ["612"]},
                                            {"desc": "4.2h median", "keywords": ["4.2"]}]},
        "feedback_rounds": [], "feedback_requirements": [], "extra_allowed": [45, 2025],
        "rationale_hint": "Two figures incl. a decimal; factual tone.",
    },
    {
        "id": "h-low-5", "difficulty": "low", "sub_class": "social_post",
        "format": "short post",
        "instruction": "Write a brief post sharing the latest customer satisfaction score.",
        "table": {"caption": "CSAT Q3 2025",
                  "columns": ["Metric", "Value"], "rows": [["NPS", 58], ["Responses", 1300]]},
        "constraints": {"audience": "customers", "tonality": "appreciative",
                        "min_words": 25, "max_words": 55,
                        "required_points": [{"desc": "NPS 58", "keywords": ["58"]}]},
        "feedback_rounds": [], "feedback_requirements": [], "extra_allowed": [1300, 2025, 3],
        "rationale_hint": "Single required figure; appreciative tone.",
    },
    # ===== MED: 3–4 constraints, 1 feedback round =====
    {
        "id": "h-med-1", "difficulty": "med", "sub_class": "summary_email",
        "format": "summary email",
        "instruction": "Write an email to the sales director summarizing Q3 performance across the three product lines.",
        "table": {"caption": "Revenue by product line (EUR)",
                  "columns": ["Product line", "Q3 2024", "Q3 2025"],
                  "rows": [["Core", 1100000, 1240000], ["Analytics", 700000, 880000], ["Connect", 450000, 410000]]},
        "constraints": {"audience": "the sales director (non-technical)", "tonality": "professional and analytical",
                        "min_words": 120, "max_words": 220, "framing": "lead with the overall result, then the per-line detail",
                        "required_points": [{"desc": "Core Q3 2025 1,240,000", "keywords": ["1,240,000", "1.24"]},
                                            {"desc": "Analytics Q3 2025 880,000", "keywords": ["880,000", "880"]},
                                            {"desc": "Connect Q3 2025 410,000", "keywords": ["410,000", "410"]}]},
        "feedback_rounds": ["Please name the strongest and weakest line explicitly, and add the total Q3 2025 revenue across all lines."],
        "feedback_requirements": [{"round": 1, "desc": "names strongest/weakest + total 2,530,000",
                                   "keywords": ["2,530,000", "2.53 million", "2.53m", "strongest", "weakest"]}],
        "extra_allowed": [2530000, 2250000, 280000, 2024, 2025, 3],
        "rationale_hint": "Three required figures + framing; feedback adds total (2,530,000) and strongest/weakest naming.",
    },
    {
        "id": "h-med-2", "difficulty": "med", "sub_class": "one_page_report",
        "format": "one-page report",
        "instruction": "Write a one-page report on the quarter's hiring funnel for the leadership team.",
        "table": {"caption": "Hiring funnel Q3 2025",
                  "columns": ["Stage", "Count"],
                  "rows": [["Applications", 1450], ["Interviews", 230], ["Offers", 48], ["Hires", 35]]},
        "constraints": {"audience": "the leadership team", "tonality": "neutral and informative",
                        "min_words": 130, "max_words": 240, "framing": "highlight the largest drop-off in the funnel",
                        "required_points": [{"desc": "1,450 applications", "keywords": ["1,450", "1450"]},
                                            {"desc": "35 hires", "keywords": ["35 hire", "35 new", "35"]}]},
        "feedback_rounds": ["Add the offer-to-hire conversion rate as a percentage."],
        "feedback_requirements": [{"round": 1, "desc": "offer->hire ~73%", "keywords": ["73%", "73 %", "72.9", "73 percent"]}],
        "extra_allowed": [230, 48, 72.9, 73, 2025],
        "rationale_hint": "Funnel report; feedback adds the 35/48 = ~73% conversion. Faithfulness must accept 73 / 72.9.",
    },
    {
        "id": "h-med-3", "difficulty": "med", "sub_class": "customer_email",
        "format": "customer email",
        "instruction": "Write an email to a key customer summarizing their account usage this quarter.",
        "table": {"caption": "Account usage Q3 2025",
                  "columns": ["Metric", "Value"],
                  "rows": [["Active seats", 320], ["Reports generated", 5400], ["Uptime", "99.95%"]]},
        "constraints": {"audience": "a key enterprise customer", "tonality": "warm but professional",
                        "min_words": 110, "max_words": 200, "framing": "open with appreciation for the partnership",
                        "required_points": [{"desc": "320 seats", "keywords": ["320"]},
                                            {"desc": "uptime 99.95%", "keywords": ["99.95"]}]},
        "feedback_rounds": ["Mention the number of reports generated and invite them to a quarterly review call."],
        "feedback_requirements": [{"round": 1, "desc": "5,400 reports + review call invite",
                                   "keywords": ["5,400", "5400"]}],
        "extra_allowed": [99.95, 2025, 3],
        "rationale_hint": "Warm customer email; feedback adds reports figure + a call invite.",
    },
    {
        "id": "h-med-4", "difficulty": "med", "sub_class": "announcement_post",
        "format": "announcement post",
        "instruction": "Write a post announcing a new feature and its early adoption numbers.",
        "table": {"caption": "Feature X early adoption (first 30 days)",
                  "columns": ["Metric", "Value"],
                  "rows": [["Accounts enabled", 540], ["Avg. weekly uses", 12], ["Satisfaction", "4.6/5"]]},
        "constraints": {"audience": "existing customers and prospects", "tonality": "enthusiastic but credible",
                        "min_words": 70, "max_words": 140, "framing": "lead with the customer benefit, not the metric",
                        "required_points": [{"desc": "540 accounts", "keywords": ["540"]},
                                            {"desc": "satisfaction 4.6", "keywords": ["4.6"]}]},
        "feedback_rounds": ["Tone down the superlatives and make it credible; add the average weekly uses figure."],
        "feedback_requirements": [{"round": 1, "desc": "avg weekly uses 12", "keywords": ["12 use", "12 time", "twelve", "12 weekly", "average of 12", "12 per", "12"]}],
        "extra_allowed": [30, 5, 2025],
        "rationale_hint": "Feedback both softens tone and adds a figure; tests dual-aspect feedback.",
    },
    {
        "id": "h-med-5", "difficulty": "med", "sub_class": "summary_email",
        "format": "summary email",
        "instruction": "Write an email to the operations lead summarizing this month's fulfilment metrics.",
        "table": {"caption": "Fulfilment October 2025",
                  "columns": ["Metric", "Value"],
                  "rows": [["Orders shipped", 8600], ["On-time rate", "94%"], ["Returns", 340]]},
        "constraints": {"audience": "the operations lead", "tonality": "direct and businesslike",
                        "min_words": 100, "max_words": 190, "framing": "flag the on-time rate against a 95% target",
                        "required_points": [{"desc": "8,600 shipped", "keywords": ["8,600", "8600"]},
                                            {"desc": "on-time 94%", "keywords": ["94%", "94 %", "94 percent"]}]},
        "feedback_rounds": ["Add the returns figure and state the gap to the 95% on-time target in percentage points."],
        "feedback_requirements": [{"round": 1, "desc": "returns 340 + 1 pp gap", "keywords": ["340"]}],
        "extra_allowed": [94, 95, 1, 2025],
        "rationale_hint": "Feedback adds returns + the 1-percentage-point gap (95-94).",
    },
    # ===== HIGH: 5+ constraints, 2 feedback rounds incl. a tension revision =====
    {
        "id": "h-high-1", "difficulty": "high", "sub_class": "multi_section_report",
        "format": "multi-section report",
        "instruction": "Write a structured quarterly business review for the executive board.",
        "table": {"caption": "Q3 2025 company KPIs",
                  "columns": ["KPI", "Q2 2025", "Q3 2025"],
                  "rows": [["Revenue (EUR)", 2250000, 2530000], ["New customers", 480, 610],
                           ["Churn rate", "3.1%", "2.7%"], ["Gross margin", "71%", "73%"]]},
        "constraints": {"audience": "the executive board", "tonality": "formal and measured",
                        "min_words": 220, "max_words": 420,
                        "framing": "balanced — name both a win and a risk",
                        "required_sections": ["Summary", "Financials", "Customers", "Outlook"],
                        "required_points": [{"desc": "revenue 2,530,000", "keywords": ["2,530,000", "2.53"]},
                                            {"desc": "churn 2.7%", "keywords": ["2.7%", "2.7 %"]},
                                            {"desc": "gross margin 73%", "keywords": ["73%", "73 %"]}]},
        "feedback_rounds": [
            "Add the quarter-over-quarter revenue growth as a percentage in the Financials section.",
            "The board wants it tighter — cut it toward the lower end of the word range, but you must still keep all four sections and add the new-customer count for Q3.",
        ],
        "feedback_requirements": [
            {"round": 1, "desc": "QoQ revenue growth ~12.4%", "keywords": ["12.4%", "12.4 %", "12%", "12 percent", "12.4"]},
            {"round": 2, "desc": "Q3 new customers 610", "keywords": ["610"]},
        ],
        "extra_allowed": [2250000, 480, 3.1, 2.7, 71, 73, 12.4, 12, 280000, 2025, 4],
        "rationale_hint": "5+ constraints, four sections, two feedback rounds; round 2 is a tension revision (shorten yet add content). QoQ growth 280000/2250000 = 12.4%.",
    },
    {
        "id": "h-high-2", "difficulty": "high", "sub_class": "multi_section_report",
        "format": "multi-section report",
        "instruction": "Write a structured incident retrospective for engineering leadership.",
        "table": {"caption": "Incident INC-204 metrics",
                  "columns": ["Metric", "Value"],
                  "rows": [["Detection time (min)", 18], ["Resolution time (min)", 142],
                           ["Customers affected", 2300], ["Error rate peak", "7.4%"]]},
        "constraints": {"audience": "engineering leadership", "tonality": "blameless and analytical",
                        "min_words": 220, "max_words": 400,
                        "framing": "blameless — focus on system and process, not individuals",
                        "required_sections": ["Summary", "Timeline", "Impact", "Action items"],
                        "required_points": [{"desc": "142 min resolution", "keywords": ["142"]},
                                            {"desc": "2,300 customers", "keywords": ["2,300", "2300"]},
                                            {"desc": "peak error 7.4%", "keywords": ["7.4%", "7.4 %"]}]},
        "feedback_rounds": [
            "Add the detection time and compute total time from detection to resolution in minutes.",
            "Tighten it toward the lower word bound, but keep all four sections and add at least two concrete action items.",
        ],
        "feedback_requirements": [
            {"round": 1, "desc": "detection 18 + total 160 min", "keywords": ["160"]},
            {"round": 2, "desc": "action items present", "keywords": ["action item", "action items"]},
        ],
        "extra_allowed": [18, 7.4, 160, 204, 2025],
        "rationale_hint": "Blameless retro; round 1 adds total 18+142=160; round 2 tension (shorten + keep sections + add action items).",
    },
    {
        "id": "h-high-3", "difficulty": "high", "sub_class": "exec_email",
        "format": "executive email",
        "instruction": "Write an email to the CEO summarizing the regional sales picture and recommending a focus region.",
        "table": {"caption": "Q3 2025 sales by region (EUR)",
                  "columns": ["Region", "Q3 sales", "YoY change"],
                  "rows": [["EMEA", 1150000, "+14%"], ["AMER", 980000, "+6%"], ["APAC", 400000, "+22%"]]},
        "constraints": {"audience": "the CEO", "tonality": "concise, decisive, executive",
                        "min_words": 160, "max_words": 280,
                        "framing": "end with a single clear recommendation",
                        "required_points": [{"desc": "EMEA 1,150,000", "keywords": ["1,150,000", "1.15"]},
                                            {"desc": "APAC +22%", "keywords": ["22%", "22 %"]},
                                            {"desc": "AMER 980,000", "keywords": ["980,000", "980"]}]},
        "feedback_rounds": [
            "Add the total Q3 sales across all three regions.",
            "Make it shorter and sharper for the CEO — move to the lower half of the word range — but keep the total and add the EMEA YoY figure.",
        ],
        "feedback_requirements": [
            {"round": 1, "desc": "total 2,530,000", "keywords": ["2,530,000", "2.53"]},
            {"round": 2, "desc": "EMEA YoY +14%", "keywords": ["14%", "14 %"]},
        ],
        "extra_allowed": [2530000, 1150000, 980000, 400000, 14, 6, 22, 2025, 3],
        "rationale_hint": "Executive email; round 2 tension (shorten yet add EMEA YoY + keep total).",
    },
    {
        "id": "h-high-4", "difficulty": "high", "sub_class": "multi_section_report",
        "format": "multi-section report",
        "instruction": "Write a structured monthly product report for the product council.",
        "table": {"caption": "Product metrics November 2025",
                  "columns": ["Metric", "Oct", "Nov"],
                  "rows": [["DAU", 41000, 47000], ["Feature adoption", "38%", "45%"],
                           ["Crash-free rate", "99.2%", "99.6%"], ["Support tickets", 820, 690]]},
        "constraints": {"audience": "the product council", "tonality": "objective and data-led",
                        "min_words": 220, "max_words": 400,
                        "framing": "tie each metric movement to a likely cause hypothesis",
                        "required_sections": ["Engagement", "Quality", "Support", "Next steps"],
                        "required_points": [{"desc": "DAU 47,000", "keywords": ["47,000", "47000", "47k"]},
                                            {"desc": "crash-free 99.6%", "keywords": ["99.6%", "99.6 %"]},
                                            {"desc": "adoption 45%", "keywords": ["45%", "45 %"]}]},
        "feedback_rounds": [
            "Add the month-over-month DAU growth as a percentage in the Engagement section.",
            "Cut it toward the lower word bound, keep all four sections, and add the change in support tickets as an absolute number.",
        ],
        "feedback_requirements": [
            {"round": 1, "desc": "MoM DAU growth ~14.6%", "keywords": ["14.6%", "14.6 %", "15%", "14.6", "15 percent"]},
            {"round": 2, "desc": "ticket drop 130", "keywords": ["130"]},
        ],
        "extra_allowed": [41000, 38, 45, 99.2, 99.6, 820, 690, 14.6, 15, 130, 6000, 2025, 4],
        "rationale_hint": "Round 1 adds MoM DAU growth 6000/41000=14.6%; round 2 tension + ticket drop 820-690=130.",
    },
    {
        "id": "h-high-5", "difficulty": "high", "sub_class": "exec_email",
        "format": "executive email",
        "instruction": "Write an email to the board summarizing the funding-round readiness metrics and a recommendation.",
        "table": {"caption": "Funding readiness Q3 2025",
                  "columns": ["Metric", "Value"],
                  "rows": [["ARR (EUR)", 9600000], ["Net revenue retention", "118%"],
                           ["Burn multiple", 1.4], ["Runway (months)", 19]]},
        "constraints": {"audience": "the board of directors", "tonality": "confident and precise",
                        "min_words": 170, "max_words": 300,
                        "framing": "make a clear go/no-go recommendation on raising now",
                        "required_points": [{"desc": "ARR 9,600,000", "keywords": ["9,600,000", "9.6 million", "9.6m", "9.6"]},
                                            {"desc": "NRR 118%", "keywords": ["118%", "118 %"]},
                                            {"desc": "runway 19 months", "keywords": ["19 month", "19-month", "19"]}]},
        "feedback_rounds": [
            "Add the burn multiple and interpret whether it is healthy.",
            "Shorten toward the lower word bound for the board, but keep the recommendation and add the net revenue retention interpretation.",
        ],
        "feedback_requirements": [
            {"round": 1, "desc": "burn multiple 1.4", "keywords": ["1.4"]},
            {"round": 2, "desc": "NRR interpretation kept", "keywords": ["118%", "118 %", "retention"]},
        ],
        "extra_allowed": [9600000, 1.4, 19, 2025, 3],
        "rationale_hint": "Confident board email; round 2 tension (shorten yet keep recommendation + NRR interpretation).",
    },
]


def _finalize(inst: dict) -> dict:
    allowed = sorted(set(_nums_from_table(inst["table"]) + [float(x) for x in inst.get("extra_allowed", [])]))
    return {
        "id": inst["id"],
        "archetype": "H",
        "difficulty": inst["difficulty"],
        "sub_class": inst.get("sub_class"),
        "format": inst["format"],
        "instruction": inst["instruction"],
        "table": inst["table"],
        "constraints": inst["constraints"],
        "feedback_rounds": inst.get("feedback_rounds", []),
        "feedback_requirements": inst.get("feedback_requirements", []),
        "allowed_numbers": allowed,
        "rationale_hint": inst["rationale_hint"],
        "provenance": _provenance(inst.get("sub_class")),
    }


def main() -> None:
    written = 0
    for inst in INSTANCES:
        rec = _finalize(inst)
        directory = INPUT_DIR / inst["difficulty"]
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{inst['id']}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
