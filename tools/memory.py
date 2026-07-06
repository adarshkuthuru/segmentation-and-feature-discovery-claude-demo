"""
Persistent run memory for segment discovery.

Appends a structured entry to memory.md after each run, reads recent context
before a run, and summarises entries older than 30 days to keep the file lean.

CLI:
    python tools/memory.py --action read    [--config config.json]
    python tools/memory.py --action write   [--config config.json]
    python tools/memory.py --action compact

Memory file: memory.md at the project root.
"""
from __future__ import annotations
import argparse, json, os, re, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from common import load_config

MEMORY_FILE = "memory.md"
CUTOFF_DAYS = 30
RECENT_SHOW = 3

_HEADER = (
    "# Segment Discovery Run Memory\n\n"
    "_Auto-maintained by tools/memory.py. "
    "Entries older than 30 days are summarised._\n\n"
)


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


def _load_outputs() -> dict:
    """Read output CSVs + run_meta.json; return memory fields."""
    import pandas as pd

    data: dict = {}

    meta_path = "outputs/run_meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            data.update(json.load(f))

    v1_path = "outputs/v1_subgroups.csv"
    if os.path.exists(v1_path):
        v1 = pd.read_csv(v1_path)
        data["segments_found"] = len(v1)
        if len(v1):
            data["best_lift"] = v1.iloc[0]["lift"]
            data["top_features"] = _features_from_rules(v1.head(3)["rule"].tolist())
            # Total unique records covered by top-5 segments (size_pct sum, approximate)
            data["coverage_pct"] = round(float(v1.head(5)["size_pct"].sum()), 1)
        data["v1_rules_evaluated"] = data.get("v1_rules_evaluated", len(v1))

    v2_path = "outputs/v2_stability.csv"
    if os.path.exists(v2_path):
        v2 = pd.read_csv(v2_path)
        stable_n = int(v2["stable"].sum())
        total_n = len(v2)
        data["stability_pass"] = f"{stable_n}/{total_n}"
        data["unstable_rules"] = v2[~v2["stable"]]["rule"].tolist()

    v3_path = "outputs/v3_drivers.csv"
    if os.path.exists(v3_path):
        v3 = pd.read_csv(v3_path)
        data["top_drivers"] = v3.head(5)["feature"].tolist() if len(v3) else []

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
        _emit("[memory] No memory.md found -- this appears to be the first run.\n")
        return

    entries = _parse_entries(text)
    relevant = [e for e in entries if cfg_name is None or e["config_name"] == cfg_name]
    recent = relevant[-RECENT_SHOW:]

    out: list[str] = [
        "",
        "=" * 64,
        "  PRIOR RUN CONTEXT  (memory.md)",
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

    row_count = outs.get("row_count", "n/a")
    base_rate = outs.get("bau", None)
    bau_str = f"{float(base_rate):.4%}" if base_rate is not None else "n/a"

    segs = outs.get("segments_found", 0)
    best_lift = outs.get("best_lift", "n/a")
    coverage = outs.get("coverage_pct", "n/a")
    coverage_str = f"{coverage}% (top 5 segs)" if isinstance(coverage, (int, float)) else "n/a"

    top_feats = outs.get("top_features", [])
    stab = outs.get("stability_pass", "n/a — no time_column")
    unstable = outs.get("unstable_rules", [])
    top_drivers = outs.get("top_drivers", [])

    # Stage durations from run_meta.json
    durations = outs.get("stage_durations", {})
    dur_str = "  |  ".join(f"{k}: {v:.0f}s" for k, v in durations.items()) if durations else "n/a"

    lines = [
        f"### {now} — {cfg_name}",
        f"**Data:** {os.path.basename(cfg['data_path'])} | {row_count:,} rows | BAU: {bau_str} | {cfg.get('direction', 'suppression')}" if isinstance(row_count, int) else f"**Data:** {os.path.basename(cfg['data_path'])} | BAU: {bau_str} | {cfg.get('direction', 'suppression')}",
        f"**Features in top rules:** {', '.join(top_feats) if top_feats else 'n/a'}",
        f"**Segments found:** {segs} | **Best lift:** {best_lift}x | **List coverage:** {coverage_str}",
        f"**Stability:** {stab} rules stable" + (f" ({len(unstable)} failed)" if unstable else ""),
    ]
    if unstable:
        preview = unstable[:2]
        suffix = " ..." if len(unstable) > 2 else ""
        lines.append(f"**Unstable rules:** {'; '.join(preview)}{suffix}")
    if top_drivers:
        lines.append(f"**Top SHAP drivers:** {', '.join(top_drivers)}")
    lines.append(f"**Stage durations:** {dur_str}")
    lines.append(f"**Config delta vs prior run:** {config_delta}")
    lines.append(f"**Config snapshot:** {json.dumps(cfg_snapshot, separators=(',', ':'))}")

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
    ap.add_argument("--action", choices=["read", "write", "compact"], required=True)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()

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
