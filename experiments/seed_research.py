"""Curated research instances for archetype A.

Writes 15 task instances to ``data/test_inputs/a_exploratory_research/`` at
three difficulty levels (5 each). The questions are style-derived from
AssistantBench (Yoran et al., 2024) and BrowseComp (Wei et al., 2025).

The difficulty axis is the structural complexity of the research task, not the
obscurity of a single fact:
- Low: one fact, direct lookup. One Tavily snippet typically suffices.
- Medium: two facts that must be combined in the answer.
- High: three or more facts requiring ordering, joint constraints, or
  multi-entity listing.

The questions use stable historical or definitional facts so the gold answers
do not drift with the live web. Provenance is documented per instance.

Run:
    python experiments/seed_research.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_DIR = REPO / "data" / "test_inputs" / "a_exploratory_research"


def _provenance(source: str, difficulty: str) -> dict:
    return {
        "source_benchmark": source,
        "adaptation": (
            "Question style adapted from the source benchmark; specific instance curated for stable historically "
            "grounded ground truth so the answer does not drift with the live web. The structural research-and-"
            f"synthesis profile (difficulty: {difficulty}) is preserved."
        ),
        "license": "Adapted under fair use for academic research",
    }


ASSISTANT_BENCH = "AssistantBench (Yoran et al., 2024)"
BROWSECOMP = "BrowseComp (Wei et al., 2025)"

# Each row: (difficulty, n, question, gold_value, unit_label, source)
INSTANCES = [
    # ── LOW: one fact, one Tavily snippet usually suffices ──
    ("low", 1, "What is the elevation of Mount Everest in meters, using the most widely cited current measurement?", "8849", "elevation_m", ASSISTANT_BENCH),
    ("low", 2, "In what calendar year did euro banknotes and coins first enter physical circulation in the eurozone?", "2002", "year", ASSISTANT_BENCH),
    ("low", 3, "Who painted the Mona Lisa?", "Leonardo da Vinci", "person_name", ASSISTANT_BENCH),
    ("low", 4, "What is the capital city of Australia?", "Canberra", "city_name", ASSISTANT_BENCH),
    ("low", 5, "What is the chemical element symbol for gold?", "Au", "chemical_symbol", ASSISTANT_BENCH),

    # ── MEDIUM: two facts to combine ──
    ("med", 1, "What is the second-largest country in South America by total area, and what is its capital city?", "Argentina, Buenos Aires", "country_and_capital", ASSISTANT_BENCH),
    ("med", 2, "Who composed the opera 'Don Giovanni', and in what city was it first performed?", "Wolfgang Amadeus Mozart, Prague", "composer_and_city", ASSISTANT_BENCH),
    ("med", 3, "Which Roman emperor is credited with rebuilding the Pantheon in Rome as it stands today, and in approximately which century did the rebuilding take place?", "Hadrian, 2nd century", "person_and_century", ASSISTANT_BENCH),
    ("med", 4, "In what calendar year was the first iPhone released by Apple, and who was the CEO of Apple at that time?", "2007, Steve Jobs", "year_and_ceo", ASSISTANT_BENCH),
    ("med", 5, "What are the two official languages of Canada at the federal level?", "English, French", "two_languages", ASSISTANT_BENCH),

    # ── HIGH: three or more facts, with ordering, joint constraints, or listing ──
    ("high", 1, "Name the first three astronauts to walk on the surface of the Moon, in the order in which they stepped onto its surface.", "Neil Armstrong, Buzz Aldrin, Pete Conrad", "three_persons_ordered", BROWSECOMP),
    ("high", 2, "List the first three women to be awarded a Nobel Prize in any field, in chronological order of their award years.", "Marie Curie (1903), Bertha von Suttner (1905), Selma Lagerloef (1909)", "three_persons_with_years_ordered", BROWSECOMP),
    ("high", 3, "Which three countries share a land border with both Germany and France?", "Belgium, Luxembourg, Switzerland", "three_countries", BROWSECOMP),
    ("high", 4, "Name the three highest mountain peaks in the European Alps, in descending order of elevation.", "Mont Blanc, Monte Rosa (Dufourspitze), Dom", "three_peaks_ordered", BROWSECOMP),
    ("high", 5, "Name the three countries that have won the FIFA men's World Cup more than three times each.", "Brazil, Italy, Germany", "three_countries", BROWSECOMP),
]


def main() -> None:
    written = 0
    for difficulty, n, question, value, unit, source in INSTANCES:
        directory = INPUT_DIR / difficulty
        directory.mkdir(parents=True, exist_ok=True)
        instance_id = f"a-{difficulty}-{n}"
        record = {
            "id": instance_id,
            "archetype": "A",
            "difficulty": difficulty,
            "instruction": question,
            "ground_truth": {"value": value, "unit": unit},
            "provenance": _provenance(source, difficulty),
        }
        (directory / f"{instance_id}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        written += 1
    print(f"Wrote {written} instances under {INPUT_DIR.relative_to(REPO)}")
    print("Difficulty axis: low = one fact (single lookup); medium = two facts combined; high = three or more facts with ordering or listing.")
    print("Verify the gold answers manually before running validate_a.py.")


if __name__ == "__main__":
    main()
