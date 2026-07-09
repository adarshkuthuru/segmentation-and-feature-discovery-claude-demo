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

**Golden rule: this skill and the `tools/segmentation/` scripts are 100% generic.
Everything specific to an example lives in a JSON run spec (`config.json`). Your
job is to produce a correct run spec, then run the stages and narrate.** Never
hardcode a column name, target, or path into the tools.

## The run spec is the contract
The tools read a JSON spec (schema documented in `tools/segmentation/common.py`, template in
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

### Before starting — read project documentation and context

Read these files at the project root **before** running any pipeline stage:

1. **`README.md`** — current directory structure, run commands, and conventions.
   Use this to verify file paths, understand what scripts exist, and catch any
   structural changes since the last session.
2. **`CHANGELOG_segmentation.md`** — recent additions, deletions, and modifications
   to the segmentation pipeline. Surfaced automatically when you run the memory
   command below; also readable directly if you want only the changelog.
3. Run `python tools/segmentation/memory.py --action read --config config.json`
   — prints recent run memory (BAU, rules, SHAP) **and** the last 5 changelog
   entries in one pass.

Use what you see to:
- Verify the scripts and paths in README.md match what actually exists before running.
- Call out features that were **reliable in prior runs** (cross-run signal = higher confidence).
- Warn if a rule resembles an **unstable rule from a prior run**.
- Flag if BAU or best lift **deviates materially** from the typical range.
- Note any high-null features flagged before.
- Flag recent structural changes that might affect this run.

---

### Before running the stages — archive prior outputs, then enforce retention

Before any stage overwrites `outputs/segmentation/`, copy the current
`v0_tree_cuts.csv`, `v1_subgroups.csv`, `v2_stability.csv`, `v3_drivers.csv`,
`REPORT.md`, and the current `.pptx` deck into `archives/` with a
`_archived_<today's date>` suffix on each filename (flat files, no
per-date subdirectories — that is the wrong convention; see below).

**Retention cap: keep only the 30 most recent archived run-dates in
`archives/`, discard the rest.**

1. List everything in `archives/` and extract the run-date from each entry:
   - flat files use the `_archived_YYYY-MM-DD` suffix in the filename.
   - any legacy per-date subdirectory (e.g. `archives/2026-07-06/`) counts as
     one run-date too — flatten it into the standard file-suffix convention
     while you're at it, since a subdirectory is stale-convention clutter.
2. Collect the **distinct** run-dates represented, sort descending (newest
   first).
3. If there are more than 30 distinct dates, delete every file (and any
   leftover legacy subdirectory) whose run-date falls outside the 30 most
   recent — do this **before** copying today's outputs in, so today's run
   never gets pruned.
4. Note what was pruned (dates removed, file count) in the
   `CHANGELOG_segmentation.md` entry for this session, e.g.
   `Archive retention: pruned N files older than the 30 most recent runs.`

1. **EDA & one-feature cuts** — `python tools/segmentation/tree_cuts.py [--config ...]`
   Establish BAU; show single-feature thresholds. Note single features are
   usually weak alone → motivates the multi-feature search.
2. **Multi-feature subgroup search** — `python tools/segmentation/subgroup_search.py`
   The core. Ranked multi-condition rules with size + rate + lift. These are the
   non-obvious combinations the manual loop misses.
3. **Stability validation** — `python tools/segmentation/stability.py`
   Re-checks each top rule within each `time_column` value; flags any that is not
   persistently on the right side of BAU. (No-op if no `time_column`.)
4. **Driver analysis** — `python tools/segmentation/drivers.py`
   SHAP ranking of global drivers; confirm the rules are mechanistically sensible.
5. **Report** — write ranked, validated segments + a business headline to
   `outputs/segmentation/REPORT.md` (via `run_demo.py` if present, else compile
   directly from the stage CSVs).

### After completing — update memory, changelog, and README

**Always run:**
```
python tools/segmentation/memory.py --action write --config config.json
```
This writes the full run entry to `memory_segmentation.md` **and** appends a
lightweight run entry to `CHANGELOG_segmentation.md` automatically.

**If structural changes were made** during this session (new files, deleted files,
modified scripts, config edits, new outputs added to the directory tree), do **all three**:

1. Append a `[structural]` entry to `CHANGELOG_segmentation.md`:
   ```
   ## YYYY-MM-DD HH:MM — [brief title] [structural]

   ### Added
   - `path/to/file` — one-line description

   ### Deleted
   - `path/to/file` — reason

   ### Modified
   - `path/to/file` — what changed and why
   ```

2. Update `README.md` to reflect the change — specifically the directory tree,
   the "Run it" commands, or the "Output & archiving convention" section if any
   of those are now out of date.

3. Verify `README.md` is consistent with what actually exists on disk (directory
   tree, file names, run commands) before ending the session.

## Rules of engagement
- **Never invent statistics** — read the tool's CSV in `outputs/segmentation/`, then narrate.
- **Confidence/lift is deterministic** (computed in the tools); you interpret.
- **Human-in-the-loop**: present ranked rules to accept/reject; don't auto-decide.
- **Guard against leakage** — the single most common failure. Anything populated
  only after the outcome must go in `exclude_columns`.
- For a **new dataset**, you only ever write a new spec — the tools don't change.
