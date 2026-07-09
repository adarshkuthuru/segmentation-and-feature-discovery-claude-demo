"""
Persistent run memory for segment discovery.

Appends a structured entry to memory_segmentation.md after each run, reads recent
context before a run, and summarises entries older than 30 days to keep the file
lean. This is the segment-discovery workstream's memory file — the dataset-analyzer
(EDA) workstream keeps its own separate memory_eda.md at the project root.

CLI:
    python tools/segmentation/memory.py --action read    [--config config.json]
    python tools/segmentation/memory.py --action write   [--config config.json]
    python tools/segmentation/memory.py --action compact

Memory file: memory_segmentation.md at the project root.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import load_config

MEMORY_FILE = "memory_segmentation.md"
CHANGELOG_FILE = "CHANGELOG_segmentation.md"
CUTOFF_DAYS = 30
RECENT_SHOW = 3
CHANGELOG_RECENT = 5  # number of recent changelog entries to surface in action_read

_HEADER = (
    "# Segment Discovery Run Memory\n\n"
    "_Workstream: segment-discovery. Auto-maintained by tools/segmentation/memory.py. "
    "Entries older than 30 days are summarised. For the dataset-analyzer (EDA) "
    "workstream, see [memory_eda.md](memory_eda.md) instead._\n\n"
)


# ── changelog helpers ─────────────────────────────────────────────────────────

def _changelog_append(entry: str) -> None:
    """Append a new dated entry block to CHANGELOG_segmentation.md."""
    p = Path(CHANGELOG_FILE)
    if p.exists():
        existing = p.read_text(encoding="utf-8")
        new_text = existing.rstrip() + "\n\n" + entry.strip() + "\n\n---\n"
    else:
        header = (
            "# Segmentation Pipeline Changelog\n\n"
            "_Auto-maintained by tools/segmentation/memory.py. "
            "Read before each run; written after each run._\n\n---\n\n"
        )
        new_text = header + entry.strip() + "\n\n---\n"
    p.write_text(new_text, encoding="utf-8")


def _changelog_read_recent() -> str:
    """Return the last CHANGELOG_RECENT entry blocks from CHANGELOG_segmentation.md."""
    p = Path(CHANGELOG_FILE)
    if not p.exists():
        return "[changelog] No CHANGELOG_segmentation.md found — this appears to be the first run.\n"
    text = p.read_text(encoding="utf-8")
    # Split on any --- separator (with optional surrounding whitespace)
    import re as _re
    blocks = [b.strip() for b in _re.split(r"\n\s*---\s*\n", text)
              if b.strip() and not b.strip().startswith("#")]
    recent = blocks[-CHANGELOG_RECENT:]
    return "\n\n---\n\n".join(recent)


# ── file helpers ──────────────────────────────────────────────────────────────

def _read_file() -> str:
    p = Path(MEMORY_FILE)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _write_file(content: str) -> None:
    Path(MEMORY_FILE).write_text(content, encoding="utf-8")


def _parse_entries(text: str) -> list[dict]:
    """Return list of dicts with keys: timestamp, config_name, body."""
    entries = []
    pattern = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) — (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        ts_str, cfg_name = m.group(1), m.group(2).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        entries.append({"timestamp": ts, "config_name": cfg_name, "body": body})
    return entries


_RULE_KEYWORDS = {"AND", "OR", "NOT", "IN", "IS", "NULL", "TRUE", "FALSE"}

def _features_from_rules(rules: list[str]) -> list[str]:
    """Extract column-name tokens from pysubgroup rule strings, excluding keywords."""
    seen: set[str] = set()
    out: list[str] = []
    for rule in rules:
        for tok in re.findall(r"[A-Z][A-Z0-9_]{2,}", rule):
            if tok not in _RULE_KEYWORDS and tok not in seen:
                seen.add(tok)
                out.append(tok)
    return out


def _rule_to_label(rule: str) -> str:
    """Convert a pysubgroup rule string into a short human-readable business label."""
    conditions = [c.strip() for c in rule.split(" AND ")]
    parts: list[str] = []
    for cond in conditions:
        m = re.match(r"FICO: \[(\d+\.?\d*):(\d+\.?\d*)\[", cond)
        if m:
            parts.append(f"FICO {int(float(m.group(1)))}–{int(float(m.group(2)))}")
            continue
        m = re.match(r"(\w+)==0\.0", cond)
        if m:
            feat = m.group(1)
            tm = re.search(r"_(\d+)$", feat)
            t = tm.group(1) if tm else "?"
            if "DQ" in feat:
                src = "BC" if "BC" in feat else "AL"
                parts.append(f"Clean {src} DQ {t}mo")
            elif "INQCNT" in feat:
                parts.append(f"No Inq {t}mo")
            else:
                parts.append(f"{feat}=0")
            continue
        m = re.match(r"(\w+): \[(.+?):(.+?)\[", cond)
        if m:
            feat, lo_s, hi_s = m.group(1), m.group(2), m.group(3)
            lo, hi = float(lo_s), float(hi_s)
            if "BAL" in feat:
                parts.append(f"${lo/1000:.0f}K–${hi/1000:.0f}K Bal")
            elif "UTIL" in feat:
                parts.append(f"Util {int(lo)}–{int(hi)}%")
            elif "TRDAGE" in feat:
                parts.append(f"TrdAge {int(lo)}–{int(hi)}mo")
            elif "INCOME" in feat:
                parts.append(f"Income ${lo/1000:.0f}K–${hi/1000:.0f}K")
            else:
                parts.append(f"{feat} {lo:.0f}–{hi:.0f}")
    return " + ".join(parts) if parts else rule[:50]


def _shap_grounded(rule: str, v3_rank: dict[str, int]) -> str:
    """Return top-2 SHAP-ranked features appearing in the rule, formatted as FEAT (#rank)."""
    feats = [f for f in re.findall(r"[A-Z][A-Z0-9_]{2,}", rule) if f not in _RULE_KEYWORDS]
    ranked = sorted([(f, v3_rank[f]) for f in feats if f in v3_rank], key=lambda x: x[1])
    return ", ".join(f"{f} (#{r})" for f, r in ranked[:2]) if ranked else "—"


def _build_segment_table(v1, v2, v3, bau: float) -> str:
    """Build a full markdown segment table matching the 2026-07-06 memory format."""
    import pandas as pd

    v3_rank = {row["feature"]: i + 1 for i, (_, row) in enumerate(v3.iterrows())}
    wave_cols = [c for c in v2.columns if c.startswith("resp[")]
    wave_labels = [c[5:-1] for c in wave_cols]  # strip "resp[" and "]"

    merged = v2.merge(
        v1[["rule", "size", "size_pct", "response_rate", "lift"]],
        on="rule", how="left",
    )

    wave_hdr = " | ".join(wave_labels)
    col_count = 9 + len(wave_cols)
    lines = [
        f"| # | Full Rule (pysubgroup) | Business Label | Size | Size% | Overall Rate | {wave_hdr} | Stable | Lift | SHAP-grounded features |",
        "|" + "|".join(["---"] * col_count) + "|",
    ]
    for i, (_, row) in enumerate(merged.iterrows(), 1):
        rule = row["rule"]
        size = f"{int(row['size']):,}" if not pd.isna(row.get("size", float("nan"))) else "—"
        size_pct = f"{float(row['size_pct']):.2f}%" if not pd.isna(row.get("size_pct", float("nan"))) else "—"
        rate = f"{float(row['response_rate']):.2f}%" if not pd.isna(row.get("response_rate", float("nan"))) else "—"
        stable = "✓" if row["stable"] else "✗"
        lift = f"{float(row['overall_lift']):.2f}×"
        wave_rates = " | ".join(
            f"{float(row[c]):.2f}%" if c in row.index and not pd.isna(row[c]) else "—"
            for c in wave_cols
        )
        shap_feats = _shap_grounded(rule, v3_rank)
        label = _rule_to_label(rule)
        lines.append(
            f"| {i} | `{rule}` | {label} | {size} | {size_pct} | {rate} | {wave_rates} | {stable} | {lift} | {shap_feats} |"
        )
    return "\n".join(lines)


def _auto_observations(v1, v2, v3, bau: float) -> list[str]:
    """Auto-generate key observations from run data for future-run context."""
    import pandas as pd

    obs: list[str] = []
    total_rules = len(v2)

    # Feature frequency across stable rules
    feat_counts: dict[str, int] = {}
    for rule in v2["rule"]:
        for feat in re.findall(r"[A-Z][A-Z0-9_]{2,}", rule):
            if feat not in _RULE_KEYWORDS:
                feat_counts[feat] = feat_counts.get(feat, 0) + 1
    frequent = sorted(feat_counts.items(), key=lambda x: -x[1])
    for feat, cnt in frequent[:3]:
        if cnt >= 2:
            obs.append(
                f"{feat} appears in {cnt}/{total_rules} rules — "
                f"highly reliable suppression signal; watch for drift if distribution shifts"
            )

    # Top SHAP driver commentary
    if len(v3) >= 2:
        top1, top2 = v3.iloc[0], v3.iloc[1]
        obs.append(
            f"{top1['feature']} ({float(top1['mean_abs_shap']):.3f}) is the #1 SHAP driver; "
            f"{top2['feature']} ({float(top2['mean_abs_shap']):.3f}) is #2"
        )

    # Wave volatility warnings
    wave_cols = [c for c in v2.columns if c.startswith("resp[")]
    if wave_cols:
        for _, row in v2.iterrows():
            vals = [float(row[c]) for c in wave_cols if not pd.isna(row.get(c))]
            if vals and (max(vals) - min(vals)) > 0.08:
                rule_short = row["rule"][:65] + ("…" if len(row["rule"]) > 65 else "")
                obs.append(
                    f"Rule '{rule_short}' has wave spread "
                    f"{min(vals):.2f}%–{max(vals):.2f}% — monitor if this widens"
                )

    # Stability pass criterion (always include)
    obs.append(
        f"Stability pass criterion: all individual wave rates AND overall rate < BAU ({bau:.2f}%)"
    )
    return obs


def _load_outputs() -> dict:
    """Read output CSVs + run_meta.json; return memory fields."""
    import pandas as pd

    data: dict = {}

    meta_path = "outputs/segmentation/run_meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            data.update(json.load(f))

    v1_path = "outputs/segmentation/v1_subgroups.csv"
    if os.path.exists(v1_path):
        v1 = pd.read_csv(v1_path)
        data["segments_found"] = len(v1)
        if len(v1):
            data["best_lift"] = v1.iloc[0]["lift"]
            # BAU from v1 bau column (avoids dependency on run_meta.json)
            bau = float(v1.iloc[0]["bau"])
            total_rows_raw = float(v1.iloc[0]["size"]) / (float(v1.iloc[0]["size_pct"]) / 100)
            total_rows = round(total_rows_raw / 100) * 100  # round to nearest 100
            data["bau"] = bau
            data["bau_count"] = round(bau / 100 * total_rows)
            data["total_rows"] = total_rows
        data["_v1"] = v1  # private; popped after use in action_write

    v2_path = "outputs/segmentation/v2_stability.csv"
    if os.path.exists(v2_path):
        v2 = pd.read_csv(v2_path)
        stable_n = int(v2["stable"].sum())
        total_n = len(v2)
        data["stability_pass"] = f"{stable_n}/{total_n}"
        data["unstable_rules"] = v2[~v2["stable"]]["rule"].tolist()
        data["deployed_n"] = stable_n
        data["_v2"] = v2
        # Features from stable rules only (matches the quality signal from v2, not all candidates)
        data["top_features"] = _features_from_rules(v2["rule"].tolist())

    v3_path = "outputs/segmentation/v3_drivers.csv"
    if os.path.exists(v3_path):
        v3 = pd.read_csv(v3_path)
        if len(v3):
            top5 = v3.head(5)
            data["top_drivers"] = top5["feature"].tolist()
            data["top_drivers_with_values"] = [
                f"{row['feature']} ({float(row['mean_abs_shap']):.3f})"
                for _, row in top5.iterrows()
            ]
        data["_v3"] = v3

    return data


# ── actions ───────────────────────────────────────────────────────────────────

def _emit(text: str) -> None:
    """Write text to stdout, replacing any unencodable characters."""
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.buffer.write(text.encode(enc, errors="replace"))
    sys.stdout.buffer.flush()


def action_read(cfg_name: str | None) -> None:
    text = _read_file()
    if not text:
        _emit("[memory] No memory_segmentation.md found -- this appears to be the first run.\n")
        return

    entries = _parse_entries(text)
    relevant = [e for e in entries if cfg_name is None or e["config_name"] == cfg_name]
    recent = relevant[-RECENT_SHOW:]

    out: list[str] = [
        "",
        "=" * 64,
        "  PRIOR RUN CONTEXT  (memory_segmentation.md)",
        "=" * 64,
    ]

    if not recent:
        out.append(f"  No prior runs recorded for config '{cfg_name}'.")
    else:
        for e in recent:
            out.append(e["body"])
            out.append("")

    # Append archive summary for this config if present
    if cfg_name and "## ARCHIVED SUMMARY" in text:
        arch_block = text[text.index("## ARCHIVED SUMMARY"):]
        summary_match = re.search(
            r"(### " + re.escape(cfg_name) + r" -- \d+ runs.*?)(?=\n###|\Z)",
            arch_block,
            re.DOTALL,
        )
        if summary_match:
            out.append("--- ARCHIVED SUMMARY ---")
            out.append(summary_match.group(1).strip())
            out.append("")

    out.append("=" * 64)
    out.append("")

    # Also surface recent changelog entries
    changelog_text = _changelog_read_recent()
    if changelog_text:
        out.append("")
        out.append("=" * 64)
        out.append(f"  RECENT CHANGELOG  ({CHANGELOG_FILE}, last {CHANGELOG_RECENT} entries)")
        out.append("=" * 64)
        out.append(changelog_text)
        out.append("=" * 64)
        out.append("")

    _emit("\n".join(out))


def action_write(cfg: dict) -> None:
    cfg_name = cfg.get("name", "unnamed")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = _read_file()
    entries = _parse_entries(text)
    prior_same = [e for e in entries if e["config_name"] == cfg_name]

    # Config delta vs last run for this config
    cfg_snapshot = {
        "feature_columns": cfg.get("feature_columns"),
        "time_column": cfg.get("time_column"),
        "min_segment_pct": cfg.get("min_segment_pct"),
        "direction": cfg.get("direction"),
        "exclude_columns": sorted(cfg.get("exclude_columns", [])),
    }
    config_delta = "first run"
    if prior_same:
        snap_match = re.search(r"\*\*Config snapshot:\*\* (.+)", prior_same[-1]["body"])
        if snap_match:
            try:
                prior_snap = json.loads(snap_match.group(1))
                diffs = [k for k, v in cfg_snapshot.items() if prior_snap.get(k) != v]
                config_delta = ("; ".join(f"{d} changed" for d in diffs)) if diffs else "unchanged"
            except (json.JSONDecodeError, KeyError):
                config_delta = "unknown (parse error)"

    outs = _load_outputs()

    # Pop private DataFrame keys before any serialisation
    v1 = outs.pop("_v1", None)
    v2 = outs.pop("_v2", None)
    v3 = outs.pop("_v3", None)

    # BAU string: "0.41% (410/100,000)"
    bau = outs.get("bau")
    bau_count = outs.get("bau_count")
    total_rows = outs.get("total_rows")
    if bau is not None and bau_count is not None and total_rows is not None:
        bau_str = f"{float(bau):.2f}% ({int(bau_count):,}/{int(total_rows):,})"
    elif bau is not None:
        bau_str = f"{float(bau):.2f}%"
    else:
        bau_str = "n/a"

    # Feature list from ALL top rules
    top_feats = outs.get("top_features", [])

    # "N features | Best lift: Xx | Top N deployed"
    feature_count = len(cfg.get("feature_columns") or [])
    best_lift = outs.get("best_lift", "n/a")
    deployed_n = outs.get("deployed_n", outs.get("stability_pass", "n/a").split("/")[0] if "/" in str(outs.get("stability_pass", "")) else "n/a")

    stab = outs.get("stability_pass", "n/a — no time_column")
    unstable = outs.get("unstable_rules", [])

    # SHAP drivers with values
    top_drivers_with_values = outs.get("top_drivers_with_values", [])
    top_drivers = outs.get("top_drivers", [])
    drivers_str = ", ".join(top_drivers_with_values) if top_drivers_with_values else ", ".join(top_drivers) if top_drivers else "n/a"

    lines = [
        f"### {now} — {cfg_name}",
        f"**Data:** {os.path.basename(cfg['data_path'])} | BAU: {bau_str} | {cfg.get('direction', 'suppression')}",
        f"**Features in top rules:** {', '.join(top_feats) if top_feats else 'n/a'}",
        f"**Segments found (v1):** {feature_count} features | **Best lift:** {best_lift:.3f}x | **Top {deployed_n} deployed**" if isinstance(best_lift, float) else f"**Segments found (v1):** {feature_count} features | **Best lift:** {best_lift}x | **Top {deployed_n} deployed**",
        f"**Stability:** {stab} rules stable (pass = all wave rates < BAU = {float(bau):.2f}%)" if bau is not None else f"**Stability:** {stab} rules stable",
    ]
    if unstable:
        preview = unstable[:2]
        suffix = " ..." if len(unstable) > 2 else ""
        lines.append(f"**Unstable rules:** {'; '.join(preview)}{suffix}")
    lines.append(f"**Top SHAP drivers:** {drivers_str}")
    lines.append(f"**Config delta vs prior run:** {config_delta}")
    lines.append(f"**Config snapshot:** {json.dumps(cfg_snapshot, separators=(',', ':'))}")

    # Full segment table (requires v1 + v2 + v3 DataFrames)
    if v1 is not None and v2 is not None and v3 is not None and bau is not None:
        lines.append("")
        lines.append(f"**TOP {deployed_n} SUPPRESSION SEGMENTS — full rule text, wave rates, SHAP alignment:**")
        lines.append("")
        lines.append(_build_segment_table(v1, v2, v3, float(bau)))

    # Key observations for future runs
    if v1 is not None and v2 is not None and v3 is not None and bau is not None:
        obs = _auto_observations(v1, v2, v3, float(bau))
        if obs:
            lines.append("")
            lines.append("**Key observations for future runs:**")
            for o in obs:
                lines.append(f"- {o}")

    entry_text = "\n".join(lines)

    # Append at the bottom of ACTIVE RUNS section (chronological order)
    section_header = "## ACTIVE RUNS (last 30 days)\n\n"
    if not text:
        new_text = _HEADER + section_header + entry_text + "\n\n---\n"
    elif section_header in text:
        # Find the end of the ACTIVE RUNS section (before ## ARCHIVED or end of file)
        active_start = text.index(section_header)
        after_header = active_start + len(section_header)
        # Locate where ARCHIVED section starts (if any)
        arch_marker = "\n## ARCHIVED"
        if arch_marker in text[after_header:]:
            arch_pos = after_header + text[after_header:].index(arch_marker)
            new_text = text[:arch_pos] + entry_text + "\n\n---\n" + text[arch_pos:]
        else:
            new_text = text.rstrip() + "\n\n" + entry_text + "\n\n---\n"
    else:
        new_text = text + "\n\n" + section_header + entry_text + "\n\n---\n"

    _write_file(new_text)
    print(f"[memory] Entry written -> {MEMORY_FILE}  ({cfg_name} @ {now})")

    # Append a lightweight run entry to the changelog
    data_name = os.path.basename(cfg.get("data_path", "unknown"))
    segs_summary = f"{deployed_n} stable rules" if deployed_n != "n/a" else stab
    lift_summary = f"{float(best_lift):.3f}×" if isinstance(best_lift, float) else str(best_lift)
    changelog_entry = (
        f"## {now} — {cfg_name} [run]\n\n"
        f"**Data:** {data_name} | **BAU:** {bau_str} | **Direction:** {cfg.get('direction', 'suppression')}  \n"
        f"**Config delta:** {config_delta}  \n"
        f"**Segments:** {segs_summary} | Best lift: {lift_summary}  \n"
        f"**Outputs:** v0_tree_cuts.csv, v1_subgroups.csv, v2_stability.csv, v3_drivers.csv, REPORT.md"
    )
    _changelog_append(changelog_entry)
    print(f"[memory] Changelog entry written -> {CHANGELOG_FILE}")


def action_compact() -> None:
    text = _read_file()
    if not text:
        print("[memory] Nothing to compact.")
        return

    entries = _parse_entries(text)
    cutoff = datetime.now() - timedelta(days=CUTOFF_DAYS)
    old = [e for e in entries if e["timestamp"] < cutoff]
    recent = [e for e in entries if e["timestamp"] >= cutoff]

    if not old:
        print(f"[memory] No entries older than {CUTOFF_DAYS} days — nothing to compact.")
        return

    # Group old entries by config_name and build summaries
    by_config: dict[str, list[dict]] = {}
    for e in old:
        by_config.setdefault(e["config_name"], []).append(e)

    summaries: list[str] = []
    for cfg_name, group in sorted(by_config.items()):
        period_start = min(e["timestamp"] for e in group).strftime("%Y-%m-%d")
        period_end = max(e["timestamp"] for e in group).strftime("%Y-%m-%d")
        n = len(group)

        feature_counts: dict[str, int] = {}
        lifts: list[float] = []
        unstable_examples: list[str] = []

        for e in group:
            feat_m = re.search(r"\*\*Features in top rules:\*\* (.+)", e["body"])
            if feat_m and feat_m.group(1) != "n/a":
                for f in feat_m.group(1).split(", "):
                    f = f.strip()
                    feature_counts[f] = feature_counts.get(f, 0) + 1

            lift_m = re.search(r"\*\*Best lift:\*\* ([\d.]+)x", e["body"])
            if lift_m:
                try:
                    lifts.append(float(lift_m.group(1)))
                except ValueError:
                    pass

            unstable_m = re.search(r"\*\*Unstable rules:\*\* (.+)", e["body"])
            if unstable_m:
                unstable_examples.append(unstable_m.group(1).strip())

        reliable = sorted(
            (f for f, cnt in feature_counts.items() if cnt >= max(1, n // 2)),
            key=lambda f: -feature_counts[f],
        )
        lift_range = f"{min(lifts):.2f}-{max(lifts):.2f}x" if lifts else "n/a"
        unique_failures = list(dict.fromkeys(unstable_examples))[:2]

        s_lines = [
            f"### {cfg_name} -- {n} run{'s' if n > 1 else ''} ({period_start} to {period_end})",
            f"- Reliable features (>=50% of runs): {', '.join(reliable) if reliable else 'none consistent'}",
            f"- Typical best lift: {lift_range}",
        ]
        if unique_failures:
            s_lines.append(f"- Recurring unstable rules: {'; '.join(unique_failures)}")
        summaries.append("\n".join(s_lines))

    # Rebuild file: active section + archive section
    active_section = "## ACTIVE RUNS (last 30 days)\n\n"
    if recent:
        active_section += ("\n\n---\n\n".join(e["body"] for e in recent)) + "\n\n---\n\n"

    # Preserve any pre-existing archive entries, then append new ones
    existing_archive = ""
    if "## ARCHIVED SUMMARY" in text:
        arch_start = text.index("## ARCHIVED SUMMARY")
        existing_archive = re.sub(
            r"^## ARCHIVED SUMMARY[^\n]*\n\n?", "", text[arch_start:], flags=re.DOTALL
        ).strip()

    archive_section = "## ARCHIVED SUMMARY (older than 30 days)\n\n"
    if existing_archive:
        archive_section += existing_archive + "\n\n"
    archive_section += "\n\n".join(summaries) + "\n"

    _write_file(_HEADER + active_section + "\n" + archive_section)
    print(
        f"[memory] Compacted {len(old)} old entries into "
        f"{len(by_config)} archive summary block(s)."
    )


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Segment discovery run memory.")
    ap.add_argument("--action", choices=["read", "write", "compact", "changelog"], required=True)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

    if args.action == "changelog":
        # Print recent changelog entries (for standalone inspection)
        text = _changelog_read_recent()
        _emit(
            "\n" + "=" * 64 + "\n"
            f"  RECENT CHANGELOG  ({CHANGELOG_FILE}, last {CHANGELOG_RECENT} entries)\n"
            + "=" * 64 + "\n"
            + text + "\n"
            + "=" * 64 + "\n"
        )
        return

    if args.action == "read":
        cfg_name = None
        if args.config and os.path.exists(args.config):
            try:
                cfg_name = load_config(args.config).get("name")
            except Exception:
                pass
        action_read(cfg_name)

    elif args.action == "write":
        cfg = load_config(args.config)
        action_write(cfg)

    elif args.action == "compact":
        action_compact()


if __name__ == "__main__":
    main()
