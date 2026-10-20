"""Write the plain-language Iteration 2 briefing as Word."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reports"
    / "2026-10-11-iteration-2-plain-language.docx"
)

BLACK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x55, 0x55, 0x55)


def shade(cell, hex_color):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tc_pr.append(shd)


def set_run(run, size=11, bold=False, italic=False, color=BLACK):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def add_paragraph(document, text, size=11, bold=False, italic=False, color=BLACK, space_after=10, space_before=0):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    paragraph.paragraph_format.line_spacing = 1.12
    run = paragraph.add_run(text)
    set_run(run, size=size, bold=bold, italic=italic, color=color)
    return paragraph


def add_heading(document, text):
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run(text)
    set_run(run, size=16, bold=True, color=BLACK)
    return paragraph


def add_table(document, headers, rows):
    table = document.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = ""
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(header)
        set_run(run, size=10, bold=True)
        shade(cell, "F0F0F0")
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            cell = table.rows[row_index + 1].cells[col_index]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(value)
            set_run(run, size=10)
    document.add_paragraph().paragraph_format.space_after = Pt(4)


def build():
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.font.color.rgb = BLACK

    add_paragraph(
        document,
        "What Iteration 2 actually did",
        size=22,
        bold=True,
        space_after=2,
    )
    add_paragraph(
        document,
        "A plain-language note on the Semester 2 study",
        size=12,
        italic=True,
        color=GRAY,
        space_after=2,
    )
    add_paragraph(document, "11 October 2026", size=11, color=GRAY, space_after=12)

    add_paragraph(
        document,
        "Semester 2 asked two questions. Is a new way of searching worth switching to, in place of the hill-climb we already have? And can a few extra operational rules sit on a maintenance plan without breaking it?",
    )
    add_paragraph(
        document,
        "Both were tried on the real heavy-maintenance forecast. This note is the version you can read without a glossary open beside you. The seed-by-seed tables are still in the handover if you need every decimal.",
    )

    add_heading(document, "The short answer")
    add_paragraph(
        document,
        "Keep the hill-climb. Use the step sizes an earlier settings study already found, and pass them in when you call it, so the published defaults from Iteration 1 stay exactly as they are.",
    )
    add_paragraph(
        document,
        "The new search, basin-hopping, came out a little smoother and no better on the worst day. It was also slower than the five minutes we allowed. That is not enough to switch.",
    )
    add_paragraph(
        document,
        "A worst day of 19 aircraft available cannot be reached on this forecast. Six D checks are already open at the start, and they hold the worst day at 18 or lower. Later work should not spend time chasing 19.",
    )

    add_heading(document, "How a plan is scored")
    add_paragraph(document, "Two numbers, in this order.")
    add_paragraph(
        document,
        "The worst day is the quietest day in the whole forecast: the fewest aircraft still available when maintenance is heaviest. Higher is better. Every finished search in this study landed on 18.",
    )
    add_paragraph(
        document,
        "Smoothness is how even the rest of the year looks. It is the standard deviation of daily availability, so a lower number means the fleet does not lurch between very busy weeks and very quiet ones. We said we would switch methods only if the typical run improved smoothness by at least 0.005, still held a worst day of 18, and usually finished inside five minutes.",
    )

    add_heading(document, "The two searches")
    add_paragraph(
        document,
        "The hill-climb walks the plan one small change at a time and keeps a change only when the plan gets better. It always produces the same schedule, so it was run once.",
    )
    add_paragraph(
        document,
        "Basin-hopping uses the same kinds of moves. Early on, while the search is still hot, it will sometimes accept a worse plan, so it can climb out of a rut. Those accepts get rare as it cools. The plan we keep is the best one seen along the way, even if the search later wanders off it.",
    )
    add_paragraph(
        document,
        "Each move slides one check by a set number of days, earlier or later, but only inside the window the maintenance rules already allow. A check can never start after its due date. The search begins with coarse slides and works down to a single day: 28 days and 14, then 14 and 7, then 7 and 3, then 3 and 1. It stops after 400 steps. Both methods used that same ladder, so any gain would have come from how a move is accepted, not from a different step size.",
    )

    add_heading(document, "Did the new search win?")
    add_paragraph(
        document,
        "No. On the decision run the hill-climb finished at a worst day of 18 and smoothness 1.392, in about two minutes.",
    )
    add_paragraph(
        document,
        "Basin-hopping depends on a random seed, so it was run three times and judged on the middle result, not the luckiest one. That middle result was smoothness 1.390, still with a worst day of 18. The gain was 0.001. We had asked for 0.005. A typical run took a little over five minutes, and two of the three were stopped when they hit the time limit.",
    )
    add_table(
        document,
        ["Search", "Worst day", "Smoothness", "Time"],
        [
            ["Hill-climb", "18", "1.392", "about 2 minutes"],
            ["Basin-hopping, middle of three runs", "18", "1.390", "a little over 5 minutes; two runs stopped"],
            ["Stricter basin-hopping, middle of three", "18", "1.392", "about 1 minute"],
        ],
    )
    add_paragraph(
        document,
        "The stricter version refuses any move that makes the worst day worse. It reached the same smoothness as the hill-climb, and it was faster. It is there if we ever need it. On these runs the looser rule did not give the worst day away, so the stricter rule was not what saved the result.",
    )
    add_paragraph(
        document,
        "An older simulated-annealing trial, from before this study, sat at the original hill-climb's smoothness (1.414) with a worst day of 18. That was a side check. It was not run again, and it is not the method this study was judging.",
    )

    add_heading(document, "Does the starting plan matter?")
    add_paragraph(
        document,
        "Yes. We tried three openings, with the extra operational rules turned off, so the starting point was not mixed up with those rules.",
    )
    add_paragraph(
        document,
        "The plan as it comes out of the forecast. A bunched plan, which pulls each aircraft's next movable check toward the middle of the fleet, then rebuilds the later checks so the maintenance intervals still hold. And a spread plan, which pushes that same check away from the middle, then rebuilds.",
    )
    add_paragraph(
        document,
        "The very first check on each aircraft cannot move. The maintenance replay pins it to its due date, so bunching and spreading act on the next check: the first one the replay is actually free to place somewhere else inside its window.",
    )
    add_paragraph(
        document,
        "Before any search, all three openings have a worst day of 15. The loaded plan is already the smoothest of the three. After the search, every opening reaches a worst day of 18. The loaded start still finishes smoothest. Bunching the fleet, or fanning those checks out, makes the finished plan worse for both searches. Start from the loaded forecast.",
    )
    add_table(
        document,
        ["Opening", "Before any search", "Hill-climb", "Basin-hopping"],
        [
            ["As loaded", "worst day 15, smoothness 1.95", "worst day 18, smoothness 1.392", "worst day 18, smoothness 1.389"],
            ["Bunched", "worst day 15, smoothness 1.96", "worst day 18, smoothness 1.405", "worst day 18, smoothness 1.401"],
            ["Spread", "worst day 15, smoothness 1.98", "worst day 18, smoothness 1.417", "worst day 18, smoothness 1.416"],
        ],
    )

    add_heading(document, "Can we add operational rules?")
    add_paragraph(
        document,
        "These are dummy rules, in their own file, operational_constraints.json. They are not dates or groups from the sponsor. The forecast workbook was not edited.",
    )
    add_paragraph(document, "There are three kinds of rule.")
    add_paragraph(
        document,
        "A busy period is a stretch of dates where availability has to stay above a floor. We used two stretches that are already busy in the loaded forecast: 27 April to 26 May 2033, and 14 September to 13 October 2033.",
    )
    add_paragraph(
        document,
        "A displacement limit is how far a check may slide from where the loaded plan put it. That includes slides caused when a later check is rebuilt after an earlier one moves. Loose allows 70 days, medium 42, tight 21. A check can only move earlier anyway, and its own window is often about that wide, so the 70-day leash rarely bites. The 42-day and 21-day leashes do.",
    )
    add_paragraph(
        document,
        "A dependency group is a set of aircraft that need to be available together. We named two groups of four. Loose and medium say at least two of the four must be available every day. Tight says at least three.",
    )
    add_paragraph(
        document,
        "A move that breaks any of these is thrown out, for both searches, even while basin-hopping is still hot. Annealing cannot sneak past a hard rule.",
    )
    add_paragraph(
        document,
        "Loose and medium are already legal on the loaded plan, and the search kept them legal. Both still reach a worst day of 18. The price is smoothness. Loose finishes around 1.51 and medium around 1.72, because the search has less room to shuffle checks. Medium, with the shorter leash, is the rougher of the two, and it finishes in a few seconds because it runs out of legal moves quickly.",
    )
    add_paragraph(
        document,
        "Tight is already illegal before the search starts. In both busy stretches the worst day on the loaded plan is 15, and the rule asks for 16. Both groups of four fall to two aircraft available, and the rule asks for three. That was reported as infeasible. Nothing was repaired. The tight case is there to show the limits breaking a plan, not to build a fixer.",
    )
    add_table(
        document,
        ["Scenario", "What it asks", "What happened"],
        [
            [
                "Loose",
                "70-day leash, busy-period floor of 15, two of every four aircraft available",
                "Stayed legal. Worst day 18, smoothness 1.51",
            ],
            [
                "Medium",
                "42-day leash, same busy periods and groups",
                "Stayed legal. Worst day 18, smoothness 1.72",
            ],
            [
                "Tight",
                "21-day leash, busy-period floor of 16, three of every four available",
                "Already illegal on the loaded plan. Left as infeasible",
            ],
        ],
    )

    add_heading(document, "Did turning the knobs help?")
    add_paragraph(
        document,
        "We changed one setting at a time: how hot the early search is, how many times it tries to escape a rut, how long it sits on a flat patch, and how long it polishes at the end. The sweep was capped at one hour, with the operational rules turned off. Nothing cleared the bar we set for switching methods.",
    )
    add_paragraph(
        document,
        "The most promising single run was a cooler escape temperature. On one seed it reached smoothness 1.389 in about two and a half minutes. That is still only about 0.003 better than the hill-climb, short of 0.005. A second run of that same setting was stopped after it passed five minutes, back at the hill-climb's smoothness, so it does not count as a confirmed repeat.",
    )

    add_heading(document, "One place the slides and the code disagree")
    add_paragraph(
        document,
        "The execution-plan deck says a move that lowers the worst day is always rejected. The search we tested does not do that. While it is still hot, it may accept that move. Those accepts get rare as it cools, and the plan we hand back is the best one seen, so a dip along the way is not the answer. The stricter fallback refuses that dip outright. The deck was left as it was presented.",
    )

    add_heading(document, "What to take forward")
    add_paragraph(
        document,
        "Use the hill-climb with the step-size ladder above, and a cap of 400 steps. Leave the published defaults in the hill-climb module alone, and pass those step sizes in from the caller, so the Iteration 1 result can still be reproduced.",
    )
    add_paragraph(
        document,
        "Start from the loaded forecast. Bunching or spreading the opening checks makes the finished plan worse.",
    )
    add_paragraph(
        document,
        "Dummy limits can sit on the plan when the loaded forecast already satisfies them. When it does not, say so.",
    )
    add_paragraph(document, "Do not hunt a worst day of 19 on this forecast.")

    add_heading(document, "Where the work lives")
    add_paragraph(
        document,
        "The hill-climb is vn_priority_based_selection.py. Iteration 2 calls it and does not change its published defaults. Classic simulated annealing is in savn_priority_sa.py, and the basin-hopping search is in savn_basin_hopping.py. The staggered starts, the operational limits, and the keep-or-drop rule are in savn_iteration2.py.",
    )
    add_paragraph(
        document,
        "The measured tables, including every seed, are in the handover note dated 30 October 2026, with a Word copy beside it. A shorter lab note from the same work is the Iteration 2 summary dated 11 October 2026. Both sit in docs/reports.",
    )

    document.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
