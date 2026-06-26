# Solution Landscape — Segmentation & Feature Discovery (Use Case #3)

Research on readily-available tools, libraries, and GitHub repos to execute this
use case, with a build-vs-buy read and the recommended demo stack.

## What the use case actually is (frame this correctly)

The spreadsheet calls it "Segmentation," which pulls toward K-means clustering —
**resist that.** Every piece of evidence is *supervised*: there is a target
(response / booking rate), the team used *one-feature decision-tree cuts to find
thresholds*, and they validated with *"Seg 2: 0.031% vs 0.214% BAU."* The
plain-English goal is "which bucket definitions are most **useful for the
business**" — usefulness measured against an outcome.

That is the textbook definition of **subgroup discovery** (a.k.a. rule-based /
supervised segmentation, emerging-pattern mining): *find describable subsets
whose target distribution is interesting.* It gives ranked, human-readable rules
with target stats — exactly the deliverable. Unsupervised clustering is a
secondary "we can also do this" aside, not the centerpiece.

---

## Tier 1 — On-the-nose engines (the spine of the build)

| Tool | What it does | Fit | Link |
|---|---|---|---|
| **pysubgroup** | Ranked human-readable rules with target stats; beam/Apriori/DFS search; pandas-native | ★★★ exact match — this is the centerpiece | [github.com/flemmerich/pysubgroup](https://github.com/flemmerich/pysubgroup) · [PyPI](https://pypi.org/project/pysubgroup/) |
| **skope-rules** | Learns precise logical rules to "scope" a target class (between a decision tree and random forest) | ★★★ rule extraction w/ precision/recall | [github.com/scikit-learn-contrib/skope-rules](https://github.com/scikit-learn-contrib/skope-rules) |
| **imodels** | sklearn-compatible bundle of interpretable rule models (RuleFit, Skope, FIGS, Bayesian rule lists, etc.) | ★★★ one import, many rule algos | [github.com/csinva/imodels](https://github.com/csinva/imodels) |
| **RuleFit** | Sparse linear model over decision-rule features incl. interactions | ★★ ranked rules + effect sizes | [interpretable-ml-book/rulefit](https://christophm.github.io/interpretable-ml-book/rulefit.html) |
| **sklearn DecisionTree** | Depth-1/2 trees = the exact "one-feature cuts" the real project used | ★★★ baseline / v0 | scikit-learn |

> **Driver analysis (R31):** **SHAP** ([github.com/shap/shap](https://github.com/shap/shap))
> for feature importance + partial dependence, to confirm rules are mechanistically
> sensible.

## Tier 2 — AutoML / clustering (the unsupervised "also")

| Tool | Note | Link |
|---|---|---|
| **PyCaret** (clustering module) | Low-code K-means/HDBSCAN + profiling; good for the unsupervised aside | [pycaret.org](https://pycaret.gitbook.io/docs/) |
| **H2O AutoML / DataRobot** | Enterprise AutoML; named in the source sheet; heavier, paid (DataRobot) | h2o.ai / datarobot.com |
| **Databricks AutoML** | If the client is already on Databricks | databricks.com |

These find *statistical* clusters but not *target-relevant, rule-described*
segments — keep them secondary.

## Tier 3 — Agentic / LLM data-analyst frameworks (the "agentic" wrapper)

| Tool | What it gives you | Link |
|---|---|---|
| **Claude Code + skills/tools** (recommended) | Agent plans, runs the Python tools, reads outputs, narrates — exactly this demo | — |
| **MetaGPT — Data Interpreter** | Open-source agent: plan → write code → execute in notebook; SOTA on data tasks | [github.com/FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) (`examples/di`) |
| **PandasAI** | Conversational pandas/SQL; code in a sandbox; quick EDA | [github.com/sinaptik-ai/pandas-ai](https://github.com/sinaptik-ai/pandas-ai) |
| **Microsoft Data Formulator** | AI-driven visual data exploration, agent mode | [github.com/microsoft/data-formulator](https://github.com/microsoft/data-formulator) |
| **EDA-GPT** | Automated LLM-driven EDA; benchmarks above PandasAI on complex queries | [github.com/shaunthecomputerscientist/EDA-GPT](https://github.com/shaunthecomputerscientist/EDA-GPT) |
| **Julius AI** (hosted) | Autonomous EDA, no-code; good for the "what's out there" slide | julius.ai |
| **OpenAI Code Interpreter / LangGraph** | Sandboxed code execution / statistical-reasoning agent orchestration | — |

> The 2025 research scene (DataSciBench, MLE-Dojo, Data Interpreter) confirms
> code-writing agents are now SOTA for data-science tasks — but the *quality* of
> segment discovery still comes from the specialized library underneath. The
> agent's value is orchestration + narration + human-in-the-loop, not replacing
> pysubgroup.

---

## Build vs Buy

- **Buy/hosted (Julius, DataRobot, Data Formulator):** fast to show, but black-box,
  data leaves the building (bank blocker), and they don't produce the *suppression-
  rule* output the project needs.
- **Build (recommended):** thin agent (Claude Code skill) orchestrating
  `pysubgroup + sklearn + SHAP`. ~200 lines, runs locally on bank data, produces
  exactly the ranked-validated-rules deliverable, and maps 1:1 to the manual steps
  it replaces (auditable for a regulated client).

## Recommended demo stack

```
Claude Code (agent + skill)        <- orchestration, narration, human-in-the-loop
   └── pysubgroup                  <- multi-feature rule discovery (core)
   └── scikit-learn DecisionTree   <- single-feature cuts (v0, mirrors manual)
   └── SHAP                        <- driver analysis (why)
   └── pandas                      <- EDA, stability across windows
```

**Surface:** Claude Code is the natural fit (it executes Python). **Cowork** is the
packaging path if you later want to hand a connector/plugin to non-technical
analysts.

## Mapping to the real project steps (R27–R32)

| Project step | Demo stage | Tool |
|---|---|---|
| R27 EDA | v0 | `tree_cuts.py` (+ BAU) |
| R28 Hypothesis testing | v0/v2 | rate comparisons |
| R29 Segmentation | **v1** | `subgroup_search.py` (pysubgroup) |
| R30 Trend / time-series | v2 | `stability.py` (windows) |
| R31 Driver analysis | v3 | `drivers.py` (SHAP) |
| R32 Validation | v2 | stability threshold |

---
### Sources
- [pysubgroup (GitHub)](https://github.com/flemmerich/pysubgroup) · [PyPI](https://pypi.org/project/pysubgroup/) · [docs](https://pysubgroup.readthedocs.io/)
- [skope-rules](https://github.com/scikit-learn-contrib/skope-rules) · [imodels](https://github.com/csinva/imodels) · [RuleFit chapter](https://christophm.github.io/interpretable-ml-book/rulefit.html)
- [MetaGPT / Data Interpreter](https://github.com/FoundationAgents/MetaGPT) · [PandasAI](https://github.com/sinaptik-ai/pandas-ai) · [Data Formulator](https://github.com/microsoft/data-formulator) · [EDA-GPT](https://github.com/shaunthecomputerscientist/EDA-GPT)
- [PyCaret clustering](https://pycaret.gitbook.io/docs/) · [Data Interpreter paper](https://arxiv.org/html/2402.18679v1) · [DataSciBench](https://arxiv.org/html/2502.13897v1)
