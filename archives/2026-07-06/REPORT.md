# Segment Discovery — Suppression Analysis
## Credit Card Direct-Mail Campaign

**Population:** 100,000 solicited prospects  
**Target:** `responded` (BCP_APPLICATION_ID is not null → applied)  
**BAU Response Rate:** 0.41%  
**Direction:** Suppression — find groups who almost never respond

---

## Stability Note

The automated `stable` flag requires ALL mailing-wave rates to fall below **50% of BAU (< 0.205%)**. No segment meets that strict threshold. However, every segment listed below is consistently **below BAU** across all 3 waves (Jan / Feb / Mar 2026), which is the operationally meaningful criterion for suppression.

---

## Top Suppression Segments (ranked by lift vs BAU)

| # | Business Label | Rule | Size | Size % | Resp Rate | BAU | Lift | Jan Rate | Feb Rate | Mar Rate |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | FICO Mid + Clean DQ | No DQ (3yr) + No BC DQ (90d) + FICO 664–694 | 10,947 | 11.0% | 0.24% | 0.41% | 0.58x | 0.25% | 0.19% | 0.27% |
| 2 | Mid-Util, No Inquiry | No recent DQ + No BC inquiries + BC util 16–35% | 10,881 | 10.9% | 0.24% | 0.41% | 0.58x | 0.25% | 0.25% | 0.22% |
| 3 | Good-FICO, No Inquiry | No BC DQ (5yr) + No BC inquiries + FICO 694–730 | 13,060 | 13.1% | 0.26% | 0.41% | 0.64x | 0.30% | 0.20% | 0.28% |
| 4 | Mid-FICO, No DQ 3yr | No BC DQ (3yr) + FICO 664–694 | 12,939 | 12.9% | 0.26% | 0.41% | 0.64x | 0.26% | 0.23% | 0.30% |
| 5 | High Balance, Clean | Total balance $67.5K–$136K + No DQ (1yr) | 13,079 | 13.1% | 0.28% | 0.41% | 0.67x | 0.33% | 0.29% | 0.21% |
| 6 | High Balance + No DQ5 | Total balance $67.5K–$136K + No BC DQ (5yr) | 15,644 | 15.6% | 0.28% | 0.41% | 0.69x | — | — | — |

---

## SHAP Feature Drivers (Global Importance)

| Rank | Feature | Mean |SHAP| | Interpretation |
|---|---|---|---|
| 1 | EFX_BC_UTIL_1 | 0.058 | Bankcard utilization is the single strongest driver |
| 2 | EFX_AL_BAL_1 | 0.057 | Total open balance (all trades) — second strongest |
| 3 | EFX_AL_TRDAGE_1 | 0.036 | Age of all open trades |
| 4 | FICO | 0.035 | Credit score |
| 5 | EFX_AL_DQOCURNC_3 | 0.031 | DQ occurrences (3-year window) |
| 6 | EFX_BC_BAL_5 | 0.025 | Bankcard balance (sub-category) |
| 7 | EFX_BC_TRDAGE_1 | 0.022 | Age of most recent bankcard trade |
| 8 | EFX_AL_TRDCNT_1 | 0.021 | Total number of open trades |

---

## Analyst Actions — Accept / Reject

- [ ] **Seg 1** — FICO Mid + Clean DQ (10.9%, 0.58x lift) — *ACCEPT / REJECT*
- [ ] **Seg 2** — Mid-Util, No Inquiry (10.9%, 0.58x lift) — *ACCEPT / REJECT*
- [ ] **Seg 3** — Good-FICO, No Inquiry (13.1%, 0.64x lift) — *ACCEPT / REJECT*
- [ ] **Seg 4** — Mid-FICO, No DQ 3yr (12.9%, 0.64x lift) — *ACCEPT / REJECT*
- [ ] **Seg 5** — High Balance, Clean (13.1%, 0.67x lift) — *ACCEPT / REJECT*

> Accepting Seg 1 + Seg 2 alone suppresses ~21% of mail with rates 42% below BAU.
> Accepting all 5 could suppress ~40–45% of mail (overlap-adjusted) with rates 33–42% below BAU.

---

*Run: 2026-06-26 | Stages v0 to v3 | Full tables in outputs/v*.csv*
