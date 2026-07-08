# Segment Discovery Run Memory

_Workstream: segment-discovery. Auto-maintained by tools/segmentation/memory.py.
Entries older than 30 days are summarised. For the dataset-analyzer (EDA)
workstream, see [memory_eda.md](memory_eda.md) instead._

## ACTIVE RUNS (last 30 days)

### 2026-07-06 — capital_one_dm_suppression  *(updated: stability threshold corrected to BAU)*
**Data:** Sample_Data.csv | BAU: 0.41% (410/100,000) | suppression
**Features in top rules:** EFX_AL_DQOCURNC_5, EFX_BC_DQOCURNC_3, FICO, EFX_AL_DQOCURNC_1, EFX_BC_INQCNT_1, EFX_BC_UTIL_1, EFX_AL_BAL_1
**Segments found (v1):** 25 searched | **Best lift:** 0.579x | **Top 6 deployed**
**Stability:** 6/6 rules stable (pass = all wave rates < BAU = 0.41%)
**Top SHAP drivers:** EFX_BC_UTIL_1 (0.087), EFX_AL_BAL_1 (0.084), EFX_AL_TRDAGE_1 (0.057), FICO (0.055), EFX_AL_DQOCURNC_3 (0.050)
**Config delta vs prior run:** first run
**Config snapshot:** {"feature_columns":["FICO","CURRENT_INCOME","EFX_AL_BAL_1","EFX_BC_BAL_1","EFX_BC_BAL_5","EFX_AR_BAL_1","EFX_AL_TRDCNT_1","EFX_BC_TRDCNT_1","EFX_BC_TRDCNT_4","EFX_AL_TRDCNT_5","EFX_BC_TRDCNT_5","EFX_AL_TRDAGE_1","EFX_BC_TRDAGE_1","EFX_BC_TRDAGE_2","EFX_BC_TRDAGE_3","EFX_BC_INQCNT_1","EFX_BC_INQCNT_2","EFX_BC_INQCNT_4","EFX_AL_DQOCURNC_1","EFX_AL_DQOCURNC_2","EFX_AL_DQOCURNC_3","EFX_BC_DQOCURNC_3","EFX_AL_DQOCURNC_5","EFX_BC_DQOCURNC_5","EFX_BC_UTIL_1"],"time_column":"TEST_CELL_DROP_DATE","min_segment_pct":1.0,"direction":"suppression","exclude_columns":["BCP_ACCOUNT_ID","BCP_APPLICATION_ID","BCP_APPLICATION_RECEIVED_DATE","PV","SOLICITATION_ID","TEST_CELL_DROP_DATE"]}

**TOP 6 SUPPRESSION SEGMENTS — full rule text, wave rates, SHAP alignment:**

| # | Full Rule (pysubgroup) | Business Label | Size | Size% | Overall Rate | Jan | Feb | Mar | Stable | Lift | SHAP-grounded features |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `EFX_AL_DQOCURNC_5==0.0 AND EFX_BC_DQOCURNC_3==0.0 AND FICO: [664.0:694.0[` | Clean DQ (5yr+3mo) + FICO 664–694 | 10,947 | 10.95% | 0.24% | 0.25% | 0.19% | 0.27% | ✓ | 0.58× | FICO (#4), EFX_AL_DQOCURNC_3 (#5) |
| 2 | `EFX_AL_DQOCURNC_1==0.0 AND EFX_BC_INQCNT_1==0.0 AND EFX_BC_UTIL_1: [16.0:35.0[` | Mid-Util + No Inquiry + Clean DQ | 10,881 | 10.88% | 0.24% | 0.25% | 0.25% | 0.22% | ✓ | 0.58× | EFX_BC_UTIL_1 (#1) |
| 3 | `EFX_BC_DQOCURNC_3==0.0 AND EFX_BC_INQCNT_1==0.0 AND FICO: [664.0:694.0[` | FICO 664–694 + No BC Inq + Clean BC DQ | 10,616 | 10.62% | 0.25% | 0.28% | 0.23% | 0.25% | ✓ | 0.62× | FICO (#4) |
| 4 | `EFX_BC_DQOCURNC_5==0.0 AND EFX_BC_INQCNT_1==0.0 AND FICO: [694.0:730.0[` | FICO 694–730 + No Inquiry + Clean BC DQ | 13,060 | 13.06% | 0.26% | 0.30% | 0.20% | 0.28% | ✓ | 0.64× | FICO (#4) |
| 5 | `EFX_BC_DQOCURNC_3==0.0 AND FICO: [664.0:694.0[` | FICO 664–694 + Clean BC DQ 3mo | 12,939 | 12.94% | 0.26% | 0.26% | 0.23% | 0.30% | ✓ | 0.64× | FICO (#4) |
| 6 | `EFX_AL_BAL_1: [67488.0:135936.0[ AND EFX_AL_DQOCURNC_1==0.0` | High Balance $67.5K–$136K + Clean DQ | 13,079 | 13.08% | 0.28% | 0.33% | 0.29% | 0.21% | ✓ | 0.67× | EFX_AL_BAL_1 (#2) |

**Key observations for future runs:**
- FICO band 664–730 appears in 4/6 rules — highly reliable suppression signal; watch for drift if FICO distribution shifts
- EFX_BC_UTIL_1 (mid-range 16–35%) is the #1 SHAP driver; rules using it (seg 2) are mechanistically strong
- EFX_AL_BAL_1 band $67.5K–$136K (seg 6) has more wave volatility (0.21%–0.33%) — monitor if this widens
- No inquiry in past 1 month (EFX_BC_INQCNT_1==0) appears in 3 rules; confirms low credit-seeking behaviour
- Stability pass criterion: all individual wave rates AND overall rate < BAU (0.41%)

---
