"""Insert the Family-S section (Section 7) into the Phase 2b notebook, in place.

Adds 9 cells (scorecard with X/P join, summary figure, capability gradient +
P-c re-check, findings, routing derivation / v1.2 changelog, plain-language
summary) BEFORE the radar appendix, preserving every existing cell and output.
A timestamped backup is written next to the notebook first. Idempotent: if a
"## 7. Family S" cell already exists, the script aborts.

Run:
    PYTHONPATH=. python experiments/add_family_s_section.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NB = REPO / "notebooks" / "results_analysis_phase2b.ipynb"

NEW_CELLS = [
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "## 7. Family S \u2014 Staged Adaptivity (three-form comparison)\n",
   "\n",
   "*Added after the Section-6 consolidation; design and pre-registered hypotheses in IT-066, smoke hardening in IT-067, results in IT-068.*\n",
   "\n",
   "Design (IT-066): family S maps the boundary of **compiled conditional control flow** \u2014 how much of the agent's adaptivity a **state-machine workflow** (SM; `src/archetypes/f_action_execution/state_machine.py`) recovers. The SM keeps every LLM call at plan time (two calls, like the canonical workflow; the read stage is imported unchanged) and lets a deterministic executor branch on the **enumerated, structured outcome categories** of `attempt_close_case` (success / refused / already_closed), with per-step branch tables, `{case_id}`/`{reason}` template substitution, `stop_batch` semantics, an iteration cap, and a fail-safe default stop for uncovered outcomes.\n",
   "\n",
   "Three variants: **s1_enumerated_switch** and **s2_bounded_until** reuse the family-X x1 and family-P p-b instances VERBATIM \u2014 only the SM was swept; the canonical workflow/agent columns below are **joined from the X/P grids** on identical instances (zero duplicate spend). **s3_content_synthesis** (new, `seed_s.py`) keeps the p-b close batches but requires ONE report mail whose body names exactly the cases closed in THIS run \u2014 content that only exists at run time; **s3-4 is the built-in control** (no refusal in the batch, so the content is plan-time derivable). All three forms ran on s3.\n",
   "\n",
   "Same grid and read discipline as the other families (nano 2\u00d7, mini 2\u00d7, gpt-5.2 1\u00d7; per-cell n = 5; 10.2% flip band; latest run per key). Post-smoke hardening before the grid (IT-067): the SM planner prompt was given the same db_update tool-contract line the canonical planner already had (parity fix), plus step-completeness and post_actions semantics \u2014 logged, IT-056 precedent.\n",
   "\n",
   "*What the next cell does:* it prints the family-S scorecard \u2014 success per variant \u00d7 execution form for each grid cell plus the pooled score and average token cost, with the joined X/P baselines marked \u2014 and lists the hard errors."
  ]
 },
 {
  "cell_type": "code",
  "metadata": {},
  "execution_count": null,
  "outputs": [],
  "source": [
   "# Family S scorecard \u2014 three execution forms; canonical W/A joined from X/P on identical instances\n",
   "C_SM = '#5aa08a'\n",
   "PCOL_S = {**PCOL, 'state_machine': C_SM}\n",
   "\n",
   "S1_IDS = [f'x1-{n}' for n in range(1, 6)]\n",
   "S2_IDS = [f'p-b-{n}' for n in range(1, 6)]\n",
   "S3_IDS = [f's3-{n}' for n in range(1, 6)]\n",
   "S_JOIN = {'s1_enumerated_switch': (S1_IDS, 'X'), 's2_bounded_until': (S2_IDS, 'P'),\n",
   "          's3_content_synthesis': (S3_IDS, 'S')}\n",
   "VARIANTS_S = list(S_JOIN)\n",
   "FORMS = ['workflow', 'agent', 'state_machine']\n",
   "\n",
   "def s_rows(variant, paradigm, model=None, run_label=None):\n",
   "    ids, join_fam = S_JOIN[variant]\n",
   "    fam = 'S' if (paradigm == 'state_machine' or variant == 's3_content_synthesis') else join_fam\n",
   "    rows = [r for r in ROWS if r.get('family') == fam and r['instance'] in ids and r['paradigm'] == paradigm]\n",
   "    if model:\n",
   "        rows = [r for r in rows if r['model'] == model]\n",
   "    if run_label:\n",
   "        rows = [r for r in rows if r['run_label'] == run_label]\n",
   "    return rows\n",
   "\n",
   "hdr = ''.join(f'{SHORT[m][-4:]+\" \"+l[-1]:>9}' for m, l in CELLS)\n",
   "print(f'{\"variant\":22} {\"form\":14}' + hdr + f'{\"pooled\":>9} {\"avg_tok\":>8}')\n",
   "for v in VARIANTS_S:\n",
   "    for p in FORMS:\n",
   "        joined = ' (joined)' if p != 'state_machine' and v != 's3_content_synthesis' else ''\n",
   "        line = f'{v:22} {p:14}'\n",
   "        ok = tot = 0\n",
   "        for m, l in CELLS:\n",
   "            sub = s_rows(v, p, model=m, run_label=l)\n",
   "            k = sum(1 for r in sub if r.get('correct')); ok += k; tot += len(sub)\n",
   "            line += f'{f\"{k}/{len(sub)}\":>9}'\n",
   "        line += f'{f\"{ok}/{tot}\":>9} {_avg_tok(s_rows(v, p)):>8.0f}' + joined\n",
   "        print(line)\n",
   "\n",
   "errs = [r for r in fam_rows('S') if r.get('error') or r.get('errors')]\n",
   "print(f'\\nHARD/TOOL ERRORS (family-S sweeps): {len(errs)}')\n",
   "for r in errs:\n",
   "    msg = r.get('error') or (r.get('errors') or [''])[0]\n",
   "    print(f'  {r[\"instance\"]:7} {SHORT[r[\"model\"]]:12} {r[\"run_label\"]:5} {r[\"paradigm\"]:14} :: {str(msg)[:70]}')"
  ]
 },
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "*What the next cell does:* it draws the family-S summary \u2014 pooled success per variant for all three execution forms (canonical columns joined from X/P where marked) and the average token cost (log scale). Third-form color: teal."
  ]
 },
 {
  "cell_type": "code",
  "metadata": {},
  "execution_count": null,
  "outputs": [],
  "source": [
   "xs = np.arange(len(VARIANTS_S)); w = 0.26\n",
   "labels = ['s1\\nenumerated switch', 's2\\nbounded until', 's3\\ncontent synthesis']\n",
   "f, ax = plt.subplots(1, 2, figsize=(13, 4.6))\n",
   "for i, p in enumerate(FORMS):\n",
   "    off = (i - 1) * w\n",
   "    ax[0].bar(xs + off, [_rate(s_rows(v, p)) for v in VARIANTS_S], w, label=p, color=PCOL_S[p])\n",
   "    ax[1].bar(xs + off, [_avg_tok(s_rows(v, p)) for v in VARIANTS_S], w, label=p, color=PCOL_S[p])\n",
   "ax[0].set_title('Success rate, pooled (W/A joined from X/P on s1/s2)'); ax[0].set_ylabel('%'); ax[0].set_ylim(0, 105)\n",
   "ax[1].set_title('Avg total tokens'); ax[1].set_ylabel('tokens'); ax[1].set_yscale('log')\n",
   "for a in ax:\n",
   "    a.set_xticks(xs); a.set_xticklabels(labels, fontsize=8.5); a.legend(fontsize=8)\n",
   "f.suptitle('Family S \u2014 staged adaptivity: what compiled branching recovers, and what it cannot', fontsize=12)\n",
   "plt.tight_layout(); plt.show()"
  ]
 },
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "*What the next cell does:* it draws the capability gradient per variant \u2014 one panel per variant, success across the three tiers, one line per execution form. The reference-tier convergence of SM and agent on s1/s2 (both perfect) versus the SM/workflow floor on s3 is the family's answer in one picture. It also prints the P-c reference-tier re-check (row 3.4 piggyback, run1 + run2)."
  ]
 },
 {
  "cell_type": "code",
  "metadata": {},
  "execution_count": null,
  "outputs": [],
  "source": [
   "TIERS = [(MODELS[0], ('run1', 'run2')), (MODELS[1], ('run1', 'run2')), (MODELS[2], ('run1',))]\n",
   "tx = np.arange(3); tlabels = [SHORT[m] for m, _ in TIERS]\n",
   "f, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)\n",
   "for a, v in zip(axes, VARIANTS_S):\n",
   "    for p, marker in (('workflow', 'o'), ('agent', 's'), ('state_machine', '^')):\n",
   "        ys = []\n",
   "        for m, ls in TIERS:\n",
   "            sub = [r for r in s_rows(v, p, model=m) if r['run_label'] in ls]\n",
   "            ys.append(_rate(sub))\n",
   "        a.plot(tx, ys, '-', marker=marker, color=PCOL_S[p], linewidth=2, label=p)\n",
   "    a.set_title(v, fontsize=9.5); a.set_xticks(tx); a.set_xticklabels(tlabels, fontsize=8)\n",
   "    a.set_ylim(-5, 105)\n",
   "axes[0].set_ylabel('success %'); axes[0].legend(fontsize=8)\n",
   "f.suptitle('Family S \u2014 capability gradient per variant (SM converges on the agent where outcomes are enumerable)', fontsize=12)\n",
   "plt.tight_layout(); plt.show()\n",
   "\n",
   "# P-c reference-tier re-check (row 3.4 piggyback): run1 + run2 on gpt-5.2\n",
   "print('P-c (c_source_unknown) at the reference tier:')\n",
   "for p in ('workflow', 'agent'):\n",
   "    for l in ('run1', 'run2'):\n",
   "        sub = fam_rows('P', variant='c_source_unknown', paradigm=p, model=MODELS[2], run_label=l)\n",
   "        if sub:\n",
   "            print(f'  {p:9} {l}: {sum(1 for r in sub if r.get(\"correct\"))}/{len(sub)}')"
  ]
 },
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "### Findings S\n",
   "\n",
   "**s1 (enumerated switch).** The SM takes the x1 cell \u2014 the canonical workflow's tier-invariant 0/25 \u2014 to **19/25 pooled and 5/5 at the reference tier**, at ~5.0k tokens versus the agent's ~14.4k (0.35\u00d7) and the canonical workflow's ~4.1k \u2014 the SM keeps workflow cost economics. Structure of the misses: nano's single s1 failure is a provider connection error (nano would be 10/10 clean), and **all five mini failures are `ReadPlan` validation crashes on the x1-runbook instructions** \u2014 the same mini read-stage schema fragility as X-1/m1 (the read stage is imported unchanged; now four-times replicated). The x1 zero is therefore a **limit of the two-stage form, not of compiled control flow**; below the reference tier the read-stage schema ceiling binds first.\n",
   "\n",
   "**s2 (bounded until).** The SM takes P-b \u2014 the other structural zero \u2014 to **14/25 pooled and 5/5 at the reference tier**, matching the agent's success profile (15/25; also 5/5 at reference, also unstable below) at ~5.2k tokens versus the agent's ~19.1k (0.27\u00d7). An outcome-dependent COUNT is SM-compatible when the stop condition is deterministically checkable on a structured response; below the reference tier neither form is reliable \u2014 a capability floor, not a paradigm gap.\n",
   "\n",
   "**s3 (content synthesis) \u2014 the boundary.** Both workflow forms stay structurally low (canonical 2/25, SM 4/25) while the agent carries the cell (**13/25 pooled, 4/5 at reference**, with visible temperature-0 flips instance by instance \u2014 the two-run discipline earned its keep here). The **control instance s3-4** separates the mechanism: with no refusal in the batch, the closed set is plan-time derivable and all three forms pass at the reference tier. What breaks the compiled forms is exactly and only the run-dependent report CONTENT: **path selection is compilable, content synthesis is not.**\n",
   "\n",
   "**Errors.** Family-S hard errors concentrate where the known ceilings predict: 5\u00d7 mini ReadPlan (s1), 2\u00d7 nano ReadPlan (s3 canonical workflow), 2 provider connection errors (counted as failures, marked in the scorecard).\n",
   "\n",
   "**P-c re-check (piggyback).** Reference tier combined over run1+run2: workflow **5/10** vs agent **9/10** \u2014 the row 3.4 gap persists at the reference tier; the earlier small-n caveat is resolved, the hard break stands."
  ]
 },
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "### Routing derivation \u2014 row 2.1 split (family S) and the v1.1 \u2192 v1.2 changelog\n",
   "\n",
   "Applied with the fixed decision rule (pooled gap beyond the two-run noise band, control axes resolve to no gate):\n",
   "\n",
   "- **Row 2.1 splits into two conditions** (family S, IT-068). Runtime-observed results steer the process AND *(a)* the outcome space is **build-time enumerable** on structured responses, branch tests are deterministic, and depth is bounded \u2192 **compiled conditional workflow** (state-machine form): reference tier 5/5 + 5/5 on the two former structural zeros at 0.27\u20130.35\u00d7 the agent's tokens; **capability-conditional below** the reference tier (mini bound by the read-stage schema ceiling, nano unstable on the until-loop) \u2014 the Stage-3 check carries the condition, exactly as for X-3. *(b)* Runtime information must flow into generated **content**, the outcome space is not enumerable, or depth is unbounded \u2192 **AGENT \u2014 hard break confirmed** (s3: 13/25 vs 4/25 and 2/25; the s3-4 control isolates the mechanism).\n",
   "- **Row 3.4 evidence upgrade** (P-c reference re-check): W 5/10 vs A 9/10 at the reference tier \u2014 the unknown-source hard break holds at every tier; capability note closed.\n",
   "- **Build note (rows 7.3):** the decided-workflow checklist gains the state-machine option \u2014 per-step branch tables over enumerated structured outcomes, bounded template substitution (`{case_id}`/`{reason}`), default-stop for uncovered outcomes, iteration caps. Every element traces to the S cells.\n",
   "- **TADF-Core Q1** gains the sub-question: *\"\u2026and can every branch input be enumerated at build time from structured tool responses?\"* \u2014 yes \u2192 state-machine workflow from the reference tier; no \u2192 agent.\n",
   "- **Unchanged:** rows 1.x, 2.2, 2.3 (m1's drift branch is enumerable in principle \u2014 flagged as an optional SM extension, untested, needs the family-M trigger machinery), 3.x, 4.x\u20136.x.\n",
   "\n",
   "**Scope statement (kept honest):** the S evidence covers enumerable outcome spaces of ONE transactional tool with structured responses; free-text outcome interpretation and genuinely novel outcome categories were not injectable without breaking the frozen tool contract (IT-066 deviation note) and remain agent territory by the m-family evidence and by construction of the default-stop."
  ]
 },
 {
  "cell_type": "markdown",
  "metadata": {},
  "source": [
   "### Ergebnisse in einfacher Sprache (plain-language summary, Family S)\n",
   "\n",
   "Familie S hat getestet, **wie viel \"Agent\" man in einen Workflow einbauen kann, ohne einen Agent zu bauen** \u2014 mit einer dritten Form: einem Workflow, der wie eine Weiche vorgeplante Pfade je nach Tool-Antwort (Erfolg / abgelehnt / schon geschlossen) nimmt. Wichtig: Das LLM plant weiterhin alles VORHER; zur Laufzeit w\u00e4hlt eine deterministische Weiche nur den vorgebauten Pfad.\n",
   "\n",
   "**Fall 1 \u2014 Die Regeln reagieren auf Tool-Antworten (s1):** Vorher 0/25 f\u00fcr den Workflow. **Mit der Weiche: auf dem starken Modell 5/5 \u2014 zu Workflow-Kosten** (\u22485.000 Tokens; der Agent zahlt knapp das Dreifache). Die alte Null lag also an der zu einfachen Workflow-Bauform, nicht am Paradigma.\n",
   "\n",
   "**Fall 2 \u2014 \"Mach weiter, bis das System ablehnt\" (s2):** Vorher 0/25. **Mit Weiche + Schleife + Stopp-Bedingung: 5/5 auf dem starken Modell**, gleichauf mit dem Agent, zu gut einem Viertel der Agent-Kosten.\n",
   "\n",
   "**Fall 3 \u2014 Der Bericht muss sagen, was WIRKLICH passiert ist (s3):** Hier bricht die Weiche: Sie kann Pfade w\u00e4hlen, aber keinen **Inhalt** erzeugen, der erst zur Laufzeit entsteht (welche Cases wurden tats\u00e4chlich geschlossen?). Workflow 2/25, Weiche 4/25, **Agent 13/25**. Die Kontrollinstanz beweist den Mechanismus: Wenn nichts Unvorhersehbares passiert, schaffen es alle drei.\n",
   "\n",
   "**Die Regel f\u00fcr den Architekten:** Frage nicht mehr nur *\"Steuert Laufzeit-Information den Prozess?\"*, sondern auch: *\"Kann ich alle m\u00f6glichen Antworten des Systems VORHER aufz\u00e4hlen \u2014 und muss nur der PFAD darauf reagieren, oder auch der INHALT?\"* Aufz\u00e4hlbare Antworten + Pfadwahl \u2192 Workflow mit Weiche (ab starkem Modell, deutlich billiger). Nicht aufz\u00e4hlbar oder Inhalt laufzeitabh\u00e4ngig \u2192 Agent. Und unterhalb des starken Modells gilt wieder: Modellst\u00e4rke pr\u00fcfen \u2014 dieselbe Bedingung wie bei X-3."
  ]
 }
]


def main() -> None:
    nb = json.loads(NB.read_text())
    if any(c["cell_type"] == "markdown" and "".join(c["source"]).startswith("## 7. Family S")
           for c in nb["cells"]):
        raise SystemExit("Family-S section already present -- nothing to do.")
    backup = NB.with_name(f"results_analysis_phase2b.backup_{datetime.now():%Y%m%d_%H%M%S}.ipynb")
    backup.write_text(json.dumps(nb, indent=1))
    idx = next((i for i, c in enumerate(nb["cells"])
                if c["cell_type"] == "markdown"
                and "".join(c["source"]).startswith("## Appendix (exploratory) — paradigm radar")),
               len(nb["cells"]))
    nb["cells"] = nb["cells"][:idx] + NEW_CELLS + nb["cells"][idx:]
    NB.write_text(json.dumps(nb, indent=1))
    print(f"Inserted {len(NEW_CELLS)} cells at position {idx}; backup: {backup.name}")
    print("Now: open the notebook and Run All (the loader picks up the S sweeps automatically).")


if __name__ == "__main__":
    main()
