"""
v3 tool  --  Driver analysis (why the segments behave as they do).

Fits a gradient-boosted model on the target and uses SHAP to rank which
attributes most drive the outcome globally. Confirms the discovered rules are
mechanistically sensible, not artifacts. Dataset-agnostic.

Usage:  python tools/segmentation/drivers.py [--config config.json]
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
import shap
from common import load_config, load_data, feature_cols, target_name


def driver_ranking(df, cfg, sample: int = 20000) -> pd.DataFrame:
    feats = feature_cols(df, cfg)
    X = pd.get_dummies(df[feats], drop_first=True)
    y = df[target_name(cfg)]
    model = HistGradientBoostingClassifier(max_depth=4, max_iter=150, random_state=0)
    model.fit(X, y)

    Xs = X.sample(min(sample, len(X)), random_state=0)
    sv = shap.TreeExplainer(model).shap_values(Xs)
    if isinstance(sv, list):
        sv = sv[1]
    return (pd.DataFrame({"feature": Xs.columns,
                          "mean_abs_shap": np.abs(sv).mean(axis=0)})
            .sort_values("mean_abs_shap", ascending=False).reset_index(drop=True))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    df = load_data(cfg)
    res = driver_ranking(df, cfg)
    pd.set_option("display.width", 120)
    print(f"\n[{cfg.get('name','run')}] Top drivers of {target_name(cfg)} "
          f"(mean |SHAP|):\n")
    print(res.head(15).to_string(index=False))
    res.to_csv("outputs/segmentation/v3_drivers.csv", index=False)
    print("\nSaved -> outputs/segmentation/v3_drivers.csv")
