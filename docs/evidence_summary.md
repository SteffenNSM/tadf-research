# Evidence Summary — Final Grid (TADF Phase 2)

Every number below is computed from the raw grid results under
`data/results/final/` by `experiments/analyze_evidence.py`
(`PYTHONPATH=. python experiments/analyze_evidence.py`). Grid design per
deviation D-032 (IT-053): gpt-5.4-nano 2x clean + 1x robustness, gpt-5.4-mini
2x + 1x, gpt-5.2 1x + 1x; judge frozen on gpt-5.2; temperature 0, seed 42.
Cells pool 5 clean sweeps unless a model tier is stated. Read as patterns:
per-cell n is 5-25, and the run-to-run flip rate (item 8) bounds single-run
interpretation.

## Gate evidence (decision-tree stages)

1. **G1 — Runtime-observed results determine the next step.** On the three
   designed runtime-feedback instances (f-high-1/2/5) the workflow scores
   **0/15** and the agent **13/15** — the largest paradigm gap in the grid
   (87 percentage points), invariant across all three capability tiers. The
   same workflow scores 35/60 on plan-time F instances, so the mechanism,
   not the archetype, carries the gap. Workflow traces include executing the
   explicitly prohibited recovery action (IT-047).

2. **G1 correction (supersedes reading (a) of IT-047/049).** The
   read-conditional instance f-med-2 was hypothesized to be
   workflow-feasible; the grid refutes this: workflow **1/5** vs agent
   **5/5**, including the mini and gpt-5.2 tiers. Conditional branching as
   such — not only action-outcome branching — breaks the two-stage form.
   G1 is therefore phrased over runtime-observed results generally.

3. **G2 — Codifiable, stable rules.** Archetype D: workflow **75/75 (100%)**
   at **903 ± 4 tokens** (near-deterministic cost) versus agent **60/75
   (80%)** at 5,562 ± 23. Error-direction census: **12 of 15** agent errors
   are permissive (under-escalation) — 80% sit in the dangerous direction.
   Robustness: workflow 18/18, agent 13/18.

4. **G3 — Open, chained search.** Archetype A high tier (provider errors
   excluded): workflow **14/25 (56%)** vs agent **23/25 (92%)**; on the small
   tiers 3/10 vs 9/10, on gpt-5.2 4/5 vs 5/5 — the gap shrinks from 60 to 20
   points with capability but never flips sign.

5. **G4 — Enumeration is heterogeneity-conditional, not count-conditional.**
   Nine heterogeneous reassignments (f-med-3): workflow 2/5 vs agent 5/5.
   Sixteen IDENTICAL updates (f-med-4): **5/5 for both**. Seven recipients
   requiring per-target resolution (f-med-5): **0/5 for both**. G high
   (15-18-step plans): workflow 11/25. The structured-output ceiling binds
   on argument heterogeneity, not raw count.

6. **Saturation — the third routing outcome.** H-high: workflow **1/25**,
   agent **0/25** (six-plus simultaneous constraints with rework rounds).
   B-high (three-plus fields combined across systems into one answer):
   8/25 vs 10/25, unstable for both. Neither paradigm carries these cells;
   the evidenced recommendation is task decomposition.

7. **Capability switch (stage 3).** E-high flips sign across tiers: nano
   W 5/10 vs A 7/10, mini W **9/10** vs A **5/10**, gpt-5.2 W 5/5 vs A 4/5 —
   the only sign flip in the grid; the decomposed-judgment workflow binds
   from the mid tier upward. Related capability floors: agent recovery
   absent on nano (IT-047), runbook argument-binding fails on nano (IT-051),
   spec generation brittle below mid tier (IT-043).

## Deep patterns

8. **Temperature-0 flip rate: 10.2%** (49/480 instance-paradigm pairs change
   outcome between run 1 and run 2 on nano and mini) — the quantified basis
   for the two-run discipline and for reading single runs conservatively.

9. **Tokens per SOLVED task** (clean, all cells; selection caveat: the two
   paradigms solve partly different instances): B 3,197 vs 20,515 (6.4x),
   D 903 vs 6,953 (7.7x), F 8,389 vs 23,471, G 5,890 vs 13,996, A 7,547 vs
   13,554, H 3,214 vs 6,592 — but C INVERTED (1,713 vs 1,415; chunk
   overhead) and E at parity (1,725 vs 1,722).

10. **E strict-bias correction (supersedes the absolute claim of IT-046).**
    Across 90 scored workflow artefacts: **35 false fails vs 17 missed
    fails** — a systematic 2:1 strict bias, not an exclusive error
    direction; the zero-missed-fails observation was nano-specific.

11. **Constraint-type census carries paradigm signatures (G).** Workflow
    failures concentrate on recipient resolution (`emails`: 28) with **zero**
    ordering violations (a fixed pipeline cannot emit out-of-order plans);
    the agent violates ordering 4x and spreads across categories. Failure
    classes are diagnostic of the paradigm.

12. **Over-revision decay (H agent).** Compliance by self-revision turns:
    1 turn 19/21 (90%), 2 turns 8/17 (47%), 3 turns 2/26 (8%), 4 turns 0/11
    (0%) — monotone decay (confounded with tier, since feedback rounds force
    turns; direction unambiguous). Judge-disagreement flags on 17/150 clean
    artefacts: the frozen judge misses what the deterministic compliance
    layer catches in 11% of cases.

13. **Structural reliability is symmetric.** Non-provider crashes: 3
    workflow schema-validation crashes (SearchPlan/ActionPlan) vs 3 agent
    failures including 2 recursion-limit overflows. Neither paradigm is
    infrastructurally safer; they are differently fragile.
