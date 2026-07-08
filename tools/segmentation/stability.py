"""
v2 tool  --  Stability / trend validation across a time or cohort column.

Takes the discovered rules (outputs/segmentation/v1_subgroups.csv) and re-computes the target
rate within each value of cfg["time_column"]. A segment is STABLE if it stays on
the right side of BAU in every window. Dataset-agnostic.

If no time_column is set in the run spec, this is a no-op (prints a notice).

Usage:  python tools/segmentation/stability.py [--config config.json]
"""
from __future__ import annotations
import argparse
import pandas as pd
import pysubgroup as ps
from common import load_config, load_data, segment_stats, bau, target_name


def stability(df, cfg, rules_csv: str = "outputs/segmentation/v1_subgroups.csv", top: int = 6):
    win = cfg.get("time_column")
    if not win or win not in df.columns:
        return None
    tgt = target_name(cfg)
    base = bau(df, cfg)
    suppression = cfg["direction"] == "suppression"
    thresh = base  # stable = consistently on the correct side of BAU

    rules = pd.read_csv(rules_csv).head(top)
    windows = sorted(df[win].dropna().unique())
    out = []
    for _, r in rules.iterrows():
        mask = ps.Conjunction.from_str(r["rule"]).covers(df)
        row = {"rule": r["rule"], "overall_lift": r["lift"]}
        rates = []
        for w in windows:
            sub = df[mask & (df[win] == w)]
            wr = sub[tgt].mean() if len(sub) else float("nan")
            row[f"resp[{w}]"] = round(100 * wr, 4)
            row[f"n[{w}]"] = int(len(sub))
            rates.append(wr)
        ok = [x for x in rates if x == x]
        row["stable"] = bool(ok) and all(
            (x < thresh) if suppression else (x > thresh) for x in ok)
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    df = load_data(cfg)
    res = stability(df, cfg)
    if res is None:
        print(f"[{cfg.get('name','run')}] no time_column set -> stability skipped.")
    else:
        base = bau(df, cfg)
        pd.set_option("display.width", 180, "display.max_colwidth", 70)
        print(f"\nBAU={base:.4%}  window={cfg['time_column']}  "
              f"direction={cfg['direction']}\n")
        print(res.to_string(index=False))
        res.to_csv("outputs/segmentation/v2_stability.csv", index=False)
        print("\nSaved -> outputs/segmentation/v2_stability.csv")
