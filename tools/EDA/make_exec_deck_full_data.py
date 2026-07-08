"""
Non-technical executive deck for the full Capital One direct-mail prospects
dataset (data/Sample_Data.csv, all 100,000 rows — no subsampling). Numbers are
taken from the finalized report, not recomputed. Charts are reused from
outputs/EDA/figures/.

Output: outputs/EDA/Full_Data_executive_summary.pptx
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
OUT_DIR = ROOT / "outputs" / "EDA"
FIG_DIR = OUT_DIR / "figures"
DECK = OUT_DIR / "Full_Data_executive_summary.pptx"

NAVY = RGBColor(0x1F, 0x2D, 0x50)
BLUE = RGBColor(0x4C, 0x72, 0xB0)
GREEN = RGBColor(0x2E, 0x8B, 0x57)
AMBER = RGBColor(0xC8, 0x8A, 0x00)
RED = RGBColor(0xB0, 0x3A, 0x2E)
GREY = RGBColor(0x55, 0x55, 0x55)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def add_slide():
    return prs.slides.add_slide(BLANK)


def textbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def set_bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def title_line(tf, text, size=32, color=NAVY, bold=True):
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return p


def bullet(tf, text, size=20, color=GREY, bold=False, bullet_char="•  "):
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = f"{bullet_char}{text}"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    p.space_after = Pt(10)
    return p


def caption(slide, text, top):
    tf = textbox(slide, Inches(0.7), top, Inches(12), Inches(0.6))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(16)
    r.font.italic = True
    r.font.color.rgb = GREY


# Slide 1 — Title
s = add_slide()
set_bg(s, NAVY)
tf = textbox(s, Inches(1), Inches(2.3), Inches(11.3), Inches(2.2))
p = tf.paragraphs[0]
r = p.add_run()
r.text = "Direct-Mail Prospect Data — Readiness Review"
r.font.size = Pt(40)
r.font.bold = True
r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
p2 = tf.add_paragraph()
r = p2.add_run()
r.text = "What's in the data, whether it's clean, and what to do before modeling"
r.font.size = Pt(20)
r.font.color.rgb = RGBColor(0xC9, 0xD4, 0xE8)
p3 = tf.add_paragraph()
r = p3.add_run()
r.text = "100,000 mailed prospects  •  Prepared for executive review  •  July 2026"
r.font.size = Pt(15)
r.font.color.rgb = RGBColor(0x9A, 0xA8, 0xC4)

# Slide 2 — What this data is
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.5), Inches(12), Inches(1))
title_line(tf, "What this data is")
tf = textbox(s, Inches(0.9), Inches(1.8), Inches(11.5), Inches(5))
bullet(tf, "100,000 prospects mailed a direct-mail credit card offer, one row per prospect.", 22)
bullet(tf, "Each row carries the prospect's credit-history snapshot from three credit bureaus, plus income and credit score.", 22)
bullet(tf, "There's no ready-made \"did they respond?\" column, so we built one: responded = whether the prospect submitted an application.", 22)
bullet(tf, "Only 0.41% of prospects responded, and just 0.084% went on to actually open a card — this is a needle-in-a-haystack problem by design.", 22, RED, bold=True)

# Slide 3 — Data health
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.5), Inches(12), Inches(1))
title_line(tf, "Data health at a glance")
tf = textbox(s, Inches(0.9), Inches(1.7), Inches(11.7), Inches(5))
bullet(tf, "No duplicate records, no broken or mixed-up data types — the file is structurally sound.", 22, GREEN, bold=True)
bullet(tf, "Credit scores and other fields fall within sensible ranges — no obvious data-entry errors.", 22, GREEN, bold=True)
bullet(tf, "The three mailing waves (Jan, Feb, Mar) are similar in size and response rate — no red flags there.", 22, GREEN, bold=True)
bullet(tf, "Caution: many credit-history fields are \"missing by design\" (coded values meaning \"no trade on file\") rather than truly unknown — we've already translated these correctly.", 22, AMBER)
bullet(tf, "Caution: the three credit bureaus report the same information for most fields — effectively triple-counting the same signal unless simplified.", 22, AMBER)
tf2 = textbox(s, Inches(0.9), Inches(6.5), Inches(11.7), Inches(0.8))
p = tf2.paragraphs[0]
r = p.add_run()
r.text = "Bottom line: the data is trustworthy, but needs simplification before modeling."
r.font.size = Pt(20)
r.font.bold = True
r.font.color.rgb = NAVY

# Slide 4 — What the data looks like
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.4), Inches(12), Inches(1))
title_line(tf, "What the data looks like")
if (FIG_DIR / "histograms.png").exists():
    s.shapes.add_picture(str(FIG_DIR / "histograms.png"), Inches(1.3), Inches(1.3), height=Inches(5.0))
caption(s, "Credit scores cluster in a normal range; income, balances, and credit activity have a long tail of high-usage prospects.", Inches(6.5))

# Slide 5 — Response is rare
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.4), Inches(12), Inches(1))
title_line(tf, "Response is rare — and that shapes everything downstream")
if (FIG_DIR / "target_balance.png").exists():
    s.shapes.add_picture(str(FIG_DIR / "target_balance.png"), Inches(3.6), Inches(1.4), height=Inches(4.9))
caption(s, "Out of 100,000 prospects mailed, 410 responded and only 84 opened a card.", Inches(6.5))

# Slide 6 — Key relationship
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.4), Inches(12), Inches(1))
title_line(tf, "Key relationship in the data")
if (FIG_DIR / "corr_heatmap.png").exists():
    s.shapes.add_picture(str(FIG_DIR / "corr_heatmap.png"), Inches(3.4), Inches(1.2), height=Inches(5.2))
tf = textbox(s, Inches(0.9), Inches(6.6), Inches(11.7), Inches(0.7))
p = tf.paragraphs[0]
r = p.add_run()
r.text = "The three credit bureaus (Equifax, Experian, TransUnion) largely say the same thing about each prospect — one bureau's view is usually enough."
r.font.size = Pt(17)
r.font.color.rgb = GREY
p.alignment = PP_ALIGN.CENTER

# Slide 7 — Issues to address
s = add_slide()
tf = textbox(s, Inches(0.7), Inches(0.5), Inches(12), Inches(1))
title_line(tf, "What to address before modeling")
tf = textbox(s, Inches(0.9), Inches(1.8), Inches(11.7), Inches(5))
bullet(tf, "Simplify the three-bureau repetition into one clean signal per attribute.", 22)
bullet(tf, "Correctly separate \"no credit trade on file\" from a true missing value in every credit-history field (already handled in this analysis).", 22)
bullet(tf, "Plan the model around the extreme rarity of response — accuracy alone would be misleading; use methods built for rare-event prediction.", 22, AMBER, bold=True)
bullet(tf, "Exclude fields that only exist because someone already responded (they would leak the answer into the model).", 22)

# Slide 8 — Next steps
s = add_slide()
set_bg(s, NAVY)
tf = textbox(s, Inches(0.9), Inches(0.7), Inches(11.5), Inches(1))
p = tf.paragraphs[0]
r = p.add_run()
r.text = "Recommended next steps"
r.font.size = Pt(34)
r.font.bold = True
r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
tf = textbox(s, Inches(1.1), Inches(2.1), Inches(11), Inches(4.5))
for txt in [
    "Simplify and clean the credit-bureau fields as outlined, then proceed to a response/booking propensity model.",
    "Expect a rare-event model — plan evaluation and targeting decisions around lift/ranking, not raw accuracy.",
    "Loop in the campaign team on whether the small wave-to-wave response differences are worth investigating.",
]:
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = "→  " + txt
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor(0xE8, 0xEE, 0xF8)
    p.space_after = Pt(16)

prs.save(DECK)
print(f"Executive deck written to: {DECK}")
