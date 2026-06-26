"""
Shared, DATASET-AGNOSTIC helpers for the segment-discovery tools.

Nothing here is specific to any one example. All example-specific facts (which
file, which target, which columns are IDs/leakage, what the missing-value
sentinels are, time column, direction) live in a JSON **run spec** that the
agent writes from the prompt. See `spec.example.json` and the SKILL.

Run spec schema (all keys optional except data_path + target):

{
  "name": "credit_card_solicitation",
  "data_path": "data/Sample_Data.csv",        # csv or xlsx
  "sheet": null,                                # for xlsx
  "target": {
     "name": "responded",                       # name to create
     # ONE of the following derivation modes:
     "from_notnull": "BCP_APPLICATION_ID",       #  -> 1 where column is non-null
     "column": "responded", "positive_value": 1, #  -> use an existing 0/1 column
     "from_value": {"column": "status", "equals": "booked"}
  },
  "direction": "suppression",                    # "suppression" (low) | "targeting" (high)
  "id_columns": ["SRC_ID", "ACCT_ID"],           # identifiers, never features
  "exclude_columns": ["BCP_ACCOUNT_ID"],         # leakage / post-outcome / unwanted
  "feature_columns": null,                        # null = auto-select; or explicit list
  "time_column": "TEST_CELL_DROP_DATE",          # optional, for stability
  "missing_sentinels": [9999997, 9999998, 9999999, 995, 997, 998, 999],
  "min_segment_pct": 1.0,
  "max_auto_features": 40,                        # cap when auto-selecting
  "data_dictionary": "data/BEST_Data_Dictionary.xlsx"  # reference only
}
"""
from __future__ import annotations
import json
import os
import pandas as pd

DEFAULT_CONFIG = "config.json"


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config(path: str | None = None) -> dict:
    path = path or os.environ.get("SEGMENT_CONFIG", DEFAULT_CONFIG)
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("missing_sentinels", [])
    cfg.setdefault("id_columns", [])
    cfg.setdefault("exclude_columns", [])
    cfg.setdefault("feature_columns", None)
    cfg.setdefault("min_segment_pct", 1.0)
    cfg.setdefault("max_auto_features", 40)
    cfg.setdefault("direction", "suppression")
    cfg.setdefault("time_column", None)
    cfg["_path"] = path
    return cfg


def target_name(cfg: dict) -> str:
    return cfg["target"].get("name", "target")


# --------------------------------------------------------------------------- #
# Data loading (sentinel cleaning + target derivation)
# --------------------------------------------------------------------------- #
def load_data(cfg: dict) -> pd.DataFrame:
    p = cfg["data_path"]
    if p.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(p, sheet_name=cfg.get("sheet") or 0)
    else:
        df = pd.read_csv(p)

    # 1) sentinel codes -> NaN (only on numeric columns)
    sentinels = set(cfg.get("missing_sentinels", []))
    if sentinels:
        num = df.select_dtypes("number").columns
        df[num] = df[num].mask(df[num].isin(sentinels))

    # 2) derive / normalise target
    df[target_name(cfg)] = _derive_target(df, cfg["target"])
    return df


def _derive_target(df: pd.DataFrame, t: dict) -> pd.Series:
    if "from_notnull" in t:
        return df[t["from_notnull"]].notna().astype(int)
    if "from_value" in t:
        fv = t["from_value"]
        return (df[fv["column"]] == fv["equals"]).astype(int)
    col = t["column"]
    pos = t.get("positive_value", 1)
    return (df[col] == pos).astype(int)


# --------------------------------------------------------------------------- #
# Feature selection
# --------------------------------------------------------------------------- #
def feature_cols(df: pd.DataFrame, cfg: dict) -> list[str]:
    if cfg.get("feature_columns"):
        return [c for c in cfg["feature_columns"] if c in df.columns]

    tgt = target_name(cfg)
    drop = set(cfg["id_columns"]) | set(cfg["exclude_columns"]) | {tgt}
    # also drop the raw column(s) the target was derived from (leakage)
    t = cfg["target"]
    for k in ("from_notnull", "column"):
        if k in t:
            drop.add(t[k])
    if "from_value" in t:
        drop.add(t["from_value"]["column"])

    feats = []
    for c in df.columns:
        if c in drop:
            continue
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            feats.append(c)
        elif s.nunique(dropna=True) <= 20:          # low-card categorical
            feats.append(c)
        # else: high-cardinality text / dates -> skip
    cap = cfg.get("max_auto_features", 40)
    return feats[:cap]


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
def bau(df: pd.DataFrame, cfg: dict) -> float:
    return df[target_name(cfg)].mean()


def segment_stats(df: pd.DataFrame, mask, cfg: dict) -> dict:
    base = bau(df, cfg)
    tgt = target_name(cfg)
    sub = df[mask]
    rate = sub[tgt].mean() if len(sub) else 0.0
    return {
        "size": int(len(sub)),
        "size_pct": round(100 * len(sub) / len(df), 2),
        "response_rate": round(100 * rate, 4),
        "bau": round(100 * base, 4),
        "lift": round(rate / base, 3) if base else None,
    }
