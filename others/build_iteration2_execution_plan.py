"""Build Iteration 2 Execution Plan.pptx (black/white, 16:9).

WARNING: Do NOT run this against the live deck to overwrite it. The presentation
may contain manual edits not captured here. Edit existing .pptx files in place
(PowerPoint MCP/COM) instead. Only write a *new* filename if explicitly asked.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "Iteration 2 Execution Plan.pptx"

# Black-and-white theme — black text/accents, white and light-gray fills only
BG = RGBColor(0xFF, 0xFF, 0xFF)
NAVY = RGBColor(0x00, 0x00, 0x00)  # primary titles
ACCENT = RGBColor(0x00, 0x00, 0x00)  # bars / emphasis
PALE = RGBColor(0xF0, 0xF0, 0xF0)  # light gray panels
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x55, 0x55, 0x55)  # secondary text
BODY = RGBColor(0x1A, 0x1A, 0x1A)
LINE = RGBColor(0xB0, 0xB0, 0xB0)
CARD = RGBColor(0xFF, 0xFF, 0xFF)
PANEL = RGBColor(0xF5, 0xF5, 0xF5)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def set_run(run, *, size=20, bold=False, color=BODY, name="Calibri"):
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


def add_textbox(slide, left, top, width, height, text, *, size=20, bold=False,
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


def add_bullets(slide, left, top, width, height, items, *, size=18, color=BODY,
                space_after=14):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = "• " + item
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


def metric_card(slide, left, top, width, height, label, value, fill=PALE,
                value_color=NAVY, value_size=32):
    add_card(slide, left, top, width, height, fill=fill, line=ACCENT)
    add_textbox(
        slide, left + Inches(0.22), top + Inches(0.22), width - Inches(0.4), Inches(0.4),
        label, size=17, bold=True, color=ACCENT
    )
    add_textbox(
        slide, left + Inches(0.22), top + Inches(0.68), width - Inches(0.4), Inches(0.95),
        value, size=value_size, bold=True, color=value_color
    )


def section_label(slide, text):
    add_textbox(
        slide, Inches(0.5), Inches(0.18), Inches(12.2), Inches(0.35),
        text, size=17, bold=True, color=ACCENT
    )


def title(slide, text, top=Inches(0.45)):
    add_textbox(
        slide, Inches(0.5), top, Inches(12.3), Inches(0.7),
        text, size=40, bold=True, color=NAVY, font="Calibri"
    )


def timeline_node(slide, left, top, width, height, step, label, highlight=False):
    fill = PALE if highlight else CARD
    line = ACCENT if highlight else LINE
    add_card(slide, left, top, width, height, fill=fill, line=line)
    add_textbox(
        slide, left + Inches(0.08), top + Inches(0.2), width - Inches(0.16), Inches(0.4),
        step, size=15, bold=True, color=ACCENT, align=PP_ALIGN.CENTER
    )
    add_textbox(
        slide, left + Inches(0.08), top + Inches(0.65), width - Inches(0.16), Inches(0.85),
        label, size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER
    )


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # 1 Title
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    panel = s.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, Inches(1.15), Inches(8.4), Inches(4.55)
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = PANEL
    panel.line.fill.background()
    accent_edge = s.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, Inches(1.15), Inches(0.12), Inches(4.55)
    )
    accent_edge.fill.solid()
    accent_edge.fill.fore_color.rgb = ACCENT
    accent_edge.line.fill.background()
    add_textbox(
        s, Inches(0.7), Inches(1.55), Inches(7.3), Inches(0.45),
        "SEMESTER 2 · EXECUTION PLAN", size=16, bold=True, color=ACCENT
    )
    add_textbox(
        s, Inches(0.7), Inches(2.2), Inches(7.3), Inches(1.6),
        "Iteration 2 Execution Plan", size=48, bold=True, color=NAVY
    )
    add_textbox(
        s, Inches(0.7), Inches(4.15), Inches(7.3), Inches(1.0),
        "Priority search → validated research workstreams", size=22, color=MUTED
    )
    add_textbox(
        s, Inches(0.7), Inches(6.05), Inches(12), Inches(0.45),
        "UQ × Northrop Grumman  ·  Fleet maintenance optimisation", size=19, color=MUTED
    )
    metric_card(s, Inches(8.55), Inches(1.45), Inches(4.25), Inches(1.85),
                "BASELINE", "Priority VNS")
    metric_card(s, Inches(8.55), Inches(3.55), Inches(4.25), Inches(1.85),
                "FOCUS", "SA · Constraints · Knobs · Stagger", value_size=24)
    add_notes(
        s,
        "Welcome. This is the Iteration 2 execution plan. Iteration 1 gave us a working "
        "priority-based VNS baseline with measured availability gains. Semester 2 turns that "
        "baseline into validated research workstreams—especially whether simulated annealing "
        "can sit on top of priority search, plus constraints, hyperparameters, and starting-point "
        "effects. Takeaway: we know what works today, what is still hill-climbing, and what we "
        "will test next."
    )

    # 2 Recap
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "ITERATION 1 RECAP")
    title(s, "Priority VNS delivered a practical baseline")
    metric_card(s, Inches(0.5), Inches(1.3), Inches(5.95), Inches(1.55),
                "MINIMUM AVAILABILITY", "15 → 18 aircraft")
    metric_card(s, Inches(6.75), Inches(1.3), Inches(5.95), Inches(1.55),
                "RUNTIME", "~15.4 seconds")
    add_card(s, Inches(0.5), Inches(3.1), Inches(12.3), Inches(3.85), fill=CARD, line=LINE)
    add_textbox(
        s, Inches(0.8), Inches(3.35), Inches(11.7), Inches(0.5),
        "What works well — and what is still limited", size=22, bold=True, color=NAVY
    )
    add_bullets(
        s, Inches(0.8), Inches(4.0), Inches(11.7), Inches(2.7),
        [
            "We focus first on maintenance that hits the worst availability days.",
            "When we move a check, we rebuild that aircraft’s later schedule so rules stay valid.",
            "We update availability cheaply instead of recalculating from scratch.",
            "Today we only accept better moves — and we stop when nothing improves.",
        ],
        size=20, space_after=16,
    )
    add_notes(
        s,
        "Quick recap of where we landed.\n\n"
        "On the heavy dataset, we raised the worst-day availability from fifteen aircraft to eighteen, "
        "in about fifteen seconds.\n\n"
        "What works well is how we search: we focus on the worst days, rebuild an aircraft’s plan "
        "when we move a check, and update availability cheaply.\n\n"
        "What is still limited is decision-making. Today we only keep better moves, and we stop when "
        "nothing improves. That is why we are looking at simulated annealing next."
    )

    # 3 Roadmap
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "ROADMAP")
    title(s, "Four workstreams for Semester 2")
    cards = [
        ("1. SA + VNS hybrid", "Keep smart search ideas, but sometimes accept a temporary worse move."),
        ("2. Operational constraints", "Availability-max windows, surrounding moves, local std control."),
        ("3. Hyperparameters", "Test which settings actually change the results."),
        ("4. Initial stagger", "Controlled starts to separate start effect from algorithm gain."),
    ]
    for i, (h, body) in enumerate(cards):
        left = Inches(0.45 + (i % 2) * 6.4)
        top = Inches(1.25 + (i // 2) * 2.85)
        add_card(s, left, top, Inches(6.15), Inches(2.65), fill=CARD, line=LINE)
        accent = s.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE, left, top, Inches(0.12), Inches(2.65)
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = ACCENT
        accent.line.fill.background()
        add_textbox(s, left + Inches(0.4), top + Inches(0.45), Inches(5.45), Inches(0.65),
                    h, size=26, bold=True, color=NAVY)
        add_textbox(s, left + Inches(0.4), top + Inches(1.25), Inches(5.45), Inches(1.15),
                    body, size=19, color=BODY)
    add_notes(
        s,
        "Four workstreams for Semester 2.\n\n"
        "One: simulated annealing — I will explain what that means, then how it fits our design.\n\n"
        "Two: operational constraints — protect busy windows, and control how surrounding "
        "maintenance can move.\n\n"
        "Three: settings analysis — find which controls actually change the results.\n\n"
        "Four: starting stagger — check whether a good start is doing some of the work for us.\n\n"
        "I will spend the most time on annealing next."
    )

    # 4 What is simulated annealing
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "SIMULATED ANNEALING")
    title(s, "What simulated annealing is — in plain terms")
    ideas = [
        ("1 · Search", "We try changes to the maintenance schedule and score each new plan."),
        ("2 · Accept", "Better moves are always kept. Worse moves can still be kept early on, by chance."),
        ("3 · Cool down", "Over time we accept fewer worse moves, so the search settles on a strong plan."),
    ]
    for i, (h, body) in enumerate(ideas):
        left = Inches(0.5 + i * 4.2)
        add_card(s, left, Inches(1.3), Inches(3.95), Inches(2.1), fill=PALE, line=LINE)
        add_textbox(s, left + Inches(0.25), Inches(1.5), Inches(3.45), Inches(0.4),
                    h, size=20, bold=True, color=NAVY)
        add_textbox(s, left + Inches(0.25), Inches(2.05), Inches(3.45), Inches(1.1),
                    body, size=16, color=BODY)
    add_card(s, Inches(0.5), Inches(3.65), Inches(12.3), Inches(3.3), fill=CARD, line=ACCENT)
    add_textbox(s, Inches(0.8), Inches(3.9), Inches(11.7), Inches(0.45),
                "Why it helps", size=22, bold=True, color=NAVY)
    add_textbox(
        s, Inches(0.8), Inches(4.45), Inches(11.7), Inches(2.2),
        "Think of the search like walking over hills. Today’s method only walks uphill. "
        "That is fast and safe, but you can get stuck on a small hill when a better peak is nearby.\n\n"
        "Simulated annealing sometimes takes a downhill step early, so you can leave a trap and "
        "reach a better overall schedule. As the search “cools,” those downhill steps become rare, "
        "and we settle on the best plan we found.",
        size=18, color=BODY,
    )
    add_notes(
        s,
        "Before I talk about how annealing fits our code, I want to explain what it is in plain "
        "language.\n\n"
        "Simulated annealing is a search method. The idea comes from metalworking: heat metal so "
        "the atoms can move around, then cool it slowly so it settles into a strong structure. In "
        "optimisation, “heat” means we are more willing to try unusual moves. “Cooling” means we "
        "become stricter over time.\n\n"
        "There are three simple steps.\n\n"
        "First, search. We propose a change to the maintenance schedule — for example, shift a "
        "check a few days earlier or later — then score the new plan.\n\n"
        "Second, accept. If the new plan is better, we keep it. Early on we may also keep a "
        "slightly worse plan by chance, so we can escape dead ends.\n\n"
        "Third, cool down. Over time we accept fewer worse moves and settle on the best plan.\n\n"
        "Think of walking over hills: today’s method only walks uphill and can get stuck. "
        "Annealing sometimes steps downhill early to reach a better peak. Next I will show how "
        "this maps onto our optimiser."
    )

    # 5 How SA fits / integration
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "HOW IT FITS")
    title(s, "How annealing fits into our design")
    add_card(s, Inches(0.5), Inches(1.3), Inches(6.0), Inches(4.15), fill=PALE, line=ACCENT)
    add_textbox(s, Inches(0.75), Inches(1.5), Inches(5.5), Inches(0.45),
                "KEEP · How we search today", size=18, bold=True, color=ACCENT)
    add_bullets(
        s, Inches(0.75), Inches(2.1), Inches(5.5), Inches(3.1),
        [
            "Focus on the worst availability days first",
            "Rebuild the aircraft schedule after each move",
            "Update availability without recalculating everything",
            "Try larger timing shifts, then smaller ones",
            "Remember the best schedule found so far",
        ],
        size=17, space_after=14,
    )
    add_card(s, Inches(6.75), Inches(1.3), Inches(6.0), Inches(4.15), fill=CARD, line=LINE)
    add_textbox(s, Inches(7.0), Inches(1.5), Inches(5.5), Inches(0.45),
                "CHANGE · How we accept moves", size=18, bold=True, color=NAVY)
    add_bullets(
        s, Inches(7.0), Inches(2.1), Inches(5.5), Inches(3.1),
        [
            "Currently: only keep improving moves",
            "New method: annealing acceptance — better moves always; worse moves sometimes, more early, less later",
            "Drop improve-only early-exit so worse candidates can be tried",
        ],
        size=17, space_after=16,
    )
    add_card(s, Inches(0.5), Inches(5.65), Inches(12.3), Inches(1.3), fill=PANEL, line=ACCENT)
    add_textbox(
        s, Inches(0.8), Inches(5.95), Inches(11.7), Inches(0.75),
        "Verdict: Keep how we find candidate moves. Change how we decide which moves to accept.",
        size=19, bold=True, color=NAVY
    )
    add_notes(
        s,
        "Walk the code-level verdict. Priority selection, rebuild, incremental availability, and "
        "VNS shifts are compatible proposal machinery for SA. Currently we only keep improving "
        "moves and exit early — classic hill-climbing. The new method is annealing acceptance: "
        "better moves always; worse moves sometimes, more early, less later. Drop the "
        "improve-only early-exit so worse candidates can be tried. Composition is clean if we "
        "keep proposals and swap acceptance."
    )

    # 5 Hybrid design
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "RECOMMENDED DESIGN")
    title(s, "Smart search + annealing acceptance")
    nodes = [
        ("1", "Target the\nworst days"),
        ("2", "Different\nshift sizes"),
        ("3", "Sometimes accept\na worse move"),
        ("4", "Keep the\nbest result"),
    ]
    for i, (num, label) in enumerate(nodes):
        left = Inches(0.5 + i * 3.2)
        add_card(s, left, Inches(1.3), Inches(2.95), Inches(2.15), fill=PALE, line=ACCENT)
        add_textbox(s, left + Inches(0.1), Inches(1.5), Inches(2.75), Inches(0.45),
                    num, size=22, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
        add_textbox(s, left + Inches(0.1), Inches(2.05), Inches(2.75), Inches(1.1),
                    label, size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        if i < 3:
            arrow = s.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                left + Inches(2.98), Inches(2.1), Inches(0.2), Inches(0.4)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()
    add_card(s, Inches(0.5), Inches(3.7), Inches(12.3), Inches(3.2), fill=CARD, line=LINE)
    add_textbox(s, Inches(0.8), Inches(3.95), Inches(11.7), Inches(0.5),
                "Work plan", size=22, bold=True, color=NAVY)
    add_bullets(
        s, Inches(0.8), Inches(4.55), Inches(11.7), Inches(2.1),
        [
            "Decide how to score temporary worse moves fairly.",
            "Keep today’s method as the baseline to beat.",
            "Only keep annealing if it clearly improves results.",
        ],
        size=20, space_after=18,
    )
    add_notes(
        s,
        "Recommend the hybrid: priority-biased proposals, VNS neighbourhoods, SA acceptance, and "
        "best-so-far tracking. Baseline stays deterministic priority VNS; SA is an additive "
        "experiment. Energy definition matters because our score is a lexicographic tuple—either "
        "scalarise carefully or stage Metropolis by objective component."
    )

    # 6 Constraints
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "CONSTRAINTS")
    title(s, "Availability-max is necessary but not sufficient")
    add_textbox(
        s, Inches(0.5), Inches(1.2), Inches(12.3), Inches(0.5),
        "The current model maximises availability under maintenance rules but is under-constrained for ops realism.",
        size=18, color=MUTED
    )
    items = [
        ("Availability-max windows", "Limit when and how far events can move to protect peak demand periods."),
        ("Surrounding event moves", "Bound knock-on shifts so local edits stay operationally coherent."),
        ("Local std control", "Cap local availability variation, not only global lexicographic std."),
        ("Separate validity checks", "Report constraint satisfaction independently of raw availability gains."),
    ]
    for i, (h, body) in enumerate(items):
        top = Inches(1.8 + i * 1.2)
        add_card(s, Inches(0.5), top, Inches(12.3), Inches(1.1), fill=CARD, line=LINE)
        add_textbox(s, Inches(0.8), top + Inches(0.12), Inches(11.7), Inches(0.4),
                    h, size=19, bold=True, color=NAVY)
        add_textbox(s, Inches(0.8), top + Inches(0.52), Inches(11.7), Inches(0.45),
                    body, size=19, color=BODY)
    add_notes(
        s,
        "Stakeholders care about operable schedules, not only a higher minimum availability. "
        "Constraints are a first-class workstream: prototype availability-max windows, surrounding "
        "event move limits, and local standard-deviation control. Validate constraint satisfaction "
        "separately so we do not confuse a prettier availability curve with a feasible plan."
    )

    # 7 Hyperparameters
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "SENSITIVITY")
    title(s, "Which knobs actually move the needle?")
    add_card(s, Inches(0.5), Inches(1.3), Inches(6.05), Inches(5.5), fill=CARD, line=LINE)
    add_textbox(s, Inches(0.8), Inches(1.6), Inches(5.5), Inches(0.5),
                "Fixed today", size=24, bold=True, color=NAVY)
    add_bullets(
        s, Inches(0.8), Inches(2.4), Inches(5.5), Inches(4.1),
        [
            "How far we shift maintenance dates",
            "How long we let the search run",
            "Whether we stop early once we find an improvement",
            "If we add annealing: how quickly we cool the search",
        ],
        size=22, space_after=32,
    )
    add_card(s, Inches(6.8), Inches(1.3), Inches(5.95), Inches(5.5), fill=PALE, line=ACCENT)
    add_textbox(s, Inches(7.1), Inches(1.6), Inches(5.4), Inches(0.5),
                "Analysis approach", size=24, bold=True, color=ACCENT)
    add_bullets(
        s, Inches(7.1), Inches(2.4), Inches(5.4), Inches(4.1),
        [
            "Test settings on the heavy maintenance data",
            "Compare schedule quality against runtime",
            "Report which settings actually matter",
            "Avoid endless tuning — document and decide",
        ],
        size=22, space_after=32,
    )
    add_notes(
        s,
        "Avoid tuning theatre. Document the knobs we already fix—shift sets, max iterations, "
        "priority early-exit—and any SA temperature or cooling parameters if SA proceeds. Run "
        "sensitivity on heavy data and report which knobs move quality versus runtime. The goal "
        "is a short list of material levers, not an endless grid search."
    )

    # 8 Stagger
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "STARTING POINT")
    title(s, "Separate start effect from algorithm gain")
    add_card(s, Inches(0.5), Inches(1.3), Inches(12.3), Inches(5.5), fill=CARD, line=LINE)
    add_bullets(
        s, Inches(0.9), Inches(1.7), Inches(11.5), Inches(4.7),
        [
            "Local search quality depends on the starting schedule.",
            "A ‘better algorithm’ may simply have a luckier start.",
            "Design controlled stagger variants of the initial plan.",
            "Hold seed and evaluation protocol fixed across algorithms.",
            "Attribute gains to method only after start effects are isolated.",
        ],
        size=24, space_after=22,
    )
    add_notes(
        s,
        "Without stagger controls, we risk mis-attributing improvement. Controlled stagger variants "
        "let us separate starting-point effects from algorithm gains. Use the same seed and protocol "
        "when comparing priority VNS, SA hybrids, and any constraint-aware variants. This keeps "
        "Iteration 2 claims honest."
    )

    # 9 Timeline
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "PLAN")
    title(s, "From baseline freeze to decision gate")
    nodes = [
        ("1", "Freeze\nbaseline"),
        ("2", "SA\nacceptance"),
        ("3", "Energy /\nstaged rule"),
        ("4", "Constraint\nprototypes"),
        ("5", "Sensitivity\n+ stagger"),
        ("6", "Decision\ngate"),
    ]
    for i, (num, label) in enumerate(nodes):
        left = Inches(0.35 + i * 2.15)
        timeline_node(s, left, Inches(1.45), Inches(2.0), Inches(2.35), f"Step {num}", label,
                      highlight=(i == 0 or i == 5))
        if i < 5:
            arrow = s.shapes.add_shape(
                MSO_AUTO_SHAPE_TYPE.RIGHT_ARROW,
                left + Inches(2.02), Inches(2.4), Inches(0.14), Inches(0.35)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()
    add_card(s, Inches(0.5), Inches(4.15), Inches(12.3), Inches(2.7), fill=PALE, line=ACCENT)
    add_bullets(
        s, Inches(0.8), Inches(4.45), Inches(11.7), Inches(2.15),
        [
            "Freeze priority VNS early so every later comparison stays fair.",
            "Only then replace acceptance, define energy, and add constraint/sensitivity work.",
            "End with an explicit go / no-go decision on SA and constraint prototypes.",
        ],
        size=19, space_after=16,
    )
    add_notes(
        s,
        "Order the work so comparisons stay fair. Freeze the baseline early; only then change "
        "acceptance, define the energy or staged rule, prototype constraints, run sensitivity and "
        "stagger studies, and hit a decision gate. Do not invent new algorithms before the "
        "baseline is locked."
    )

    # 10 Success criteria
    s = prs.slides.add_slide(blank)
    add_bg(s)
    add_accent_bar(s)
    section_label(s, "DECISION CRITERIA")
    title(s, "What “good enough” looks like — and when to stop")
    add_card(s, Inches(0.5), Inches(1.3), Inches(6.05), Inches(5.5), fill=PALE, line=ACCENT)
    add_textbox(s, Inches(0.8), Inches(1.6), Inches(5.5), Inches(0.5),
                "Success measures", size=24, bold=True, color=ACCENT)
    add_bullets(
        s, Inches(0.8), Inches(2.4), Inches(5.5), Inches(4.1),
        [
            "Quality: min / std / average availability",
            "Runtime within a practical budget",
            "Constraint validity rate on prototypes",
            "Clear attribution vs frozen baseline",
        ],
        size=22, space_after=32,
    )
    add_card(s, Inches(6.8), Inches(1.3), Inches(5.95), Inches(5.5), fill=CARD, line=LINE)
    add_textbox(s, Inches(7.1), Inches(1.6), Inches(5.4), Inches(0.5),
                "Risks and exits", size=24, bold=True, color=NAVY)
    add_bullets(
        s, Inches(7.1), Inches(2.4), Inches(5.4), Inches(4.1),
        [
            "Abandon SA if no gain vs priority VNS",
            "Use staged acceptance if lex energy thrashing",
            "Keep priority VNS if hybrid underperforms",
            "Do not ship constraints that fail validity checks",
        ],
        size=22, space_after=32,
    )
    add_notes(
        s,
        "Close with measurable gates. Success is quality, runtime, and constraint validity against "
        "the frozen baseline. Exit criteria matter: abandon SA if it does not beat priority VNS; "
        "switch to staged acceptance if lexicographic energy thrashing appears; keep the baseline "
        "if the hybrid underperforms. Research continues only where evidence supports it."
    )

    prs.save(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
