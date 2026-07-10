---
name: dataset-analyzer
description: >
  Analyze any dataset using Python and the Polars library. Use this skill whenever the user asks to
  analyze, explore, inspect, profile, or summarize a dataset. Also trigger when the user uploads a CSV,
  Parquet, JSON, or Excel file and asks questions like "what does this data look like", "check for missing
  values", "show me stats", "describe the data", "how many nulls", "what are the columns", "find
  duplicates", "detect outliers", "show correlations", "check distributions", "is my data clean", or any
  variation of exploratory data analysis (EDA). Even if the user simply says "take a look at this data" or
  "tell me about this file", this skill should activate. This is the EXECUTOR skill: it produces a full
  5-phase EDA report (Markdown + charts) and a non-technical executive deck. Pair it with the eda-reviewer
  skill to audit the report afterwards.
---

# Dataset Analyzer (EDA Executor)

Perform a professional, checklist-driven exploratory analysis of any tabular dataset using **Python** and
the **Polars** library, with charts via **matplotlib/seaborn**. The methodology follows a 20-item, 5-phase
standard. The final deliverables are:

1. `output/<dataset>_eda_report.md` — the full report, with embedded charts.
2. `output/figures/*.png` — every chart referenced by the report.
3. `output/<dataset>_executive_summary.pptx` — a short, non-technical deck for executives.

After the report is written, an optional **eda-reviewer** pass audits it for completeness and quality.

## Cross-run memory and changelog

### Before starting — read project documentation and context

Read these files at the project root **before** running any analysis:

1. **`README.md`** — current directory structure, tool locations, and conventions.
   Use this to verify EDA script paths and understand what templates exist.
2. **`CHANGELOG_EDA.md`** — recent additions, deletions, and modifications to the
   EDA workstream (scripts, templates, tool updates). Read this to catch any changes
   since the last session before writing new code or running existing scripts.
3. **`memory_eda.md`** — prior run findings for the same dataset (data-quality issues
   already known, sentinel codes confirmed, key structural findings). Skim the most
   recent entry.

### After completing — update memory, changelog, and README

**Always append to `memory_eda.md`:** date, dataset + row/column count,
target/derivation if any, the most important quality finding, where the artifacts
were written. Terse — this is a lookup aid, not a duplicate of the report.

**Always append a run entry to `CHANGELOG_EDA.md`:**
```
## YYYY-MM-DD — [dataset name] [run]

**Dataset:** path/to/file (N rows × M columns)
**Target (derived):** [how target was derived and base rate]
**Key finding:** [single most important quality or structural finding]
**Outputs:** [list of files written]
```

**If structural changes were made** (new scripts, deleted files, modified tools,
new templates), do **all three**:

1. Append a `[structural]` entry to `CHANGELOG_EDA.md`:
   ```
   ## YYYY-MM-DD — [brief title] [structural]

   ### Added / Deleted / Modified
   - `path/to/file` — description
   ```

2. Update `README.md` to reflect the change — specifically the directory tree or
   the "Skills available" / "Output & archiving convention" sections if any of
   those are now out of date.

3. Verify `README.md` is consistent with what actually exists on disk (file names,
   tool paths, script names) before ending the session.

## Setup

Install the core and plotting libraries. Excel and time-series diagnostics are optional extras:

```bash
pip install polars matplotlib seaborn        # core + charts
pip install openpyxl                          # only for .xlsx / .xls input
pip install scipy statsmodels                 # optional: kurtosis, ADF/KPSS/ACF (time-series only)
```

Import defensively so a missing optional library degrades gracefully instead of crashing:

```python
try:
    import matplotlib
    matplotlib.use("Agg")  # headless: write PNGs without a display
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAVE_PLOTS = True
except ImportError:
    HAVE_PLOTS = False
```

If a plotting library is unavailable, still produce the numeric report and note which charts were skipped.

## Artifacts & conventions

- Report: `output/<dataset>_eda_report.md`. Charts: `output/figures/<name>.png`, referenced with **relative**
  links so they resolve from the report's location, e.g. `![Correlation heatmap](figures/corr_heatmap.png)`.
- Create both `output/` and `output/figures/` up front (`Path(...).mkdir(parents=True, exist_ok=True)`).
- On Windows, write the report as UTF-8 (`open(path, "w", encoding="utf-8")`) and, if you also print to the
  console, reconfigure stdout to UTF-8 (`sys.stdout.reconfigure(encoding="utf-8")`) so emoji/box glyphs do
  not crash under cp1252.

## Step 1: Load the data

Detect the file format from its extension and load accordingly.

```python
import polars as pl

ext = path.lower().rsplit(".", 1)[-1]
if ext == "csv":
    df = pl.read_csv(path)
elif ext == "parquet":
    df = pl.read_parquet(path)
elif ext in ("json", "jsonl"):
    try:
        df = pl.read_ndjson(path)
    except Exception:
        df = pl.read_json(path)
elif ext in ("xlsx", "xls"):
    df = pl.read_excel(path)
```

Print a preview (`df.head(5)`) so the raw data is visible before analysis.

## Step 2: Classify columns (drives phase gating)

Auto-detect each column's role so the specialized phases (18-20) gate themselves:

- **numeric** — `dtype.is_numeric()`.
- **datetime** — already a Date/Datetime dtype, OR a string column where most values parse as dates.
- **free-text** — a string column with high uniqueness AND a high average token count (e.g. avg > 5 words).
- **categorical** — every other string column.

Time-based (Phase 5, #18-19) runs only if a **datetime** column exists; text EDA (#20) runs only if a
**free-text** column exists. Otherwise emit a one-line "Not applicable — no datetime/free-text columns
detected" so the section is explicitly present, not silently dropped.

## Sentinel handling (applies to every count below)

Treat common sentinel codes as missing before counting nulls or computing stats, so hidden missingness is
not masked:

```python
SENTINEL_NUMBERS = [-1, -999, -9999, 999, 9999]
SENTINEL_STRINGS = ["n/a", "na", "null", "none", "unknown", "missing", "?", "", " "]
```

Replace numeric sentinels with null in numeric columns, and case-insensitive string sentinels with null in
string columns, then run the audits on the cleaned frame. **Note** in the report that this was done and how
many values it converted.

---

# The 5-phase / 20-item methodology

Each item below lists **what to compute**, the **why it matters** rationale, and (where relevant) the chart
to save. Skip an item only when it is genuinely not applicable, and say so.

## Phase 1 — Business & Data Understanding

**1. Project Overview & Objective.** State the business question if the user/prompt gave one; otherwise emit
a generic objective ("Exploratory profiling of <dataset> to assess quality and structure before modeling").
*Why: anchors every downstream step to a decision.*

**2. Dataset Shape & Structure.** Rows, columns, per-column dtype, a 5-row sample, and the **grain** (what
one row represents, e.g. "one flower sample"). *Why: fast mental map.*

**3. Data Dictionary.** If a sidecar dictionary exists (`data/<name>_dictionary.csv`/`.md`), use it.
Otherwise auto-generate a column/inferred-meaning table and label it "inferred". Flag raw vs derived.
*Why: prevents misinterpretation later.*

## Phase 2 — Data Quality Checks

**4. Duplicate Records.** Full-row duplicate count via `df.is_duplicated().sum()`; show a couple of examples;
note partial-key duplicates if an ID-like column exists. *Why: duplicates inflate counts and skew stats.*

**5. Missing Value Analysis.** Null count, null %, and **fill rate** per column (after sentinel handling).
Flag >5%, warn loudly >50%. Save a **missingness matrix** PNG. Heuristic for random vs systematic: correlate
the null masks across columns. *Why: missingness affects every downstream statistic.*

**6. Type Mismatches / Mixed Types.** Flag string columns fully castable to numeric, string columns
parseable as dates, and columns with mixed/inconsistent types. *Why: mixed types break aggregations and hide
invalid values.*

**7. Inconsistent Categorical Labels.** Per string column, detect values that collapse to the same canonical
form under lower-casing / trimming (e.g. `"NY "`, `"ny"`, `"NY"`); report collisions. *Why: silently splits
one category into several.*

**8. Range & Domain Violations.** Generic rules — negatives where a column is otherwise non-negative, future
dates, percentages outside 0-100 — plus per-column rule hooks. *Why: points to upstream data-entry/pipeline
errors.*

**9. Redundant / Near-Duplicate Features.** Flag numeric pairs with |Pearson r| > 0.95, and any duplicate or
constant columns. *Why: redundancy adds noise and multicollinearity.*

## Phase 3 — Univariate & Distribution Analysis

**10. Descriptive Statistics (Numeric).** count, mean, std, and percentiles **0, 1, 5, 25, 50, 75, 95, 99,
100**. Flag min/max that look like entry errors. *Why: numeric baseline + early error detection.*

**11. Descriptive Statistics (Categorical).** cardinality, top-N value counts, most frequent value. Flag
**high-cardinality** columns that will need an encoding strategy. *Why: surfaces rare categories/structural
issues.*

**12. Distribution Analysis.** Skewness and **kurtosis** per numeric column; suggest a transformation
(e.g. log / Box-Cox) when strongly skewed. Save **histogram** and **box-plot** PNGs. *Why: drives
scaling/transformation decisions.*

**13. Outlier Detection.** **IQR** (1.5×IQR fences) and **Z-score** (|z|>3) per numeric column; report counts
and bounds. Document outliers — do not auto-remove. *Why: outliers distort averages, correlations, models.*

## Phase 4 — Relationship & Target Analysis

**14. Correlation Analysis.** Pearson matrix for numeric features + a **heatmap** PNG; list the strongest
positive/negative pairs. *Why: feature selection + multicollinearity.*

**15. Target Variable Deep Dive.** If a target is named or inferred, analyze its distribution; for
classification report **class balance** (counts + imbalance ratio). *Why: determines modeling approach and
metrics.*

**16. Bivariate / Multivariate.** Feature-vs-target box plots and/or a **pairplot** PNG; bring in a third
variable via color where useful. *Why: surfaces interactions univariate analysis misses.*

**17. Feature Interactions & Derived Insights.** Note candidate engineered features (e.g. an area = length ×
width). *Why: feeds feature engineering.*

## Phase 5 — Segment, Time & Specialized Analysis (gated)

**18. Time-Based Trends** *(only if a datetime column exists)* — seasonality, trend, timeline anomalies.

**19. Time-Series Deep Dive** *(only if datetime + statsmodels)* — stationarity (ADF/KPSS), ACF/PACF, rolling
mean/std, lag & change-point notes. Else skip with a one-line note.

**20. Text-Specific EDA** *(only if a free-text column exists)* — token/word-count distribution, vocabulary
size, top terms, encoding issues. Else skip with a one-line note.

When a Phase 5 item does not apply, still print its header with "Not applicable — <reason>".

---

## Presentation guidelines

- Lead the report with a **plain-language executive summary**: what the dataset is, whether it is clean, and
  the top things to fix first.
- One section per phase, one sub-section per item, using clear headers.
- Use tables for stats; embed charts with relative links; caption every chart.
- Proactively call out anything unusual (extreme skew, near-constant columns, class imbalance, redundant
  features, domain violations).
- End with a prioritized **Recommended Next Steps** list.

## Final step: Executive deck (`.pptx`)

After the report is finalized, generate a short **non-technical** deck with the `anthropic-skills:pptx`
skill, reusing the charts in `output/figures/`. Write it to `output/<dataset>_executive_summary.pptx`.

- **Audience:** executives. No jargon — avoid "kurtosis", "Z-score", "cardinality", "multicollinearity".
  Translate to plain business language ("a few unusually large values", "these two measurements say the same
  thing").
- **Every slide leads with a takeaway**, not a statistic. Keep it to ~6-8 slides:
  1. Title — dataset, purpose, date.
  2. What this data is: Dataset Shape & Structure.
  3. A slide for the Phase 2: Data Quality Checks.
  4. Slide for the Phase 3 — Univariate & Distribution Analysis
  5. Slide for the Phase 4 — Relationship & Target Analysis
  6. Optional Slide (if applicable) for Phase 5 — Segment, Time & Specialized Analysis (gated)
  6. Issues to address before modeling — the cleanup list in business terms.
  7. Recommended next steps — what this enables.
- Numbers must match the report exactly (derive the deck from the finalized report, do not recompute).

## Edge cases

- File unreadable → report the error clearly and suggest checking path/format.
- Zero rows → state it and skip the statistics phases.
- All non-numeric → skip numeric percentiles/correlation; focus on categorical + text.
- >1M rows → note performance; consider sampling for the plots only (compute stats on the full frame).
- A column with mixed/unparseable types → flag it rather than silently coercing.
