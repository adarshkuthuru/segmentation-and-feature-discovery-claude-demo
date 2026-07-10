# Segmentation Pipeline Changelog

_Tracks structural changes (files added/deleted/modified, code changes) and
pipeline run events. Run entries are appended automatically by
`tools/segmentation/memory.py --action write`. Manual entries are added by
Claude whenever files are created, deleted, or modified outside of a normal run._

_Read this at the start of each session before running the pipeline.
Write a new entry whenever a structural change is made to the pipeline._

---

## 2026-06-22 — Run 1 [run]

**Data:** Sample_Data.csv | **BAU:** 0.41% (410/100,000) | **Direction:** suppression  
**Config:** capital_one_dm_suppression (first run)  
**Segments:** 6 stable rules | Best lift: 0.579×  
**Outputs:** v0–v3 CSVs, REPORT.md

---

## 2026-06-26 — Run 2 [run]

**Data:** Sample_Data.csv | **BAU:** 0.41% | **Direction:** suppression  
**Config delta:** unchanged  
**Segments:** 6/6 stable | Best lift: 0.579× | Rules identical to run 1  
**Outputs:** v0–v3 CSVs, REPORT.md

---

## 2026-07-01 — Overview PPT created [structural]

### Added
- `tools/segmentation/build_overview_ppt.py` — 2-slide summary deck (later archived)
- `outputs/segmentation/Segment_Feature_Discovery_Overview.pptx` — exec overview

---

## 2026-07-06 — Run 3 + stability threshold fix [run + structural]

**Data:** Sample_Data.csv | **BAU:** 0.41% | **Direction:** suppression  
**Config delta:** unchanged  
**Segments:** 6/6 stable | Best lift: 0.579× | Rules identical to runs 1–2  
**Outputs:** v0–v3 CSVs, REPORT.md, Suppression_Segment_Report_2026-07-06.pptx

### Modified
- `tools/segmentation/memory.py` — stability threshold corrected from incorrect
  value to BAU (0.41%); all wave rates must be below BAU to pass stability

---

## 2026-07-07 — EDA skill + reviewer skill added [structural]

### Added
- `.claude/skills/dataset-analyzer/SKILL.md` — generic 5-phase/20-item EDA skill
- `.claude/skills/eda-reviewer/SKILL.md` — EDA audit/review skill
- `.claude/skills/segment-discovery-reviewer/SKILL.md` — segment pipeline reviewer
- `tools/EDA/eda_full_data.py` — EDA executor script
- `tools/EDA/make_exec_deck_full_data.py` — EDA executive deck builder

---

## 2026-07-09 14:22 — Run 4 [run]

**Data:** Sample_Data.csv | **BAU:** 0.41% | **Direction:** suppression  
**Config delta:** unchanged  
**Segments:** 6/6 stable | Best lift: 0.579× | Rules confirmed identical (4th consecutive)  
**Outputs:** v0–v3 CSVs, REPORT.md

---

## 2026-07-09 14:35 — Run 5 [run]

**Data:** Sample_Data.csv | **BAU:** 0.41% | **Direction:** suppression  
**Config delta:** unchanged  
**Segments:** 6/6 stable | Best lift: 0.579× | Rules confirmed identical (5th consecutive)  
**Outputs:** v0–v3 CSVs, REPORT.md

---

## 2026-07-09 — PPT redesign + canonical build script [structural]

### Added
- `tools/segmentation/build_ppt.py` — canonical 6-slide executive PPT builder
  replacing all dated scripts; dynamic CSV loading, native tables, fixed word_wrap
- `tools/segmentation/segment_labels.json` — business labels + plain-English
  criteria for known pysubgroup rule strings; auto-fallback for unknown rules
- `outputs/segmentation/Suppression_Segment_Report_2026-07-09.pptx` — rebuilt
  as clean 6-slide deck (no SHAP slide; slides 4&5 use native tables)

### Deleted
- `tools/segmentation/build_ppt_2026_07_06.py` — superseded by build_ppt.py
- `tools/segmentation/build_ppt_2026_07_09.py` — superseded by build_ppt.py
- `tools/segmentation/build_overview_ppt.py` — 2-slide overview deck (archived)
- `settings.local.json` (project root) — wrong-project file (referenced unrelated repo)
- `archives/REPORT_archived_2026-07-09_r2.md` — intra-day intermediate duplicate
- `archives/Suppression_Segment_Report_2026-07-09_archived_2026-07-09_r2.pptx` — intra-day intermediate duplicate
- `tools/segmentation/__pycache__/` — bytecode cache

### Modified
- `outputs/segmentation/REPORT.md` — updated for latest 3-run cross-validation
- `README.md` — fully rewritten: updated directory tree, setup, run commands,
  worked example, output/archiving convention

### Key design decisions
- PPT now 6 slides (SHAP removed per user request — technical; belongs in REPORT.md only)
- word_wrap bug fixed: `tf.text_frame.word_wrap = True` (not `tf.word_wrap = True`,
  which is a silent no-op on Shape objects)
- Monitor threshold: spread > 0.090 pct-pt catches Segs 4 & 6 (amber); was previously
  0.00080 which flagged every segment
- Segment labels in `segment_labels.json` decouple display names from rule strings

---

## 2026-07-09 — Change management files added [structural]

### Added
- `CHANGELOG_segmentation.md` (this file) — timestamped log of all pipeline
  additions/deletions/modifications; read before each run, written after each run
- `CHANGELOG_EDA.md` — equivalent changelog for the EDA workstream

### Modified
- `tools/segmentation/memory.py` — extended with `--action changelog` to read
  recent changelog entries; `--action write` now also appends a lightweight run
  entry to `CHANGELOG_segmentation.md`
- `.claude/skills/segment-discovery/SKILL.md` — added changelog read/write steps
  to workflow (before and after running pipeline stages)
- `.claude/skills/dataset-analyzer/SKILL.md` — added changelog read/write steps
  to the cross-run memory section

---
