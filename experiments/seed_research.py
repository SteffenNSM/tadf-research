"""Curated research instances for archetype A: Exploratory Research and Synthesis.

Writes 15 task instances to ``data/test_inputs/a_exploratory_research/`` at
three difficulty levels (5 each). Questions are style-derived from
AssistantBench (Yoran et al., 2024) and BrowseComp (Wei et al., 2025); the
specific facts are author-curated so the gold answers are stable and verifiable.

Difficulty axis (revised): the STRUCTURE of the retrieval, not the obscurity of
one fact.
- Low:  two distinct sources whose facts are combined, retrievable in parallel.
- Med:  three distinct sources aggregated in parallel.
- High: runtime-dependent chains with a SINGLE-VALUE endpoint. The question
        asks only for the final fact (a stadium, a stadium address, a town's
        mayor, a country's leader), but reaching it requires the chain: the
        town of a company, then that town's mayor; the 2. Bundesliga winner,
        then its stadium, then the address. A plan-upfront workflow cannot fill
        the later queries because it does not yet know the intermediate result;
        only the agent can chain search-by-search. The single-value endpoint
        removes the compound-answer / early-stopping confound: the agent cannot
        "finish" on an intermediate part. The bridge entities are obscure enough
        that a broad query does not surface the final fact (except a-high-4,
        kept as a deliberately weaker-binding control the workflow may
        brute-force).

Memorization: every instance must be NON-memorized on the strongest model used
(no-tool check), otherwise it measures the model's parametric knowledge rather
than the retrieval paradigms. The check is run per model on the author's
machine; each instance's provenance carries the pending flag.

Run:
    python experiments/seed_research.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "a_exploratory_research"

BENCHMARK_REF = "AssistantBench (Yoran et al., 2024); BrowseComp (Wei et al., 2025)"


def _prov(construction: str, axis: str, domain: str, sources: list[str], note: str = "") -> dict:
    return {
        "source_benchmark": BENCHMARK_REF,
        "construction_method": construction,
        "difficulty_axis": axis,
        "domain": domain,
        "sources": sources,
        "verification": {
            "memorization_no_tool": "pending (must be non-memorized on the strongest model used)",
            "retrievable_via_tavily": "pending (confirm on the run)",
            "gold_verified": "author-supplied; confirm on the run",
        },
        "note": note,
        "license": "Original work by the author (task design)",
    }


LOW_AXIS = "two distinct sources combined, retrievable in parallel"
MID_AXIS = "three distinct sources aggregated in parallel"
HIGH_AXIS = "runtime-dependent chain: each search's result is the input to the next (a plan-upfront workflow cannot chain)"


INSTANCES: list[dict] = [
    # ── LOW: two distinct sources, parallel ──
    {
        "id": "a-low-1",
        "difficulty": "low",
        "instruction": "Which company was founded earlier: Multivac (headquartered in Wolfertschwenden) or Brueckner Maschinenbau (headquartered in Siegsdorf)? Answer with the company name.",
        "ground_truth": {"value": "Brueckner Maschinenbau", "unit": "company_name"},
        "provenance": _prov(
            "Two founding years (Brueckner 1960, Multivac 1961) retrieved and compared.",
            LOW_AXIS, "SME hidden champions",
            ["https://de.wikipedia.org/wiki/Br%C3%BCckner_Maschinenbau", "https://de.wikipedia.org/wiki/Multivac"],
            "Reused from the prior corpus (a-med-2).",
        ),
    },
    {
        "id": "a-low-2",
        "difficulty": "low",
        "instruction": "What is the name of the founder of the Boston Consulting Group (BCG), and what is the name of the founder of Heidelberg Materials (formerly HeidelbergCement)?",
        "ground_truth": {"value": "Bruce Doolin Henderson; Johann Philipp Schifferdecker", "unit": "two_founders"},
        "provenance": _prov(
            "Two independent founder facts combined in parallel.",
            LOW_AXIS, "corporate history",
            ["https://en.wikipedia.org/wiki/Boston_Consulting_Group", "https://en.wikipedia.org/wiki/Heidelberg_Materials"],
        ),
    },
    {
        "id": "a-low-3",
        "difficulty": "low",
        "instruction": "In which year was the Kamener Kreuz motorway interchange opened, and at which motorway interchange does the German Bundesautobahn 2 (A 2) begin?",
        "ground_truth": {"value": "1937; Kreuz Oberhausen", "unit": "year_and_interchange"},
        "provenance": _prov(
            "Two independent infrastructure facts combined in parallel.",
            LOW_AXIS, "German road infrastructure",
            ["https://de.wikipedia.org/wiki/Kamener_Kreuz", "https://de.wikipedia.org/wiki/Bundesautobahn_2"],
        ),
    },
    {
        "id": "a-low-4",
        "difficulty": "low",
        "instruction": "In the German town of Harsewinkel, an agricultural-machinery company with a doubled letter 'A' in its name is headquartered. What is the company, and what is the name of the important monastery in that town?",
        "ground_truth": {"value": "CLAAS; Kloster Marienfeld", "unit": "company_and_monastery"},
        "provenance": _prov(
            "Two parallel facts about Harsewinkel (town given in the question): the company (CLAAS) and the town's notable monastery (Kloster Marienfeld, in the Marienfeld district). Neither fact depends on the other.",
            LOW_AXIS, "SME hidden champion + local history",
            ["https://de.wikipedia.org/wiki/Claas", "https://de.wikipedia.org/wiki/Kloster_Marienfeld"],
        ),
    },
    {
        "id": "a-low-5",
        "difficulty": "low",
        "instruction": "Which national team was knocked out by Italy in the semi-final of UEFA Euro 2012, and who was that team's starting (first-choice) goalkeeper at the tournament?",
        "ground_truth": {"value": "Germany; Manuel Neuer", "unit": "team_and_goalkeeper"},
        "provenance": _prov(
            "Result plus roster fact, two parallel lookups.",
            LOW_AXIS, "football history",
            ["https://en.wikipedia.org/wiki/UEFA_Euro_2012", "https://en.wikipedia.org/wiki/Germany_national_football_team"],
            "Reused from the prior corpus (a-med-4); Neuer confirmed non-memorized on gpt-5.4-nano (IT-039).",
        ),
    },
    # ── MED: three distinct sources, parallel ──
    {
        "id": "a-med-1",
        "difficulty": "med",
        "instruction": "By straight-line distance, which two of these three sites lie closest to each other: Bauhaus Dessau, Naumburg Cathedral, or the Wartburg? Answer with the two site names.",
        "ground_truth": {"value": "Bauhaus Dessau and Naumburg Cathedral", "unit": "site_pair"},
        "provenance": _prov(
            "Three site locations retrieved; the closest pair is selected. Parallel, no runtime dependency.",
            MID_AXIS, "German cultural geography",
            ["https://de.wikipedia.org/wiki/Bauhaus_Dessau", "https://de.wikipedia.org/wiki/Naumburger_Dom", "https://de.wikipedia.org/wiki/Wartburg"],
            "Reused from the prior corpus (a-high-3).",
        ),
    },
    {
        "id": "a-med-2",
        "difficulty": "med",
        "instruction": "Consider the clubs relegated from the German Bundesliga at the end of the 2022/23 season and at the end of the 2023/24 season. Of those clubs, which has the most members? Answer with the club name.",
        "ground_truth": {"value": "FC Schalke 04", "unit": "club_name"},
        "provenance": _prov(
            "Relegated clubs across two seasons plus a membership comparison, parallel aggregation.",
            MID_AXIS, "football",
            ["https://de.wikipedia.org/wiki/Bundesliga_2022/23", "https://de.wikipedia.org/wiki/Bundesliga_2023/24", "https://de.wikipedia.org/wiki/FC_Schalke_04"],
            "Reused from the prior corpus (a-high-4).",
        ),
    },
    {
        "id": "a-med-3",
        "difficulty": "med",
        "instruction": "On what dates were the companies Toyota, Volkswagen, and Porsche founded? Give the founding date of each.",
        "ground_truth": {"value": "Toyota: 28 August 1937; Volkswagen: 28 May 1937; Porsche: 25 April 1931", "unit": "three_founding_dates"},
        "provenance": _prov(
            "Three independent founding dates aggregated in parallel.",
            MID_AXIS, "automotive corporate history",
            ["https://en.wikipedia.org/wiki/Toyota", "https://en.wikipedia.org/wiki/Volkswagen", "https://en.wikipedia.org/wiki/Porsche"],
        ),
    },
    {
        "id": "a-med-4",
        "difficulty": "med",
        "instruction": "Which club won the German Bundesliga in each of these three seasons: 2008/09, 2017/18, and 1994/95?",
        "ground_truth": {"value": "VfL Wolfsburg; FC Bayern München; Borussia Dortmund", "unit": "three_champions"},
        "provenance": _prov(
            "Three season champions retrieved in parallel.",
            MID_AXIS, "football history",
            ["https://de.wikipedia.org/wiki/Fu%C3%9Fball-Bundesliga"],
        ),
    },
    {
        "id": "a-med-5",
        "difficulty": "med",
        "instruction": "What are the street names and building numbers of the headquarters of RWE AG, E.ON SE, and the BMW Group (Konzernzentrale)?",
        "ground_truth": {"value": "RWE Platz 1; Brüsseler Platz 1; Petuelring 130", "unit": "three_streets"},
        "provenance": _prov(
            "Three corporate-headquarters streets aggregated in parallel (street only, no postcode/city, to reduce gold-format noise).",
            MID_AXIS, "German corporates",
            ["https://en.wikipedia.org/wiki/RWE", "https://en.wikipedia.org/wiki/E.ON", "https://en.wikipedia.org/wiki/BMW"],
        ),
    },
    # ── HIGH: runtime-dependent chains (result of hop 1 feeds hop 2) ──
    {
        "id": "a-high-1",
        "difficulty": "high",
        "instruction": "The Winkelmann Group is headquartered in a German town in Westphalia (Muensterland). A small river whose name begins with W (a tributary of the Ems, NOT the well-known Weser) flows through that town, and the town's stadium is named after that river. What is the name of that stadium?",
        "ground_truth": {"value": "Wersestadion", "unit": "stadium"},
        "provenance": _prov(
            "Chain: Winkelmann Group -> town Ahlen -> river Werse -> Wersestadion. Single-value endpoint (the stadium); the stadium name needs the town and river, which need the company.",
            HIGH_AXIS, "SME hidden champion + local geography",
            ["https://de.wikipedia.org/wiki/Winkelmann_Group", "https://de.wikipedia.org/wiki/Wersestadion"],
            "Reused from the prior corpus (a-high-1), converted to a single-value endpoint.",
        ),
    },
    {
        "id": "a-high-2",
        "difficulty": "high",
        "instruction": "Who was the mayor (Bürgermeister) in 2016 of the German town in which the company KALDEWEI (Franz Kaldewei GmbH & Co. KG) is headquartered?",
        "ground_truth": {"value": "Alexander Berger", "unit": "mayor"},
        "provenance": _prov(
            "Chain: KALDEWEI -> town Ahlen -> Ahlen's 2016 mayor (Alexander Berger). Single-value endpoint; the mayor needs the town, which needs the company. Obscure final fact. The honorific 'Dr.' is optional; the semantic judge accepts the name with or without the title.",
            HIGH_AXIS, "SME hidden champion + local politics",
            ["https://de.wikipedia.org/wiki/Kaldewei", "https://de.wikipedia.org/wiki/Ahlen"],
        ),
    },
    {
        "id": "a-high-3",
        "difficulty": "high",
        "instruction": "What is the full street address of the home stadium of the team that won the German 2. Bundesliga in 1997?",
        "ground_truth": {"value": "Fritz-Walter-Straße 1, 67663 Kaiserslautern", "unit": "stadium_address"},
        "provenance": _prov(
            "Chain: 2. Bundesliga 1996/97 champion -> 1. FC Kaiserslautern -> Fritz-Walter-Stadion -> its address. Single-value endpoint; the address needs the club and stadium.",
            HIGH_AXIS, "football + venue address",
            ["https://de.wikipedia.org/wiki/2._Fu%C3%9Fball-Bundesliga_1996/97", "https://de.wikipedia.org/wiki/Fritz-Walter-Stadion"],
        ),
    },
    {
        "id": "a-high-4",
        "difficulty": "high",
        "instruction": "What is the name of the iconic natural swimming pool in the U.S. city that is home to the university of the Texas Longhorns?",
        "ground_truth": {"value": "Barton Springs Pool", "unit": "natural_pool"},
        "provenance": _prov(
            "Chain: Texas Longhorns -> University of Texas at Austin -> Austin -> Barton Springs Pool. Single-value endpoint; the pool needs the city, which needs identifying the team's university.",
            HIGH_AXIS, "US sports + local geography",
            ["https://en.wikipedia.org/wiki/Texas_Longhorns", "https://en.wikipedia.org/wiki/Barton_Springs_Pool"],
        ),
    },
    {
        "id": "a-high-5",
        "difficulty": "high",
        "instruction": "Who was the mayor (Bürgermeister) in 2022 of the town in which VEKA AG is headquartered?",
        "ground_truth": {"value": "Katrin Reuscher", "unit": "mayor"},
        "provenance": _prov(
            "Chain: VEKA AG -> town Sendenhorst -> the town's 2022 mayor. Single-value endpoint; obscure final fact, needs the town.",
            HIGH_AXIS, "SME hidden champion + local politics",
            ["https://de.wikipedia.org/wiki/Veka", "https://de.wikipedia.org/wiki/Sendenhorst"],
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
            "archetype": "A",
            "difficulty": inst["difficulty"],
            "instruction": inst["instruction"],
            "ground_truth": inst["ground_truth"],
            "provenance": inst["provenance"],
        }
        (directory / f"{inst['id']}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False)
        )
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
