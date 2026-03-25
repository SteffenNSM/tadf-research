# dtrf-research – Code Repository
## Dynamic Task-Level Routing Framework

Dieses Repository enthält die Implementierung und Experimente für die DTRF-Masterarbeit.
Es wird mit Betreuer Tom Celig (CIIS, Universität Köln) geteilt.

---

## Repository-Struktur

```
dtrf-research/
├── CLAUDE.md              ← Diese Datei
├── README.md              ← Projekt-Übersicht (für den Prof)
├── src/                   ← DTRF-Implementierung
│   ├── router/            ← LLM-basierter Klassifikator + IF-THEN-Regelkonfiguration
│   └── evaluation/        ← Router-Accuracy-Evaluation
├── experiments/           ← Kontrollierte WF-vs-Agent-Experimente pro Archetype
└── data/                  ← Datensätze, Ergebnisse, Logs
```

---

## Artifact: DTRF v2

**Router-Implementierung:** LLM-basierter Klassifikator, der IF-THEN-Regeln aus einer
Markdown-Konfigurationsdatei liest.

**4 Routing-Dimensionen:**
1. Task Ambiguity
2. Output Schema Constraint
3. Information Availability
4. Consequence of Error

**7 Task Archetypes:**
Open Information Gathering · Structured Retrieval and Transformation ·
Ambiguous Classification · Output Quality Evaluation · Threshold-Based Decision ·
Multi-Source Synthesis · Action Execution

**Baselines:**
1. Workflow-only
2. Agent-only
3. DAAO-style difficulty-only router (Su et al., 2025)
4. DTRF v2

---

## Beim Schreiben von Thesis-Text

Thesis-Schreibkontext befindet sich im übergeordneten Ordner:
`../Writing and Context Agent/writing_context.md`
