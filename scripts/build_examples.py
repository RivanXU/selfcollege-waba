#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Build the original, English-only public teaching example.

Run from any directory: python scripts/build_examples.py
Requires the project requirements and Poppler's pdftoppm. The example is authored
for this repository; no real course slides, assignments, or student data are used.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from render_study_pdfs import MathFormula, publish_outputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples"
NAVY = colors.HexColor("#17334D")
TEAL = colors.HexColor("#17786E")
INK = colors.HexColor("#263E50")
MUTED = colors.HexColor("#576B79")
LINE = colors.HexColor("#D6E2E3")
PALE = colors.HexColor("#EDF5F3")
PAPER = colors.HexColor("#FBFCFA")
BLUE = colors.HexColor("#EAF1F8")
AMBER = colors.HexColor("#FBF3E1")
W, H = 595.276, 841.89
MARGIN = 46
CONTENT = W - 2 * MARGIN
SLIDE_W, SLIDE_H = 960, 540

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=11.1,
                      leading=17.7, textColor=INK)
SMALL = ParagraphStyle("small", fontName="Helvetica", fontSize=9.3,
                       leading=14.5, textColor=MUTED)
LABEL = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=11.3,
                       leading=16.5, textColor=TEAL)


def paragraph(c, text, x, top, width, style=BODY):
    p = Paragraph(text, style)
    _, height = p.wrap(width, 1000)
    if c._pagesize == (W, H) and top - height < 60:
        raise ValueError(f"Guide page {c.getPageNumber()} reaches the footer ({top - height:.1f} pt): split the knowledge block.")
    p.drawOn(c, x, top - height)
    return top - height


def equation(c, latex, center_x, center_y, fontsize=15, max_width=None):
    formula = MathFormula(latex, fontsize)
    width, height = formula.width, formula.height
    if max_width is None and c._pagesize == (W, H):
        max_width = CONTENT - 8
    if max_width and width > max_width:
        raise ValueError(f"Formula is too wide ({width} pt): split its steps; preserve font size.")
    formula.drawOn(c, center_x - width / 2, center_y - height / 2)
    return height


def section(c, label, top):
    c.setFillColor(TEAL)
    c.roundRect(MARGIN, top - 17, 3, 16, 1.5, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 12.6)
    c.drawString(MARGIN + 12, top - 13, label)
    return top - 31


def note(c, label, text, top, tone=PALE):
    p = Paragraph(text, BODY)
    _, height = p.wrap(CONTENT - 30, 1000)
    box_height = height + 53
    if top - box_height < 60:
        raise ValueError(f"Guide page {c.getPageNumber()} note reaches the footer: split the knowledge block.")
    c.setFillColor(tone)
    c.roundRect(MARGIN, top - box_height, CONTENT, box_height, 7, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10.8)
    c.drawString(MARGIN + 15, top - 22, label)
    p.drawOn(c, MARGIN + 15, top - 36 - height)
    return top - box_height - 20


def guide_page(c, number, title, subtitle):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, H - 8, W, 8, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawString(MARGIN, H - 32, "SELFCOLLEGE WABA / ORIGINAL PUBLIC DEMO")
    c.setFont("Helvetica", 8.6)
    c.setFillColor(MUTED)
    c.drawRightString(W - MARGIN, H - 32, "BEGINNER STUDY GUIDE")
    c.setStrokeColor(LINE)
    c.line(MARGIN, H - 44, W - MARGIN, H - 44)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 23)
    c.drawString(MARGIN, H - 80, title)
    top = paragraph(c, subtitle, MARGIN, H - 92, CONTENT, SMALL) - 25
    c.line(MARGIN, 40, W - MARGIN, 40)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, 25, "Connected study workflow / Original neutral fixture")
    c.drawRightString(W - MARGIN, 25, f"{number:02d} / 08")
    c.bookmarkPage(f"guide-{number}")
    c.addOutlineEntry(title, f"guide-{number}")
    return top


def symbol_table(c, top):
    rows = [
        ("N", "Listed items", "All distinct items in the chosen source log.", "count"),
        ("C", "Checked items", "Listed items checked against the source.", "count"),
        ("U", "Unchecked items", "Listed items still awaiting a source check.", "count"),
        ("q", "Checked fraction", "Checked items as a share of listed items.", "no unit"),
    ]
    columns = [MARGIN + 11, MARGIN + 73, MARGIN + 211, W - MARGIN - 58]
    c.setFillColor(NAVY)
    c.roundRect(MARGIN, top - 30, CONTENT, 30, 4, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9.3)
    c.setFillColor(colors.white)
    for x, text in zip(columns, ["Symbol", "Quantity", "Meaning", "Unit"]):
        c.drawString(x, top - 19, text)
    row_top = top - 30
    for i, row in enumerate(rows):
        c.setFillColor(colors.white if i % 2 == 0 else PALE)
        c.rect(MARGIN, row_top - 46, CONTENT, 46, fill=1, stroke=0)
        formula = MathFormula(row[0], 11)
        formula.drawOn(c, columns[0], row_top - 23 - formula.height / 2)
        paragraph(c, row[1], columns[1], row_top - 10, 127, SMALL)
        paragraph(c, row[2], columns[2], row_top - 8, 216, SMALL)
        paragraph(c, row[3], columns[3], row_top - 13, 55, SMALL)
        row_top -= 46
    return row_top - 18


def workflow(c, x, y, width, height, kind="source"):
    """An original neutral workflow; both decks share every drawing origin."""
    labels = (["Read the whole source", "Connect nearby ideas", "Explain the reasoning", "Practice and check"]
              if kind == "source" else
              ["Read all source pages", "Link the ideas in order", "Show why each step works", "Try it and check it"])
    captions = ["READ", "CONNECT", "EXPLAIN", "PRACTICE"]
    box_w, box_h = (width - 30) / 2, (height - 35) / 2
    origins = [(x, y + box_h + 35), (x + box_w + 30, y + box_h + 35),
               (x, y), (x + box_w + 30, y)]
    for index, (xx, yy) in enumerate(origins):
        c.setFillColor(PALE if index % 2 == 0 else BLUE)
        c.roundRect(xx, yy, box_w, box_h, 6, fill=1, stroke=0)
        slide_text(c, [captions[index]], xx + 12, yy + box_h - 23, 10, color=TEAL, bold=True)
        slide_text(c, [labels[index]], xx + 12, yy + 21, 10, color=INK)
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.3)
    # Arrows are deliberately outside the boxes and follow the source order.
    for yy in (y + box_h / 2, y + box_h + 35 + box_h / 2):
        c.line(x + box_w + 7, yy, x + box_w + 23, yy)
        c.line(x + box_w + 23, yy, x + box_w + 19, yy + 3)
        c.line(x + box_w + 23, yy, x + box_w + 19, yy - 3)
    # The second block feeds the third; the connector goes around the boxes.
    c.line(x + width - box_w / 2, y + box_h + 35, x + width - box_w / 2, y + box_h + 18)
    c.line(x + width - box_w / 2, y + box_h + 18, x + box_w / 2, y + box_h + 18)
    c.line(x + box_w / 2, y + box_h + 18, x + box_w / 2, y + box_h + 5)
    c.line(x + box_w / 2, y + box_h + 5, x + box_w / 2 - 3, y + box_h + 9)
    c.line(x + box_w / 2, y + box_h + 5, x + box_w / 2 + 3, y + box_h + 9)


def ledger(c, x, y, width, height):
    """Eight synthetic items, six checked: a source-log count, never a score."""
    gap = 12
    cell_w = (width - 3 * gap) / 4
    cell_h = (height - 32) / 2
    for i in range(8):
        xx = x + (i % 4) * (cell_w + gap)
        yy = y + (1 - i // 4) * (cell_h + 12)
        checked = i < 6
        c.setFillColor(PALE if checked else colors.white)
        c.setStrokeColor(TEAL if checked else LINE)
        c.roundRect(xx, yy, cell_w, cell_h, 5, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(xx + cell_w / 2, yy + cell_h - 19, f"Item {i + 1}")
        c.setFont("Helvetica", 9)
        c.drawCentredString(xx + cell_w / 2, yy + 14, "Checked" if checked else "Pending")
    slide_text(c, ["Synthetic source log: 6 checked, 2 pending"], x, y - 22, 10, color=MUTED)


def slide_text(c, lines, x, y, font_size=18, leading=27, color=INK, bold=False):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
    for i, text in enumerate(lines):
        c.drawString(x, y - i * leading, text)


SLIDE_COPY = {
    "source": [
        {"title": "Build a connected study route",
         "intro": ["Read the complete source before explaining its parts.", "Group consecutive ideas around the question they answer."],
         "body": ["Keep the source order visible.", "Name the link between each knowledge block.", "Use the explanation to attempt the next task."],
         "connection": "A coherent route connects the source, the reasoning and the practice."},
        {"title": "Check what the source log covers",
         "intro": ["Count distinct listed items and record which were checked.", "The checked fraction describes this log, not learning quality."],
         "body": ["Listed items: 8", "Checked against the source: 6"],
         "connection": "The denominator defines the whole; the numerator identifies the checked part."},
        {"title": "Use the record to choose a next step",
         "intro": ["Separate checked items from items still awaiting a check.", "Then choose a useful explanation or practice task."],
         "body": ["A pending item calls for a source check.", "A checked item can still need explanation or practice."],
         "connection": "The count tells us what was recorded; a worked explanation tests the reasoning."},
    ],
    "target": [
        {"title": "Build a connected study route",
         "intro": ["Read all of the source before teaching one small part.", "Put nearby ideas together around their shared question."],
         "body": ["Follow the order in the source.", "Say how one group of ideas leads to the next.", "Use what you explained to try the next task."],
         "connection": "Link what the source says to why it works and how to use it."},
        {"title": "Check what the source log covers",
         "intro": ["List each item once and mark the items you have checked.", "This fraction describes the list, not how well you learned."],
         "body": ["There are 8 items on the list.", "You checked 6 items against the source."],
         "connection": "The bottom number is the whole list; the top number is the checked part."},
        {"title": "Use the record to choose a next step",
         "intro": ["Keep checked items apart from items not yet checked.", "Then pick something useful to explain or try."],
         "body": ["Check the source for an item still marked pending.", "Even a checked item may need more explanation or practice."],
         "connection": "A count shows what you logged; explain and try an idea to check your reasoning."},
    ],
}


def build_slides(kind):
    path = OUT / ("source-slides.pdf" if kind == "source" else "translated-slides.pdf")
    c = canvas.Canvas(str(path), pagesize=(SLIDE_W, SLIDE_H), invariant=1)
    c.setTitle("Connected study workflow: " + ("academic English" if kind == "source" else "plain-English mirror"))
    c.setAuthor("selfcollege-waba")
    c.setSubject("Original neutral public example; no real course or learner data")
    for index, copy in enumerate(SLIDE_COPY[kind], 1):
        c.setFillColor(PAPER)
        c.rect(0, 0, SLIDE_W, SLIDE_H, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.rect(0, SLIDE_H - 9, SLIDE_W, 9, fill=1, stroke=0)
        slide_text(c, ["READ / CONNECT / EXPLAIN / PRACTICE"], 52, 502, 10, color=TEAL, bold=True)
        slide_text(c, [copy["title"]], 52, 461, 27.5, color=NAVY, bold=True)
        slide_text(c, copy["intro"], 52, 420, 18, leading=27)
        c.setStrokeColor(LINE)
        c.line(52, 363, 908, 363)
        if index == 1:
            slide_text(c, copy["body"], 56, 331, 17, leading=30)
            slide_text(c, ["A route, not four unrelated summaries."], 56, 191, 13, color=TEAL, bold=True)
            workflow(c, 530, 142, 372, 197, kind)
        elif index == 2:
            slide_text(c, copy["body"], 56, 331, 17, leading=30)
            equation(c, r"q=\frac{C}{N}", 271, 237, 21, 410)
            equation(c, r"q=\frac{6}{8}=\frac{3}{4}", 271, 164, 21, 410)
            slide_text(c, ["N = listed items    C = checked items    q = checked fraction"], 56, 117, 11.4, color=MUTED)
            ledger(c, 540, 164, 348, 157)
        else:
            equation(c, r"U=N-C", 479, 315, 21, 820)
            equation(c, r"r=\frac{U}{N}\qquad q+r=1", 479, 229, 21, 820)
            slide_text(c, copy["body"], 56, 160, 17, leading=29)
            slide_text(c, ["U = pending items    r = pending fraction    N > 0    C + U = N"], 56, 112, 11.4, color=MUTED)
        c.setFillColor(PALE)
        c.roundRect(52, 51, 856, 52, 6, fill=1, stroke=0)
        slide_text(c, [copy["connection"]], 66, 71, 12.8, color=TEAL)
        slide_text(c, ["Original neutral demonstration / Synthetic source-check counts"], 52, 26, 9, color=MUTED)
        slide_text(c, [f"0{index} / 03"], 866, 26, 9, color=MUTED)
        c.showPage()
    c.save()
    return path


HOMEWORK = ("An original practice source log lists 10 distinct items. Seven items have been "
            "checked against that source; the other items are pending. No item is listed twice, "
            "and every listed item has exactly one of these two statuses. "
            "(a) Find the checked fraction and write it as a percentage. "
            "(b) Find the number and fraction of pending items. "
            "(c) Verify that the two fractions add to one. "
            "(d) Does the checked percentage prove that the learner understands the source? "
            "Explain your answer and propose one next study action.")


def derivation(c, top, steps):
    """Keep one displayed operation and its reason in the same knowledge block."""
    for latex, reason in steps:
        height = MathFormula(latex, 15).height
        equation(c, latex, W / 2, top - height / 2, 15)
        top = paragraph(c, reason, MARGIN, top - height - 7, CONTENT) - 15
    return top


def build_guide():
    path = OUT / "beginner-study-guide.pdf"
    c = canvas.Canvas(str(path), pagesize=(W, H), invariant=1)
    c.setTitle("A connected study route: beginner study guide")
    c.setAuthor("selfcollege-waba")
    c.setSubject("Original cross-disciplinary workflow, synthetic counts and integrated practice")

    top = guide_page(c, 1, "Read, connect, explain, practice", "Source slides 1-3 / An original neutral example for any course or subject.")
    top = section(c, "The question behind this lesson", top)
    top = paragraph(c, "How can a source become a connected explanation and then a useful practice task? "
                    "Read the whole source, group its consecutive ideas, explain their links, and try a task "
                    "that uses those ideas. A separate source log records what you checked.", MARGIN, top, CONTENT) - 21
    top = note(c, "What our counts mean", "The example log is invented for this demonstration. Each item is listed once "
               "and is either checked against the source or pending. A checked item can still be difficult "
               "to understand. These counts measure the log's coverage, not mastery or learning quality.", top)
    top = section(c, "Meet the symbols before calculating", top)
    top = symbol_table(c, top)
    top = paragraph(c, "N is the total; C and U are its non-overlapping parts. The checked fraction q compares "
                    "C with N. Homework begins a new log with new counts.", MARGIN, top, CONTENT) - 23
    top = section(c, "Follow the source's logical route", top)
    top = paragraph(c, "<b>Slide 1:</b> connect the study actions. <b>Slide 2:</b> understand the count and its fraction. "
                    "<b>Slide 3:</b> identify pending work and choose a next action. Pages 6-7 apply the "
                    "same reasoning to a complete practice question.", MARGIN, top, CONTENT)
    c.showPage()

    top = guide_page(c, 2, "Keep knowledge blocks connected", "Source slide 1 / Read the whole argument before explaining one step.")
    top = section(c, "1. Read: discover the source's question", top)
    top = paragraph(c, "Look through all source pages first. Identify the main question, the starting assumptions "
                    "and the result. Keep page numbers visible so the explanation can be traced back to its source.", MARGIN, top, CONTENT) - 23
    top = section(c, "2. Connect: group consecutive ideas", top)
    top = paragraph(c, "A knowledge block may span several neighbouring pages. Group them because they answer one question, "
                    "not because each contains one formula. Keep the original order and say what one block "
                    "establishes before the next block begins.", MARGIN, top, CONTENT) - 23
    top = note(c, "A transition to say out loud", "We have identified the whole set of listed items. "
               "Next we need to know which of those items were checked. That distinction will let us "
               "calculate a fraction, and the remaining items will guide the next source check.", top)
    top = section(c, "3. Explain: show the missing steps", top)
    top = paragraph(c, "Define unfamiliar concepts before using them. For a calculation, introduce every symbol "
                    "beside its first formula, show one transformation per line and state its reason. "
                    "For an argument, connect a claim to its evidence. For code, show how each step changes the state.", MARGIN, top, CONTENT) - 23
    top = section(c, "4. Practice: reuse the connection", top)
    top = paragraph(c, "Include the entire practice question, its conditions and its subparts. Point to the blocks "
                    "that supply each prerequisite. Then solve and check the task, explaining why the method applies. "
                    "The source log helps us locate unfinished checking; an attempted task gives evidence about reasoning.", MARGIN, top, CONTENT) - 23
    top = paragraph(c, "<b>Next:</b> slide 2 compresses a fraction into one line. Page 3 expands its meaning and "
                    "calculates it without turning the number into a claim about understanding.", MARGIN, top, CONTENT, SMALL)
    c.showPage()

    top = guide_page(c, 3, "Understand the fraction first", "Source slide 2 / The denominator is the whole; the numerator is the chosen part.")
    top = section(c, "1. State the definition and its condition", top)
    top = paragraph(c, "N means distinct listed items; C means items checked against the source; "
                    "q means the checked fraction. We require N greater than zero and C between zero and N. "
                    "Dividing by N asks how much of the whole list belongs to the checked group.", MARGIN, top, CONTENT) - 12
    top = derivation(c, top, [
        (r"q=\frac{C}{N}", "<b>Definition:</b> put the checked count above the fraction bar and the total count below it."),
        (r"q=\frac{6}{8}", "<b>Substitute:</b> this invented log has C = 6 and N = 8."),
        (r"q=\frac{3}{4}", "<b>Simplify:</b> divide both numerator and denominator by 2. The share stays the same."),
        (r"q=0.75", "<b>Divide:</b> three divided by four is 0.75, a number between zero and one."),
        (r"100\,q=75", "<b>Convert to per hundred:</b> multiply the share by 100."),
    ])
    top = note(c, "Interpret the percentage", "The checked fraction is 75%: 6 of the 8 listed items were checked. "
               "A percentage is a share expressed per hundred; this does not imply there were 100 actual items. "
               "The percentage reports source-check coverage, not how well anyone understands the material.", top)
    c.showPage()

    top = guide_page(c, 4, "Connect the checked and pending parts", "Source slide 3 / Derive the link one justified transformation at a time.")
    top = paragraph(c, "N is the total, C is checked and U is pending. Every item belongs to exactly one group, "
                    "so C + U = N and U = N - C. The new symbol r means the <b>pending fraction</b>: "
                    "U divided by N. Both q and r refer to the same positive total N.", MARGIN, top, CONTENT) - 16
    top = derivation(c, top, [
        (r"q+r=\frac{C}{N}+\frac{U}{N}", "<b>1. Use the definitions:</b> q describes the checked group; r describes the pending group."),
        (r"q+r=\frac{C+U}{N}", "<b>2. Add equal-denominator fractions:</b> combine the counts and keep the same whole N."),
        (r"q+r=\frac{C+(N-C)}{N}", "<b>3. Substitute U = N - C:</b> pending items are the total minus checked items."),
        (r"q+r=\frac{N}{N}", "<b>4. Cancel +C with -C:</b> the numerator returns to the full count N."),
        (r"q+r=1", "<b>5. Divide N by itself:</b> this works because N is positive."),
        (r"r=1-q", "<b>6. Subtract q from both sides:</b> the pending share is what remains of the whole."),
    ])
    top = note(c, "Why this connection matters", "For the first log, q is 0.75, so the pending share is 0.25, "
               "or 25%. This conclusion depends on two exclusive statuses covering the same complete list. "
               "It would fail if items were duplicated or if a third status were left out.", top)
    c.showPage()

    top = guide_page(c, 5, "Choose a useful next study action", "Interpretation bridge / Connect the record to explanation and practice.")
    top = section(c, "1. Check the record before using the result", top)
    top = paragraph(c, "Confirm what counts as an item and use that definition consistently. Count each item once. "
                    "Use the same list for N, C and U; do not compare a checked count from one source with "
                    "a total from a different source. An empty list has no defined checked fraction.", MARGIN, top, CONTENT) - 23
    top = note(c, "What the result can and cannot establish", "The 75% result tells us that 6 of 8 listed items "
               "were checked. It does not measure item difficulty, explanation quality or understanding. "
               "A difficult idea and a short definition both count as one item under this simple rule.", top, AMBER)
    top = section(c, "2. Continue the logic in different subjects", top)
    top = paragraph(c, "<b>For an argument:</b> explain how a claim follows from its evidence and identify an assumption.<br/>"
                    "<b>For a procedure:</b> explain why each step is needed and check the result against its conditions.<br/>"
                    "<b>For code:</b> trace a small input, describe the changing state and test a boundary case.<br/>"
                    "<b>For a calculation:</b> identify the model, define symbols, derive the relation and check the units.", MARGIN, top, CONTENT) - 24
    top = section(c, "3. Turn a gap into one concrete task", top)
    top = paragraph(c, "A pending item suggests a source check: locate the passage, verify what it says and then update "
                    "the log. A checked but confusing item suggests an explanation task: state the question, "
                    "show the missing step, and try a small example. These actions address different needs.", MARGIN, top, CONTENT) - 24
    top = paragraph(c, "<b>Connection to homework:</b> the next pages use a new synthetic log. We keep the same definitions "
                    "and show how the earlier fraction and complement relations answer each part.", MARGIN, top, CONTENT, SMALL)
    c.showPage()

    top = guide_page(c, 6, "Read the full question, build a plan", "Integrated practice / The complete original question comes before its solution.")
    top = note(c, "Original authored practice question", HOMEWORK, top, BLUE)
    top = section(c, "1. Reset the example and identify what is given", top)
    top = paragraph(c, "This is a <b>new log</b>: N = 10 and C = 7. The counts from the first log no longer apply. "
                    "U is the pending count, q the checked fraction and r the pending fraction. "
                    "The question guarantees no duplicates and exactly two exclusive statuses.", MARGIN, top, CONTENT) - 21
    top = section(c, "2. Link each subpart to its prerequisite", top)
    top = paragraph(c, "<b>(a)</b> Page 3 defines the checked fraction and percentage.<br/>"
                    "<b>(b)-(c)</b> Page 4 explains the pending count, its fraction and the sum check.<br/>"
                    "<b>(d)</b> Page 5 separates what a count records from what an explanation demonstrates.", MARGIN, top, CONTENT) - 20
    top = section(c, "3. Solve part (a): start with the relation", top)
    top = derivation(c, top, [
        (r"q=\frac{C}{N}", "<b>Choose the definition:</b> the question asks for checked items as a share of the whole list."),
        (r"q=\frac{7}{10}", "<b>Substitute the new counts:</b> use C = 7 and N = 10; do not reuse 6 and 8."),
    ])
    top = paragraph(c, "Continue on page 7: evaluate this fraction, find the pending group and interpret what "
                    "the result means. Every subpart uses a relation already introduced in the lesson.", MARGIN, top, CONTENT, SMALL)
    c.showPage()

    top = guide_page(c, 7, "Complete and interpret the practice", "Parts (a)-(d) / Calculate, check the whole and choose a useful next action.")
    top = section(c, "4. Finish part (a), then find the pending group", top)
    top = derivation(c, top, [
        (r"q=0.7", "<b>(a) Divide 7 by 10:</b> 0.7 is the checked share, equivalent to 70%."),
        (r"U=10-7", "<b>(b) Subtract the checked count from the total:</b> pending items are U = N - C."),
        (r"U=3", "<b>Evaluate:</b> three listed items are still pending."),
        (r"r=\frac{3}{10}", "<b>Use the pending-fraction definition:</b> r = U divided by the same total N."),
        (r"r=0.3", "<b>Divide:</b> the pending share is 0.3, equivalent to 30%."),
        (r"q+r=0.7+0.3", "<b>(c) Substitute both shares:</b> the two groups cover the same whole list."),
        (r"q+r=1", "<b>Add:</b> the shares total one, consistent with the assumptions."),
    ])
    top = note(c, "Part (d): interpret and act", "No. Checking 70% of listed items does not prove understanding. "
               "Choose one checked item, explain how it connects to its preceding idea, then attempt a task "
               "using that connection. Alternatively, verify one pending item against the source and update the log.", top)
    c.showPage()

    top = guide_page(c, 8, "Try a fresh question and explain it", "Retrieval practice / Use the same reasoning with new records, then state its limits.")
    top = note(c, "Try before reading the answer", "Two new synthetic logs use the same item definition. "
               "Log A has 5 listed items and 4 checked; log B has 10 listed items and 6 checked. "
               "(a) Which has more checked items? (b) Which has a larger checked fraction? "
               "(c) Find each pending fraction. (d) Does the larger fraction establish better understanding?", top, BLUE)
    top = section(c, "Separate a count from a fraction", top)
    top = paragraph(c, "<b>(a)</b> Log B has more checked items: 6 is greater than 4. "
                    "<b>(b)</b> Compare fractions because the totals differ. Here q<sub>A</sub> and "
                    "q<sub>B</sub> are the checked fractions of logs A and B; the subscripts label the log.", MARGIN, top, CONTENT) - 12
    top = derivation(c, top, [
        (r"q_A=\frac{4}{5}", "<b>Substitute log A:</b> its checked count is 4 and its total is 5."),
        (r"q_A=0.8", "<b>Divide:</b> A has an 80% checked share."),
        (r"q_B=\frac{6}{10}", "<b>Substitute log B:</b> its checked count is 6 and its total is 10."),
        (r"q_B=0.6", "<b>Divide:</b> B has a 60% checked share. A's fraction is larger, despite its smaller count."),
    ])
    top = section(c, "Reuse the complement and explain the limit", top)
    top = paragraph(c, "<b>(c)</b> Page 4 gives r = 1 - q. A's pending share is 0.2 (20%); B's is 0.4 (40%). "
                    "<b>(d)</b> Neither fraction establishes understanding. These are records of source checks, "
                    "not scores for reasoning. To examine reasoning, explain an idea and attempt a suitable task.", MARGIN, top, CONTENT) - 18
    top = paragraph(c, "<b>Final check:</b> the method needs a positive total, a consistent item definition, "
                    "no duplicate items and two statuses covering the whole. If those conditions change, "
                    "revisit the definition before reusing a formula.", MARGIN, top, CONTENT, SMALL)
    c.showPage()
    c.save()
    return path


def build_spec(portable=True):
    data = {
        "course_code": "STUDY WORKFLOW",
        "course_name": "Connected study workflow - original neutral demonstration",
        "lecture": "Read, connect, explain and practice",
        "file_stem": "study-workflow",
        "source_pdf": "examples/source-slides.pdf" if portable else str(OUT / "source-slides.pdf"),
        "translated_pdf": "examples/translated-slides.pdf" if portable else str(OUT / "translated-slides.pdf"),
        "bilingual_layout": {"page_width": 1190.551, "page_height": 841.89,
                             "annotation_height": 260},
        "labels": {"source_heading": "Source slide - academic English",
                   "translation_heading": "Mirror slide - plain English",
                   "terms_heading": "Vocabulary",
                   "guide_name": "study-guide", "bilingual_name": "slide-companion",
                   "source_footer": "Original neutral demo / slide {page}",
                   "guide_reference_footer": "Study-guide pages {pages}"},
        "bilingual": [
            {"source_page": 1, "title": "Build a connected study route", "guide_pages": "1-2, 5",
             "terms": [["Knowledge block", "Consecutive source ideas answering one shared question."],
                       ["Transition", "The connection from a previous conclusion to the next question."],
                       ["Practice", "A task that uses the ideas just explained."]],
             "notes": [{"label": "Prerequisite bridge", "text": "Read the whole source before teaching its parts. A formula, argument, code trace or procedure belongs in the knowledge block it helps explain. Keep the source order and make each transition explicit."}],
             "homework": [{"label": "Practice connection", "text": "The complete original practice question is on study-guide page 6. Its final part asks you to distinguish a source-check record from evidence about reasoning and to choose one useful next action.", "source": "Original neutral fixture; full question page 6, solution pages 6-7."}]},
            {"source_page": 2, "title": "Check what the source log covers", "guide_pages": "1, 3, 6-7",
             "terms": [["Numerator", "The top number: checked items C."],
                       ["Denominator", "The bottom number: all listed items N, which must be positive."],
                       ["Percentage", "A fraction expressed as an amount per hundred."]],
             "notes": [{"label": "What the symbols and counts mean", "text": "N is the distinct listed count; C is the checked count; q is the checked fraction. The pictured log is synthetic. Its 6 of 8 checked items give 75% source-check coverage, not a score for understanding or learning quality."}],
             "homework": [{"label": "Practice connection", "text": "Part (a) resets the example to N = 10 and C = 7. Use the same definition, substitute the new values, then convert the resulting share to a percentage. Do not carry over 6 and 8.", "source": "Definition page 3; complete question and guided solution pages 6-7."}]},
            {"source_page": 3, "title": "Use the record to choose a next step", "guide_pages": "4-5, 7-8",
             "terms": [["Pending", "A listed item still awaiting its source check; count U."],
                       ["Complement", "What remains of a whole after one part is removed."],
                       ["Subscript", "A label identifying a particular value, such as log A or B."]],
             "notes": [{"label": "Connect the relation to its conditions", "text": "The new symbol r is the pending fraction, U divided by N. The two groups cover the same nonempty list without overlap, so q + r = 1. Page 4 derives the connection one step at a time. A checked item can still need explanation or practice."}],
             "homework": [{"label": "Practice connection", "text": "Parts (b)-(c) find the pending count and fraction, then check that both shares total one. Part (d) interprets the result. Page 8 compares two fresh logs and shows why larger counts and larger fractions answer different questions.", "source": "All public slides, illustrations and questions are independently authored neutral fixtures."}]},
        ],
    }
    path = OUT / "demo-spec.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def normalize_public_pdf_metadata(path):
    """Keep public metadata reproducible, UTC and free of local environment data."""
    titles = {
        "source-slides.pdf": "Connected study workflow: academic English",
        "translated-slides.pdf": "Connected study workflow: plain-English mirror",
        "slide-companion.pdf": "Connected study workflow: matched slide companion",
        "beginner-study-guide.pdf": "A connected study route: beginner study guide",
    }
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.metadata = {
        "/Title": titles[path.name],
        "/Author": "selfcollege-waba",
        "/Subject": "Original neutral public fixture; synthetic counts; no real course or learner data",
        "/Creator": "selfcollege-waba public example builder",
        "/Producer": "selfcollege-waba public example builder",
        "/CreationDate": "D:20000101000000Z",
        "/ModDate": "D:20000101000000Z",
    }
    if "/Metadata" in writer.root_object:
        del writer.root_object["/Metadata"]
    if "/EmbeddedFiles" in writer.root_object.get("/Names", {}):
        raise ValueError("A public example must not include embedded files.")
    with path.open("wb") as stream:
        writer.write(stream)


def make_previews(paths, temporary):
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise RuntimeError("pdftoppm is required to render and inspect every public example page.")
    targets = {}
    for path in paths:
        prefix = temporary / path.stem
        subprocess.run([renderer, "-r", "110", "-png", str(path), str(prefix)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        targets[path.stem] = sorted(temporary.glob(path.stem + "-*.png"))
    previews = OUT / "previews"
    previews.mkdir(exist_ok=True)
    choices = {"comparison.png": targets["slide-companion"][1],
               "explanation.png": targets["beginner-study-guide"][3],
               "practice.png": targets["beginner-study-guide"][5]}
    for destination, source in choices.items():
        image = PILImage.open(source).convert("RGB")
        image.thumbnail((1600, 1800), PILImage.Resampling.LANCZOS)
        image.save(previews / destination)
    # A full contact sheet allows a reviewer to see every page in one artifact.
    rendered = [(key, i + 1, page) for key, pages in targets.items()
                for i, page in enumerate(pages)]
    thumb_w, thumb_h = 300, 440
    sheet = PILImage.new("RGB", (thumb_w * 4, (len(rendered) + 3) // 4 * thumb_h), "#E5EBEB")
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for index, (name, number, page) in enumerate(rendered):
        thumb = PILImage.open(page).convert("RGB")
        thumb.thumbnail((thumb_w - 18, thumb_h - 42), PILImage.Resampling.LANCZOS)
        x, y = (index % 4) * thumb_w, (index // 4) * thumb_h
        sheet.paste(thumb, (x + (thumb_w - thumb.width) // 2, y + 30))
        draw.text((x + 9, y + 10), f"{name} / {number}", fill="#17334D")
    sheet.save(temporary / "contact-sheet.png")
    return targets


def main():
    global OUT
    destination = OUT
    # Render and validate every example before changing the maintained bundle.
    with tempfile.TemporaryDirectory(prefix=".selfcollege-demo-", dir=ROOT.parent) as temp_name:
        temp = Path(temp_name)
        OUT = temp / "examples"
        OUT.mkdir()
        try:
            source = build_slides("source")
            target = build_slides("target")
            guide = build_guide()
            spec = build_spec(portable=False)
            subprocess.run([sys.executable, str(ROOT / "scripts/render_study_pdfs.py"),
                            "--spec", str(spec), "--output-dir", str(temp / "composed")], cwd=ROOT, check=True)
            companion = OUT / "slide-companion.pdf"
            shutil.copyfile(temp / "composed" / "study-workflow_slide-companion.pdf", companion)
            paths = [source, target, companion, guide]
            for public_pdf in paths:
                normalize_public_pdf_metadata(public_pdf)
            previews = make_previews(paths, temp)
            # Keep a complete render set outside version control for real visual QA.
            qa = ROOT / "tmp" / "example-qa"
            qa.mkdir(parents=True, exist_ok=True)
            for page in temp.glob("*.png"):
                shutil.copyfile(page, qa / page.name)
            source_pages = PdfReader(source).pages
            target_pages = PdfReader(target).pages
            assert len(source_pages) == len(target_pages) == 3
            assert all(list(a.mediabox) == list(b.mediabox)
                       for a, b in zip(source_pages, target_pages))
            # Compare all content operators after removing wording operands. This
            # verifies shared drawing/text origins, not merely equal page boxes.
            def geometry(page):
                return [(repr(operands) if op not in (b"Tj", b"TJ") else "wording", op)
                        for operands, op in ContentStream(page.get_contents(), page.pdf).operations]
            assert all(geometry(a) == geometry(b) for a, b in zip(source_pages, target_pages))
            report = {"authorship": "Original demo authored for selfcollege-waba; no private course content",
                      "slide_layout": "Shared renderer, fixed text origins, identical workflow, ledger and formulas",
                      "content_operator_geometry_equal": True,
                      "pdf_pages": {path.name: len(PdfReader(path).pages) for path in paths},
                      "rendered_pages": sum(len(items) for items in previews.values()),
                      "homework": "Complete original question and all conditions on guide page 6; full solution pages 6-7",
                      "formula_rendering": "Vector glyph outlines and horizontal fraction rules; no formula bitmap",
                      "visual_review_status": "pending for regenerated outputs",
                      "visual_review_required": True}
            (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")

            build_spec(portable=True)
            generated = sorted(path for path in OUT.rglob("*") if path.is_file())
            publications = [{"path": str(destination / path.relative_to(OUT)), "stage": str(path)}
                            for path in generated]
            for item in publications:
                Path(item["path"]).parent.mkdir(parents=True, exist_ok=True)
            publish_outputs(publications, [], temp)
        finally:
            OUT = destination
    print(json.dumps({"outputs": [str(destination / path.name) for path in paths],
                      "qa_directory": str(qa.relative_to(ROOT)), **report}, indent=2))


if __name__ == "__main__":
    main()
