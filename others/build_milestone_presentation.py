"""Build Iteration 1 Milestone Presentation.pptx."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Iteration 1 Milestone Presentation.pptx"
NEIGHBOUR_FLOW = ROOT / "Flowchart of Neighborhood Search.png"
PRIORITY_FLOW = ROOT / "Priority Based Optimiser Flowchart.png"
PRIORITY_SELECT_FLOW = ROOT / "Priority Based Selection Flowchart.png"

# Northrop-style black and white palette
BG = RGBColor(0xFF, 0xFF, 0xFF)
NAVY = RGBColor(0x00, 0x00, 0x00)       # titles / primary
ACCENT = RGBColor(0x00, 0x00, 0x00)     # bars / emphasis
PALE = RGBColor(0xF0, 0xF0, 0xF0)       # light gray panels
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x55, 0x55, 0x55)      # secondary text
BODY = RGBColor(0x1A, 0x1A, 0x1A)
GREEN = RGBColor(0x00, 0x00, 0x00)      # positive metrics stay B&W
AMBER = RGBColor(0x4A, 0x4A, 0x4A)      # mid emphasis
RED = RGBColor(0x2B, 0x2B, 0x2B)        # strong bars / warnings
CARD = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xB0, 0xB0, 0xB0)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def set_run(run, *, size=18, bold=False, color=BODY, name="Calibri"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = name


def add_bg(slide):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = BG
    shape.line.fill.background()


def add_accent_bar(slide, top=Inches(0.0), height=Inches(0.12)):
    bar = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, top, SLIDE_W, height
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()


def add_textbox(slide, left, top, width, height, text, *, size=18, bold=False,
                color=BODY, align=PP_ALIGN.LEFT, font="Calibri"):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run(run, size=size, bold=bold, color=color, name=font)
    return box


def add_bullets(slide, left, top, width, height, items, *, size=16, color=BODY):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = item
        set_run(run, size=size, color=color)
    return box


def add_card(slide, left, top, width, height, fill=CARD, line=LINE):
    card = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = fill
    card.line.color.rgb = line
    card.line.width = Pt(1)
    return card


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def metric_card(slide, left, top, width, height, label, value, fill=PALE, value_color=GREEN):
    add_card(slide, left, top, width, height, fill=fill, line=ACCENT)
    add_textbox(
        slide, left + Inches(0.18), top + Inches(0.18), width - Inches(0.3), Inches(0.35),
        label, size=12, bold=True, color=ACCENT
    )
    add_textbox(
        slide, left + Inches(0.18), top + Inches(0.55), width - Inches(0.3), Inches(0.7),
        value, size=26, bold=True, color=value_color
    )


def timeline_node(slide, left, top, width, height, title, subtitle, highlight=False):
    fill = PALE if highlight else WHITE
    line = ACCENT if highlight else LINE
    add_card(slide, left, top, width, height, fill=fill, line=line)
    add_textbox(
        slide, left + Inches(0.1), top + Inches(0.18), width - Inches(0.2), Inches(0.55),
        title, size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER
    )
    add_textbox(
        slide, left + Inches(0.1), top + Inches(0.75), width - Inches(0.2), Inches(0.55),
        subtitle, size=11, color=MUTED, align=PP_ALIGN.CENTER
    )


def section_label(slide, text):
    add_textbox(
        slide, Inches(0.55), Inches(0.28), Inches(12), Inches(0.3),
        text, size=12, bold=True, color=ACCENT
    )


def title(slide, text, top=Inches(0.55)):
    add_textbox(
        slide, Inches(0.55), top, Inches(12.2), Inches(0.7),
        text, size=30, bold=True, color=NAVY, font="Calibri"
    )


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # ------------------------------------------------------------------
    # 1 Opening
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    navy_panel = s.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, Inches(1.4), Inches(7.8), Inches(4.4)
    )
    navy_panel.fill.solid()
    navy_panel.fill.fore_color.rgb = NAVY
    navy_panel.line.fill.background()
    add_textbox(
        s, Inches(0.7), Inches(1.7), Inches(6.8), Inches(0.35),
        "ITERATION 1 · MILESTONE REVIEW", size=13, bold=True, color=PALE
    )
    add_textbox(
        s, Inches(0.7), Inches(2.2), Inches(6.8), Inches(1.6),
        "From exhaustive search to practical priority selection",
        size=32, bold=True, color=WHITE
    )
    add_textbox(
        s, Inches(0.7), Inches(4.0), Inches(6.8), Inches(1.0),
        "Fleet maintenance scheduling for Northrop Grumman: "
        "four optimiser implementations, measured schedule quality, "
        "and a practical path to scale.",
        size=16, color=PALE
    )
    metric_card(s, Inches(8.3), Inches(1.8), Inches(4.3), Inches(1.5),
                "MINIMUM AVAILABILITY", "15 → 18 aircraft")
    metric_card(s, Inches(8.3), Inches(3.55), Inches(4.3), Inches(1.5),
                "AVAILABILITY STD DEV", "1.96 → 1.44")
    add_textbox(
        s, Inches(8.3), Inches(5.3), Inches(4.3), Inches(0.5),
        "Priority selection made the optimiser practical",
        size=14, bold=True, color=NAVY
    )
    add_notes(
        s,
        "Takeaway: Iteration 1 evolved from a working idea into a practical optimiser.\n\n"
        "Script: Open with the outcome — priority-based selection raised worst-case "
        "fleet availability from 15 to 18 aircraft and reduced variation from 1.96 to 1.44. "
        "Then preview the four milestones that got us here.\n\n"
        "Transition: Start with what 'better' means for this problem."
    )

    # ------------------------------------------------------------------
    # 2 Measures
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "PROBLEM AND SUCCESS MEASURES")
    title(s, "A better schedule protects the worst day first")
    add_textbox(
        s, Inches(0.55), Inches(1.35), Inches(12.2), Inches(0.5),
        "Objective: keep as many aircraft available as possible, especially on the hardest days.",
        size=16, color=MUTED
    )
    cards = [
        ("1. Minimum availability", "Maximise the lowest number of available aircraft across the horizon."),
        ("2. Standard deviation", "If the minimum is tied, reduce day-to-day variation."),
        ("3. Average availability", "If still tied, raise the average."),
        ("4. Runtime", "The method must finish in practical time as the fleet grows."),
    ]
    for i, (h, body) in enumerate(cards):
        left = Inches(0.55 + (i % 2) * 6.2)
        top = Inches(2.05 + (i // 2) * 2.15)
        add_card(s, left, top, Inches(5.9), Inches(1.9), fill=WHITE, line=LINE)
        add_textbox(s, left + Inches(0.25), top + Inches(0.25), Inches(5.4), Inches(0.4),
                    h, size=18, bold=True, color=NAVY)
        add_textbox(s, left + Inches(0.25), top + Inches(0.8), Inches(5.4), Inches(0.85),
                    body, size=15, color=BODY)
    add_notes(
        s,
        "Takeaway: Quality is lexicographic — worst-case availability first.\n\n"
        "Script: Explain that a schedule with a higher floor is preferred even if average "
        "availability is similar. Runtime became a hard constraint once we moved from a "
        "simple dataset to a heavy multi-year forecast.\n\n"
        "Transition: Show the four implementation milestones."
    )

    # ------------------------------------------------------------------
    # 3 Roadmap
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "ALGORITHM EVOLUTION")
    title(s, "Four implementations, each responding to a scaling problem")
    nodes = [
        ("Milestone 1", "Simple fleet\nbaseline optimiser", False),
        ("Milestone 2", "Full neighbourhood\nsearch", False),
        ("Milestone 3", "200 random\nsamples", False),
        ("Milestone 4", "Priority-based\nselection", True),
    ]
    for i, (h, sub, hi) in enumerate(nodes):
        left = Inches(0.55 + i * 3.15)
        timeline_node(s, left, Inches(2.1), Inches(2.85), Inches(2.0), h, sub, highlight=hi)
        if i < 3:
            arrow = s.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                left + Inches(2.9), Inches(2.85), Inches(0.22), Inches(0.35)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()
    add_card(s, Inches(0.55), Inches(4.5), Inches(12.2), Inches(2.2), fill=WHITE, line=LINE)
    add_bullets(
        s, Inches(0.85), Inches(4.7), Inches(11.6), Inches(1.8),
        [
            "Simple dataset: proved the objective and feasibility checks (80 events).",
            "Heavy dataset: 24 aircraft, 278 maintenance events over a multi-year horizon.",
            "Search strategy evolved from exhaustive → sampled → priority-targeted.",
            "Final method is deterministic, rule-aware, and substantially faster.",
        ],
        size=15,
    )
    add_notes(
        s,
        "Takeaway: Each milestone solved the previous bottleneck.\n\n"
        "Script: Walk left to right. Milestone 1 is reported separately because the "
        "dataset was simpler. Milestones 2–4 share the heavy forecast.\n\n"
        "Transition: Start with the simple-dataset proof."
    )

    # ------------------------------------------------------------------
    # 4 Milestone 1
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MILESTONE 1 · SIMPLE DATASET")
    title(s, "The simple dataset proved the optimisation objective")
    add_card(s, Inches(0.55), Inches(1.5), Inches(7.4), Inches(5.2), fill=WHITE, line=LINE)
    add_bullets(
        s, Inches(0.85), Inches(1.75), Inches(6.9), Inches(4.7),
        [
            "Input: Simple Random Fleet Plans (80 maintenance events).",
            "Shift event start times within feasible windows.",
            "Reject overlapping maintenance on the same aircraft.",
            "Score schedules lexicographically: min → −std → average.",
            "Variable neighbourhood search with coarse-to-fine shifts.",
            "Established the baseline optimiser design before scaling.",
        ],
        size=16,
    )
    metric_card(s, Inches(8.3), Inches(1.5), Inches(4.4), Inches(1.5),
                "DATASET SCALE", "80 events", fill=PALE, value_color=NAVY)
    metric_card(s, Inches(8.3), Inches(3.25), Inches(4.4), Inches(1.5),
                "PURPOSE", "Proof of concept", fill=PALE, value_color=NAVY)
    metric_card(s, Inches(8.3), Inches(5.0), Inches(4.4), Inches(1.5),
                "COMPARISON NOTE", "Separate from heavy", fill=PALE, value_color=AMBER)
    add_notes(
        s,
        "Takeaway: Milestone 1 validated the objective, not industrial scale.\n\n"
        "Script: Do not compare this runtime directly with later heavy-dataset runs. "
        "It proved we could improve availability under hard feasibility constraints.\n\n"
        "Transition: Moving to the heavy forecast exposed scalability limits."
    )

    # ------------------------------------------------------------------
    # 5 Milestone 2
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MILESTONE 2 · FULL NEIGHBOURHOOD")
    title(s, "Full neighbourhood search improved quality—but did not scale")
    add_card(s, Inches(0.55), Inches(1.45), Inches(6.3), Inches(5.3), fill=WHITE, line=LINE)
    add_bullets(
        s, Inches(0.85), Inches(1.7), Inches(5.8), Inches(4.8),
        [
            "Heavy forecast: 24 aircraft, 278 events.",
            "For every aircraft and event, try each shift (±28, ±14, ±7, ±3).",
            "Deep-copy and fully evaluate every feasible neighbour.",
            "Candidate count grows with fleet size × events × shifts.",
            "Quality gains were real, but evaluation cost became impractical.",
        ],
        size=15,
    )
    if NEIGHBOUR_FLOW.exists():
        s.shapes.add_picture(
            str(NEIGHBOUR_FLOW), Inches(7.1), Inches(1.45), width=Inches(5.7)
        )
    else:
        add_card(s, Inches(7.1), Inches(1.45), Inches(5.7), Inches(5.3), fill=PALE, line=ACCENT)
        add_textbox(
            s, Inches(7.3), Inches(3.5), Inches(5.3), Inches(1.0),
            "Neighbourhood search flowchart", size=16, color=NAVY, align=PP_ALIGN.CENTER
        )
    add_notes(
        s,
        "Takeaway: Exhaustive neighbour evaluation does not scale with the heavy dataset.\n\n"
        "Script: Emphasise that every feasible move was considered. That is thorough, "
        "but too expensive once the forecast grew.\n\n"
        "Transition: Sampling reduced work next."
    )

    # ------------------------------------------------------------------
    # 6 Milestone 3
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MILESTONE 3 · 200 RANDOM SAMPLES")
    title(s, "Sampling 200 neighbours reduced work but added uncertainty")
    add_card(s, Inches(0.55), Inches(1.5), Inches(12.2), Inches(5.2), fill=WHITE, line=LINE)
    left_items = [
        "Same heavy dataset and shift sets as full neighbourhood search.",
        "If more than 200 neighbours exist, randomly sample 200.",
        "Cut evaluation cost dramatically versus the full set.",
        "Trade-off: non-deterministic candidate selection.",
        "Same seed later enables reproducible benchmarking.",
    ]
    right_items = [
        "Faster than exhaustive search.",
        "May miss the best improving move in a neighbourhood.",
        "Still scores complete candidate schedules each time.",
        "Still deep-copies and revalidates broadly.",
        "Motivated a smarter, deterministic selection policy.",
    ]
    add_textbox(s, Inches(0.9), Inches(1.8), Inches(5.5), Inches(0.4),
                "What changed", size=18, bold=True, color=NAVY)
    add_bullets(s, Inches(0.9), Inches(2.35), Inches(5.5), Inches(3.8), left_items, size=15)
    add_textbox(s, Inches(7.0), Inches(1.8), Inches(5.3), Inches(0.4),
                "Limits remaining", size=18, bold=True, color=NAVY)
    add_bullets(s, Inches(7.0), Inches(2.35), Inches(5.3), Inches(3.8), right_items, size=15)
    add_notes(
        s,
        "Takeaway: Random sampling buys speed, but leaves quality to chance.\n\n"
        "Script: Explain the 200-sample cap as a practical compromise that still "
        "evaluated full schedules. It was an intermediate step, not the end state.\n\n"
        "Transition: Priority selection targets the worst availability regions."
    )

    # ------------------------------------------------------------------
    # 7 Milestone 4
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MILESTONE 4 · PRIORITY-BASED SELECTION")
    title(s, "Priority selection searches the worst availability regions first")
    add_card(s, Inches(0.55), Inches(1.4), Inches(6.2), Inches(5.35), fill=WHITE, line=LINE)
    add_bullets(
        s, Inches(0.85), Inches(1.65), Inches(5.7), Inches(4.9),
        [
            "Rank events by the worst availability during their interval.",
            "Search the worst priority level first; expand only if needed.",
            "Move one check, then rebuild later events using A/B/C/D rules.",
            "Update availability by replacing only the affected aircraft.",
            "Deterministic, rule-compliant, and substantially faster.",
            "Measured result: min 15→18, std 1.96→1.44.",
            "Measured runtime: 15.4 seconds (median of 3 runs).",
        ],
        size=14,
    )
    if PRIORITY_FLOW.exists():
        s.shapes.add_picture(
            str(PRIORITY_FLOW), Inches(7.0), Inches(1.4), width=Inches(5.8)
        )
    else:
        add_card(s, Inches(7.0), Inches(1.4), Inches(5.8), Inches(5.35), fill=PALE, line=ACCENT)
        add_textbox(
            s, Inches(7.2), Inches(3.5), Inches(5.4), Inches(1.0),
            "Priority optimiser flowchart", size=16, color=NAVY, align=PP_ALIGN.CENTER
        )
    add_notes(
        s,
        "Takeaway: Target the bottleneck days instead of sampling blindly.\n\n"
        "Script: Highlight rule-aware rebuild and incremental scoring — these keep "
        "candidates valid and cheap to evaluate. Quote the measured 15.4-second median "
        "runtime on the heavy dataset. This is the practical end state of Iteration 1.\n\n"
        "Transition: Zoom into how priority levels actually work with a real example."
    )

    # ------------------------------------------------------------------
    # 8 Priority deep dive (exclusive buckets)
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MILESTONE 4 · HOW PRIORITY LEVELS WORK")
    title(s, "Each event gets one priority — the worst day it covers")
    add_textbox(
        s, Inches(0.55), Inches(1.25), Inches(12.2), Inches(0.4),
        "From the heavy starting schedule: global min availability = 15 · 278 events · 24 aircraft",
        size=14, color=MUTED
    )

    # Three explanation cards
    panels = [
        (
            "1. Score every event",
            [
                "Look at fleet availability on every day that event is in the hangar.",
                "Priority = the minimum of those days.",
                "Example: hangar days with avail [18, 15, 16] → priority 15.",
            ],
        ),
        (
            "2. Split into exclusive buckets",
            [
                "Level 15 → 20 events (touch a day-15 trough).",
                "Level 16 → 10 events · 17 → 9 · then more at milder levels.",
                "Same 278 events once — not nested, not cumulative.",
            ],
        ),
        (
            "3. Search worst first",
            [
                "Try only level-15 events × shifts (e.g. 20 × 2 = 40).",
                "If any move improves the score, stop and pick the best.",
                "Only then expand to 16, 17… if level 15 finds nothing.",
            ],
        ),
    ]
    for i, (heading, items) in enumerate(panels):
        left = Inches(0.55 + i * 4.15)
        add_card(s, left, Inches(1.75), Inches(4.0), Inches(3.35), fill=WHITE, line=LINE)
        add_textbox(
            s, left + Inches(0.2), Inches(1.9), Inches(3.6), Inches(0.4),
            heading, size=15, bold=True, color=NAVY
        )
        add_bullets(
            s, left + Inches(0.2), Inches(2.4), Inches(3.6), Inches(2.5),
            items, size=12
        )

    # Clarifying callout
    add_card(s, Inches(0.55), Inches(5.25), Inches(12.2), Inches(1.55), fill=PALE, line=ACCENT)
    add_textbox(
        s, Inches(0.8), Inches(5.4), Inches(11.7), Inches(0.35),
        "Common confusion", size=14, bold=True, color=NAVY
    )
    add_textbox(
        s, Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8),
        "The 20 level-15 events each have a min of 15 in their hangar window — they are not "
        "20 separate causes of the trough. After a move, availability is recomputed and events "
        "are re-bucketed. Fixing level 15 does not “add those 20 into level 16” in the same pass.",
        size=14, color=BODY
    )
    add_notes(
        s,
        "Takeaway: Priority buckets are an exclusive partition by each event's worst day.\n\n"
        "Script: Walk the three panels. Stress that level 15's 20 events and level 16's 10 "
        "are different events — not stages of a repair ladder. On day-15 troughs, only nine "
        "aircraft are actually in maintenance (24 − 15); the 20 events are those whose "
        "windows overlap some trough day. Then explain search: 40 candidates at level 15, "
        "not 200 random samples of the full neighbourhood.\n\n"
        "Transition: Show the measured quality and runtime comparison."
    )

    # ------------------------------------------------------------------
    # 9 Comparison
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "MEASURED COMPARISON · HEAVY DATASET")
    title(s, "Better worst-case availability with less variation")
    metric_card(s, Inches(0.55), Inches(1.5), Inches(4.0), Inches(1.7),
                "MINIMUM AVAILABILITY", "15 → 18")
    metric_card(s, Inches(4.75), Inches(1.5), Inches(4.0), Inches(1.7),
                "STANDARD DEVIATION", "1.96 → 1.44")
    metric_card(s, Inches(8.95), Inches(1.5), Inches(3.8), Inches(1.7),
                "AVERAGE AVAILABILITY", "21.76 → 21.75", value_color=NAVY)

    # Measured runtime bars (heavy dataset, wall-clock)
    add_card(s, Inches(0.55), Inches(3.5), Inches(12.2), Inches(3.2), fill=WHITE, line=LINE)
    add_textbox(
        s, Inches(0.85), Inches(3.7), Inches(11.6), Inches(0.4),
        "Measured runtime on the heavy dataset (24 aircraft, 278 events)",
        size=16, bold=True, color=NAVY
    )
    # Full = 919.8s, Random = 451.1s, Priority median = 15.4s
    runtime_rows = [
        ("Full neighbourhood", 919.8 / 919.8, RED, "920 s  (~15.3 min)"),
        ("200 random samples", 451.1 / 919.8, AMBER, "451 s  (~7.5 min)"),
        ("Priority selection", max(15.4 / 919.8, 0.04), GREEN, "15.4 s  (median of 3)"),
    ]
    for i, (label, frac, color, note) in enumerate(runtime_rows):
        top = Inches(4.25 + i * 0.7)
        add_textbox(s, Inches(0.85), top, Inches(3.0), Inches(0.4), label, size=14, color=BODY)
        bar = s.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(4.0), top + Inches(0.05), Inches(6.5 * frac), Inches(0.35)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = color
        bar.line.fill.background()
        add_textbox(s, Inches(10.6), top, Inches(2.0), Inches(0.4), note, size=12, bold=True, color=BODY)
    add_notes(
        s,
        "Takeaway: Priority selection delivered the quality win about 60× faster than full search.\n\n"
        "Script: Quote measured runtimes — full neighbourhood 920 seconds, random-200 451 seconds, "
        "priority 15.4 seconds median. Quality: minimum availability 15 to 18, std 1.96 to 1.44. "
        "Average barely changed because the objective prioritises the floor.\n\n"
        "Transition: Close with lessons and next steps."
    )

    # ------------------------------------------------------------------
    # 9 Lessons
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "LESSONS AND NEXT STEPS")
    title(s, "Iteration 1 converted a working idea into a practical optimiser")
    lessons = [
        ("Scale changed the design", "Methods that worked on 80 events were too slow on 278."),
        ("Target the bottleneck", "Searching worst-availability regions preserved quality with less work."),
        ("Rules must travel with moves", "Downstream A/B/C/D rebuild keeps candidates operationally valid."),
        ("Next steps", "Formal timed benchmarks, sensitivity tests, and broader fleet validation."),
    ]
    for i, (h, body) in enumerate(lessons):
        left = Inches(0.55 + (i % 2) * 6.2)
        top = Inches(1.5 + (i // 2) * 2.5)
        add_card(s, left, top, Inches(5.9), Inches(2.2), fill=WHITE, line=LINE)
        add_textbox(s, left + Inches(0.25), top + Inches(0.3), Inches(5.4), Inches(0.45),
                    h, size=18, bold=True, color=NAVY)
        add_textbox(s, left + Inches(0.25), top + Inches(0.9), Inches(5.4), Inches(1.0),
                    body, size=15, color=BODY)
    add_notes(
        s,
        "Takeaway: Iteration 1 ends with a practical, rule-aware priority optimiser.\n\n"
        "Script: Recap the journey in one sentence, restate the measured quality win, "
        "and invite questions on next validation work.\n\n"
        "Transition: Appendix holds methodology, detailed metrics, and full flowcharts."
    )

    # ------------------------------------------------------------------
    # 10 Appendix methodology
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX A")
    title(s, "Benchmark methodology and evidence sources")
    add_bullets(
        s, Inches(0.7), Inches(1.5), Inches(12), Inches(5.3),
        [
            "Simple milestone reported separately on Simple Random Fleet Plans.xlsx (80 events).",
            "Heavy milestones use heavy_maintenance_forecast.xlsx (24 aircraft, 278 events).",
            "Quality metrics for priority selection taken from optimised_heavy_maintenance_output.xlsx.",
            "Original: min 15, std 1.956849, avg 21.760979.",
            "Optimised: min 18, std 1.443721, avg 21.745685.",
            "Heavy-dataset runtimes (this machine): full 920 s; random-200 (seed 42) 451 s; priority median 15.4 s (3 runs).",
            "Priority was timed three times; full and random-200 were timed once each for the comparison slide.",
        ],
        size=16,
    )

    # ------------------------------------------------------------------
    # 11 Detailed metrics table
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX B")
    title(s, "Detailed schedule quality metrics")
    rows, cols = 3, 4
    table = s.shapes.add_table(rows, cols, Inches(0.8), Inches(1.8), Inches(11.7), Inches(2.6)).table
    headers = ["Schedule", "Min availability", "Std deviation", "Average availability"]
    data = [
        headers,
        ["Original (heavy)", "15", "1.956849", "21.760979"],
        ["Priority optimised", "18", "1.443721", "21.745685"],
    ]
    for r, row in enumerate(data):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    set_run(run, size=14, bold=(r == 0), color=NAVY if r == 0 else BODY)
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = PALE
    add_textbox(
        s, Inches(0.8), Inches(4.8), Inches(11.7), Inches(1.5),
        "Lexicographic score improved primarily on minimum availability and standard deviation. "
        "Average availability is nearly unchanged, which is expected when the objective prioritises "
        "the worst day over the mean.",
        size=15, color=MUTED
    )

    # ------------------------------------------------------------------
    # 12 Neighbour flowchart full
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX C")
    title(s, "Full neighbourhood-search flowchart")
    if NEIGHBOUR_FLOW.exists():
        s.shapes.add_picture(str(NEIGHBOUR_FLOW), Inches(1.2), Inches(1.5), width=Inches(10.9))

    # ------------------------------------------------------------------
    # 14 Priority selection explainer flowchart
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX D")
    title(s, "Priority buckets and worst-first search")
    if PRIORITY_SELECT_FLOW.exists():
        s.shapes.add_picture(
            str(PRIORITY_SELECT_FLOW), Inches(0.7), Inches(1.35), width=Inches(11.9)
        )

    # ------------------------------------------------------------------
    # 15 Priority optimiser flowchart full
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX E")
    title(s, "Full priority-selection flowchart")
    if PRIORITY_FLOW.exists():
        s.shapes.add_picture(str(PRIORITY_FLOW), Inches(1.2), Inches(1.5), width=Inches(10.9))

    # ------------------------------------------------------------------
    # 16 Rules and caveats
    # ------------------------------------------------------------------
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "APPENDIX F")
    title(s, "Maintenance rules, feasibility, and caveats")
    add_bullets(
        s, Inches(0.7), Inches(1.5), Inches(12), Inches(5.3),
        [
            "Check sequence: A, B, A, C, A, B, A, D with larger checks resetting smaller ones.",
            "Hard constraints: start windows, no overlaps, stay inside the supplied horizon.",
            "Priority search rebuilds only the affected aircraft after a candidate move.",
            "Do not compare simple-dataset runtime directly with heavy-dataset runtime.",
            "Quality and runtime figures above are measured wall-clock results on the heavy dataset.",
            "Automated unit tests cover fixed-horizon scoring, rebuild rules, and deterministic priority order.",
        ],
        size=16,
    )

    prs.save(OUTPUT)
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    build()
