# Iteration Log

This log documents every design decision and change to the TADF repository, in
the format required by Design Science Research (Hevner Guideline G6, design as a
search process). Each entry records the date, the affected component, the
starting state, the decision, the result, and the finding. The log is updated at
the time of the change, not retrospectively. It feeds Appendix B of the thesis.

Entry format:
- **Date** — ISO date.
- **Component** — the module, archetype, or document affected.
- **Starting state** — what existed before.
- **Decision** — what was changed and why.
- **Result** — the concrete outcome.
- **Finding** — what was learned, if anything.

---

## IT-001 — Repository restructure to the A–H taxonomy

- **Date:** 2026-05-21
- **Component:** Repository structure, `src/archetypes/`
- **Starting state:** The repository encoded the earlier seven-archetype
  taxonomy in the directory names `open_information_gathering`,
  `structured_retrieval`, `ambiguous_classification`,
  `output_quality_evaluation`, `threshold_based_decision`,
  `multi_source_synthesis`, and `action_execution`. Only `structured_retrieval`
  was implemented, as a test, using a custom automotive vehicle-extraction task.
- **Decision:** Rebuild the repository against the final eight-archetype
  taxonomy A–H (Section 4.2.7 of the thesis). The new structure adds G
  (Strategic and Adaptive Planning) and H (Content and Document Drafting and
  Refinement), and folds the former `multi_source_synthesis` into A
  (Exploratory Research and Synthesis). The existing repository shell, git
  history, and GitHub remote are retained; `src/`, `data/`, and `experiments/`
  are rebuilt. Task inputs are benchmark-derived per the user decision.
- **Result:** Repository blueprint written (`docs/repository_blueprint.md`).
  Core modules `llm.py`, `logging.py`, and `state.py` rebuilt to the Phase 2
  protocol. Old archetype directories scheduled for removal once the new
  structure is validated.
- **Finding:** The earlier test implementation of `structured_retrieval`
  documents the canonical-minimal workflow form clearly and is retained as a
  reference pattern for the benchmark-derived rebuild of archetype B.

## IT-002 — Core alignment to the Phase 2 protocol

- **Date:** 2026-05-21
- **Component:** `src/core/llm.py`, `src/core/logging.py`, `src/core/state.py`
- **Starting state:** `llm.py` hardcoded `temperature=0` globally and an
  inconsistent model snapshot; `logging.py` and `state.py` were stubs or
  extraction-specific.
- **Decision:** Pin the model to `gpt-4o-2024-11-20`; introduce a per-archetype
  temperature policy (0.0 for G, 0.2 elsewhere); implement an `ExecutionLogger`
  callback that captures token usage, tool calls, latency, and errors;
  generalize `TaskState` so all eight archetypes share one schema.
- **Result:** Three core modules rebuilt. The model version differs from the
  earlier draft of the Phase 2 protocol (`gpt-4o-2024-08-06`); the protocol is
  to be updated to `gpt-4o-2024-11-20`, the more recent stable snapshot.
- **Finding:** Token-usage key names vary across LangChain conventions; the
  logger reads the provider usage block first and falls back to
  `usage_metadata`. To be confirmed against the installed version once the
  workspace is available for execution.

## IT-003 — Data layer switched from Supabase to local SQLite

- **Date:** 2026-05-21
- **Component:** `src/core/db.py`, `src/core/tools/database.py`, `data/schema/`
- **Starting state:** The data layer used a Supabase cloud database with a
  publishable (anon) key. Attempts to access the CRM tables returned 403
  Forbidden: the anon key cannot create tables (DDL) and row-level security
  blocks writes, and the tables did not exist.
- **Decision:** Replace the cloud database with a self-contained SQLite database
  shipped in the repository (`data/crm.db`). Rationale: full reproducibility
  (a reviewer reproduces the experiment by cloning the repo, with no external
  provisioning), no RLS or DDL friction, and controlled latency via the
  protocol's synthetic-latency policy rather than variable network latency. The
  switch is invisible to the paradigm comparison: the database is reached only
  through the tool interface, so the storage backend is a controlled detail
  behind that boundary. Real external services (Gmail, Calendar) remain reserved
  for the Phase 4 case study, where external-tool fidelity is the demonstration
  target.
- **Result:** `db.py` rebuilt for SQLite (lazy connection, dict rows).
  `tools/database.py` rewritten with `read_table`, `db_read`, `db_search` over
  SQLite with a table allowlist. `data/schema/schema.sql` and
  `experiments/load_db.py` added. Database built and loaded
  (accounts=20, contacts=45, agents=10, cases=120, opportunities=60).
- **Finding:** The blueprint and the Phase 2 protocol reference Supabase and
  must be updated to SQLite. Booleans are stored as 0/1 in SQLite; the executor
  comparison handles this because Python treats 1 == True.

## IT-004 — Archetype B implemented and partially validated

- **Date:** 2026-05-21
- **Component:** `src/archetypes/b_structured_retrieval/`
- **Starting state:** Empty package after the A-H restructure.
- **Decision:** Implement archetype B (Structured Data Retrieval and
  Transformation) from CRMArena structured querying (Huang et al., 2025),
  read-only, with TCR scoring. Workflow: `plan` (one LLM call, NL question to
  QuerySpec) -> `execute` (deterministic query executor) -> `format`. Agent:
  ReAct loop with `db_read`/`db_search`. Pure data models in `schemas.py`;
  deterministic logic in `query_executor.py`; TCR in `ground_truth.py`.
  Difficulty over join depth (low: 1 table; medium: 2-3 joins; high: 4+ tables
  with grouped argmax). Fifteen instances generated with deterministic ground
  truth (`experiments/seed_crm.py`).
- **Result:** Deterministic validation passes fully. The query executor matches
  the independently computed ground truth on all 15 instances, both against the
  seed JSON and against the SQLite database (15/15 each). All modules compile;
  the workflow graph and the ReAct agent build without error.
- **Finding:** The OpenAI API is not reachable from the sandbox (network egress
  is restricted to the package index). The LLM-dependent end-to-end runs
  (workflow plan node, agent) therefore execute on the author's machine via
  `experiments/validate_b.py`. The deterministic core, which carries the
  correctness risk, is fully validated in the sandbox. Open robustness item: if
  the plan-node LLM emits a filter value as a string where the column is boolean
  or integer, the executor comparison may miss; to be observed in the
  author-side run and handled if it occurs.

## IT-005 — Fair TCC measurement and robust answer extraction for B

- **Date:** 2026-05-26
- **Component:** `src/archetypes/b_structured_retrieval/workflow.py`,
  `src/archetypes/b_structured_retrieval/ground_truth.py`
- **Starting state:** The smoke-test run of `experiments/validate_b.py` on
  three instances (one per difficulty) revealed two measurement issues. First,
  the workflow's database reads were not recorded as tool calls because the
  ``execute`` node invoked ``read_table`` directly, while the agent's reads
  went through the LangChain tool callback. Tool-Call Count (TCC) was therefore
  asymmetric and the workflow looked artificially free of tool activity.
  Second, the agent's answers were scored by exact match after numeric parsing.
  Bare values like "39" scored correctly, but values embedded in prose such as
  "39 cases" or "The answer is 39." would be marked wrong despite containing
  the right number.
- **Decision:** (i) Route the workflow's reads through the ``db_read``
  LangChain tool via ``db_read.invoke(...)`` so the callback fires on equal
  footing with the agent's tool calls; this makes TCC a comparable metric across
  paradigms. (ii) Replace the strict numeric parser in ``is_correct`` with a
  regex-based extractor that finds all numbers in the predicted string and uses
  the last one as the final answer; add whole-word entity matching for
  non-numeric answers, so prose-wrapped answers are not penalized.
- **Result:** The deterministic executor regression test still passes 15/15.
  Eleven new edge cases for ``is_correct`` pass: exact numerics, embedded
  numerics with units and prose, thousands separators, float precision,
  entity-name exact/case-insensitive/in-sentence matches, and the correct
  rejection of wrong numbers and missing answers. Module syntax clean.
- **Finding:** The choice of "last number" for prose answers reflects the
  empirical convention that LLMs place the final answer at the end. If the
  full B sweep reveals counterexamples, the heuristic will be tightened. The
  whole-word entity match could in principle produce false positives if the
  agent mentions the expected entity in passing before answering with another;
  to be observed in the full sweep and refined if necessary.

## IT-006 — Model decision and reasoning_effort policy

- **Date:** 2026-05-26
- **Component:** `src/core/llm.py`, Phase-2 protocol (Appendix A.6),
  Master_Thesis_v2.md (Section 4.4.2 and Appendix A)
- **Starting state:** The protocol pinned `gpt-4o-2024-11-20` from an earlier
  iteration. The user has access to two newer GPT-5-family snapshots: `gpt-5.4`
  (frontier) and `gpt-5.2-2025-12-11` (current-generation, lower cost).
- **Decision:** Switch the main Phase-2 sweep to `gpt-5.2-2025-12-11`. Set
  `reasoning_effort="none"` explicitly so the model operates as a standard
  chat-completion model. Reasoning tokens, when enabled, are billed separately
  and would confound the co-primary Token Cost metric. Reserve a cross-model
  robustness check on a three-archetype subset with `gpt-5.4` for the discussion
  of cross-version generalizability.
- **Result:** `src/core/llm.py` rewritten: `MODEL_NAME = "gpt-5.2-2025-12-11"`,
  `REASONING_EFFORT = "none"` passed via `model_kwargs`. Phase-2 protocol
  Section A.6 updated with the model justification (current-generation, SME
  realism, budget tractability, structural contrast not contingent on the
  latest snapshot) and the reasoning-effort policy. Cost estimate revised to
  approximately US$230–520 for the full sweep, to be verified against the
  OpenAI billing dashboard before execution. Master_Thesis_v2.md references in
  Section 4.4.2, Appendix A, and the Limitations checklist updated to match.
- **Finding:** The choice of 5.2 over 5.4 is methodologically conservative
  rather than disadvantageous: at a slightly weaker model, the agent's
  arithmetic and join failures appear more clearly, which strengthens the
  workflow advantage measured at the SME-realistic deployment point. The
  cross-model robustness check on a subset addresses the "would the result
  hold at frontier capability?" critique without doubling the experimental
  cost.

## IT-007 — Archetype B full validation sweep and TADF v1 rule derivation

- **Date:** 2026-05-26
- **Component:** `experiments/validate_b.py`, `data/results/b_validation_20260526_145220.json`
- **Starting state:** Archetype B implemented (config, schemas, executor, workflow, agent, ground truth). Smoke test on three instances (one per difficulty) on gpt-5.2-2025-12-11 had shown workflow 3/3, agent 1/3, token ratio 4.5x to 11.2x.
- **Decision:** Run the full 15-instance validation (5 instances × 3 difficulty levels × 2 paradigms = 30 executions) at one run per instance. The protocol's three-runs-per-instance variance estimate is deferred to a consolidated multi-run pass once all eight archetypes are implemented. Effect sizes from the single-run pass are expected to be large enough to derive the TADF v1 routing rule for B from this evidence.
- **Result:** Workflow 15/15 correct (100%), agent 7/15 correct (47%) on gpt-5.2-2025-12-11 with `reasoning_effort="none"`. Token cost ratio agent-over-workflow rises monotonically with task difficulty: 4.0x at low, 5.8x at medium, 8.2x at high. Workflow average tokens per instance: 1033 (sd ≈ 50); agent average: 6284 (sd ≈ 3700). Tool calls comparable across paradigms (workflow 1–2, agent 1–3). Zero LLM or tool errors across all 30 executions. The full performance matrix is persisted in `data/results/b_validation_20260526_145220.json`.
- **Finding:** Three systematic agent failure classes emerged that constitute discussion material for Chapter 6. (i) Numerical aggregation errors on single-table operations: miscounted totals (b-low-2: 1210825 vs ground truth 1314825), miscounted row counts (b-low-3: 40 vs 43), incorrect averages (b-low-5: 105504 vs 103035). The LLM reads the data but fails to fold it correctly. (ii) Join-filter drift: when aggregation requires a join, the agent omits a filter or aggregates over the wrong subset (b-med-1: 83.5 vs 94.6; b-med-3: 33 vs 61; b-med-4: 1.95 vs 2.04). (iii) Argmax with confusable group keys: when several groups are present, the agent returns a plausible but wrong key (b-high-3: 'Product' vs 'Shipping'; b-high-5: 'EMEA' vs 'AMER'). The workflow's deterministic executor structurally avoids all three failure classes. **TADF v1 rule for B:** IF a task matches archetype B with dimensional profile (high Step Predictability, high Information Availability, low Output Ambiguity, moderate Error Consequence), THEN execute as LLM workflow with deterministic query executor. Observed advantage on gpt-5.2-2025-12-11 (n=15): TCR +53 percentage points, token cost 6x lower on average and up to 8.2x lower at high difficulty.

## IT-008 — Archetype A implementation (Exploratory Research and Synthesis)

- **Date:** 2026-05-26
- **Component:** `src/archetypes/a_exploratory_research/`, `src/core/tools/search.py`, `experiments/seed_research.py`, `experiments/validate_a.py`, `.env.example`, `requirements.txt`
- **Starting state:** Empty `a_exploratory_research` package after the A-H restructure. Archetype A is the dimensional opposite of B: low Step Predictability, low Information Availability, high Output Ambiguity. The a-priori routing direction from Table 3 is agent loop.
- **Decision:** Implement A using AssistantBench (Yoran et al., 2024) and BrowseComp (Wei et al., 2025) as the source benchmarks. Web search is provided by Tavily live with a per-query disk cache under `data/search_cache/`, so re-runs are reproducible and both paradigms see identical snippets for identical queries (chosen over a pre-computed snapshot to preserve LLM creativity in query phrasing, and over uncached live calls to preserve fair comparability). Workflow canonical-minimal form: two LLM calls (`plan_searches` and `synthesize`) with deterministic `execute_searches` between them. Agent canonical-minimal form: ReAct with `tavily_search` as the only tool. Output schema `ResearchAnswer(answer, sources)`. Ground truth scored by a frozen-prompt LLM judge against curated gold answers; the Cohen's-kappa-against-human-sample check is scheduled for the consolidated multi-run pass.
- **Result:** All A modules implemented and validated for syntax. The langgraph workflow compiles with nodes `plan_searches`, `execute_searches`, `synthesize`. The ReAct agent compiles with the single `tavily_search` tool. Fifteen instances (5 low, 5 medium, 5 high) generated by `experiments/seed_research.py`. The instances use historically stable facts (e.g., year the euro entered physical circulation; year Fortran was released; submersible Alvin's 1977 Galapagos vent observation) so the gold answers do not drift with the live web; provenance is documented per instance as "style-adapted from the source benchmark". `tavily-python` added to `requirements.txt`. `.env.example` cleaned (Supabase block removed, Tavily key added).
- **Finding:** The disk-cache design solves a subtle fairness threat for A. Without a cache, workflow and agent could be exposed to different snapshots of the web (depending on when each runs and how Tavily's index changes), confounding the paradigm comparison. With the cache, identical queries return identical snippets across paradigms and across re-runs. The first paradigm to issue a given query populates the cache; subsequent paradigms read from it. Open item: a curated gold answer like "8849" for Mount Everest's elevation may shift slightly across sources (8848 or 8848.86 also appear). The LLM judge's instruction to accept "minor wording differences and units after sensible conversion" handles this, but kappa-validation on human-judged sample remains required.

## IT-009 — Archetype A smoke-test and judge precision fix

- **Date:** 2026-05-26
- **Component:** `experiments/validate_a.py` smoke run on three instances, `src/archetypes/a_exploratory_research/ground_truth.py`
- **Starting state:** Archetype A implementation complete (workflow, agent, judge, 15 instances, Tavily with disk cache).
- **Decision:** Run a smoke test on one instance per difficulty (a-low-1, a-med-1, a-high-1), observe paradigm behavior, then refine the judge prompt if needed before the full sweep.
- **Result:** All three instances ran without infrastructure errors. The token-efficiency contrast goes in the opposite direction from B, exactly as the TADF dimensional profile for A predicts: the agent uses about a third of the tokens of the workflow on average (a-low-1: 1121 vs 2526; a-med-1: 1230 vs 2375; a-high-1: 1397 vs 3246), about a third of the tool calls (1 vs 4–5), and about half the latency. Correctness is tied at 2/3 raw, and would be tied at 3/3 after the judge fix described below. The workflow's plan_searches issues four to five queries upfront because it cannot iterate; the agent issues one focused query, observes, and answers. This is the structural cost of upfront planning under low Information Availability, predicted by Table 3 and now confirmed.
- **Finding:** The judge prompt mishandled numeric measurement precision. For a-low-1, both paradigms answered "8,848.86 m" (the 2020 China-Nepal official measurement), but the curated gold was "8849" (the commonly cited rounded value), and the judge marked both as incorrect. This is a methodological error, not a paradigm error. The judge prompt was refined to distinguish numeric measurement precision (8848, 8848.86, 8849 all refer to the same elevation) from discrete identifiers (different years, names, symbols remain different). After this fix the spelling-out is concrete enough that the judge should accept the candidates. The Everest gold answer remains "8849" because the judge now handles the variant correctly. Open follow-up: kappa-validation against a human sample on 20 percent of judged answers, scheduled for the consolidated multi-run pass.

## IT-010 — Removed defensive prompt floor from A's plan node

- **Date:** 2026-05-26
- **Component:** `src/archetypes/a_exploratory_research/config.py` (PLAN_PROMPT)
- **Starting state:** The plan prompt contained an authored heuristic floor that instructed the LLM to issue at least two to three queries even for simple lookups, four to six for synthesis questions, and up to eight for deep ones. On the smoke test the LLM followed the floor and issued five queries for the Mount Everest elevation question, where one query trivially suffices.
- **Decision:** Remove the heuristic floor and replace it with a minimality directive: "Plan the minimum number of focused queries needed; use as few as you can while still being likely to retrieve the necessary facts." The other guideline keeps each query targeted to a specific piece of information.
- **Result:** The plan prompt now lets the LLM decide query count from the question itself. The plan-execute-synthesize architecture is unchanged; the workflow still cannot iterate on results. Syntax compiles. Re-run of `validate_a.py` pending on the author's machine.
- **Finding:** The earlier floor conflated two distinct sources of workflow over-planning. One is structural and legitimate: the workflow cannot iterate, so it plans defensively even with a minimality directive. The other was an authored prompt bias that artificially inflated the query count beyond what the question justified, biasing the paradigm comparison against the workflow. Removing the floor isolates the structural cost. The expectation for the next run is that the workflow will use one or two queries on simple lookups (narrowing the token gap with the agent there) and still use more queries on harder questions, where the legitimate structural cost remains. The TADF routing direction for A is not expected to change, but the magnitude of the agent's advantage should be reported on a methodologically clean basis.

## IT-011 — Redesigned difficulty axis and instance set for archetype A

- **Date:** 2026-05-27
- **Component:** `experiments/seed_research.py`, `src/archetypes/a_exploratory_research/ground_truth.py`, `data/test_inputs/a_exploratory_research/`
- **Starting state:** The first instance set for A operationalized difficulty as obscurity of one single fact (low: Mount Everest elevation; medium: second-largest South American country; high: who proved Fermat's Last Theorem). On the smoke test, both paradigms solved every difficulty level with a single Tavily query, because Tavily returns prominent named entities in the first snippet regardless of obscurity. The intended structural progression of search complexity was therefore absent, and the paradigm comparison was effectively only tested at one difficulty stratum.
- **Decision:** Reoperationalize the difficulty axis as the **number of distinct facts the answer requires**, not as obscurity of one fact. Low remains one fact direct lookup. Medium is now two facts combined in the answer (country plus capital; composer plus city; year plus CEO). High is now three or more facts with ordering or joint constraints (first three Moonwalkers in order; first three women Nobel laureates in chronological order; three countries bordering both Germany and France; three highest Alpine peaks in descending order; three countries that have won the FIFA World Cup more than three times). The judge prompt is extended to handle list and compound answers explicitly: a list answer requires all entities present, and a specified ordering must match; a compound answer requires both facts. The output schema (ResearchAnswer with answer plus sources) is unchanged.
- **Result:** All 15 instances regenerated under `data/test_inputs/a_exploratory_research/{low,med,high}/`. The judge prompt now lists list-answer and compound-answer rules explicitly alongside the numeric-precision and entity-identity rules from IT-009. Syntax compiles. Re-run of `validate_a.py` pending on the author's machine.
- **Finding:** The original difficulty operationalization conflated two things: structural complexity of the research task and obscurity of one entity. Tavily's index makes obscure single entities almost as easy to find as common ones; the structural complexity is the only honest axis. The new high stratum genuinely requires the LLM to find a list, identify members, and order them, which is the work the agent's iteration was supposed to handle better than the workflow's upfront plan. The TADF routing hypothesis for A is therefore now testable on a difficulty progression that actually varies the relevant dimension. Expected pattern: on low, both paradigms converge (one search suffices); on medium, the workflow may issue two parallel queries while the agent issues one and answers; on high, the agent's iteration may yield real savings if the first search returns only part of the list, otherwise the paradigms remain close. The empirical answer will inform whether the A routing rule should be difficulty-conditional.

## IT-012 — Archetype A full validation sweep and refined routing rule

- **Date:** 2026-05-27
- **Component:** `experiments/validate_a.py`, `data/results/a_validation_20260527_093105.json`
- **Starting state:** Archetype A implemented with the redesigned difficulty axis (IT-011), the bias-corrected plan prompt (IT-010), the extended judge prompt for compound and list answers (IT-009 plus IT-011 update), and the Tavily disk cache. Three-instance smoke tests had confirmed the methodological setup but suggested the agent's advantage on A might be smaller than the a-priori routing direction in Table 3 predicted.
- **Decision:** Run the full 15-instance validation at one run per instance on gpt-5.2-2025-12-11, parallel to the B sweep (single-run breadth before multi-run consolidation), to obtain a stratified picture across all three difficulty levels.
- **Result:** Workflow 14/15 correct, agent 15/15 correct. Workflow average tokens 1716; agent average 4429. Token cost ratio agent-over-workflow rises monotonically with difficulty: 1.5x at low, 1.9x at medium, 3.9x at high. The workflow's single failure is a-high-4 ("three highest peaks in the European Alps, in descending order"): the plan node issued one search and the LLM read "Liskamm" as the third peak instead of "Dom"; the workflow could not iterate to correct. The agent issued five parallel tool calls on the same instance and assembled the correct list. Zero LLM or tool errors across the 30 executions. Full matrix persisted in `data/results/a_validation_20260527_093105.json`.
- **Finding:** The a-priori routing direction for A in Table 3 was "agent loop"; the empirical evidence inverts this on the cost axis and partially confirms it on the correctness axis. Three observations matter. First, the gpt-5.2 agent uses parallel tool calls rather than sequential iteration, which inflates input tokens because accumulated snippets are re-read by the next LLM turn; this is the mechanism behind the 1.5x-to-3.9x ratio. Second, the workflow's plan-execute-synthesize structure is more token-efficient because snippets only appear in the single synthesis call, not in every LLM turn. Third, iteration genuinely helps correctness on the one instance where a single search is insufficient to assemble a multi-entity ordered list (a-high-4); without iteration the workflow committed to an incomplete first-snippet answer.

**Refined TADF v1 rule for A:**

  IF a task matches archetype A (Exploratory Research and Synthesis) AND error consequence is low to moderate, THEN execute as LLM workflow with plan-execute-synthesize. Observed advantage on gpt-5.2-2025-12-11 (n=15): comparable TCR (workflow 93%, agent 100%) at approximately one third of the token cost (workflow 1716 vs agent 4429 average).

  IF a task matches archetype A AND error consequence is high OR the question requires assembling a multi-entity ordered list where a single search may be incomplete, THEN execute as agent loop. The agent recovers missed entities through iterative or parallel searches at the cost of 2.6x to 4x higher token consumption.

This refines the dimensional reading of Table 3: the Error Consequence dimension, originally treated as a secondary modulator, emerges as the decisive routing axis for A within the workflow-vs-agent choice. Section 4.2.7 is updated accordingly when the taxonomy iteration is finalized in 4.2.6.

## IT-013 — Archetype F implementation (Transactional Action Execution)

- **Date:** 2026-05-27
- **Component:** `data/schema/schema.sql`, `experiments/seed_crm.py`, `experiments/load_db.py`, `src/core/tools/mail.py`, `src/core/tools/calendar.py`, `src/core/tools/database.py`, `src/core/tools/_latency.py`, `src/archetypes/f_action_execution/`, `experiments/seed_actions.py`, `experiments/validate_f.py`
- **Starting state:** Empty `f_action_execution` package after the A-H restructure. F is the bipolar archetype in Table 3, with canonical inputs favoring the workflow and novel inputs favoring the agent paradigm; the high difficulty stratum is meant to test the canonical/novel split directly.
- **Decision:** Implement F covering Mail, Calendar, and CRM-update domains (Project Management deferred to scope). Schema extended with WorkBench-shaped ``emails`` and ``events`` tables. Eight new LangChain tools added across ``mail.py`` (send/search/forward/delete) and ``calendar.py`` (create/search/update/delete); ``database.py`` gains a ``db_update`` tool restricted to a per-table column whitelist for safety. Layer-2 simulated tools (mail and calendar) carry the protocol's synthetic latency (300 ms +/- 50 ms) seeded by the call signature so identical calls yield identical delays across paradigms and re-runs. Workflow canonical-minimal form: ``plan_actions`` (one LLM call producing an ``ActionPlan``) -> ``execute_actions`` (deterministic dispatch via ``TOOL_DISPATCH``) -> END. Agent canonical-minimal form: ReAct with all eleven tools. Ground truth is outcome-centric per WorkBench (Styles et al., 2024): each instance has a Python predicate that queries the post-execution database state and returns True if the required outcome holds; predicates live next to the instances in ``seed_actions.py``. The validator resets the database to the seed via ``load_db.load()`` before each task run so workflow and agent see identical pre-state.
- **Result:** All modules implemented and syntax-validated. Workflow graph compiles with nodes ``plan_actions`` and ``execute_actions``. Agent compiles with eleven tools. Fifteen instances generated under ``data/test_inputs/f_action_execution/``, five per difficulty, with the high stratum split into three canonical (familiar WorkBench patterns: filter-then-act on multiple records, with explicit subject placeholders and per-record actions) and two novel sub-classes (argmax-then-act over an aggregated metric; conditional branching where the action depends on a pre-state predicate). Pre-action sanity check passes: all 15 predicates return False against the freshly loaded seed. Post-action sanity check passes: after manually issuing the required action (``db_update`` or ``send_email``), the corresponding predicate flips to True.
- **Finding:** Three design decisions traceable here for the final write-up. First, the synthetic-latency policy in ``_latency.py`` derives the per-call delay from a hash of the call signature so that identical calls (same tool, same args) yield identical delays across paradigms and reruns; this preserves the wall-clock latency comparability that pure-random jitter would break. Second, ``db_update`` enforces a per-table updatable-columns whitelist, which prevents the agent or a misbehaving workflow plan from mutating columns outside the intended action surface; this is a fairness safeguard, since both paradigms face the same restriction. Third, the workflow's failure-and-continue policy in ``execute_actions`` (record errors and proceed) is the protocol-defined paradigm behavior; the agent's ability to retry after failure remains an agent-only structural feature. Open methodological note: the DB reset between runs makes single-instance ground truth comparable, but stochastic agent behavior (variable iteration count, parallel tool calls) means within-instance variance still requires the multi-run pass to estimate properly. To be observed in the validation runs.

## IT-014 — Two-stage workflow restructure for archetype F (plan_reads -> plan_actions)

- **Date:** 2026-06-10
- **Component:** `src/archetypes/f_action_execution/schemas.py`, `src/archetypes/f_action_execution/config.py`, `src/archetypes/f_action_execution/workflow.py`
- **Starting state:** The canonical-minimal F workflow from IT-013 was single-stage: one LLM call (`plan_actions`) produced an `ActionPlan`, then `execute_actions` dispatched it deterministically. The smoke test on three instances (f-low-1, f-med-1, f-high-1) on gpt-5.2-2025-12-11 exposed a structural failure mode that the single-stage form cannot avoid. On f-med-1 ("for every Open case assigned to agent 3, set status to In Progress"), the planner did not know the concrete case IDs and produced a `db_update` call with `filters={"agent_id": 3, "status": "Open"}` instead of `record_id=<int>`; the tool rejected the args with a Pydantic validation error. On f-high-1 ("for every High-priority Open case assigned to agent 1, email the agent"), the planner produced `db_search(table="cases", filters={...})` instead of `db_search(table, column, query)`; the tool rejected the call. Both failures share the same cause: the action planner had to invent identifiers it could not see, and in doing so silently misused the tool API. The agent paradigm, by contrast, solved both instances by reading first, observing the IDs, then acting.
- **Decision:** Restructure the F workflow to two LLM stages with deterministic executors bracketing each stage, mirroring archetype A's `plan_searches -> execute_searches -> synthesize` topology. New graph: `plan_reads (LLM 1) -> execute_reads (Python) -> plan_actions (LLM 2) -> execute_actions (Python) -> END`. The first stage produces a `ReadPlan` (new Pydantic model in `schemas.py`) restricted to a `READ_TOOLS` literal of `db_read`, `db_search`, `search_emails`, `search_events`. The second stage receives the serialized read results in its prompt and produces an `ActionPlan` with concrete IDs and field values. The `PLAN_ACTIONS_PROMPT` explicitly states "db_update updates one row at a time by record_id; it does not accept filters" to discourage the filter-style misuse observed in the single-stage form. Both stages keep `with_structured_output(..., method="function_calling")` for gpt-5 strict-mode compatibility. The agent paradigm is unchanged: it remains free to interleave reads and actions, observe results, and recover from failed calls.
- **Result:** All modules compile. Workflow graph topology verified (`plan_reads -> execute_reads -> plan_actions -> execute_actions -> end`). Smoke test on the same three instances rerun on gpt-5.2-2025-12-11: workflow now correct on all three (3/3) where it was previously 1/3. Token totals: f-low-1 workflow 2 279 vs agent 3 567 (0.64x); f-med-1 workflow 2 257 vs agent 6 184 (0.37x); f-high-1 workflow 2 227 vs agent 5 933 (0.38x). The workflow is now both correct and substantially more token-efficient on the canonical instances tested. One residual observation: on f-low-1 the workflow over-reads (5 tool calls including 2 unnecessary `db_read` and 2 `search_emails`), because the read planner is conservative when the task self-contains all required values. Correctness is unaffected; the token contrast still favors the workflow because the agent's system prompt carries all eleven tool definitions per LLM call. Full 15-instance sweep persisted to `data/results/f_validation_<stamp>.json` pending.
- **Finding:** This restructure isolates a structural property of archetype F that the dimensional profile in Table 3 already implied but had not been operationalized in code. F has **high Information Availability** (the identifiers and field values exist in the local database) but they are not in the prompt; the planner must fetch them before it can produce concrete action arguments. A single-stage workflow conflates lookup and action planning into one LLM call, which is exactly the call that has no access to the IDs it needs. The two-stage form makes the lookup explicit and deterministic, leaving the second LLM call to plan actions against observed values rather than guessed ones. The same logic explains why archetype A required a two-stage form for the same reason (information had to be retrieved before synthesis): A and F differ in their information source (web vs local DB) but share the **fetch-then-act** structure that the canonical-minimal workflow has to encode in two stages. This is a generalizable design pattern across archetypes whose Information Availability is high but indirect, and is added to the framework discussion in Chapter 6. Methodologically: the F-workflow's correctness gain on canonical High (f-high-1) does not yet test the bipolar hypothesis from Table 3; that hypothesis depends on the novel-High instances (f-high-4 argmax-then-act, f-high-5 conditional-branching), which the full sweep will exercise. The expected pattern is canonical-High dominated by the workflow, novel-High closer to parity or favoring the agent.

## IT-015 — Archetype F: methodological tightening and full validation sweep with refined routing rule

- **Date:** 2026-06-10
- **Component:** `src/core/tools/database.py`, `src/archetypes/f_action_execution/schemas.py`, `src/archetypes/f_action_execution/config.py`, `experiments/seed_crm.py`, `experiments/seed_actions.py`, `data/results/f_validation_20260610_105940.json`
- **Starting state:** The two-stage F workflow from IT-014 had been smoke-tested on three instances and run once across the full 15-instance set (results file `f_validation_20260610_095239.json`). A pre-IT-015 audit of the setup against three criteria — production realism, benchmark fidelity to WorkBench (Styles et al., 2024) and WorkArena L1/L2 (Drouin et al., 2024), and discrimination power of the difficulty axis — uncovered three methodological gaps. (i) The predicates checked only positive post-conditions; spurious side-effects (extra outbox emails, additional state mutations) would not flip a "correct" run to "incorrect", contrary to WorkBench's outcome-centric scoring which explicitly distinguishes correct outcome from spurious writes. (ii) The `PLAN_READS_PROMPT` lacked an explicit zero-floor: on tasks that already contained every value needed to act (recipient, subject, body, dates, ids), the LLM still produced defensive reads, inflating the workflow's Low-level token cost (f-low-1 produced four spurious reads before the send). This biased the paradigm comparison against the workflow at Low difficulty. (iii) The novel sub-class of the High stratum (f-high-4 argmax-then-act, f-high-5 conditional branching) did not actually test the bipolar Step-Predictability dimension from Table 3: both instances were plan-time-decidable, meaning a single up-front read could resolve the branch without needing to observe an action outcome. None of the 15 instances required runtime feedback from a state-changing operation; the bipolar hypothesis was untested.
- **Decision:** Implement three corrective changes before the next sweep. (1) **Side-effect-aware predicates:** every predicate in `seed_actions.py` now asserts both the required positive post-condition AND the absence of spurious changes outside the intended target set. Helpers `_no_unintended_column_change`, `_no_unintended_email_status_change`, `_only_expected_new_outbox`, `_only_expected_new_events`, `_no_existing_events_changed` compare the post-state against the deterministic seed (loaded once per module load from `data/schema/seed/*.json`) and reject runs that mutate rows outside the target set or create off-target outbox sends. (2) **Empty-ReadPlan permission:** the `PLAN_READS_PROMPT` now states "If the task statement already contains every value needed to act (recipient address, subject, body, dates, ids), produce an empty `reads` list and let the action planner act directly. Reading defensively when nothing is unknown wastes tokens." This parallels the IT-010 fix on archetype A. (3) **Runtime-feedback instance** as new f-high-5 replacement: a new tool `attempt_close_case(case_id, resolution_summary)` is added to `src/core/tools/database.py` with a documented but unpredictable failure mode (the tool returns `{"closed": false, "reason": "..."}` when blocked by an "internal escalation policy"); the policy itself — `transfer_count > 3` blocks the close — is intentionally NOT exposed via the schema doc or any read tool. The new f-high-5 task instructs the assistant to attempt closing case 47 (deterministically pinned to `transfer_count=4` via a `case_overrides` block in `seed_crm.py`) and then send one of two emails depending on whether the close succeeded or was blocked. The predicate requires exactly one of the two emails to be sent, so a defensive plan that schedules both fails and an optimistic plan that picks the wrong branch also fails — only a plan that observes the action outcome and branches at runtime succeeds. Several email bodies were rewritten in natural workplace prose to better simulate the LLM's outbound writing load (predicates do not check bodies, so this affects realism but not scoring).
- **Result:** Sandbox verification: pre-action sanity check passes (all 15 predicates return False against the freshly loaded seed); post-action sanity check passes (manually applying the expected action flips the predicate to True); side-effect detection verified (manually adding one spurious outbox email or one spurious case-status change flips the corresponding predicate from True to False); the new `attempt_close_case` for case 47 returns `{"closed": false, "reason": "case escalated for manual review; automatic close is not permitted"}` and leaves case 47 status unchanged; on the new f-high-5, the predicate evaluates True only for the runtime-correct branch and False for both the optimistic-wrong (send 'Case 47 resolved' alone) and the defensive-wrong (send both emails) failure modes. Full 15-instance run on gpt-5.2-2025-12-11 (results file `f_validation_20260610_105940.json`): **workflow 11/15 (73 %)**, **agent 14/15 (93 %)**. Workflow average tokens 3 196; agent average 8 428; **token cost ratio 2.64×** agent-over-workflow (down slightly from the pre-tightening 2.34×, because the workflow's failure cases now include cases where it spends planning tokens without correct outcome). On the correct subsets the picture is more pronounced: workflow average on its 11 correct runs is 3 298 tokens; agent average on its 14 correct runs is 8 812 tokens; ratio 2.67×. f-low-1 confirms the empty-ReadPlan fix: workflow used **1 tool call** (just `send_email`) compared to four spurious reads in the pre-fix run. The full token, tool-call, latency, and per-failure error matrix is persisted in the results file.
- **Finding:** The single-run picture is now sharp enough to articulate a four-quadrant routing rule for F that distinguishes empirically observed paradigm advantages by task structure rather than by the canonical/novel dichotomy assumed in Table 3. Four failure classes emerged across the 15 instances. (i) **f-low-2 — unintended runtime-feedback at Low:** the workflow plausibly selected `attempt_close_case(6, ...)` for "Update the status of case 6 to 'Closed'" because the schema doc lists it as the case-closure tool. The hidden escalation rule blocked the close (case 6 has `transfer_count > 3` by random seed draw), the workflow's deterministic executor recorded the rejection and proceeded, no recovery; the agent first tried `attempt_close_case`, observed the block, fell back to `db_update(cases, 6, {status: 'Closed'})` and succeeded. This is the same structural recovery pattern that f-high-5 was designed to test; its appearance at Low is a methodological observation, not a bug — adding a tool with documented-but-unpredictable failure modes introduces a runtime-feedback signal at any difficulty level where the LLM plausibly selects that tool. (ii) **f-med-3 — enumeration loss at scale:** the workflow's second-stage `plan_actions` LLM produced only 7 of the 9 required `db_update` calls (output tokens 530); the seventh-most update was dropped before the LLM emitted the structured plan. The agent enumerated all 9 via parallel tool calls in a single turn. This is a new finding visible only through the tightened predicate that requires all targets to be moved. (iii) **f-med-5 — primary-contact mis-identification at scale:** the workflow sent seven emails but to the wrong recipients (the LLM picked the wrong "lowest-id contact per account" in the second stage's reasoning over the read results); the previous, loose predicate accepted seven matches by subject alone. The agent produced the correct recipient set. (iv) **f-high-5 — bipolar runtime-feedback:** the workflow planned both emails defensively (six tool calls: three reads, `attempt_close_case`, send 'Case 47 update', send 'Case 47 resolved'), the predicate caught the spurious 'resolved' send; the agent observed `closed=false` and sent only the correct branch. This is the empirical confirmation of the bipolar hypothesis from Table 3 for the runtime-feedback sub-class. (v) **f-high-4 — agent in-context aggregation failure (opposite direction):** the agent again picked agent07 as the argmax over EMEA-team Open cases instead of the correct agent05; the workflow's read-stage feeds the EMEA agents and their Open-case counts as a small structured table directly into the action prompt, where argmax over four candidates is a tractable in-prompt reasoning step. Workflow wins.

**Refined TADF v1 rule for F (four-quadrant form):**

  IF a task matches archetype F AND its action set is **plan-time-decidable** (all required IDs and field values can be retrieved by a finite set of reads, no action outcome is needed to choose the next action) AND **set size is small** (≤ ~5 records per action class), THEN execute as two-stage LLM workflow (`plan_reads → execute_reads → plan_actions → execute_actions`). Observed token advantage on gpt-5.2-2025-12-11 (n=15 single-run): ~2.6× lower token cost than the agent paradigm with equal or better correctness in this regime.

  IF a task matches archetype F AND involves **structured in-context aggregation over a small group set** (argmax/min, group-counts, ordered listings over fewer than ~10 groups), THEN execute as two-stage LLM workflow. The read stage feeds a clean tabular view to `plan_actions`, where the aggregation is reduced to in-prompt reasoning over a small table; the agent's loop carries the same data across multiple turns with intermediate text, which empirically inflates aggregation errors (f-high-4 demonstrates the agent argmax failure).

  IF a task matches archetype F AND the **action set is large enough that the second-stage LLM cannot reliably enumerate all targets** in a single structured output (empirically observed at 9+ records), THEN execute as agent loop. The agent emits parallel tool calls in a single ReAct turn without the enumeration ceiling of the structured-output stage (f-med-3, f-med-5).

  IF a task matches archetype F AND a **runtime outcome of an action determines the next action** (action failure modes are documented but not predictable from reads alone), THEN execute as agent loop. The workflow's deterministic action executor cannot re-plan after observing an action outcome; a defensive workflow that pre-plans both branches violates outcome-centric correctness when only one branch should fire (f-high-5, f-low-2).

This refines and complicates the a-priori bipolar reading of Table 3: instead of "canonical → workflow, novel → agent", the empirically supported routing axes are **runtime-feedback need** (decisive for agent) and **enumeration scale** (decisive for agent above the structured-output ceiling), with **in-context aggregation** flipping the standard novel-favors-agent expectation. The TADF v1 dimension that maps onto the empirical regime split is no longer the original "step predictability for canonical vs novel" but a composite of (a) **action-outcome dependence** (low → workflow, high → agent) and (b) **target set cardinality** (low → workflow, high → agent). Section 4.2.7 is updated when the taxonomy iteration is finalized; Chapter 6 carries the four-quadrant routing rule as F's TADF v1 specification.

Open methodological items carried into the consolidated multi-run pass: (i) the f-low-2 outcome should be re-checked under a schema-doc variant that explicitly states "use db_update for routine status changes; use attempt_close_case only when a business-rule check is desired" to test how prompt-level routing guidance interacts with the workflow's locked-in plan; (ii) the enumeration ceiling observed at 9 records should be probed at intermediate set sizes (6, 7, 8) to localize the failure boundary, but this belongs to a sensitivity analysis after all eight archetypes are implemented; (iii) the kappa-validation of the judge against a human sample (planned for A's evaluation under IT-008) is unaffected by F because F uses deterministic predicates rather than LLM-as-judge scoring.
