"""
v0 tool  --  One-feature decision-tree cuts  (EDA + driver thresholds).

For each feature, fit a shallow decision tree on the target and read off the
threshold(s) that carve out the most extreme leaf. Rank by lift. Dataset-
agnostic: everything comes from the run spec (see tools/common.py).

Usage:  python tools/tree_cuts.py [--config config.json]
"""
from __future__ import annotations
import argparse
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from common import (load_config, load_data, feature_cols, segment_stats, bau,
                    target_name)


def one_feature_cuts(df, cfg, max_depth: int = 2):
    tgt = target_name(cfg)
    min_size = int(len(df) * cfg["min_segment_pct"] / 100)
    asc = cfg["direction"] == "suppression"        # suppression -> lowest lift first
    rows = []
    for col in feature_cols(df, cfg):
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            X, names = s.fillna(s.median()).values.reshape(-1, 1), [col]
        else:
            dummies = pd.get_dummies(s, prefix=col)
            X, names = dummies.values, list(dummies.columns)
        tree = DecisionTreeClassifier(max_depth=max_depth, min_samples_leaf=min_size,
                                      random_state=0)
        tree.fit(X, df[tgt])
        leaf = tree.apply(X)
        for leaf_id in pd.unique(leaf):
            mask = leaf == leaf_id
            st = segment_stats(df, mask, cfg)
            if st["size"] >= min_size and st["lift"] is not None:
                rows.append({"feature": col,
                             "rule": _describe_leaf(tree, names, leaf_id, X),
                             **st})
    out = pd.DataFrame(rows)
    return out.sort_values("lift", ascending=asc).reset_index(drop=True)


def _describe_leaf(tree, names, leaf_id, X) -> str:
    t = tree.tree_
    idx = next(i for i in range(len(X)) if tree.apply(X[i:i + 1])[0] == leaf_id)
    node, parts = 0, []
    while t.children_left[node] != t.children_right[node]:
        f, thr = names[t.feature[node]], t.threshold[node]
        if X[idx, t.feature[node]] <= thr:
            parts.append(f"{f} <= {thr:.3g}"); node = t.children_left[node]
        else:
            parts.append(f"{f} > {thr:.3g}"); node = t.children_right[node]
    return " AND ".join(parts) if parts else "(all)"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    df = load_data(cfg)
    res = one_feature_cuts(df, cfg)
    pd.set_option("display.width", 150, "display.max_colwidth", 55)
    print(f"\n[{cfg.get('name','run')}]  target={target_name(cfg)}  "
          f"direction={cfg['direction']}")
    print(f"BAU response rate: {bau(df, cfg):.4%}   n={len(df):,}\n")
    print(f"Most extreme single-feature cuts ({cfg['direction']} candidates):\n")
    print(res.head(10).to_string(index=False))
    res.to_csv("outputs/v0_tree_cuts.csv", index=False)
    print("\nSaved -> outputs/v0_tree_cuts.csv")
