"""
v1 tool  --  Automated multi-feature subgroup discovery (the core value-add).

Uses `pysubgroup` to search thousands of multi-condition rule combinations at
once and rank those whose target rate deviates most from BAU -- the "non-obvious
combinations the manual loop misses." Dataset-agnostic: driven by the run spec.

For direction="suppression" we target the NEGATIVE class so the highest-
deviation subgroups are the LOW-response ones; for "targeting" we target the
positive class. Either way we then sort by lift in the requested direction.

Usage:  python tools/segmentation/subgroup_search.py [--config config.json]
"""
from __future__ import annotations
import argparse
import pandas as pd
import pysubgroup as ps
from common import (load_config, load_data, feature_cols, segment_stats, bau,
                    target_name)


def discover(df, cfg, result_set_size: int = 25, depth: int = 3):
    tgt = target_name(cfg)
    feats = feature_cols(df, cfg)
    work = df[feats + [tgt]].copy()

    suppression = cfg["direction"] == "suppression"
    target_value = 0 if suppression else 1
    target = ps.BinaryTarget(tgt, target_value)
    searchspace = ps.create_selectors(work, ignore=[tgt])
    task = ps.SubgroupDiscoveryTask(
        work, target, searchspace,
        result_set_size=result_set_size, depth=depth, qf=ps.WRAccQF())
    result = ps.BeamSearch(beam_width=max(50, result_set_size)).execute(task)

    min_size = int(len(df) * cfg["min_segment_pct"] / 100)
    rows = []
    for _, r in result.to_dataframe().iterrows():
        sg = r["subgroup"]
        st = segment_stats(df, sg.covers(df), cfg)
        if st["size"] >= min_size:
            rows.append({"rule": str(sg), "quality": round(r["quality"], 6), **st})
    out = pd.DataFrame(rows)
    return out.sort_values("lift", ascending=suppression).reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    df = load_data(cfg)
    res = discover(df, cfg)
    pd.set_option("display.width", 170, "display.max_colwidth", 75)
    print(f"\n[{cfg.get('name','run')}]  target={target_name(cfg)}  "
          f"direction={cfg['direction']}")
    print(f"BAU response rate: {bau(df, cfg):.4%}   n={len(df):,}   "
          f"features={len(feature_cols(df, cfg))}\n")
    print(f"Top multi-feature {cfg['direction']} segments:\n")
    print(res.head(12).to_string(index=False))
    res.to_csv("outputs/segmentation/v1_subgroups.csv", index=False)
    print("\nSaved -> outputs/segmentation/v1_subgroups.csv")
