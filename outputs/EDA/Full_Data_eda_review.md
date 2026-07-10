# EDA Review: Capital One Direct-Mail Prospects — Full Dataset

**Report reviewed:** `outputs/EDA/Full_Data_eda_report.md`
**Figures reviewed:** `outputs/EDA/figures/` (7 PNGs)
**Deck reviewed:** `outputs/EDA/Full_Data_executive_summary.pptx` (11 slides, post-fix — see Prioritized Fixes #1)

## 1. Overall completeness summary

All 20 checklist items are present, correctly gated (items 19-20 are legitimately marked
Not Applicable with a stated reason), and — unusually for a generic EDA — the report
correctly incorporates every piece of domain context it was given: the derived
`responded` target (0.410% positive, 243:1 imbalance), dictionary-driven sentinel codes
(997/998/999 for count/age/utilization; 9999997-9999999 for balances), the seven-column
leakage exclusion list, exactly 3 mailing waves keyed off `TEST_CELL_DROP_DATE`, and
explicit EFX/EXP/TRU triplet redundancy flagging with correlation evidence. The
markdown report itself is comprehensive and internally consistent — no numeric or
narrative contradictions were found.

**The most important gap was in the executive deck, and has since been fixed.** The
`.pptx` was originally built by loading `docs/templates/Zenon_2026_Template.pptx`
(which ships with 3 pre-built sample slides) and *appending* 11 new content slides
after them, rather than replacing them — producing a 14-slide deck where slides 1-3
were unfilled template boilerplate (`[Text]`, `[subtext]`, `Sample text`, `TOPIC`,
`SUB TEXT`), including the deck's own title slide. `tools/EDA/make_exec_deck_full_data.py`
was patched to delete the template's pre-existing sample slides immediately after
loading it, before appending the 11 real content slides. The deck was regenerated and
now opens directly on the actual title slide; all 11 slides contain project-specific
content with no leftover placeholder text (verified by re-extracting all slide text).

## 2. Per-item verdict table

| # | Item | Verdict | Notes |
|---|------|---------|-------|
| 1 | Project overview & objective | Present | Clear one-line objective under Phase 1, item 1. |
| 2 | Shape/structure + grain | Present | 100,000 rows × 79 columns, grain stated ("one mailed prospect"), full dtype table + 5-row sample. |
| 3 | Data dictionary | Present | Cites `BEST_Data_Dictionary.xlsx` directly (not inferred); notes 3 undocumented TRDCNT columns handled by analogy — good transparency. |
| 4 | Duplicates | Present | 0 full-row duplicates; correctly distinguishes `ACCT_ID`-populated existing customers from prospects (verified against raw data: `ACCT_ID` null_count is in fact 0, matching the report's claim). |
| 5 | Missing values + fill rate + sentinel handling | Present | Uses the correct domain sentinel codes (997/998/999, 9999997-9999999), not generic -999/-9999 defaults; states 239,312 cells / 69 columns converted; includes missingness matrix chart and a random-vs-systematic-missingness discussion. |
| 6 | Type mismatches / mixed types | Present | Date-string columns identified; no mixed-type columns found. |
| 7 | Inconsistent categorical labels | Present (N-A body) | Correctly explains there are no true categorical columns to check for label collapsing. |
| 8 | Range/domain violations | Present | FICO and utilization range checks, negative-balance check, future-date check, all zero violations post-sentinel-clean. |
| 9 | Redundant / near-duplicate features | Present | Explicitly identifies 23 EFX/EXP/TRU triplets, reports avg pairwise r per family (0.627–1.000), states they must be treated as **redundant, not independent, signal** — exactly the domain instruction. |
| 10 | Numeric stats incl. percentiles | Present | Full P0–P100 table for 25 representative metric families; states all 71 numeric features were computed, trimmed for readability. |
| 11 | Categorical stats + cardinality | Present | Correctly notes no true categoricals exist; substitutes an ID-field cardinality/null table instead. |
| 12 | Distribution shape + charts | Present | Skew/kurtosis table, transform suggestions, histogram + boxplot charts, both resolve. |
| 13 | Outlier detection (IQR/Z) | Present | IQR and Z>3 outlier counts per column; explicitly states outliers are documented, not removed. |
| 14 | Correlation + heatmap | Present | Heatmap uses one representative column per family (correctly avoiding double-counting triplet correlation, which is already covered in item 9); strongest cross-family pairs table shows genuinely low correlations (~0.01), correctly implying non-triplet features are largely independent. |
| 15 | Target deep-dive / class balance | Present | Correct derivation logic stated (`BCP_APPLICATION_ID is not null`); class table and 243:1 ratio match; explicitly calls out the ~0.41% imbalance and its modeling implications (PR-AUC, stratified CV). |
| 16 | Bivariate/multivariate charts | Present | Feature-by-target boxplot chart + means table; narrative correctly hedges that these are subtle univariate shifts, not confirmed model-level effects. |
| 17 | Feature interactions | Present | Four concrete, well-reasoned candidate engineered features (cross-bureau average, has_credit_file flag, affordability ratio, recency-window trend). |
| 18 | Time-based trends | Present | Confirms exactly 3 waves on the 3 expected dates (2026-01-06/02-10/03-10), per-wave mail volume + response rate table, trend chart, and a reasoned "stable, not seasonal" conclusion. |
| 19 | Time-series deep dive | N-A | Correctly marked not applicable (3-point series, not a continuous time series) with a clear reason. |
| 20 | Text-specific EDA | N-A | Correctly marked not applicable — no free-text columns. |

## 3. Consistency findings

- None found in the markdown report. Spot-checked several claims against their own
  tables: the "243:1" imbalance ratio matches 99,590/410 (≈242.9, rounds to 243);
  the "23 triplets" claim matches the length of the table in item 9; the "74 of 79
  columns have missing values" matches the count of populated rows in the null table;
  skew/kurtosis wording ("strongly right-skewed") matches the numeric skew values shown
  (e.g. `EFX_AR_BAL_1` skew 13.29). No narrative-vs-table contradictions found.
- One point **worth verifying**, not a contradiction: item 4 states `ACCT_ID` is
  "populated for 100,000 rows," which sounds surprising for a direct-mail *prospect*
  file — one would expect prospects to mostly lack an existing account ID. This was
  spot-checked directly against the raw CSV and confirmed correct (0 nulls), but the
  business framing ("existing Capital One customers mixed into the prospect file")
  deserves a follow-up with the data owner since it implies **100% of the file** is
  existing customers, which is unusual framing for a "prospect" file and worth a
  sentence of caveat in the report.

## 4. Broken references

All figure links resolve. Verified all 7 files referenced in the report
(`missingness_matrix.png`, `histograms.png`, `boxplots.png`, `corr_heatmap.png`,
`target_balance.png`, `feature_by_target.png`, `waves_trend.png`) exist in
`outputs/EDA/figures/`.

## 5. Prioritized fixes

1. **(Deck) FIXED — removed the 3 unfilled template placeholder slides.** Slides 1–3
   of the original `Full_Data_executive_summary.pptx` contained literal template
   boilerplate (`[Text]`, `[subtext]`, `Sample text`, `TOPIC`, `SUB TEXT`, a generic
   "About Zenon" slide) instead of this project's title/content, because the deck
   builder opened `Zenon_2026_Template.pptx` (which ships 3 pre-built sample slides)
   and appended new slides after them rather than deleting/overwriting the template's
   existing slides. `tools/EDA/make_exec_deck_full_data.py` now drops the template's
   3 sample slides right after loading it, before any content slides are appended.
   The deck was regenerated (now 11 slides, all project-specific, title slide first)
   and spot-checked slide-by-slide to confirm no leftover placeholder text remains.
2. **(Report, minor) Add one clarifying sentence to item 4** on why `ACCT_ID` is
   populated for all 100,000 rows despite this being a "prospect" file, or flag it
   as a point to confirm with the campaign/data-owner team — the current phrasing
   ("existing Capital One customers mixed into the prospect file") implies all
   100,000 are existing customers, which may or may not be the intended read.
3. No other fixes needed — the markdown report is comprehensive, correctly reflects
   every domain-specific instruction (target derivation, sentinel codes, leakage
   exclusions, wave analysis, triplet redundancy), and is ready to hand off to a
   modeling workstream once the deck fix above is applied.
