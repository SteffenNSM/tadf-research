# TADF Research

Experimental codebase for the master thesis **"Agent-Loop or LLM-Workflow? Development and Validation of an Architecture Decision Framework for Task Execution in Agentic Workplace and Enterprise Automation Settings"** (M.Sc. Information Systems, University of Cologne, CIIS; supervisor: Tom Celig).

The thesis develops the **Task-Level Architecture Decision Framework (TADF)**: empirically grounded IF-THEN design rules that specify, for each of eight task archetypes (A–H), whether a task should be executed as an **LLM workflow** (LangGraph StateGraph with fixed topology and structured output) or as an **agent loop** (ReAct with runtime tool selection). Both paradigms are implemented per archetype on an identical LLM backbone, tool interface, and logging infrastructure, so observed performance differences are attributable to the execution paradigm.

## Design

- **Paradigm comparison:** each archetype is implemented twice (`workflow.py`, `agent.py`) and run against the same task instances (5 per difficulty level: low/med/high).
- **Model:** `gpt-5.2-2025-12-11`, `reasoning_effort="none"`, temperature 0.2 (0.0 for planning), seed 42.
- **Environment:** self-contained SQLite database (`data/crm.db`) rebuilt from a deterministic seed before every run; simulated mail/calendar tools with deterministic synthetic latency (300 ms ± 50 ms); Tavily web search with a per-query disk cache so both paradigms see identical snippets.
- **Scoring:** outcome-centric post-state predicates (WorkBench-style) for B and F; frozen-prompt LLM judge for A.
- **Metrics:** TCR/OQS and Token Cost (co-primary); latency, error rate, tool-call count, robustness (secondary).

## Status

Archetypes A (Exploratory Research), B (Structured Retrieval), and F (Transactional Action Execution) are implemented and validated; C, D, E, G, H are pending. Results live in `data/results/`; every design decision is documented in `docs/iteration_log.md`.

## Reproduction

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY, TAVILY_API_KEY

python experiments/seed_crm.py
python experiments/seed_actions.py
python experiments/seed_research.py
python experiments/load_db.py

python experiments/validate_b.py --all
python experiments/validate_a.py --all
python experiments/validate_f.py --all
```

See `CLAUDE.md` for the full research context and repository layout.
