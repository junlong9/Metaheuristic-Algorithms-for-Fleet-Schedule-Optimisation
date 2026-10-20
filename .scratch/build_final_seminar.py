"""Assemble presentations/Final Seminar.pptx from the live decks.

Copies slides. Does not save over Seminar, Iteration 1, or the execution plan.
"""
import sys

import win32com.client

ROOT = r"C:\Users\davsk\OneDrive\The University of Queensland\Northrop Grumman\Iteration 1\presentations"
DEST = ROOT + r"\Final Seminar.pptx"
SEMINAR = ROOT + r"\Seminar.pptx"
PLAN = ROOT + r"\Iteration 2 Execution Plan.pptx"


def first_line(slide):
    for i in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes(i)
        if shape.HasTextFrame:
            text = shape.TextFrame.TextRange.Text.strip()
            if text:
                return text.split("\r")[0].split("\n")[0].strip()
    return ""


def shape_by_name(slide, name):
    for i in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes(i)
        if shape.Name == name:
            return shape
    raise KeyError(name)


def set_text(shape, text):
    shape.TextFrame.TextRange.Text = text.replace("\n", "\r")


def main():
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = True
    already_open = {p.FullName for p in powerpoint.Presentations}

    dest = powerpoint.Presentations.Open(DEST, False, False, True)
    seminar = powerpoint.Presentations.Open(SEMINAR, True, False, False)
    plan = powerpoint.Presentations.Open(PLAN, True, False, False)

    seminar.Slides(2).Copy()
    dest.Slides.Paste(2)
    seminar.Slides(3).Copy()
    dest.Slides.Paste(3)

    for index in (2, 4, 5, 6, 9, 11):
        plan.Slides(index).Copy()
        dest.Slides.Paste(dest.Slides.Count + 1)

    seminar.Close()
    plan.Close()

    # Title sits in TextBox 8 on the Iteration 1 title slide.
    set_text(
        shape_by_name(dest.Slides(1), "TextBox 8"),
        "Scheduling Algorithm Research.\r"
        "Prototype a range of proposed scheduling algorithm improvements with dummy data\r"
        "\r"
        "Final seminar\r"
        "\r"
        "\r"
        "\r"
        "Presenter: David Long",
    )

    recap = None
    for i in range(1, dest.Slides.Count + 1):
        if first_line(dest.Slides(i)) == "ITERATION 1 RECAP":
            recap = dest.Slides(i)
            break
    if recap is None:
        raise RuntimeError("Recap slide was not imported")

    def duplicate_recap():
        copied = recap.Duplicate()
        return copied.Item(1)

    comparison = duplicate_recap()
    starts = duplicate_recap()
    keep = duplicate_recap()
    hyper = duplicate_recap()

    fill_comparison(comparison)
    fill_starts(starts)
    fill_keep(keep)
    fill_hyper(hyper)

    order = [
        "Scheduling Algorithm Research.",
        "Why Maintenance Scheduling Matters",
        "The Problem and Bottlenecks",
        "Overview",
        "Literature Review and Method Selection",
        "Initial Dataset",
        "Best-Improvement Neighbourhood Search",
        "Extended Heavy maintenance dataset",
        "Optimised Heavy dataset using Random Sampling",
        "Optimised Heavy maintenance dataset",
        "Convergence Behaviour of Variable Neighbourhood Search",
        "Future Work and Research Direction",
        "ITERATION 1 RECAP",
        "SIMULATED ANNEALING",
        "HOW IT FITS",
        "FAIR ACCEPTANCE",
        "COMPARISON",
        "STARTING POINT",
        "OPENING STAGGER",
        "DECISION CRITERIA",
        "WHAT WE KEEP",
        "HYPERPARAMETERS",
        "References",
    ]
    place(dest, order)

    dest.Save()
    print("SLIDES", dest.Slides.Count)
    for i in range(1, dest.Slides.Count + 1):
        print(f"{i:02d} {first_line(dest.Slides(i))}")
    dest.Close()
    if not already_open:
        powerpoint.Quit()


def fill_comparison(slide):
    set_text(shape_by_name(slide, "TextBox 3"), "COMPARISON")
    set_text(
        shape_by_name(slide, "TextBox 4"),
        "Basin-hopping did not clear the keep rule",
    )
    set_text(shape_by_name(slide, "TextBox 6"), "WORST DAY")
    set_text(shape_by_name(slide, "TextBox 7"), "18 aircraft\rfor every method")
    set_text(shape_by_name(slide, "TextBox 9"), "SPREAD")
    set_text(shape_by_name(slide, "TextBox 10"), "1.390 vs 1.392\rbar was 0.005")
    set_text(
        shape_by_name(slide, "TextBox 12"),
        "Same heavy forecast. Lower spread is the smoother plan.",
    )
    set_text(
        shape_by_name(slide, "TextBox 13"),
        "• Tuned hill-climb, one run: spread 1.392, about 116 seconds.\r"
        "• Basin-hopping, median of seeds 1–3: spread 1.390, about 306 seconds. Two seeds ran past five minutes.\r"
        "• Tightened acceptance, which keeps the worst day from falling, matched the hill-climb at 1.392.\r"
        "• The keep rule asked for a 0.005 smoother plan, worst day still 18, and a typical run within five minutes.",
    )


def fill_starts(slide):
    set_text(shape_by_name(slide, "TextBox 3"), "OPENING STAGGER")
    set_text(
        shape_by_name(slide, "TextBox 4"),
        "The as-loaded opening still finishes smoothest",
    )
    set_text(shape_by_name(slide, "TextBox 6"), "AS LOADED")
    set_text(shape_by_name(slide, "TextBox 7"), "Spread 1.392\rin 63 seconds")
    set_text(shape_by_name(slide, "TextBox 9"), "BUNCHED")
    set_text(shape_by_name(slide, "TextBox 10"), "Spread 1.405\rin 48 seconds")
    set_text(
        shape_by_name(slide, "TextBox 12"),
        "Every opening starts at a worst day of 15 and finishes at 18",
    )
    set_text(
        shape_by_name(slide, "TextBox 13"),
        "• Spread opening: finished spread 1.417, in 93 seconds.\r"
        "• Figures are the tuned hill-climb. Basin-hopping was about 0.001 to 0.003 smoother on each opening, and slower.\r"
        "• Bunching or spreading the first checks leaves a bumpier finished plan.\r"
        "• The as-loaded forecast remains the start we keep.",
    )


def fill_keep(slide):
    set_text(shape_by_name(slide, "TextBox 3"), "WHAT WE KEEP")
    set_text(
        shape_by_name(slide, "TextBox 4"),
        "The tuned hill-climb is the method we take forward",
    )
    set_text(shape_by_name(slide, "TextBox 6"), "KEEP")
    set_text(
        shape_by_name(slide, "TextBox 7"),
        "Priority search on the worst availability days.\r"
        "Rebuild the aircraft after each move.\r"
        "Half-step shifts, coarse to fine.\r"
        "Accept an improving plan only.\r"
        "Start from the as-loaded forecast.",
    )
    set_text(shape_by_name(slide, "TextBox 9"), "SET ASIDE")
    set_text(
        shape_by_name(slide, "TextBox 10"),
        "Basin-hopping and temperature acceptance.\r"
        "The gain in spread was 0.001, short of 0.005, and the typical run exceeded five minutes.\r"
        "Tightened acceptance found the same plan as the hill-climb.",
    )
    set_text(shape_by_name(slide, "TextBox 12"), "Still open")
    set_text(
        shape_by_name(slide, "TextBox 13"),
        "• Hyperparameter settings are not finished. The next slide is a placeholder.\r"
        "• Published Iteration 1 defaults stay as they were. The half-step shifts are passed in by the caller.",
    )


def fill_hyper(slide):
    set_text(shape_by_name(slide, "TextBox 3"), "HYPERPARAMETERS")
    set_text(shape_by_name(slide, "TextBox 4"), "Settings sweep")
    set_text(shape_by_name(slide, "TextBox 6"), "")
    set_text(shape_by_name(slide, "TextBox 7"), "")
    set_text(shape_by_name(slide, "TextBox 9"), "")
    set_text(shape_by_name(slide, "TextBox 10"), "")
    set_text(shape_by_name(slide, "TextBox 12"), "")
    set_text(shape_by_name(slide, "TextBox 13"), "To be added.")


def place(dest, order):
    for target, title in enumerate(order, start=1):
        found = None
        for i in range(1, dest.Slides.Count + 1):
            if first_line(dest.Slides(i)) == title:
                found = i
                break
        if found is None:
            raise RuntimeError(f"Missing slide: {title}")
        if found != target:
            dest.Slides(found).MoveTo(target)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FAILED", type(exc).__name__, exc, file=sys.stderr)
        raise
