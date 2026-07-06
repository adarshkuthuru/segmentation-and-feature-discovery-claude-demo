---
name: segment-discovery
description: >
  Discover interpretable customer/entity segments with strong signal on a target
  outcome (response, booking, churn, default, fraud, conversion, value...). Use
  when the user wants segment rules, suppression lists, non-responder cohorts,
  high-value or high-risk groups, "which buckets matter", or feature/driver
  discovery from a labeled (or labelable) table. Runs SUPERVISED subgroup
  discovery (not unsupervised clustering): EDA, single-feature cuts, multi-
  feature rule search, stability validation, and SHAP driver analysis, then
  narrates ranked rules with size + lift vs BAU. Works on ANY dataset — all
  example-specific facts come from the prompt or a JSON run spec, never from the
  skill or the tools.
---

# Segment & Feature Discovery (generic)

You help an analyst find **describable segments** of a population that deviate
sharply from the base rate on a chosen target. This replaces weeks of manual EDA
+ hypothesis testing + rule development.

This is **supervised subgroup discovery**, NOT clustering. There is always a
target (a 0/1 outcome). A good segment is: (1) described by a simple rule on real
features, (2) materially different from BAU on the target, (3) large enough to
act on, (4) stable over time.

**Golden rule: this skill and the `tools/` scripts are 100% generic. Everything
specific to an example lives in a JSON run spec (`config.json`). Your job is to
produce a correct run spec, then run the stages and narrate.** Never hardcode a
column name, target, or path into the tools.

## The run spec is the contract
The tools read a JSON spec (schema documented in `tools/common.py`, template in
`spec.template.json`). Key fields: `data_path`, `target` (how to derive the 0/1
outcome), `direction` (`suppression`=low-rate / `targeting`=high-rate),
`id_columns`, `exclude_columns` (**leakage/post-outcome fields**), optional
`feature_columns` (null = auto), optional `time_column` (stability),
`missing_sentinels`. Write it to `config.json` (or `--config <file>`).

---

## Path A — the user gave you the details
If the prompt (or an attached fields/dictionary file) specifies the target and
columns, just translate that into a run spec:
1. Identify the **target** and the derivation mode (existing 0/1 column,
   `from_notnull` of an ID, or `from_value`).
2. Identify **direction** (suppress low-responders, or target high-responders).
3. Mark **id_columns** and — critically — **exclude_columns** for any field known
   only *after* the outcome (application IDs, account IDs, received dates, post-
   hoc value scores). Leakage here silently destroys the analysis.
4. From a data dictionary, pull **missing_sentinels** (treat default/missing
   codes as NaN; keep legitimate "max valid" caps OUT of the list).
5. Optionally set **feature_columns** to a clean subset (e.g. one bureau to avoid
   redundant triplets) and a **time_column** for stability.
6. Write `config.json`, then run the stages.

## Path B — cold start (no columns/target given)
Figure it out, propose, confirm, then proceed:
1. **Inspect the data**: load it, list columns + dtypes, null rates, cardinality,
   and value ranges. Detect ID-like, date-like, and constant columns.
2. **Read any data dictionary** provided; map categories, metric types, and
   sentinel/missing codes.
3. **Propose the target**: look for a plausible outcome (a 0/1 flag, or an ID/
   date that is populated only for converters → `from_notnull`). State the
   resulting base rate.
4. **Propose features & sources**: pick interpretable, non-leaky predictors. If
   the relevant attributes aren't all present, say what *additional sources/
   fields* would help (e.g. "bureau utilization, tenure, prior-campaign count")
   and, when useful, **research** domain-standard features for this problem type
   (use web search) before recommending what to pull.
5. **Confirm** the proposed spec (target, direction, excluded leakage, features)
   with the user, then write `config.json` and run.

> When you are unsure between suppression vs targeting, or about whether a column
> is leakage, ASK — getting these wrong invalidates the output.

---

## Workflow (run in order; narrate after each, numbers come from the CSVs)

### Before running stages — read memory context
Run `python tools/memory.py --action read --config config.json` (or wait for
`run_demo.py` to print it automatically). Use what you see to:
- Call out features that were **reliable in prior runs** (cross-run signal = higher confidence).
- Warn if a rule in the current results resembles an **unstable rule from a prior run**.
- Flag if the current BAU or best lift **deviates materially** from the typical range (possible
  data drift or config change).
- Note any **high-null features** flagged before, so the analyst isn't surprised again.

---

1. **EDA & one-feature cuts** — `python tools/tree_cuts.py [--config ...]`
   Establish BAU; show single-feature thresholds. Note single features are
   usually weak alone → motivates the multi-feature search.
2. **Multi-feature subgroup search** — `python tools/subgroup_search.py`
   The core. Ranked multi-condition rules with size + rate + lift. These are the
   non-obvious combinations the manual loop misses.
3. **Stability validation** — `python tools/stability.py`
   Re-checks each top rule within each `time_column` value; flags any that is not
   persistently on the right side of BAU. (No-op if no `time_column`.)
4. **Driver analysis** — `python tools/drivers.py`
   SHAP ranking of global drivers; confirm the rules are mechanistically sensible.
5. **Report** — `python run_demo.py` writes `outputs/REPORT.md` with ranked,
   validated segments + a business headline.

## Rules of engagement
- **Never invent statistics** — read the tool's CSV in `outputs/`, then narrate.
- **Confidence/lift is deterministic** (computed in the tools); you interpret.
- **Human-in-the-loop**: present ranked rules to accept/reject; don't auto-decide.
- **Guard against leakage** — the single most common failure. Anything populated
  only after the outcome must go in `exclude_columns`.
- For a **new dataset**, you only ever write a new spec — the tools don't change.
