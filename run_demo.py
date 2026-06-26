"""
End-to-end orchestrator -- the "overnight run." Dataset-agnostic: pass a run
spec; everything example-specific lives there.

    v0  one-feature decision-tree cuts          (EDA + driver thresholds)
    v1  multi-feature subgroup discovery        (the core: ranked segment rules)
    v2  stability across a time/cohort column   (trend validation; optional)
    v3  SHAP driver ranking                      (why it behaves this way)

Writes outputs/REPORT.md. This is the deterministic fallback / smoke test; in
the live demo the AGENT runs these stages (per SKILL.md) and narrates.

Usage:  python run_demo.py [--config config.json]
"""
from __future__ import annotations
import argparse, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))

from common import load_config, load_data, bau, target_name        # noqa: E402
from tree_cuts import one_feature_cuts                             # noqa: E402
from subgroup_search import discover                               # noqa: E402
from stability import stability                                    # noqa: E402
import pysubgroup as ps                                            # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    os.makedirs("outputs", exist_ok=True)

    df = load_data(cfg)
    base = bau(df, cfg)
    direction = cfg["direction"]

    one_feature_cuts(df, cfg).to_csv("outputs/v0_tree_cuts.csv", index=False)
    v1 = discover(df, cfg); v1.to_csv("outputs/v1_subgroups.csv", index=False)
    v2 = stability(df, cfg)

    if v2 is not None:
        v2.to_csv("outputs/v2_stability.csv", index=False)
        keep = v2[v2["stable"]]["rule"].tolist()
        top = v1[v1["rule"].isin(keep)].head(5)
        valid_note = " (validated stable across windows)"
    else:
        top = v1.head(5)
        valid_note = ""

    verb = "suppression" if direction == "suppression" else "targeting"
    L = []; w = L.append
    w(f"# Segment Discovery -- Overnight Run Report  ({cfg.get('name','run')})\n")
    w(f"**Population:** {len(df):,}   **Target:** `{target_name(cfg)}`   "
      f"**BAU rate:** {base:.4%}   **Direction:** {direction}\n")
    w(f"## Recommended {verb} segments (ranked by lift){valid_note}\n")
    w("| # | Segment rule | Size | Size % | Target rate | Lift vs BAU |")
    w("|---|---|---|---|---|---|")
    for i, (_, r) in enumerate(top.iterrows(), 1):
        w(f"| {i} | `{r['rule']}` | {r['size']:,} | {r['size_pct']}% | "
          f"{r['response_rate']}% | {r['lift']}x |")
    if len(top):
        best = top.iloc[0]
        union = None
        for rule in top["rule"]:
            m = ps.Conjunction.from_str(rule).covers(df)
            union = m if union is None else (union | m)
        n = int(union.sum())
        w(f"\n**Headline:** top segment `{best['rule']}` has a {target_name(cfg)} "
          f"rate of {best['response_rate']}% vs {base*100:.4f}% BAU "
          f"({best['lift']}x). The {len(top)} segments together cover "
          f"~{n:,} records ({100*n/len(df):.1f}% of the file).\n")
    w("## What the analyst does next")
    w("- Review / accept / reject each rule (human-in-the-loop).")
    w("- Operationalise accepted rules; re-run as new data lands.\n")
    w("---\n*Stages v0->v3. Full tables in outputs/v*.csv.*")

    report = "\n".join(L)
    open("outputs/REPORT.md", "w", encoding="utf-8").write(report)
    print(report)
    print("\n[saved -> outputs/REPORT.md]")


if __name__ == "__main__":
    main()
