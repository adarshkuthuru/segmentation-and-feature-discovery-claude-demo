# Segment & Feature Discovery — Agentic Demo

Demo for **Use Case #3 — Segmentation & Feature Discovery** (Agentic AI Capability
Evaluation). Finds interpretable segments that deviate sharply from the base rate
on a target outcome — replacing the **3–5 weeks** of manual EDA, hypothesis
testing, and rule development the *DM Non-Responder* project required.

> **Supervised subgroup discovery, not clustering.** There is a target (did they
> respond / book / churn?); a good segment is a simple, explainable *rule* that
> deviates from BAU, is large enough to act on, and is stable over time.

## Design: generic skill + per-example run spec

The skill and tools are **100% dataset-agnostic**. Everything example-specific
lives in a **JSON run spec** (`config.json`). To point the demo at a new dataset
you write a spec — you never edit the tools.

```
segment-discovery-demo/
├── .claude/skills/segment-discovery/SKILL.md   # the agent (generic; reads/writes a run spec)
├── spec.template.json                          # annotated run-spec template
├── config.json                                 # example A: real credit-card solicitation (BEST)
├── config.dm_campaign.json                     # example B: synthetic DM suppression
├── run_demo.py                                 # orchestrator: python run_demo.py [--config ...]
├── tools/
│   ├── common.py            # spec loader, sentinel cleaning, target derivation, stats
│   ├── tree_cuts.py        # v0 single-feature decision-tree cuts
│   ├── subgroup_search.py  # v1 multi-feature subgroup discovery (pysubgroup)
│   ├── stability.py        # v2 stability across a time/cohort column
│   └── drivers.py          # v3 SHAP driver analysis
├── data/
│   ├── Sample_Data.csv               # real 100k-row solicitation file (tri-bureau)
│   ├── BEST_Data_Dictionary.xlsx     # attribute dictionary + sentinel codes
│   └── generate_synthetic.py         # makes dm_campaign.csv (synthetic, planted segments)
└── outputs/                          # CSVs + REPORT.md (generated)
```

### The run spec (`config.json`)
Documented in [`spec.template.json`](spec.template.json) and `tools/common.py`.
Tells the tools: the data file, **how to derive the 0/1 target**, `direction`
(suppression vs targeting), which columns are IDs / **leakage to exclude**, the
feature set (or `null` to auto-select), an optional `time_column` for stability,
and the **missing-value sentinels** to treat as NaN.

## Setup
```bash
pip install pandas scikit-learn pysubgroup shap openpyxl
python data/generate_synthetic.py     # only needed for the synthetic example
```

## Run it (deterministic, no LLM)
```bash
python run_demo.py                          # example A (config.json = BEST sample)
python run_demo.py --config config.dm_campaign.json   # example B (synthetic)
# or stage-by-stage:
python tools/tree_cuts.py --config config.json
python tools/subgroup_search.py --config config.json   # <- the money shot
python tools/stability.py --config config.json
python tools/drivers.py --config config.json
```

## Run it agentically (the actual demo)
Open this folder in **Claude Code** and either give the details or let it figure
them out:

> *"Find suppression segments in data/Sample_Data.csv. Response = an application
> was received (BCP_APPLICATION_ID present). Use the BEST data dictionary for
> the bureau attributes and sentinel codes. Exclude any post-outcome fields."*

…or cold-start:

> *"Here's data/Sample_Data.csv and BEST_Data_Dictionary.xlsx — figure out a
> sensible target and predictive fields, flag any leakage, and find me low-
> response segments to suppress."*

The `segment-discovery` skill inspects the data + dictionary, writes a run spec,
runs the stages, and narrates ranked, validated rules for the analyst to accept
or reject. See [SKILL.md](.claude/skills/segment-discovery/SKILL.md) (Path A =
details given, Path B = cold start with research).

## Two worked examples

**A — Real credit-card solicitation (`config.json`).** 100k prospects, tri-bureau
attributes, derived target `responded = BCP_APPLICATION_ID present` (**BAU
0.41%**). Sentinels (`997/998/999`, `9999997-9`) → NaN; `BCP_*`/`PV` excluded as
leakage; one bureau (EFX) used to avoid redundant triplets; stability across
`SOLICITATION_ID`. Surfaces e.g. `EFX_BC_UTIL_1∈[16,35) AND FICO∈[694,730)` →
0.09% (0.21x lift).

**B — Synthetic DM suppression (`config.dm_campaign.json`).** 200k rows with three
*planted* low-response segments the pipeline rediscovers (built-in validation):
e.g. `age>=72 AND total_balance<1182` → 0.037% vs 0.18% BAU (0.21x).

## Notes
- See [SOLUTION_LANDSCAPE.md](SOLUTION_LANDSCAPE.md) for the build-vs-buy / tooling
  research and [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the live run-of-show.
- **Leakage is the #1 risk**: any field known only after the outcome must be in
  `exclude_columns`. The skill is explicit about this.
