# Segment & Feature Discovery — Agentic Demo

Demo for **Use Case #3 — Segmentation & Feature Discovery** (Agentic AI Capability
Evaluation). Finds interpretable segments that deviate sharply from the base rate
on a target outcome — replacing the manual EDA, hypothesis testing, and rule
development a suppression / targeting analysis usually requires.

> **Supervised subgroup discovery, not clustering.** There is a target (did they
> respond / book / churn?); a good segment is a simple, explainable *rule* that
> deviates from BAU (business-as-usual base rate), is large enough to act on, and
> is stable over time.

## Design: generic skills + per-example run spec

The `segment-discovery` skill and its `tools/segmentation/` scripts are **100%
dataset-agnostic**. Everything example-specific lives in a **JSON run spec**
(`config.json`). To point the pipeline at a new dataset you write a spec — you
never edit the tools.

```
segmentation-and-feature-discovery-claude-demo/
├── README.md
├── config.json                        # active run spec (Capital One DM suppression)
├── spec.template.json                 # annotated run-spec template — copy this for a new dataset
├── memory_segmentation.md             # auto-maintained cross-run memory (tools/segmentation/memory.py)
├── memory_eda.md                      # cross-run memory for the dataset-analyzer (EDA) workstream
│
├── docs/
│   ├── SOLUTION_LANDSCAPE.md          # build-vs-buy / tooling research
│   ├── Segment Discovery Demo steps.docx   # live demo walkthrough
│   └── templates/                     # Zenon brand assets used by the PPT builders
│       ├── Zenon_2026_Template.pptx
│       └── Zenon Logo.PNG
│
├── tools/
│   ├── segmentation/                  # the discovery pipeline (dataset-agnostic)
│   │   ├── common.py                  # spec loader, sentinel cleaning, target derivation, stats
│   │   ├── tree_cuts.py               # v0 single-feature decision-tree cuts
│   │   ├── subgroup_search.py         # v1 multi-feature subgroup discovery (pysubgroup)
│   │   ├── stability.py               # v2 stability across a time/cohort column
│   │   ├── drivers.py                 # v3 SHAP driver analysis
│   │   ├── memory.py                  # reads/writes memory_segmentation.md across runs
│   │   ├── build_ppt_2026_07_06.py    # branded executive PPT builder (segment-discovery results)
│   │   └── build_overview_ppt.py      # 2-slide overview deck builder
│   └── EDA/                           # generic 5-phase/20-item EDA (dataset-agnostic)
│       ├── eda_full_data.py           # EDA executor — runs on the full dataset, no subsampling
│       └── make_exec_deck_full_data.py    # non-technical exec deck for the full dataset
│
├── data/
│   ├── Sample_Data.csv                # real 100k-row solicitation file (tri-bureau)
│   └── BEST_Data_Dictionary.xlsx      # attribute dictionary + sentinel codes
│
├── outputs/
│   ├── EDA/                           # dataset-analyzer artifacts: report, figures, exec deck
│   └── segmentation/                  # segment-discovery artifacts: v0-v3 CSVs, REPORT.md, .pptx decks
│
├── archives/                          # date-stamped copies of prior outputs (archived before overwrite)
│
└── .claude/skills/                    # Claude Code agent skills — see "Skills available" below
    ├── segment-discovery/
    ├── segment-discovery-reviewer/
    ├── dataset-analyzer/
    ├── eda-reviewer/
    └── business-writing-and-advisory/
```

### The run spec (`config.json`)
Documented in [`spec.template.json`](spec.template.json) and
`tools/segmentation/common.py`. Tells the tools: the data file, **how to derive
the 0/1 target**, `direction` (suppression vs targeting), which columns are IDs /
**leakage to exclude**, the feature set (or `null` to auto-select), an optional
`time_column` for stability, and the **missing-value sentinels** to treat as NaN.

## Setup
```bash
pip install pandas scikit-learn pysubgroup shap openpyxl
```

## Run it (deterministic, no LLM)
Run each stage against the active spec, in order:
```bash
python tools/segmentation/tree_cuts.py --config config.json          # v0: EDA + single-feature cuts
python tools/segmentation/subgroup_search.py --config config.json    # v1: multi-feature rules (the money shot)
python tools/segmentation/stability.py --config config.json          # v2: stability across time windows
python tools/segmentation/drivers.py --config config.json            # v3: SHAP driver analysis
python tools/segmentation/memory.py --action read --config config.json   # cross-run memory context
```
Each stage writes its result to `outputs/segmentation/v0_tree_cuts.csv` …
`outputs/segmentation/v3_drivers.csv`.

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
runs the four stages, and narrates ranked, validated rules for the analyst to
accept or reject. See
[SKILL.md](.claude/skills/segment-discovery/SKILL.md) (Path A = details given,
Path B = cold start with research).

## Worked example

**Real credit-card solicitation (`config.json`).** 100k prospects, tri-bureau
(EFX/EXP/TRU) credit attributes, derived target
`responded = BCP_APPLICATION_ID present` (**BAU 0.41%**, 410/100,000). Sentinels
(`997/998/999`, `9999997-9`) → NaN; `BCP_*`/`PV`/`SOLICITATION_ID`/
`TEST_CELL_DROP_DATE` excluded as leakage; one bureau (EFX) used for the 25
modeled features to avoid redundant tri-bureau triplets; stability checked across
3 mailing waves (`TEST_CELL_DROP_DATE`: 2026-01-06, 2026-02-10, 2026-03-10).

Top rule found: `EFX_AL_DQOCURNC_5==0 AND EFX_BC_DQOCURNC_3==0 AND FICO∈[664,694)`
→ 10,947 prospects (10.95%), 0.24% response (0.58× lift vs BAU), stable across
all 3 waves. See [`outputs/segmentation/REPORT.md`](outputs/segmentation/REPORT.md)
for the full ranked list and SHAP drivers.

## Skills available

| Skill | Role | Purpose |
|---|---|---|
| [`segment-discovery`](.claude/skills/segment-discovery/SKILL.md) | Executor | Runs the v0→v3 pipeline; inspects data, writes the run spec, narrates ranked segment rules |
| [`segment-discovery-reviewer`](.claude/skills/segment-discovery-reviewer/SKILL.md) | Reviewer | Independent QA pass — cross-checks artifacts (spec, CSVs, REPORT, PPT, memory) for quality and accuracy without recomputing |
| [`dataset-analyzer`](.claude/skills/dataset-analyzer/SKILL.md) | Executor | General-purpose 5-phase/20-item EDA on any tabular dataset (Polars); produces a report + executive deck |
| [`eda-reviewer`](.claude/skills/eda-reviewer/SKILL.md) | Reviewer | Audits a `dataset-analyzer` report for completeness, internal consistency, and actionability |
| [`business-writing-and-advisory`](.claude/skills/business-writing-and-advisory/SKILL.md) | Support | Turns rough analysis into business-first, client-ready slide language, memos, and stakeholder writing |

Each executor/reviewer pair follows the same pattern: the executor produces
artifacts from data, the reviewer audits those artifacts for quality and
accuracy — neither re-runs the other's work end-to-end.

## Output & archiving convention

- `outputs/segmentation/` holds the **current** segment-discovery run's
  artifacts: `v0_tree_cuts.csv` … `v3_drivers.csv`, `REPORT.md`, and the
  executive `.pptx` decks.
- `outputs/EDA/` holds the `dataset-analyzer` skill's artifacts: the EDA report,
  its figures, and the non-technical executive deck.
- Before a new run overwrites `outputs/segmentation/`, prior artifacts are
  copied to `archives/<YYYY-MM-DD>/` so run history is never silently lost.
- `memory_segmentation.md` is auto-maintained by `tools/segmentation/memory.py` and persists
  cross-run signal: which features were reliable, which rules were stable, and
  how BAU/lift compare to prior runs — read this before starting a new run.
- PPT decks (`tools/segmentation/build_ppt_2026_07_06.py`,
  `tools/segmentation/build_overview_ppt.py`) are built on the Zenon brand
  template in `docs/templates/Zenon_2026_Template.pptx`.

## Notes
- See [`docs/SOLUTION_LANDSCAPE.md`](docs/SOLUTION_LANDSCAPE.md) for the
  build-vs-buy / tooling research and
  [`docs/Segment Discovery Demo steps.docx`](docs/Segment%20Discovery%20Demo%20steps.docx)
  for the live run-of-show.
- **Leakage is the #1 risk**: any field known only after the outcome must be in
  `exclude_columns`. The skill is explicit about this.
