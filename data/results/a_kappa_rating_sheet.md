# A Judge Validation — Blind Human Rating Sheet

Decide, for each of the six candidate answers, whether it is **correct (1)** or **incorrect (0)** against the gold answer. Rate each on its own; do not try to guess which system produced it or look at any model verdict first (Cohen's kappa / Gwet's AC1, threshold 0.6).

## Standard

Mark each candidate answer **correct (1)** or **incorrect (0)** against the gold answer, using the same lenient standard the automated judge uses:
- Accept different wording, capitalization, units (after sensible conversion), and numeric precision of the SAME measurement (e.g. 8848, 8848.86, 8849 are the same elevation).
- For list answers, ALL required entities must be present; if the question specifies an order (chronological, descending by quantity, etc.), the order must match.
- Mark incorrect if it states a different fact, names a different entity, gives a different year/identifier, misses a required list entity, violates a required order, expresses uncertainty, or omits the answer.
Rate independently, before looking at any model verdict.

---

## Answer A

**Question:** Name the three highest mountain peaks in the European Alps, in descending order of elevation.

**Gold answer:** Mont Blanc, Monte Rosa (Dufourspitze), Dom  _(unit: three_peaks_ordered)_

**Candidate answer:**

> Mont Blanc; Dufourspitze (Monte Rosa); Liskamm

**Your verdict (1 = correct, 0 = incorrect):** ____

---

## Answer B

**Question:** What is the elevation of Mount Everest in meters, using the most widely cited current measurement?

**Gold answer:** 8849  _(unit: elevation_m)_

**Candidate answer:**

> 8,848.86 meters

**Your verdict (1 = correct, 0 = incorrect):** ____

---

## Answer C

**Question:** Name the three highest mountain peaks in the European Alps, in descending order of elevation.

**Gold answer:** Mont Blanc, Monte Rosa (Dufourspitze), Dom  _(unit: three_peaks_ordered)_

**Candidate answer:**

> Mont Blanc; Dufourspitze; Dom

**Your verdict (1 = correct, 0 = incorrect):** ____

---

## Answer D

**Question:** What is the second-largest country in South America by total area, and what is its capital city?

**Gold answer:** Argentina, Buenos Aires  _(unit: country_and_capital)_

**Candidate answer:**

> Argentina — Buenos Aires

**Your verdict (1 = correct, 0 = incorrect):** ____

---

## Answer E

**Question:** What is the elevation of Mount Everest in meters, using the most widely cited current measurement?

**Gold answer:** 8849  _(unit: elevation_m)_

**Candidate answer:**

> 8,848.86 m

**Your verdict (1 = correct, 0 = incorrect):** ____

---

## Answer F

**Question:** What is the second-largest country in South America by total area, and what is its capital city?

**Gold answer:** Argentina, Buenos Aires  _(unit: country_and_capital)_

**Candidate answer:**

> Argentina — Buenos Aires

**Your verdict (1 = correct, 0 = incorrect):** ____

---
