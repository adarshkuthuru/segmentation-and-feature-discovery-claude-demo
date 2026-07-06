# Segment Discovery Run Memory

_Auto-maintained by tools/memory.py. Entries older than 30 days are summarised._

## ACTIVE RUNS (last 30 days)

### 2026-07-06 16:07 — capital_one_dm_suppression
**Data:** Sample_Data.csv | BAU: n/a | suppression
**Features in top rules:** EFX_AL_DQOCURNC_5, EFX_BC_DQOCURNC_3, FICO, EFX_AL_DQOCURNC_1, EFX_BC_INQCNT_1, EFX_BC_UTIL_1
**Segments found:** 25 | **Best lift:** 0.579x | **List coverage:** 58.4% (top 5 segs)
**Stability:** 0/6 rules stable (6 failed)
**Unstable rules:** EFX_AL_DQOCURNC_5==0.0 AND EFX_BC_DQOCURNC_3==0.0 AND FICO: [664.0:694.0[; EFX_AL_DQOCURNC_1==0.0 AND EFX_BC_INQCNT_1==0.0 AND EFX_BC_UTIL_1: [16.0:35.0[ ...
**Top SHAP drivers:** EFX_BC_UTIL_1, EFX_AL_BAL_1, EFX_AL_TRDAGE_1, FICO, EFX_AL_DQOCURNC_3
**Stage durations:** n/a
**Config delta vs prior run:** first run
**Config snapshot:** {"feature_columns":["FICO","CURRENT_INCOME","EFX_AL_BAL_1","EFX_BC_BAL_1","EFX_BC_BAL_5","EFX_AR_BAL_1","EFX_AL_TRDCNT_1","EFX_BC_TRDCNT_1","EFX_BC_TRDCNT_4","EFX_AL_TRDCNT_5","EFX_BC_TRDCNT_5","EFX_AL_TRDAGE_1","EFX_BC_TRDAGE_1","EFX_BC_TRDAGE_2","EFX_BC_TRDAGE_3","EFX_BC_INQCNT_1","EFX_BC_INQCNT_2","EFX_BC_INQCNT_4","EFX_AL_DQOCURNC_1","EFX_AL_DQOCURNC_2","EFX_AL_DQOCURNC_3","EFX_BC_DQOCURNC_3","EFX_AL_DQOCURNC_5","EFX_BC_DQOCURNC_5","EFX_BC_UTIL_1"],"time_column":"TEST_CELL_DROP_DATE","min_segment_pct":1.0,"direction":"suppression","exclude_columns":["BCP_ACCOUNT_ID","BCP_APPLICATION_ID","BCP_APPLICATION_RECEIVED_DATE","PV","SOLICITATION_ID","TEST_CELL_DROP_DATE"]}

---
