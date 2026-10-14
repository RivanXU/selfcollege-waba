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
from pypdf import PdfReader
from pypdf.generic import ContentStream
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from render_study_pdfs import MathFormula

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


def equation(c, latex, center_x, center_y, fontsize=25, max_width=None):
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
    c.drawString(MARGIN, 25, "Constant acceleration / An authored teaching example")
    c.drawRightString(W - MARGIN, 25, f"{number:02d} / 08")
    c.bookmarkPage(f"guide-{number}")
    c.addOutlineEntry(title, f"guide-{number}")
    return top


def symbol_table(c, top):
    rows = [
        (r"v_0", "Initial velocity", "How fast the cart moves at time zero.", r"\frac{\mathrm{m}}{\mathrm{s}}"),
        ("a", "Acceleration", "How much velocity changes each second.", r"\frac{\mathrm{m}}{\mathrm{s}^{2}}"),
        ("t", "Elapsed time", "Time since the motion starts.", r"\mathrm{s}"),
        ("v(t)", "Velocity at time t", "How fast the cart moves at the chosen time.", r"\frac{\mathrm{m}}{\mathrm{s}}"),
        (r"\Delta x", "Displacement", "Final position minus starting position.", r"\mathrm{m}"),
    ]
    columns = [MARGIN + 11, MARGIN + 72, MARGIN + 212, W - MARGIN - 48]
    c.setFillColor(NAVY)
    c.roundRect(MARGIN, top - 30, CONTENT, 30, 4, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 9.3)
    c.setFillColor(colors.white)
    for x, text in zip(columns, ["Symbol", "Quantity", "Meaning", "Unit"]):
        c.drawString(x, top - 19, text)
    row_top = top - 30
    for i, row in enumerate(rows):
        c.setFillColor(colors.white if i % 2 == 0 else PALE)
        c.rect(MARGIN, row_top - 44, CONTENT, 44, fill=1, stroke=0)
        c.setFillColor(INK)
        formula = MathFormula(row[0], 11)
        formula.drawOn(c, columns[0], row_top - 22 - formula.height / 2)
        paragraph(c, row[1], columns[1], row_top - 10, 128, SMALL)
        paragraph(c, row[2], columns[2], row_top - 8, 225, SMALL)
        formula = MathFormula(row[3], 11)
        formula.drawOn(c, columns[3] + 12 - formula.width / 2, row_top - 22 - formula.height / 2)
        row_top -= 44
    return row_top - 18


def graph(c, x, y, width, height, shade=False, detailed=True):
    """Identical source/target graph geometry; no translated image redraw."""
    left, bottom = x + 40, y + 34
    gw, gh = width - 65, height - 70
    c.setStrokeColor(LINE)
    c.setLineWidth(.8)
    for velocity in (2, 6, 10, 14):
        yy = bottom + gh * velocity / 16
        c.line(left, yy, left + gw, yy)
    start = bottom + gh * 2 / 16
    end = bottom + gh * 14 / 16
    if shade:
        path = c.beginPath()
        path.moveTo(left, bottom)
        path.lineTo(left, start)
        path.lineTo(left + gw, end)
        path.lineTo(left + gw, bottom)
        path.close()
        c.setFillColor(colors.HexColor("#D9EEE7"))
        c.drawPath(path, fill=1, stroke=0)
        c.setStrokeColor(TEAL)
        c.setDash(4, 4)
        c.line(left, start, left + gw, start)
        c.setDash()
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.2)
    c.line(left, bottom, left + gw + 8, bottom)
    c.line(left, bottom, left, bottom + gh + 7)
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(left + gw / 2, y + 4, "Elapsed time t (s)")
    c.saveState()
    c.translate(x + 8, bottom + gh / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, "Velocity v (m/s)")
    c.restoreState()
    for time in range(5):
        xx = left + gw * time / 4
        c.drawCentredString(xx, bottom - 15, str(time))
    for velocity in (0, 2, 6, 10, 14):
        c.drawRightString(left - 8, bottom + gh * velocity / 16 - 3, str(velocity))
    c.setStrokeColor(TEAL)
    c.setLineWidth(3)
    c.line(left, start, left + gw, end)
    c.setFillColor(TEAL)
    c.circle(left, start, 3.3, fill=1, stroke=0)
    c.circle(left + gw, end, 3.3, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left + 9, start + 9, "2 m/s")
    c.drawRightString(left + gw - 5, end + 11, "14 m/s")
    if shade and detailed:
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 9.4)
        c.drawCentredString(left + gw * .56, bottom + gh * .35, "Triangle: 24 m")
        if gh >= 120:
            c.drawCentredString(left + gw * .52, bottom + 8, "Rectangle: 8 m")
        else:
            c.drawString(left + 8, bottom + gh + 13, "Rectangle 8 m + triangle 24 m")


def slide_text(c, lines, x, y, font_size=18, leading=27, color=INK, bold=False):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
    for i, text in enumerate(lines):
        c.drawString(x, y - i * leading, text)


SLIDE_COPY = {
    "source": [
        {"title": "From acceleration to velocity",
         "intro": ["Constant acceleration produces equal velocity changes", "over equal time intervals."],
         "body": ["Initial velocity: 2 m/s", "Constant acceleration: 3 m/s per second", "Observation interval: 0 to 4 s"],
         "connection": "The line's slope is acceleration; its starting height is initial velocity."},
        {"title": "Displacement is the area under velocity",
         "intro": ["For this motion, the velocity-time region is a trapezoid.", "Its area equals the displacement over the interval."],
         "body": ["Average velocity is the mean of the endpoints.", "Multiply average velocity by elapsed time."],
         "connection": "The graph converts a velocity calculation into a position change."},
        {"title": "Build the constant-acceleration equation",
         "intro": ["Substitute the velocity expression into the area relation.", "Distribute the elapsed-time factor over both terms."],
         "body": ["Existing motion contributes the rectangular area.", "Acceleration contributes the additional triangular area."],
         "connection": "Every term has units of length; this model requires constant acceleration."},
    ],
    "target": [
        {"title": "From acceleration to velocity",
         "intro": ["When acceleration stays the same, velocity changes", "by the same amount each second."],
         "body": ["Start at a velocity of 2 m/s", "Add 3 m/s of velocity every second", "Watch the first 4 seconds of motion"],
         "connection": "The slope tells us how velocity changes; the line starts at the initial velocity."},
        {"title": "Displacement is the area under velocity",
         "intro": ["The space below this velocity line is a trapezoid.", "Its area tells us how far the cart moves forward."],
         "body": ["Average velocity is halfway between start and finish.", "Multiply that average by the number of seconds."],
         "connection": "The graph links how fast the cart moves to how its position changes."},
        {"title": "Build the constant-acceleration equation",
         "intro": ["Put the velocity formula into the formula for the area.", "Then multiply time into each part of the expression."],
         "body": ["The starting velocity gives the rectangle's area.", "The extra velocity gives the triangle's area."],
         "connection": "Both parts give metres; use this formula only while acceleration stays constant."},
    ],
}


def build_slides(kind):
    path = OUT / ("source-slides.pdf" if kind == "source" else "translated-slides.pdf")
    c = canvas.Canvas(str(path), pagesize=(SLIDE_W, SLIDE_H), invariant=1)
    c.setTitle("Constant acceleration: " + ("academic English" if kind == "source" else "plain-English mirror"))
    c.setAuthor("RivanXU / selfcollege-waba")
    c.setSubject("Original public example; identical source and mirror geometry")
    for index, copy in enumerate(SLIDE_COPY[kind], 1):
        c.setFillColor(PAPER)
        c.rect(0, 0, SLIDE_W, SLIDE_H, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.rect(0, SLIDE_H - 9, SLIDE_W, 9, fill=1, stroke=0)
        slide_text(c, ["MOTION / ORIGINAL PUBLIC LESSON"], 52, 502, 10, color=TEAL, bold=True)
        slide_text(c, [copy["title"]], 52, 461, 27.5, color=NAVY, bold=True)
        slide_text(c, copy["intro"], 52, 420, 18, leading=27)
        c.setStrokeColor(LINE)
        c.line(52, 363, 908, 363)
        if index == 1:
            slide_text(c, copy["body"], 56, 331, 17, leading=30)
            equation(c, r"v(t)=v_0+a\,t", 271, 202, 29, 400)
            slide_text(c, ["v0 = initial velocity    a = acceleration    t = time"], 56, 142, 12, color=MUTED)
            graph(c, 530, 128, 372, 225)
        elif index == 2:
            slide_text(c, copy["body"], 56, 331, 17, leading=30)
            equation(c, r"\bar{v}=\frac{v_0+v(t)}{2}", 271, 230, 27, 410)
            equation(c, r"\Delta x=\bar{v}\,t", 271, 157, 27, 410)
            slide_text(c, ["v-bar = average velocity    delta x = displacement"], 56, 119, 11.4, color=MUTED)
            graph(c, 530, 128, 372, 225, shade=True)
        else:
            equation(c, r"\Delta x=\frac{v_0+(v_0+a\,t)}{2}\,t", 479, 315, 29, 820)
            equation(c, r"\Delta x=v_0\,t+\frac{1}{2}a\,t^2", 479, 229, 36, 820)
            slide_text(c, copy["body"], 56, 160, 17, leading=29)
            slide_text(c, ["delta x = position change    v0 = initial velocity    a = acceleration    t = elapsed time"], 56, 112, 11.4, color=MUTED)
        c.setFillColor(PALE)
        c.roundRect(52, 51, 856, 52, 6, fill=1, stroke=0)
        slide_text(c, [copy["connection"]], 66, 71, 12.8, color=TEAL)
        slide_text(c, ["Constant acceleration / v0 = 2 m/s, a = 3 m/s2, t = 4 s"], 52, 26, 9, color=MUTED)
        slide_text(c, [f"0{index} / 03"], 866, 26, 9, color=MUTED)
        c.showPage()
    c.save()
    return path


HOMEWORK = ("A cart moves in a straight line with an initial velocity of 2 m/s. "
            "It has a constant acceleration of 3 m/s<super>2</super> in the same direction "
            "for 4 s. (a) Find its velocity after 4 s. (b) Find its displacement during "
            "these 4 s. (c) Verify the displacement using the area under a velocity-time graph.")


def build_guide():
    path = OUT / "beginner-study-guide.pdf"
    c = canvas.Canvas(str(path), pagesize=(W, H), invariant=1)
    c.setTitle("From motion to a solved assignment: beginner study guide")
    c.setAuthor("RivanXU / selfcollege-waba")
    c.setSubject("Original physics example with symbol introduction, justified derivation and integrated homework")

    top = guide_page(c, 1, "Understand the model first", "Source slides 1-3 / No previous physics course is assumed.")
    top = section(c, "The question behind every equation", top)
    top = paragraph(c, "A cart is already moving. We know how its velocity changes. "
                    "How can we work out both its final velocity and its change in position?", MARGIN, top, CONTENT) - 21
    top = note(c, "Our assumptions", "The motion is along one straight line. Acceleration stays constant. "
               "We choose the forward direction as positive. The cart keeps moving forward during the interval.", top)
    top = section(c, "Meet each symbol before using it", top)
    top = symbol_table(c, top)
    top = paragraph(c, "The subscript 0 means <b>at the start</b>. The brackets in v(t) mean "
                    "<b>the velocity evaluated at time t</b>; they do not mean multiplication. "
                    "The Greek letter delta means <b>change</b>.", MARGIN, top, CONTENT) - 23
    top = section(c, "The logical route through the lesson", top)
    top = paragraph(c, "<b>Acceleration</b> tells us the velocity change. Add the starting velocity to get "
                    "<b>final velocity</b>. The <b>velocity-time graph</b> then gives an area, "
                    "which is <b>displacement</b>. These links solve the assignment on pages 6-7.", MARGIN, top, CONTENT)
    c.showPage()

    top = guide_page(c, 2, "How acceleration changes velocity", "Source slide 1 / First understand the definition, then rearrange it.")
    top = section(c, "1. A rate means change divided by time", top)
    top = paragraph(c, "Acceleration is the change in velocity per unit of time. "
                    "For constant acceleration, compare the start with a later time t.", MARGIN, top, CONTENT)
    equation(c, r"a=\frac{v(t)-v_0}{t}", W / 2, top - 41, 29)
    top -= 86
    top = paragraph(c, "The numerator v(t) - v<sub>0</sub> is the velocity change. The denominator t "
                    "is elapsed time; this rate equation requires t greater than zero. "
                    "Here a is acceleration, v(t) is the later velocity and v<sub>0</sub> is the starting velocity. "
                    "An acceleration of 3 m/s<super>2</super> adds 3 m/s of velocity every second.", MARGIN, top, CONTENT) - 23
    top = section(c, "2. Undo the division, then add the starting value", top)
    equation(c, r"a\,t=v(t)-v_0", W / 2, top - 23, 26)
    top = paragraph(c, "Multiply both sides by t. This preserves equality and turns a rate "
                    "into the total velocity change over t seconds.", MARGIN, top - 54, CONTENT) - 13
    equation(c, r"v(t)=v_0+a\,t", W / 2, top - 22, 28)
    top = paragraph(c, "Add v<sub>0</sub> to both sides. Final velocity equals the "
                    "<b>starting velocity plus the velocity gained</b>.", MARGIN, top - 54, CONTENT) - 24
    top = section(c, "3. Insert the values only after the relation is clear", top)
    equation(c, r"v(4)=2+3\times4=14\ \mathrm{m\,s^{-1}}", W / 2, top - 28, 26)
    top -= 62
    top = note(c, "Read the answer in words", "The cart starts at 2 m/s and gains 12 m/s over 4 s. "
               "Its velocity at the end is 14 m/s. The gained velocity is not the final velocity.", top)
    c.showPage()

    top = guide_page(c, 3, "Turn velocity into displacement", "Source slide 2 / The graph explains why the next formula works.")
    top = section(c, "1. Why the area has the right meaning", top)
    top = paragraph(c, "At constant velocity, displacement equals velocity times time: the rectangle's area. "
                    "For changing velocity, add thin time strips; the total area gives displacement.", MARGIN, top, CONTENT) - 6
    graph(c, MARGIN + 44, top - 132, CONTENT - 88, 152, shade=True)
    top -= 154
    top = section(c, "2. A straight line makes the average easy", top)
    top = paragraph(c, "Constant acceleration makes velocity change linearly. The average velocity "
                    "over this interval is halfway between the two endpoints. "
                    "The new symbol v-bar denotes that average; v<sub>0</sub> and v(t) are the start and end velocities.", MARGIN, top, CONTENT)
    equation(c, r"\bar{v}=\frac{v_0+v(t)}{2}=\frac{2+14}{2}=8\ \mathrm{m\,s^{-1}}", W / 2, top - 40, 24)
    top -= 89
    top = section(c, "3. The average connects velocity to position", top)
    equation(c, r"\Delta x=\bar{v}\,t=8\times4=32\ \mathrm{m}", W / 2, top - 23, 25)
    top = paragraph(c, "The whole area equals a rectangle at the average height: 8 m/s for 4 s. "
                    "Delta x means displacement and t means elapsed time. Velocity multiplied by time gives metres.", MARGIN, top - 54, CONTENT) - 17
    top = note(c, "Distance and displacement", "Displacement is a signed position change. Distance is total path length. "
               "They have the same magnitude here because the cart never reverses direction.", top, BLUE)
    c.showPage()

    top = guide_page(c, 4, "Derive the displacement equation", "Source slide 3 / Each line follows from a reason, rather than a rule to memorise.")
    top = section(c, "1. Connect the two relations we already know", top)
    top = paragraph(c, "Page 3 gave displacement = average velocity multiplied by time. "
                    "Page 2 gave final velocity = initial velocity + acceleration multiplied by time. "
                    "Here delta x is displacement, v<sub>0</sub> is starting velocity, v(t) is final velocity, "
                    "a is acceleration and t is elapsed time.", MARGIN, top, CONTENT)
    equation(c, r"\Delta x=\frac{v_0+v(t)}{2}\,t", W / 2, top - 37, 27)
    top -= 80
    top = section(c, "2. Replace the final velocity with its expression", top)
    equation(c, r"\Delta x=\frac{v_0+(v_0+a\,t)}{2}\,t", W / 2, top - 30, 26)
    top = paragraph(c, "Substitution is valid because v(t) and v<sub>0</sub> + a t are equal. "
                    "The brackets keep that whole replacement together.", MARGIN, top - 63, CONTENT) - 21
    top = section(c, "3. Combine like terms, then distribute the time", top)
    equation(c, r"\Delta x=\frac{2v_0+a\,t}{2}\,t=v_0\,t+\frac{1}{2}a\,t^2", W / 2, top - 36, 26)
    top = paragraph(c, "The two copies of v<sub>0</sub> combine to 2v<sub>0</sub>. "
                    "Divide each numerator term by 2, then multiply each term by t. "
                    "The acceleration term contains t multiplied by t, which is t<super>2</super>.", MARGIN, top - 74, CONTENT) - 22
    top = note(c, "Where the one-half comes from", "On page 3's graph, v<sub>0</sub> t is the rectangle. "
               "The extra velocity grows from zero to a t, so its region is a triangle. "
               "A triangle has half the area of a rectangle with the same base and height.", top)
    c.showPage()

    top = guide_page(c, 5, "Check the model and the units", "Prerequisite bridge / Units carry meaning and expose mistakes before the answer is submitted.")
    top = section(c, "1. Read each unit as a relationship", top)
    top = paragraph(c, "Metres measure displacement. Seconds measure elapsed time. "
                    "Velocity is metres per second: distance for each second of motion. "
                    "Acceleration is metres per second squared: velocity change for each second.", MARGIN, top, CONTENT) - 14
    equation(c, r"[v]=\frac{\mathrm{m}}{\mathrm{s}}\qquad[a]=\frac{\mathrm{m}}{\mathrm{s}^{2}}\qquad[t]=\mathrm{s}", W / 2, top - 32, 27)
    top = paragraph(c, "The square brackets here mean <b>the unit of the quantity</b>, not a new operation "
                    "on the cart. This notation is only for checking dimensions.", MARGIN, top - 69, CONTENT) - 23
    top = section(c, "2. Check each term of the equation separately", top)
    equation(c, r"\frac{\mathrm{m}}{\mathrm{s}}\,\mathrm{s}+\frac{\mathrm{m}}{\mathrm{s}^2}\,\mathrm{s}^2=\mathrm{m}+\mathrm{m}", W / 2, top - 26, 25)
    top = paragraph(c, "Both terms describe a length, so adding them makes sense. "
                    "The squared time cancels the squared seconds in acceleration's unit. "
                    "One-half has no unit; it changes the amount, not the kind of quantity.", MARGIN, top - 63, CONTENT) - 23
    top = note(c, "A mistake the units can reveal", "If you forget to square t, the acceleration term "
               "has units of m/s. You cannot add that velocity to a displacement in metres. "
               "Checking units does not prove every arithmetic step, but it catches this structural error.", top, AMBER)
    top = section(c, "3. Check whether the assumptions still fit", top)
    top = paragraph(c, "The endpoint-average relation requires a straight velocity-time line, "
                    "which follows from constant acceleration. Positive velocity throughout this interval "
                    "means the cart moves forward without reversing. These facts explain both the formula "
                    "and the match between distance and displacement.", MARGIN, top, CONTENT) - 23
    top = paragraph(c, "<b>A common trap:</b> final velocity times time gives 56 m. "
                    "That assumes the cart was already moving at 14 m/s throughout all four seconds. "
                    "Use average velocity over the interval instead.", MARGIN, top, CONTENT, SMALL)
    c.showPage()

    top = guide_page(c, 6, "Read the assignment, build a plan", "Integrated homework / The full question is included before any solution.")
    top = note(c, "Original authored homework - exact question", HOMEWORK, top, BLUE)
    top = section(c, "1. Translate the sentence into the model", top)
    top = paragraph(c, "<b>Given:</b> v<sub>0</sub> = 2 m/s, a = 3 m/s<super>2</super>, t = 4 s. "
                    "Both velocity and acceleration point forward, so all three values are positive. "
                    "<b>Find:</b> v(4), displacement delta x, and an independent graph check.", MARGIN, top, CONTENT) - 22
    top = section(c, "2. Choose the lesson link needed for each part", top)
    top = paragraph(c, "<b>Part (a), velocity:</b> use page 2, starting value + change.<br/>"
                    "<b>Part (b), displacement:</b> use page 4, rectangle + triangle.<br/>"
                    "<b>Part (c), check:</b> use page 3, area under the velocity-time line.", MARGIN, top, CONTENT) - 24
    top = section(c, "3. Solve part (a) one action at a time", top)
    equation(c, r"v(4)=v_0+a\,t", W / 2, top - 24, 26)
    top = paragraph(c, "Write the relationship first. It matches part (a) because it predicts "
                    "velocity from the initial velocity and its change.", MARGIN, top - 54, CONTENT) - 13
    equation(c, r"a\,t=3\times4=12\ \mathrm{m\,s^{-1}}", W / 2, top - 23, 25)
    top = paragraph(c, "Multiply acceleration by elapsed time to find the velocity gained. "
                    "Then add the initial 2 m/s.", MARGIN, top - 54, CONTENT) - 13
    equation(c, r"v(4)=2+12=14\ \mathrm{m\,s^{-1}}", W / 2, top - 22, 26)
    top -= 57
    top = paragraph(c, "<b>Connection:</b> the final 14 m/s supplies the graph's endpoint for part (c). "
                    "Part (b) uses the displacement equation; the graph checks it.", MARGIN, top, CONTENT)
    c.showPage()

    top = guide_page(c, 7, "Complete and check the assignment", "Homework parts (b) and (c) / Connect calculation, graph and physical meaning.")
    top = section(c, "4. Solve part (b): calculate the two contributions", top)
    equation(c, r"\Delta x=v_0\,t+\frac{1}{2}a\,t^2", W / 2, top - 25, 28)
    top = paragraph(c, "Here delta x is displacement, v<sub>0</sub> initial velocity, a acceleration and t time. "
                    "The terms separate starting motion from the extra motion caused by acceleration.", MARGIN, top - 59, CONTENT) - 12
    equation(c, r"v_0\,t=2\times4=8\ \mathrm{m}", W / 2, top - 21, 25)
    equation(c, r"\frac{1}{2}a\,t^2=\frac{1}{2}\times3\times4^2=24\ \mathrm{m}", W / 2, top - 77, 25)
    top = paragraph(c, "Square time first: 4<super>2</super> = 16. Then multiply by 3 and divide by 2. "
                    "Finally add the two contributions: 8 + 24 = <b>32 m</b>.", MARGIN, top - 114, CONTENT) - 24
    top = section(c, "5. Solve part (c): verify with the graph", top)
    top = paragraph(c, "Draw the line from (0 s, 2 m/s) to (4 s, 14 m/s) and split at 2 m/s. "
                    "Here A means the area under the graph; its subscript names the shape.", MARGIN, top, CONTENT) - 8
    equation(c, r"A_{\mathrm{rectangle}}=4\times2=8\ \mathrm{m}", W / 2, top - 24, 24)
    equation(c, r"A_{\mathrm{triangle}}=\frac{1}{2}\times4\times(14-2)=24\ \mathrm{m}", W / 2, top - 82, 24)
    top = paragraph(c, "The triangle's height is the <b>increase</b> in velocity: 14 - 2 = 12 m/s. "
                    "The total graph area is 8 + 24 = 32 m, agreeing with part (b).", MARGIN, top - 121, CONTENT) - 20
    top = note(c, "Interpret the complete answer", "After 4 s, the cart moves at 14 m/s and is 32 m forward "
               "of its starting point. This is reasonable: its average velocity is 8 m/s, between 2 and 14; "
               "8 m/s multiplied by 4 s gives the same 32 m.", top)
    c.showPage()

    top = guide_page(c, 8, "Try it, explain it, check it", "Retrieval practice / A new question tests transfer rather than copying the worked answer.")
    top = note(c, "Try before reading the answer", "A cart starts at 1 m/s and accelerates forward at "
               "2 m/s<super>2</super> for 3 s. Find its final velocity and displacement. "
               "Explain why one-half appears in the displacement equation, then check the graph area.", top, BLUE)
    top = section(c, "Use the same chain with new numbers", top)
    top = paragraph(c, "<b>Choose:</b> v<sub>0</sub> = 1 m/s, a = 2 m/s<super>2</super>, t = 3 s. "
                    "<b>Predict:</b> final velocity should be greater than 1 m/s because acceleration is forward.", MARGIN, top, CONTENT) - 6
    equation(c, r"v(3)=1+2\times3=7\ \mathrm{m\,s^{-1}}", W / 2, top - 29, 25)
    equation(c, r"\Delta x=1\times3+\frac{1}{2}\times2\times3^2=3+9=12\ \mathrm{m}", W / 2, top - 94, 24)
    top = paragraph(c, "The graph rectangle is 3 m; the triangle is 9 m. The triangle has half "
                    "a rectangle's area because the extra velocity grows from zero to 6 m/s.", MARGIN, top - 133, CONTENT) - 22
    top = section(c, "An independent check with average velocity v-bar", top)
    equation(c, r"\bar{v}=\frac{1+7}{2}=4\ \mathrm{m\,s^{-1}}\quad\Rightarrow\quad\Delta x=4\times3=12\ \mathrm{m}", W / 2, top - 35, 24)
    top -= 82
    top = note(c, "Explain the logic without looking at a formula", "Acceleration gives the velocity change. "
               "Add the starting velocity to get the final value. With linear change, average the endpoints. "
               "Multiply that average by time to obtain displacement.", top)
    top = paragraph(c, "<b>Model limits:</b> varying acceleration can invalidate endpoint averaging. "
                    "A reversal makes distance differ from signed displacement. "
                    "Check both assumptions before reusing the formula.", MARGIN, top, CONTENT)
    c.showPage()
    c.save()
    return path


def build_spec():
    data = {
        "course_code": "PHYSICS DEMO",
        "course_name": "Constant acceleration - original public lesson",
        "lecture": "From a model to a solved assignment",
        "file_stem": "motion",
        "source_pdf": "examples/source-slides.pdf",
        "translated_pdf": "examples/translated-slides.pdf",
        "bilingual_layout": {"page_width": 1190.551, "page_height": 841.89,
                             "annotation_height": 260},
        "labels": {"source_heading": "Source slide - academic English",
                   "translation_heading": "Mirror slide - plain English",
                   "terms_heading": "Vocabulary",
                   "guide_name": "study-guide", "bilingual_name": "slide-companion",
                   "source_footer": "Original authored demo / slide {page}",
                   "guide_reference_footer": "Study-guide pages {pages}"},
        "bilingual": [
            {"source_page": 1, "title": "From acceleration to velocity", "guide_pages": "1-2, 6",
             "terms": [["Initial", "At the start; v0 is velocity at time zero."],
                       ["Rate", "Change per unit of time."],
                       ["Slope", "Change in graph height divided by change in time."]],
             "notes": [{"label": "Prerequisite bridge", "text": "A subscript identifies a particular value. The 0 in v0 labels the start; it does not multiply v. Acceleration of 3 m/s2 adds 3 m/s of velocity each second."}],
             "homework": [{"label": "Homework connection", "text": "For part (a), first calculate the gain a t = 12 m/s, then add the starting 2 m/s. The endpoint 14 m/s also feeds the graph check in part (c).", "source": "Full authored question and guided solution: study-guide pages 6-7."}]},
            {"source_page": 2, "title": "Displacement is the area under velocity", "guide_pages": "3, 7",
             "terms": [["Displacement", "Final position minus starting position; it is signed."],
                       ["Average velocity", "The constant velocity producing the same displacement."],
                       ["Trapezoid", "A four-sided region with one pair of parallel sides."]],
             "notes": [{"label": "Why this relation follows", "text": "Velocity times a short time interval gives a small displacement. Add these strips to get the area. Since the velocity line is straight, its average height is halfway between the endpoint heights."}],
             "homework": [{"label": "Homework connection", "text": "Part (c) splits the shaded region into an 8 m rectangle and a 24 m triangle. Their sum checks part (b). Distance equals forward displacement here because the cart does not reverse.", "source": "Original authored graph; study-guide pages 3 and 7."}]},
            {"source_page": 3, "title": "Build the constant-acceleration equation", "guide_pages": "4-5, 7-8",
             "terms": [["Substitution", "Replace a quantity with an expression equal to it."],
                       ["Distribute", "Multiply every term inside a sum by the outside factor."],
                       ["Dimension", "The physical kind of a quantity, such as length or time."]],
             "notes": [{"label": "The new notation and the one-half", "text": "Delta x is change in position; t squared is time multiplied by itself. The one-half comes from the triangular extra area, not from an arbitrary instruction to divide the final answer."}],
             "homework": [{"label": "Homework connection", "text": "Part (b) separates starting-motion displacement, 8 m, from acceleration's extra 24 m. Both terms must have units of metres. The new practice on page 8 checks whether the reasoning transfers.", "source": "All lesson text and questions are independently authored for this repository."}]},
        ],
    }
    path = OUT / "demo-spec.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


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
               "practice.png": targets["beginner-study-guide"][6]}
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
    OUT.mkdir(exist_ok=True)
    source = build_slides("source")
    target = build_slides("target")
    guide = build_guide()
    spec = build_spec()
    with tempfile.TemporaryDirectory(prefix="selfcollege-demo-") as temp_name:
        temp = Path(temp_name)
        subprocess.run([sys.executable, str(ROOT / "scripts/render_study_pdfs.py"),
                        "--spec", str(spec), "--output-dir", str(temp)], cwd=ROOT, check=True)
        companion = OUT / "slide-companion.pdf"
        shutil.copyfile(temp / "motion_slide-companion.pdf", companion)
        paths = [source, target, companion, guide]
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
                  "slide_layout": "Shared renderer, fixed text origins, identical graphs and formulas",
                  "content_operator_geometry_equal": True,
                  "pdf_pages": {path.name: len(PdfReader(path).pages) for path in paths},
                  "rendered_pages": sum(len(items) for items in previews.values()),
                  "homework": "Exact authored question embedded on study-guide page 6; solution pages 6-7",
                  "formula_rendering": "Vector glyph outlines and horizontal fraction rules; no formula bitmap",
                  "visual_review_status": "pending for regenerated outputs",
                  "visual_review_required": True}
        (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"outputs": [str(path.relative_to(ROOT)) for path in paths],
                          "qa_directory": str(qa.relative_to(ROOT)), **report}, indent=2))


if __name__ == "__main__":
    main()
