# TADF Research Repository

Code repository for the master thesis: **"Agent-Loop or LLM-Workflow? Development and Validation of an Architecture Decision Framework for Task Execution in Agentic Workplace and Enterprise Automation Settings"**

Author: Steffen Niesmann | Supervisor: Tom Celig
Cologne Institute for Information Systems (CIIS) | University of Cologne
Repository: https://github.com/SteffenNSM/tadf-research.git

---

## Repository Structure

```
TADF-research/
├── CLAUDE.md                  # AI assistant context (this file)
├── README.md                  # Project overview and reproduction instructions
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template (OpenAI, Tavily)
├── src/
│   ├── core/                  # Shared infrastructure
│   │   ├── llm.py             # Pinned model (gpt-5.2-2025-12-11, reasoning_effort="none")
│   │   ├── logging.py         # ExecutionLogger: tokens, tool calls, latency, errors
│   │   ├── state.py           # Shared TaskState schema
│   │   ├── db.py              # Local SQLite connection (data/crm.db)
│   │   └── tools/             # Tool layer: database, mail, calendar, search, _latency
│   ├── archetypes/            # One subdirectory per archetype A–H
│   │   ├── a_exploratory_research/    # ✅ implemented + validated (IT-008…IT-012)
│   │   ├── b_structured_retrieval/    # ✅ implemented + validated (IT-004…IT-007)
│   │   ├── c_ambiguous_classification/  # ⬜ pending
│   │   ├── d_compliance_decisioning/    # ⬜ pending
│   │   ├── e_output_verification/       # ⬜ pending
│   │   ├── f_action_execution/          # ✅ implemented + validated (IT-013…IT-015)
│   │   ├── g_strategic_planning/        # ⬜ pending
│   │   └── h_content_drafting/          # ⬜ pending
│   ├── evaluation/            # APS, metric collectors, comparison runner (stubs)
│   └── router/                # TADF design rules (output of Phase 2; pending)
├── experiments/               # Seeders, DB loader, per-archetype validators
│   ├── seed_crm.py            # Deterministic CRM seed (accounts, cases, …)
│   ├── seed_actions.py        # F instances + outcome-centric predicates
│   ├── seed_research.py       # A instances
│   ├── load_db.py             # Build/reset data/crm.db from seed JSON
│   └── validate_{a,b,f}.py    # End-to-end sweeps (real LLM)
├── docs/
│   └── iteration_log.md       # DSR iteration log (IT-001 ff.) — single source of truth for design decisions
└── data/
    ├── schema/                # schema.sql + seed/*.json (versioned)
    ├── test_inputs/           # Per archetype: low/med/high, 5 instances each
    ├── search_cache/          # Tavily per-query disk cache (fairness + reproducibility)
    └── results/               # Timestamped sweep outputs (versioned)
```

Each implemented archetype contains: `workflow.py` (LangGraph StateGraph, DAG, structured output), `agent.py` (ReAct loop), `config.py` (dimensional profile, tools, prompts), `schemas.py` (Pydantic models), `ground_truth.py` (scoring).

---

## Research Context

Design Science Research (DSR) methodology (Hevner et al., 2004; Peffers et al., 2007; Gregor & Hevner, 2013). The primary artifact is the **Task-Level Architecture Decision Framework (TADF)**: empirically grounded IF-THEN design rules that specify, per task archetype, whether agent-loop or LLM-workflow execution is appropriate in SME business process automation.

### Research Questions (thesis Section 1.3)

- **RQ:** How can an agentic system development framework for workplace and process automation settings be designed to decide, based on task characteristics, whether to execute a task via agent loops or LLM workflows, to achieve optimal resource efficiency and performance?
- **SQ1:** What task archetypes and dimensions characterize the task space for workplace and process automation and determine the selection between agent-loop and LLM-workflow execution?
- **SQ2:** What performance and resource efficiency metrics enable systematic empirical comparison of agent-loop and LLM-workflow execution across task archetypes?
- **SQ3:** How can experimental implementations of each task archetype be designed and executed across agent-loop and LLM-workflow paradigms to generate empirical routing evidence that supports optimal resource efficiency and performance?

### Four Task Dimensions (thesis Section 4.2.4)

1. **Step Predictability** — can the step sequence be specified before execution?
2. **Information Availability** — is all required information accessible at task entry?
3. **Output Ambiguity** — does the output conform to a fixed schema?
4. **Error Consequence** — how severe is failure?

### Eight Task Archetypes (thesis Section 4.2.5/4.2.7)

| ID | Archetype | Expected routing | Status |
|---|---|---|---|
| A | Exploratory Research and Synthesis | Agent loop (empirically refined: workflow at low error consequence, IT-012) | ✅ validated |
| B | Structured Data Retrieval and Transformation | LLM workflow (confirmed, IT-007) | ✅ validated |
| C | Ambiguous Classification and Disambiguation | LLM workflow with structured output | ⬜ |
| D | Compliance and Rule-Based Decisioning | LLM workflow | ⬜ |
| E | Output Verification and Quality Control | LLM workflow (LLM-as-judge) | ⬜ |
| F | Transactional Action Execution | Four-quadrant rule: workflow when plan-time-decidable / small set; agent when runtime-feedback-dependent / large enumeration (IT-015) | ✅ validated |
| G | Strategic and Adaptive Planning | Agent loop, workflow for templated processes | ⬜ |
| H | Content and Document Drafting and Refinement | Agent loop or hybrid | ⬜ |

### Evaluation Metrics

Co-primary: Task Completion Rate (TCR; B, C, D, F) or Output Quality Score (OQS; A, E, G, H), and Token Cost (TC). Secondary: Latency (L), Error Rate (ER), Tool-Call Count (TCC), Robustness (R). Aggregate Performance Score (APS) weights derived from practitioner interviews (Phase 3).

### Four Comparison Conditions

1. Workflow-only · 2. Agent-only · 3. DAAO-style difficulty router (Su et al., 2025) · 4. TADF-guided router. Conditions 3 and 4 reuse the recorded W/A trajectories.

---

## Implementation Stack

- **Framework:** LangGraph (Python 3.12), LangChain tool layer
- **Model:** `gpt-5.2-2025-12-11`, `reasoning_effort="none"`, temperature 0.2 (0.0 for G), seed 42
- **Persistence:** local SQLite (`data/crm.db`), reset to deterministic seed before each run (IT-003; protocol deviation D-001)
- **Search:** Tavily with per-query disk cache (`data/search_cache/`), so both paradigms see identical snippets
- **Synthetic latency:** 300 ms ± 50 ms per simulated mail/calendar call, derived from call-signature hash (deterministic across paradigms/re-runs)
- **Scoring:** outcome-centric post-state predicates (B, F) or frozen-prompt LLM judge (A)

## DSR Phases

| Phase | Focus | Output | Thesis chapter |
|-------|-------|--------|----------------|
| 1 | Literature review, conceptual foundation | Taxonomy, evaluation instrument | Ch. 2, 3, 4.2, 4.3 |
| 2 | Controlled task-level experiments | Performance matrix, TADF v1 rules | Ch. 4.4, 4.5 |
| 3 | Practitioner evaluation | Validated APS weights, refined TADF | Ch. 5.1 |
| 4 | Case study validation | Hybrid pipeline, APS comparison | Ch. 5.2 |

## Current Status (2026-06-11)

- A, B, F implemented and swept (single-run, 15 instances each); results in `data/results/`
- TADF v1 rules derived for A (IT-012), B (IT-007), F four-quadrant (IT-015)
- Open: archetypes C, D, E, G, H; consolidated three-run pass; perturbation/robustness runs; router conditions; payload-realism decision (D-006); per-archetype step limits (D-007)
- All deviations from the Phase 2 protocol: thesis Appendix B.1 deviation log

## Build and Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set OPENAI_API_KEY, TAVILY_API_KEY

python experiments/seed_crm.py        # generate CRM seed
python experiments/seed_actions.py    # generate F instances + predicates
python experiments/seed_research.py   # generate A instances
python experiments/load_db.py         # build data/crm.db

python experiments/validate_b.py            # smoke (3 instances)
python experiments/validate_a.py --all      # full sweep
python experiments/validate_f.py --all      # full sweep
```

## Code Conventions

- Python 3.12, type hints on all signatures, PEP 8, Google-style docstrings
- f-strings; snake_case functions, PascalCase classes
- Logging via `ExecutionLogger` callback, not print statements
- Every design decision is logged in `docs/iteration_log.md` at the time of the change (DSR Guideline G6)
