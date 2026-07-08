# Dataset Analyzer (EDA) Run Memory

_Workstream: dataset-analyzer / eda-reviewer. Manually maintained (no automation
script yet — append a new entry below after each EDA run, oldest at the bottom).
For the segment-discovery workstream, see [memory_segmentation.md](memory_segmentation.md) instead._

## RUNS

### 2026-07-07 — data/Sample_Data.csv (full dataset, 100,000 rows x 79 columns)
**Scope:** Complete file, no subsampling — `Sample_Data.csv` is the source file's
given name, not an indication of a partial/sampled extract. All statistics in the
report are computed over all 100,000 rows; the only exception is the missingness-
matrix chart, which draws a 2,000-row visual sample purely so the image renders
legibly.
**Target (derived):** `responded = BCP_APPLICATION_ID is not null` — response rate
0.410% (410/100,000); booking rate 0.084% (84/100,000). Severe class imbalance.
**Data quality:** No full-row duplicates. 239,312 sentinel-coded cells across 69
columns (997/998/999 for count/age/utilization fields; 9999997-9 for balance
fields, per `BEST_Data_Dictionary.xlsx`) converted to null before analysis.
**Key structural finding:** Every EFX/EXP/TRU bureau triplet is near-perfectly
correlated (avg pairwise r ~= 1.000) — redundant, not independent, signal. Collapse
each triplet to one representative/aggregated feature before modeling.
**Time dimension:** 3 mailing waves (2026-01-06, 2026-02-10, 2026-03-10), balanced
in volume (~33.1k-33.5k each) and response rate (0.406%-0.416%) — no wave-driven
anomaly.
**Artifacts:** `outputs/EDA/Full_Data_eda_report.md`,
`outputs/EDA/Full_Data_executive_summary.pptx`, `outputs/EDA/figures/*.png`.
Produced by `tools/EDA/eda_full_data.py` + `tools/EDA/make_exec_deck_full_data.py`.
**Note for future runs:** this EDA and the `segment-discovery` run in
`memory_segmentation.md` (2026-07-06) analyze the same source file — cross-check
findings (e.g. bureau redundancy, FICO signal) between the two workstreams rather
than re-deriving them independently.

---
