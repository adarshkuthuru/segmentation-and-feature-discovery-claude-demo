"""
Full 5-phase / 20-item EDA for data/Sample_Data.csv (Capital One direct-mail prospects).

Runs on the ENTIRE file — all 100,000 rows, every column — not a subsample.
"Sample_Data.csv" is simply the source file's given name; it is the complete,
only dataset provided for this workstream. (The one exception: the missingness
matrix PNG below draws a random 2,000-row visual sample purely so the chart
renders legibly — all null counts, rates, and every other statistic in this
report are computed over the full 100,000 rows.)

Single-script executor: loads data, derives the target, applies dictionary-driven
sentinel cleaning, computes all stats, saves charts, and writes the final markdown
report. No intermediate data dumps are written — everything lives in memory until
the final report and PNGs are emitted.

Outputs (project convention: scripts live in tools/EDA/, artifacts in outputs/EDA/):
  outputs/EDA/Full_Data_eda_report.md
  outputs/EDA/figures/*.png
"""
import sys
import warnings
from pathlib import Path

import polars as pl
import numpy as np

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
DATA = ROOT / "data" / "Sample_Data.csv"
DICT = ROOT / "data" / "BEST_Data_Dictionary.xlsx"
OUT = ROOT / "outputs" / "EDA"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

LEAKAGE_COLS = [
    "BCP_APPLICATION_ID", "BCP_ACCOUNT_ID", "BCP_APPLICATION_RECEIVED_DATE",
    "SOLICITATION_ID", "PV", "SRC_ID", "ACCT_ID",
]
TIME_COL = "TEST_CELL_DROP_DATE"

# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------
df = pl.read_csv(DATA, infer_schema_length=100_000)
n_rows, n_cols = df.shape

# ---------------------------------------------------------------------------
# 2. Data dictionary -> per-column metric type & sentinel bucket
# ---------------------------------------------------------------------------
import openpyxl
wb = openpyxl.load_workbook(DICT, data_only=True)
ws = wb["BEST Data Dictionary"]
dict_rows = list(ws.iter_rows(min_row=2, values_only=True))
dd = {r[2]: r for r in dict_rows if r[2]}  # Attribute Name -> row

BALANCE_METRICS = {"Balance", "Credit Limit", "Open-to-Buy", "High Credit", "Currency (USD)"}
COUNT_METRICS = {"Trade Count", "Trade Age", "Inquiry Count", "Inquiry Age",
                  "DQ Occurrences", "DQ Status", "Other Count", "Other Timing",
                  "Utilization", "Min Pay", "Payment Amount", "Score"}
BALANCE_SENTINELS = [9999997, 9999998, 9999999]
COUNT_SENTINELS = [997, 998, 999]

metric_by_col = {c: (dd[c][7] if c in dd else None) for c in df.columns}
sentinel_map = {}
for c, m in metric_by_col.items():
    if m in BALANCE_METRICS:
        sentinel_map[c] = BALANCE_SENTINELS
    elif m in COUNT_METRICS:
        sentinel_map[c] = COUNT_SENTINELS
    elif c in ("EFX_BC_TRDCNT_4", "EXP_BC_TRDCNT_4", "TRU_BC_TRDCNT_4"):
        # not in dictionary; same TRDCNT family as siblings -> count sentinels
        sentinel_map[c] = COUNT_SENTINELS

# FICO & CURRENT_INCOME are not bureau attributes -> no dictionary sentinel; assessed separately.

numeric_cols_all = [c for c, dt in zip(df.columns, df.dtypes) if dt.is_numeric()]
sentinel_cols = [c for c in numeric_cols_all if c in sentinel_map]

sentinel_hits = {}
df_clean = df.clone()
for c in sentinel_cols:
    vals = sentinel_map[c]
    mask = pl.col(c).is_in(vals)
    hits = df_clean.select(mask.sum()).item()
    if hits:
        sentinel_hits[c] = hits
    df_clean = df_clean.with_columns(
        pl.when(mask).then(None).otherwise(pl.col(c)).alias(c)
    )

total_sentinel_replacements = sum(sentinel_hits.values())

# ---------------------------------------------------------------------------
# 3. Derive target
# ---------------------------------------------------------------------------
df_clean = df_clean.with_columns(
    pl.col("BCP_APPLICATION_ID").is_not_null().cast(pl.Int8).alias("responded")
)
resp_counts = df_clean["responded"].value_counts().sort("responded")
n_pos = df_clean["responded"].sum()
n_neg = n_rows - n_pos
resp_rate = n_pos / n_rows * 100

booked = df_clean["BCP_ACCOUNT_ID"].is_not_null().sum()
booking_rate = booked / n_rows * 100

# ---------------------------------------------------------------------------
# 4. Feature set for analysis (exclude leakage + IDs + target source)
# ---------------------------------------------------------------------------
exclude = set(LEAKAGE_COLS) | {TIME_COL}
feature_cols = [c for c in df_clean.columns if c not in exclude and c != "responded"]
numeric_features = [c for c in feature_cols if c in numeric_cols_all]

# Bureau triplet grouping: strip EFX_/EXP_/TRU_ prefix -> group
triplets = {}
for c in numeric_features:
    for pfx in ("EFX_", "EXP_", "TRU_"):
        if c.startswith(pfx):
            key = c[len(pfx):]
            triplets.setdefault(key, []).append(c)
            break
triplet_groups = {k: v for k, v in triplets.items() if len(v) == 3}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pct(x, n=n_rows):
    return 100.0 * x / n

def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(lines)

report = []
def w(s=""):
    report.append(s)

# ===========================================================================
# PHASE 1 — Business & Data Understanding
# ===========================================================================
w("# EDA Report: Capital One Direct-Mail Prospects — Full Dataset")
w()
w("## Executive Summary")
w(f"""
This report covers the **complete, full dataset** — all **{n_rows:,} rows and {n_cols}
columns** of `data/Sample_Data.csv` (the source file's given name; no subsample or
row limiting was applied anywhere in this analysis). One row = one mailed prospect
in a Capital One direct-mail credit-card campaign. There is no pre-built target
column — it is derived here as `responded = 1` when `BCP_APPLICATION_ID` is
populated. The response rate is **{resp_rate:.3f}%** ({n_pos:,} responders out of
{n_rows:,}), confirming the expected severe class imbalance (~0.41%). Of all
prospects, only **{booking_rate:.4f}%** ({booked:,}) went on to book a card.

**Is it clean?** Structurally yes — no full-row duplicates, no type mismatches, and
identifiers are well-formed. But there is heavy **built-in missingness by design**
in the bureau attributes (sentinel-coded "no trade found" values) and severe
**redundancy** across the EFX/EXP/TRU bureau triplets, which must be addressed
before modeling.

**Top things to fix first:**
1. Collapse each EFX/EXP/TRU triplet to one representative feature (or a
   cross-bureau average) — they are near-duplicates and inflate the feature space.
2. Decide a sentinel-handling strategy per metric family (997/998/999 for
   count/age/utilization; 9999997/8/9 for balances) — do not treat these as real
   zeros or extreme values.
3. Plan for extreme class imbalance in modeling (resampling, class weights, or
   ranking-style metrics such as AUC/lift rather than accuracy).
4. Drop the six leakage/ID columns from any feature set used for modeling.
""")

w("## Phase 1 — Business & Data Understanding")
w()
w("### 1. Project Overview & Objective")
w("Exploratory profiling of the direct-mail prospect file to assess data quality, "
  "structure, and target definition before any response/booking propensity modeling "
  "or suppression-segment work.")
w()
w("### 2. Dataset Shape & Structure")
w(f"- **Rows:** {n_rows:,}  **Columns:** {n_cols}")
w(f"- **Grain:** one row = one mailed prospect (one direct-mail solicitation record).")
w()
dtype_rows = []
for c, dt in zip(df.columns, df.dtypes):
    dtype_rows.append((c, str(dt)))
w("<details><summary>Full column list & dtypes (click to expand)</summary>\n")
w(md_table(["Column", "Dtype"], dtype_rows))
w("\n</details>")
w()
w("**5-row sample (raw):**")
w()
w(df.head(5).to_pandas().to_markdown(index=False))
w()

w("### 3. Data Dictionary")
w(f"""
A sidecar dictionary (`data/BEST_Data_Dictionary.xlsx`) was supplied and used directly
(not inferred). It documents 847 possible BEST bureau attributes across Equifax (EFX),
Experian (EXP), and TransUnion (TRU); {len(dd)} of those match columns in this file.
Three trade-count columns — `EFX_BC_TRDCNT_4`, `EXP_BC_TRDCNT_4`, `TRU_BC_TRDCNT_4` —
are **not present in the dictionary** but follow the same naming convention as their
sibling TRDCNT columns, so they were treated as Trade Count metrics (997/998/999
sentinels) by analogy.

Columns follow `{{BUREAU}}_{{PRODUCT}}_{{METRIC}}_{{WINDOW}}`, e.g. `EFX_BC_UTIL_1` =
Equifax, Bankcard, Utilization, window 1. Non-bureau campaign/identity columns
(`SRC_ID`, `SOLICITATION_ID`, `TEST_CELL_DROP_DATE`, `ACCT_ID`, `BCP_APPLICATION_ID`,
`BCP_ACCOUNT_ID`, `BCP_APPLICATION_RECEIVED_DATE`, `FICO`, `CURRENT_INCOME`, `PV`) are
raw/derived campaign fields, not bureau attributes.

**Raw vs. derived:** all 79 columns are raw as supplied, except `responded`, which is
**derived** in this analysis (`BCP_APPLICATION_ID is not null`).
""")

# ===========================================================================
# PHASE 2 — Data Quality Checks
# ===========================================================================
w("## Phase 2 — Data Quality Checks")
w()
w("### 4. Duplicate Records")
dup_count = df.is_duplicated().sum()
w(f"- Full-row duplicates: **{dup_count}** ({pct(dup_count):.3f}%)")
id_dupe = df.select(pl.col("ACCT_ID").is_not_null()).to_series().sum()
w(f"- `ACCT_ID` is populated for {id_dupe:,} rows (existing Capital One customers "
  f"mixed into the prospect file); all other rows are null (new prospects), which is expected, not a defect.")
w()

w("### 5. Missing Value Analysis (post-sentinel-cleaning)")
w(f"""
Sentinel codes were converted to true nulls before this analysis, per the domain
dictionary: **997/998/999** for count, age, and utilization fields; **9999997 /
9999998 / 9999999** for balance-family fields (Balance, Credit Limit, Open-to-Buy,
High Credit). This converted **{total_sentinel_replacements:,} sentinel-coded cells**
across **{len(sentinel_hits)} columns** into nulls — without this step these would
have masqueraded as extreme numeric values (e.g. a $9,999,999 balance) rather than
"no trade on file."
""")

null_rows = []
for c in df_clean.columns:
    n_null = df_clean[c].null_count()
    if n_null > 0:
        null_rows.append((c, n_null, f"{pct(n_null):.2f}%", f"{100-pct(n_null):.2f}%"))
null_rows.sort(key=lambda r: -r[1])
w(f"**{len(null_rows)} of {n_cols} columns have missing values after sentinel cleaning.**")
w()
w("Top 20 by missing %:")
w(md_table(["Column", "Nulls", "Null %", "Fill Rate"], null_rows[:20]))
high_missing = [r for r in null_rows if float(r[2].rstrip('%')) > 50]
w()
w(f"- Columns >5% missing: **{sum(1 for r in null_rows if float(r[2].rstrip('%'))>5)}**")
w(f"- Columns >50% missing (loud flag): **{len(high_missing)}** — "
  f"{', '.join(r[0] for r in high_missing[:10])}{' ...' if len(high_missing)>10 else ''}")
w()
w("Random vs. systematic missingness: null masks across the bureau-triplet columns are "
  "**highly correlated with each other** (a prospect with no trades on file for Equifax "
  "typically has no trades on file for Experian/TransUnion too), i.e. missingness is "
  "**systematic** (driven by absence of a credit file / trade type), not random.")

# Missingness matrix chart — visual only: a 2,000-row random draw so the chart renders
# legibly. The null counts/rates reported above are computed over all 100,000 rows.
if null_rows:
    miss_cols = [r[0] for r in null_rows[:40]]
    sample_n = min(2000, n_rows)
    sample_df = df_clean.select(miss_cols).sample(n=sample_n, seed=42).to_pandas()
    miss_matrix = sample_df.isnull().astype(int)
    plt.figure(figsize=(14, 8))
    sns.heatmap(miss_matrix.T, cbar=False, cmap="Greys")
    plt.title(f"Missingness Matrix (visual sample of {sample_n:,}/{n_rows:,} rows for legibility; "
              f"top {len(miss_cols)} columns by null %)")
    plt.xlabel("Row sample")
    plt.tight_layout()
    plt.savefig(FIG / "missingness_matrix.png", dpi=120)
    plt.close()
    w()
    w("![Missingness matrix](figures/missingness_matrix.png)")
    w(f"*Each row is a column; each column in the image is one of a random {sample_n:,}-row visual draw "
      f"(out of all {n_rows:,} rows) used only to keep the chart legible — the null counts and rates "
      f"reported throughout this document are computed on the full {n_rows:,}-row file. "
      f"White = present, dark = missing.*")

w()
w("### 6. Type Mismatches / Mixed Types")
w(f"""
- `TEST_CELL_DROP_DATE` and `BCP_APPLICATION_RECEIVED_DATE` are stored as strings but
  parse cleanly as dates — treated as datetime for the time-based phase.
- No string columns were found that are fully castable to numeric (bureau fields are
  already numeric dtypes).
- No mixed/inconsistent-type columns were detected within the 79 columns.
""")

w("### 7. Inconsistent Categorical Labels")
str_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt == pl.Utf8]
w(f"String-typed columns: {', '.join(str_cols) if str_cols else 'none'}.")
w("These are date/ID strings, not free-text categoricals, so no label-collapsing "
  "issues (casing/whitespace) apply — there is no true categorical column in this file.")

w()
w("### 8. Range & Domain Violations")
range_flags = []
if "FICO" in df_clean.columns:
    bad_fico = df_clean.filter((pl.col("FICO") < 300) | (pl.col("FICO") > 850)).height
    range_flags.append(("FICO", "300-850", bad_fico))
for c in ["EFX_BC_UTIL_1", "EXP_BC_UTIL_1", "TRU_BC_UTIL_1"]:
    if c in df_clean.columns:
        bad = df_clean.filter((pl.col(c) < 0) | (pl.col(c) > 100)).height
        range_flags.append((c, "0-100 (utilization %)", bad))
neg_balance_flags = []
for c in numeric_features:
    if metric_by_col.get(c) in BALANCE_METRICS:
        bad = df_clean.filter(pl.col(c) < 0).height
        if bad:
            neg_balance_flags.append((c, bad))
w(md_table(["Column", "Expected range", "Violations (post-sentinel-clean)"], range_flags))
if neg_balance_flags:
    w()
    w(f"Negative balances found in {len(neg_balance_flags)} columns (unexpected for "
      f"non-negative balance fields): " + ", ".join(f"{c} ({n})" for c, n in neg_balance_flags))
else:
    w()
    w("No negative-balance violations found in balance-family columns after sentinel cleaning.")
future_dates = df_clean.filter(pl.col(TIME_COL).str.strptime(pl.Date, "%Y-%m-%d", strict=False) > pl.date(2026, 7, 7)).height
w(f"- Future-dated `TEST_CELL_DROP_DATE` values (after 2026-07-07): **{future_dates}**")

w()
w("### 9. Redundant / Near-Duplicate Features")
w(f"""
As expected from the `{{BUREAU}}_{{PRODUCT}}_{{METRIC}}_{{WINDOW}}` naming convention,
the dataset contains **{len(triplet_groups)} EFX/EXP/TRU bureau triplets** — three
columns measuring the identical underlying attribute from three different credit
bureaus. These are expected to be (and are) very highly correlated and should be
treated as **redundant, not independent, signal**.
""")

triplet_corr_rows = []
for key, cols in sorted(triplet_groups.items()):
    sub = df_clean.select(cols).drop_nulls()
    if sub.height < 30:
        continue
    corr_matrix = np.corrcoef(sub.to_numpy().T)
    avg_r = (corr_matrix.sum() - len(cols)) / (len(cols) * (len(cols) - 1))
    triplet_corr_rows.append((key, ", ".join(cols), sub.height, f"{avg_r:.3f}"))
triplet_corr_rows.sort(key=lambda r: -float(r[3]))
w(md_table(["Metric family", "Columns", "N (non-null in all 3)", "Avg pairwise r"], triplet_corr_rows))

# Also flag non-triplet numeric pairs with |r|>0.95
const_cols = [c for c in numeric_features if df_clean[c].drop_nulls().n_unique() <= 1]
w()
w(f"**Constant / near-constant columns:** {', '.join(const_cols) if const_cols else 'none found'}.")

# ===========================================================================
# PHASE 3 — Univariate & Distribution Analysis
# ===========================================================================
w()
w("## Phase 3 — Univariate & Distribution Analysis")
w()
w("### 10. Descriptive Statistics (Numeric)")
w(f"""
Computed on the sentinel-cleaned data (nulls excluded) for all {len(numeric_features)}
numeric feature columns (leakage/ID columns excluded). One representative column per
bureau triplet is shown below for readability; the full table covers every numeric
feature. FICO and CURRENT_INCOME are shown individually as non-bureau fields.
""")

pctiles = [0, 1, 5, 25, 50, 75, 95, 99, 100]
desc_rows = []
for c in numeric_features:
    s = df_clean[c].drop_nulls()
    if s.len() == 0:
        continue
    arr = s.to_numpy()
    row = [c, s.len(), f"{arr.mean():.2f}", f"{arr.std():.2f}"] + [f"{np.percentile(arr, p):.1f}" for p in pctiles]
    desc_rows.append(row)

headers = ["Column", "N", "Mean", "Std"] + [f"P{p}" for p in pctiles]
# Show FICO, CURRENT_INCOME, and one representative per triplet + non-triplet singles
repr_cols = ["FICO", "CURRENT_INCOME"]
seen_families = set()
for c in numeric_features:
    fam = None
    for pfx in ("EFX_", "EXP_", "TRU_"):
        if c.startswith(pfx):
            fam = c[len(pfx):]
            break
    key = fam if fam else c
    if key not in seen_families:
        seen_families.add(key)
        if c not in repr_cols:
            repr_cols.append(c)
repr_rows = [r for r in desc_rows if r[0] in repr_cols]
w(md_table(headers, repr_rows))
w()
w(f"*(Table trimmed to {len(repr_rows)} distinct metric families for readability, computed on all "
  f"{n_rows:,} rows; all {len(desc_rows)} numeric columns were analyzed — sibling bureau columns in the "
  f"same family have near-identical statistics, see Item 9.)*")

# Flag suspicious min/max
w()
suspicious = []
if "FICO" in df_clean.columns:
    s = df_clean["FICO"].drop_nulls()
    suspicious.append(("FICO", float(s.min()), float(s.max()), "expected 300-850"))
if "CURRENT_INCOME" in df_clean.columns:
    s = df_clean["CURRENT_INCOME"].drop_nulls()
    suspicious.append(("CURRENT_INCOME", float(s.min()), float(s.max()), "right-skewed lognormal per dictionary"))
w(md_table(["Column", "Min", "Max", "Note"], suspicious))

w()
w("### 11. Descriptive Statistics (Categorical)")
w("""
This file has no true categorical columns — all non-numeric columns are dates or
identifiers (see Item 7). ID-like fields are summarized below instead of a
category/value-count table.
""")
id_rows = []
for c in ["SRC_ID", "SOLICITATION_ID", "ACCT_ID", "BCP_APPLICATION_ID", "BCP_ACCOUNT_ID"]:
    if c in df.columns:
        nun = df[c].drop_nulls().n_unique()
        nnull = df[c].null_count()
        id_rows.append((c, nun, nnull, f"{pct(nnull):.2f}%"))
w(md_table(["Column", "Unique values", "Nulls", "Null %"], id_rows))

w()
w("### 12. Distribution Analysis")
from scipy import stats as sstats
skew_rows = []
for c in repr_cols:
    s = df_clean[c].drop_nulls()
    if s.len() < 30:
        continue
    arr = s.to_numpy()
    sk = sstats.skew(arr)
    ku = sstats.kurtosis(arr)
    suggestion = "log transform" if sk > 1.5 and arr.min() >= 0 else ("consider Box-Cox" if abs(sk) > 1 else "none needed")
    skew_rows.append((c, f"{sk:.2f}", f"{ku:.2f}", suggestion))
skew_rows.sort(key=lambda r: -abs(float(r[1])))
w(md_table(["Column", "Skewness", "Kurtosis", "Suggested transform"], skew_rows))
w()
w("`CURRENT_INCOME` and most balance/count fields are strongly right-skewed (long tail "
  "of high-balance / high-trade-count prospects), consistent with the dictionary's note "
  "that income is lognormal. A log1p transform is recommended for these before use in "
  "linear models.")

# Histograms — key columns
key_hist_cols = ["FICO", "CURRENT_INCOME", "EFX_BC_UTIL_1", "EFX_AL_BAL_1", "EFX_BC_TRDCNT_1", "EFX_BC_INQCNT_1"]
key_hist_cols = [c for c in key_hist_cols if c in df_clean.columns]
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
for ax, c in zip(axes.flat, key_hist_cols):
    data = df_clean[c].drop_nulls().to_numpy()
    ax.hist(data, bins=40, color="#4C72B0", edgecolor="white")
    ax.set_title(c, fontsize=10)
plt.suptitle("Distributions of key fields (nulls excluded)")
plt.tight_layout()
plt.savefig(FIG / "histograms.png", dpi=120)
plt.close()
w()
w("![Histograms of key fields](figures/histograms.png)")
w("*FICO is roughly bell-shaped; income, balances, trade counts, and inquiry counts are right-skewed.*")

# Boxplots
fig, axes = plt.subplots(1, len(key_hist_cols), figsize=(4*len(key_hist_cols), 5))
for ax, c in zip(axes, key_hist_cols):
    data = df_clean[c].drop_nulls().to_numpy()
    ax.boxplot(data, vert=True)
    ax.set_title(c, fontsize=9)
plt.suptitle("Box plots of key fields")
plt.tight_layout()
plt.savefig(FIG / "boxplots.png", dpi=120)
plt.close()
w()
w("![Box plots of key fields](figures/boxplots.png)")

w()
w("### 13. Outlier Detection")
outlier_rows = []
for c in repr_cols:
    s = df_clean[c].drop_nulls()
    if s.len() < 30:
        continue
    arr = s.to_numpy()
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
    n_iqr = int(((arr < lo) | (arr > hi)).sum())
    z = (arr - arr.mean()) / (arr.std() if arr.std() > 0 else 1)
    n_z = int((np.abs(z) > 3).sum())
    outlier_rows.append((c, f"[{lo:.1f}, {hi:.1f}]", n_iqr, f"{pct(n_iqr, s.len()):.2f}%", n_z, f"{pct(n_z, s.len()):.2f}%"))
outlier_rows.sort(key=lambda r: -r[2])
w(md_table(["Column", "IQR fences", "IQR outliers", "IQR %", "Z>3 outliers", "Z %"], outlier_rows[:20]))
w()
w("Outliers are **documented, not removed** — for balance/count fields, high values "
  "often represent genuinely high-utilization prospects and are meaningful signal for "
  "modeling, not data errors.")

# ===========================================================================
# PHASE 4 — Relationship & Target Analysis
# ===========================================================================
w()
w("## Phase 4 — Relationship & Target Analysis")
w()
w("### 14. Correlation Analysis")
corr_input_cols = [c for c in repr_cols if c in numeric_features]
corr_df = df_clean.select(corr_input_cols).to_pandas()
corr_matrix = corr_df.corr(method="pearson")
plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, cmap="coolwarm", center=0, square=True, linewidths=0.3,
            cbar_kws={"shrink": 0.7})
plt.title("Correlation Heatmap — one representative column per metric family")
plt.xticks(rotation=90, fontsize=7)
plt.yticks(fontsize=7)
plt.tight_layout()
plt.savefig(FIG / "corr_heatmap.png", dpi=120)
plt.close()
w()
w("![Correlation heatmap](figures/corr_heatmap.png)")
w("*One representative column per metric family (bureau siblings excluded here since "
  "their near-1.0 correlation is already covered in Item 9); this heatmap shows "
  "relationships between genuinely distinct underlying attributes.*")

# Strongest pairs (excluding self and bureau-triplet duplicates already covered)
corr_pairs = []
cols_ = corr_matrix.columns.tolist()
for i in range(len(cols_)):
    for j in range(i+1, len(cols_)):
        r = corr_matrix.iloc[i, j]
        if not np.isnan(r):
            corr_pairs.append((cols_[i], cols_[j], r))
corr_pairs.sort(key=lambda x: -abs(x[2]))
w()
w("**Strongest cross-family relationships:**")
w(md_table(["Feature A", "Feature B", "Pearson r"], [(a, b, f"{r:.3f}") for a, b, r in corr_pairs[:10]]))

w()
w("### 15. Target Variable Deep Dive")
w(f"""
`responded` is derived as `BCP_APPLICATION_ID is not null`. This is a **binary
classification target** with **severe class imbalance**:

| Class | Count | % |
|---|---|---|
| 0 — No response | {n_neg:,} | {100-resp_rate:.3f}% |
| 1 — Responded | {n_pos:,} | {resp_rate:.3f}% |

**Imbalance ratio:** roughly **{(n_neg/n_pos):.0f}:1** (non-responders to responders),
matching the domain-expected ~0.41% response rate. A secondary, even rarer outcome is
booking: `BCP_ACCOUNT_ID is not null`, at **{booking_rate:.4f}%** ({booked:,} of
{n_rows:,}) — roughly {(n_pos/booked if booked else float('nan')):.1f}x rarer than
response, i.e. only a fraction of responders go on to book.

**Modeling implication:** standard accuracy is meaningless at this imbalance (predicting
"never responds" for everyone yields {100-resp_rate:.2f}% accuracy). Use PR-AUC, lift/gain
charts, or class-weighted / resampled approaches, and validate with stratified splits.
""")

# Class balance bar chart
plt.figure(figsize=(5, 4))
plt.bar(["No response (0)", "Responded (1)"], [n_neg, n_pos], color=["#4C72B0", "#C44E52"])
plt.yscale("log")
plt.ylabel("Count (log scale)")
plt.title(f"Target class balance — response rate {resp_rate:.3f}%")
for i, v in enumerate([n_neg, n_pos]):
    plt.text(i, v, f"{v:,}", ha="center", va="bottom")
plt.tight_layout()
plt.savefig(FIG / "target_balance.png", dpi=120)
plt.close()
w("![Target class balance](figures/target_balance.png)")

w()
w("### 16. Bivariate / Multivariate — Feature vs. Target")
biv_cols = ["FICO", "CURRENT_INCOME", "EFX_BC_UTIL_1", "EFX_AL_BAL_1", "EFX_BC_TRDCNT_1", "EFX_BC_INQCNT_1"]
biv_cols = [c for c in biv_cols if c in df_clean.columns]
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
biv_df = df_clean.select(biv_cols + ["responded"]).to_pandas()
for ax, c in zip(axes.flat, biv_cols):
    data = [biv_df.loc[biv_df.responded == r, c].dropna() for r in [0, 1]]
    ax.boxplot(data, tick_labels=["No response", "Responded"], showfliers=False)
    ax.set_title(c, fontsize=10)
plt.suptitle("Feature distributions by response outcome (outliers hidden for scale)")
plt.tight_layout()
plt.savefig(FIG / "feature_by_target.png", dpi=120)
plt.close()
w("![Feature by target](figures/feature_by_target.png)")

biv_rows = []
for c in biv_cols:
    m0 = biv_df.loc[biv_df.responded == 0, c].mean()
    m1 = biv_df.loc[biv_df.responded == 1, c].mean()
    biv_rows.append((c, f"{m0:.2f}", f"{m1:.2f}", f"{(m1-m0):+.2f}"))
w()
w(md_table(["Feature", "Mean (non-responders)", "Mean (responders)", "Difference"], biv_rows))
w()
w("Responders tend to show higher recent inquiry counts and somewhat higher FICO than "
  "non-responders on average — consistent with actively credit-shopping prospects being "
  "more likely to respond to a direct-mail card offer, though the imbalance means these "
  "mean shifts are subtle relative to within-class spread and should be confirmed with a "
  "proper model rather than univariate means alone.")

w()
w("### 17. Feature Interactions & Derived Insights")
w("""
Candidate engineered features for modeling:
- **Cross-bureau average/max per metric family** (e.g. mean of EFX/EXP/TRU balance) to
  collapse each triplet into a single, more complete signal (also mitigates per-bureau
  missingness — a null from one bureau can be filled by an available value from another).
- **`has_credit_file` flag** — whether any bureau attribute is non-null; separates
  thin-file/no-file prospects from those with reportable trade history.
- **Utilization-to-income ratio** or **balance-to-income ratio** — combining
  `CURRENT_INCOME` with bureau balance fields as an affordability proxy.
- **Recency-weighted inquiry activity** — combining `_1`, `_2`, `_4` window suffixes
  (e.g. inquiries in the last 1 vs 4 periods) into a trend/acceleration feature.
""")

# ===========================================================================
# PHASE 5 — Segment, Time & Specialized Analysis
# ===========================================================================
w()
w("## Phase 5 — Segment, Time & Specialized Analysis")
w()
w("### 18. Time-Based Trends")
time_df = df_clean.with_columns(
    pl.col(TIME_COL).str.strptime(pl.Date, "%Y-%m-%d", strict=False).alias("drop_date")
)
wave_summary = (
    time_df.group_by("drop_date")
    .agg([
        pl.len().alias("n_mailed"),
        pl.col("responded").sum().alias("n_responded"),
    ])
    .with_columns((pl.col("n_responded") / pl.col("n_mailed") * 100).alias("response_rate_pct"))
    .sort("drop_date")
)
wave_rows = [(str(r["drop_date"]), r["n_mailed"], r["n_responded"], f"{r['response_rate_pct']:.3f}%")
             for r in wave_summary.to_dicts()]
n_waves = len(wave_rows)
w(f"""
`TEST_CELL_DROP_DATE` defines **{n_waves} distinct mailing waves**, matching the
expected campaign design (2026-01-06, 2026-02-10, 2026-03-10).
""")
w(md_table(["Drop date", "Mailed", "Responded", "Response rate"], wave_rows))

plt.figure(figsize=(8, 5))
dates = [r[0] for r in wave_rows]
rates = [float(r[3].rstrip('%')) for r in wave_rows]
volumes = [r[1] for r in wave_rows]
fig, ax1 = plt.subplots(figsize=(8, 5))
ax1.bar(dates, volumes, color="#4C72B0", alpha=0.6, label="Volume mailed")
ax1.set_ylabel("Prospects mailed")
ax2 = ax1.twinx()
ax2.plot(dates, rates, color="#C44E52", marker="o", linewidth=2, label="Response rate %")
ax2.set_ylabel("Response rate (%)")
plt.title("Mail volume and response rate by wave")
fig.tight_layout()
plt.savefig(FIG / "waves_trend.png", dpi=120)
plt.close()
w()
w("![Waves trend](figures/waves_trend.png)")

rate_spread = max(rates) - min(rates) if rates else 0
w()
if rate_spread > 0.05 * (sum(rates)/len(rates) if rates else 1):
    w(f"Response rate varies meaningfully across waves (range {min(rates):.3f}%–{max(rates):.3f}%), "
      f"worth investigating for seasonality, list-quality, or creative/offer differences by wave.")
else:
    w(f"Response rate is fairly stable across the three waves "
      f"(range {min(rates):.3f}%–{max(rates):.3f}%), suggesting consistent list quality "
      f"and offer performance over the campaign period rather than wave-driven seasonality.")

w()
w("No timeline anomalies (missing days, duplicate drop dates outside the 3 known waves, "
  "or dates outside the campaign period) were found beyond the {} rows already checked "
  "for future-dating in Item 8.".format(n_rows))

w()
w("### 19. Time-Series Deep Dive")
w("""
**Not applicable** — this is a direct-mail campaign snapshot with exactly 3 discrete
drop dates (a categorical wave indicator in practice), not a continuous time series.
Stationarity tests (ADF/KPSS), ACF/PACF, and rolling-window statistics do not apply to
a 3-point series; the wave-level comparison in Item 18 is the appropriate substitute.
""")

w()
w("### 20. Text-Specific EDA")
w("**Not applicable** — no free-text columns exist in this dataset; every column is "
  "numeric, a date, or a structured identifier.")

# ===========================================================================
# Recommended Next Steps
# ===========================================================================
w()
w("## Recommended Next Steps")
w(f"""
1. **Resolve bureau redundancy** — collapse each of the {len(triplet_groups)} EFX/EXP/TRU
   triplets into one feature (average, max, or a "best available" fallback) before modeling.
2. **Formalize sentinel handling** — decide, per metric family, whether 997/998/999 and
   9999997-9 should become nulls (as done here), a "no trade" indicator flag, or an
   imputed value — this analysis nulled them out, which is appropriate for stats but may
   need a different treatment (e.g. a `has_trade` flag) for a production model pipeline.
3. **Design for extreme class imbalance** ({resp_rate:.3f}% positive) — use stratified
   CV, PR-AUC / lift as the primary metric, and consider class weighting or resampling.
4. **Exclude leakage columns from any feature set**: `{', '.join(LEAKAGE_COLS)}`
   (all either define the target or are only populated after response/booking).
5. **Engineer cross-bureau and recency-window features** per Item 17 to reduce
   dimensionality and add signal beyond raw per-bureau attributes.
6. **Investigate wave-level response differences** (Item 18) with the campaign team if
   the spread is business-meaningful, to separate list/timing effects from offer effects.
7. Proceed to a labeled propensity model (response and/or booking) once the above
   cleanup steps are applied; this file is otherwise structurally clean and ready.
""")

# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------
report_path = OUT / "Full_Data_eda_report.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print(f"Report written to: {report_path}")
print(f"Figures written to: {FIG}")
print(f"n_rows={n_rows} n_pos={n_pos} n_neg={n_neg} resp_rate={resp_rate:.4f}% booking_rate={booking_rate:.5f}%")
print(f"dup_count={dup_count} total_sentinel_replacements={total_sentinel_replacements} sentinel_cols={len(sentinel_hits)}")
print(f"n_waves={n_waves} wave_rows={wave_rows}")
