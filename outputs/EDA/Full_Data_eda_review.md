# EDA Review: Full_Data_eda_report.md

**Reviewed:** `outputs/EDA/Full_Data_eda_report.md` (regenerated 2026-07-10) against `outputs/EDA/figures/`.

## Overall completeness summary

All 20 checklist items are present as their own section, including both gated Phase 5 items (19, 20)
correctly marked "Not applicable" with a stated reason. Every domain-context requirement was applied
correctly: the target is derived exactly as specified (`BCP_APPLICATION_ID is not null`, 0.410% positive,
243:1 imbalance), the dictionary-driven sentinel codes (997/998/999 for count/age/utilization,
9999997-9 for balances) are used instead of generic defaults, the seven leakage columns are excluded from
the feature set, `TEST_CELL_DROP_DATE` drives the three-wave time analysis, and bureau triplet redundancy
is explicitly quantified per family rather than asserted generically. This is a comprehensive, largely
consistent report. The single most important gap: **Item 9's redundancy claim and the Recommended Next
Steps both treat all 23 bureau triplets as uniformly "very highly correlated" and safe to collapse, but the
report's own correlation table shows 11 of the 23 families sitting at r = 0.627–0.932 — a meaningfully
weaker signal than the "very highly correlated" framing implies.** A close second: the Data Dictionary
section's "841 of those match columns in this file" claim is arithmetically impossible (the file has 79
columns) and misdescribes what was actually counted.

## Per-item verdict table

| # | Item | Verdict | Notes |
|---|------|---------|-------|
| 1 | Project overview & objective | Present | One-sentence objective in "Phase 1 → 1. Project Overview & Objective"; appropriately generic/pre-modeling framing. |
| 2 | Shape/structure + grain | Present | Rows/cols, full dtype table (collapsible), grain statement, 5-row raw sample all included. |
| 3 | Data dictionary | Partial | Dictionary is used directly (not inferred) and the naming convention is explained well, but the sentence "847 possible BEST bureau attributes... 841 of those match columns in this file" is incorrect — 841 cannot "match columns in this file" when the file only has 79 columns. This appears to be the count of distinct Attribute Name entries in the dictionary sheet overall, not an intersection with `df.columns`. Reads as a match-rate claim it isn't. |
| 4 | Duplicates | Present | Full-row dup count (0) plus a useful secondary check on `ACCT_ID` (99,973 unique vs 100,000 rows), correctly framed as a minor follow-up, not a blocker. |
| 5 | Missing values + fill rate + sentinel handling | Present | Sentinel-to-null conversion is quantified (239,312 cells / 69 columns), top-20 null-% table shown, systematic-vs-random missingness reasoned about qualitatively, missingness matrix chart included and clearly captioned as a visual sample. |
| 6 | Type mismatches / mixed types | Present | Explicitly checked and reports none found beyond the two date-like string columns. |
| 7 | Inconsistent categorical labels | Present (N/A, justified) | Correctly notes there are no true categorical columns to collapse; the three string columns are dates/IDs. |
| 8 | Range/domain violations | Present | FICO and utilization range checks (0 violations each), negative-balance check, future-date check. Reasonably thorough given the numeric-heavy schema. |
| 9 | Redundant / near-duplicate features | Partial | Excellent quantification — a full per-triplet avg-pairwise-r table for all 23 families plus a constant-column check. But the narrative claim ("very highly correlated... redundant, not independent signal") is stated as if uniform across all 23, while the table itself shows 11 families at r = 0.627–0.932 (well below the conventional ≥0.95 "near-duplicate" bar used elsewhere in this same report, e.g. Item 14's cross-family list). The report doesn't flag this gradient or soften the "collapse all triplets" recommendation for the lower-agreement families (this nuance *is* present in the companion executive deck, but not carried into the markdown report). |
| 10 | Numeric descriptive stats + percentiles | Present | Full P0/P1/P5/P25/P50/P75/P95/P99/P100 table for a 25-family representative set, with a clear note that all 71 numeric columns were computed (just trimmed for display). |
| 11 | Categorical descriptive stats + cardinality | Present (substituted appropriately) | No true categoricals exist, so the section substitutes an ID-cardinality table (SRC_ID, SOLICITATION_ID, ACCT_ID, BCP_APPLICATION_ID, BCP_ACCOUNT_ID) — a sensible adaptation, clearly labeled as such. |
| 12 | Distribution shape (skew/kurtosis) + charts | Present | Skew/kurtosis table with transform suggestions, histogram grid, box-plot grid, both captioned. |
| 13 | Outlier detection (IQR/Z) | Present | Both methods reported per column with fences and counts; explicitly states outliers are documented, not removed, with a domain rationale. |
| 14 | Correlation + heatmap | Present | Heatmap (one representative per family) plus a top-10 strongest cross-family pairs table, all showing near-zero r (max 0.011) — internally consistent with the "each family is independent signal" claim in Item 17. |
| 15 | Target deep-dive / class balance | Present | Class counts, %, imbalance ratio (243:1), secondary booking-rate outcome, modeling-implication guidance, and a log-scale bar chart. All numbers are internally consistent (99,590 + 410 = 100,000; 99,590/410 ≈ 242.9 ≈ "243:1"). |
| 16 | Bivariate/multivariate + charts | Present | Feature-by-target box-plot grid plus a means-by-class table; the narrative correctly caveats that the mean shifts are subtle relative to within-class spread. |
| 17 | Feature interactions / derived insights | Present | Four concrete, well-reasoned candidate engineered features (cross-bureau average, has-credit-file flag, utilization/balance-to-income ratio, recency-window trend). |
| 18 | Time-based trends | Present | Correct 3-wave breakdown matching the specified drop dates, volume+rate dual-axis chart, and a reasonable stability conclusion (0.406–0.416% range). |
| 19 | Time-series deep dive | N-A (justified) | Correctly explains why ADF/KPSS/ACF don't apply to a 3-point wave series and points back to Item 18 as the substitute. |
| 20 | Text-specific EDA | N-A (justified) | Correctly notes no free-text columns exist. |

## Consistency findings

- **Item 9 vs. its own table:** the prose says all 23 EFX/EXP/TRU triplets are "very highly correlated,"
  but the table shows a wide range (1.000 down to 0.627). Roughly half the triplets (12 of 23) meet a
  ≥0.95 "near-duplicate" bar; the other 11 (mostly `DQOCURNC` delinquency families and a few `TRDCNT`/`INQCNT`
  families) sit at 0.627–0.932 — meaningfully weaker agreement than the blanket "redundant, not independent"
  framing glosses over.
- **Recommended Next Steps #1** ("collapse each of the 23 ... triplets into one feature") inherits the same
  overgeneralization — it doesn't distinguish the 12 safe-to-collapse families from the 11 that may carry
  bureau-specific signal, even though the underlying data (the Item 9 table) supports making that
  distinction, and the companion executive deck (`Full_Data_executive_summary.pptx`) *does* make it
  explicitly (12 vs. 11 split, calling out the delinquency fields for review before collapsing).
- **Item 3 dictionary match count:** "847 possible... ; 841 of those match columns in this file" is not
  possible given the file has 79 columns. This number is very likely the count of distinct `Attribute Name`
  entries across the whole dictionary sheet (`len(dd)` in the generating script), not an intersection with
  the file's actual columns — the wording should be corrected to avoid implying an (impossible) 841-column
  match.
- No other narrative claim was found to contradict its supporting table/chart. Target imbalance, booking
  rate, sentinel replacement counts, and wave-level figures all check out arithmetically against the tables
  presented.

## Broken references

All figures resolve — `missingness_matrix.png`, `histograms.png`, `boxplots.png`, `corr_heatmap.png`,
`target_balance.png`, `feature_by_target.png`, and `waves_trend.png` all exist in `outputs/EDA/figures/`
and are referenced with correct relative paths and captions.

## Prioritized fixes

1. **Correct the Item 9 / Next-Steps-#1 framing** — split the 23 triplets into the ~12 families with
   avg r ≥ 0.95 (safe to collapse outright) and the ~11 with r in the 0.627–0.932 range (review before
   collapsing, particularly the `DQOCURNC` delinquency families where bureau disagreement may be real
   signal, not noise). This nuance already exists in the executive deck — just needs to be pulled back into
   the markdown report so the two artifacts agree.
2. **Fix the Item 3 dictionary-match sentence** — either report the actual intersection between dictionary
   attribute names and this file's 79 columns, or reword to "841 distinct attributes are documented in the
   dictionary sheet overall" so it no longer reads as a per-file match count.
3. (Minor, optional) Consider noting in Item 9 that `EFX_BC_TRDCNT_4`/`EXP_BC_TRDCNT_4`/`TRU_BC_TRDCNT_4`
   were treated as Trade Count sentinels "by analogy" (already stated in Item 3) — a one-line cross-reference
   there would help a reader who jumps straight to Item 9's correlation table.

Beyond these two content-accuracy fixes, the report is thorough, well-organized, and directly actionable —
no structural gaps, no missing charts, and strong alignment with all of the supplied domain context
(sentinel codes, leakage exclusion, derived target, three-wave time column).
