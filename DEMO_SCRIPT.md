# Demo Run-of-Show — Segmentation & Feature Discovery

~10 minutes. Goal: show an agent compress 3–5 weeks of manual segment discovery
into an "overnight run" that an analyst reviews.

The skill is **generic** — it works on any dataset by writing a JSON run spec.
Two examples are ready: `config.json` (real credit-card solicitation, BEST data)
and `config.dm_campaign.json` (synthetic, with planted segments for validation).
Pick whichever lands best with the audience; the script below uses the real one.

## Before you start (once)
```bash
pip install pandas scikit-learn pysubgroup shap openpyxl
cd segment-discovery-demo
python data/generate_synthetic.py            # only for the synthetic example
python run_demo.py                            # real sample; warm cache, confirm clean
```
Open the folder in **Claude Code**.

## Two ways to open the demo
- **Details given (Path A):** *"Find suppression segments in Sample_Data.csv;
  response = BCP_APPLICATION_ID present; use the BEST dictionary for sentinels;
  exclude post-outcome fields."* → agent writes `config.json`, runs stages.
- **Cold start (Path B):** *"Here's the data + dictionary — figure out a target
  and predictive fields, flag leakage, find low-response segments."* → agent
  inspects, proposes a spec (and can research domain-standard features), confirms,
  then runs. Great for showing the "no instructions needed" capability.

## The narrative arc (tell this, don't just run code)

**1. The problem (30s).** "On the DM Non-Responder project, analysts spent 3–5
weeks manually trying hundreds of feature combinations to find customers who
never respond, so the bank could stop mailing them. We're going to let an agent
do the search and just review the answer."

**2. Frame it right (30s).** "This is *supervised* discovery — we have a target
(did they respond?). We want simple, explainable *rules*, not black-box clusters
the bank can't act on."

**3. v0 — what the analyst did by hand (2 min).**
> Ask Claude: *"Establish the base response rate and find single-feature cuts
> with the most signal."*
Shows BAU ≈ 0.18% and that single features alone are weak/noisy → motivates the
real search.

**4. v1 — the money shot (3 min).**
> *"Now search across thousands of multi-feature combinations and rank the
> segments that respond far below BAU."*
Surfaces e.g. **`age>=72 AND total_balance<1182` → 0.037% vs 0.18% BAU (0.21x),
n≈8k.** Point out these are *non-obvious combinations* the manual loop misses.

**5. v2 — validation (2 min).**
> *"Confirm each segment stays low across the 1-year and 2-year campaign windows."*
One segment drifts above threshold and is flagged unstable — show that the agent
*rejects* weak findings, it doesn't just rubber-stamp.

**6. v3 + report (1.5 min).**
> *"Rank the global drivers and write the overnight report."*
SHAP confirms total_balance / prior_campaigns / age drive response — same
features the rules use. Open `outputs/REPORT.md`: ranked validated segments +
"suppress ~16% of the file, almost no booking loss."

**7. Close (30s).** "Weeks → overnight. Human stays in the loop on accept/reject.
Swap in real anonymized bureau data by changing two lines in `common.py`."

## The "expand from simple" story (for Q&A)
- **Simplest:** the `SKILL.md` + four tool scripts you just saw (today).
- **+ Connector:** point the skill at a live warehouse (Snowflake/Databricks MCP)
  instead of a CSV.
- **+ Sub-agents:** explorer / scorer / validator / narrator as separate agents
  (parallelize the R27–R32 loops).
- **+ Cowork plugin:** package as a connector so non-technical analysts run it.
- **+ Memory:** store accepted segment definitions for reuse across campaigns.

## If something breaks on stage
Run the deterministic fallback — `python run_demo.py` always produces
`outputs/REPORT.md` without any LLM call.

## Planted ground truth (so you can speak to accuracy)
SEG-A (mailer-saturated + dormant credit), SEG-B (low-util + many cards),
SEG-C (older + thin balances), all ≈0.04–0.09% vs 0.18% BAU. The pipeline
rediscovering them *is* the validation.
