# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
r"""Explicit, vector-only mathematics inside guarded ReportLab paragraphs.

The input protocol is only ``\(LaTeX\)``.  User markup is validated before
trusted placeholders are generated.  Native image-fragment *geometry* supplies
atomic width, baseline and line reflow; its private payload draws vector paths
and never constructs an image or opens a resource.
"""
from dataclasses import dataclass
import math

from matplotlib.ft2font import LoadFlags
from matplotlib.path import Path as MathPath
from reportlab.lib.abag import ABag
from reportlab.platypus import Paragraph
from reportlab.platypus.paragraph import paraFontSizeHeightOffset


def inline_parts(text):
    """Return (is_math, content) parts; escaped delimiters stay ordinary text."""
    text = str(text)
    parts, ordinary, expression = [], [], None
    pos = 0
    while pos < len(text):
        if text[pos] != '\\':
            (ordinary if expression is None else expression).append(text[pos])
            pos += 1
            continue
        end = pos
        while end < len(text) and text[end] == '\\':
            end += 1
        count = end - pos
        target = ordinary if expression is None else expression
        if end == len(text) or text[end] not in '()' or count % 2 == 0:
            target.append(text[pos:end])
            pos = end
            continue
        target.append('\\' * (count - 1))
        delimiter = text[end]
        if delimiter == '(':
            if expression is not None:
                raise ValueError('Nested inline math delimiters are not allowed.')
            parts.append((False, ''.join(ordinary)))
            ordinary, expression = [], []
        else:
            if expression is None:
                raise ValueError('Inline math closing delimiter has no opening delimiter.')
            latex = ''.join(expression)
            if not latex.strip():
                raise ValueError('Inline math must contain a LaTeX expression.')
            parts.append((True, latex))
            expression = None
        pos = end + 1
    if expression is not None:
        raise ValueError('Inline math opening delimiter has no closing delimiter.')
    parts.append((False, ''.join(ordinary)))
    return parts


def glyph_bounds(parsed):
    """Actual, unhinted glyph/rule extents relative to MathText's baseline."""
    bounds = []
    for glyph in parsed.glyphs:
        font, size, char, x, y = glyph[0], glyph[1], glyph[2], glyph[-2], glyph[-1]
        font.set_size(size, 72)
        font.load_char(char, flags=LoadFlags.NO_HINTING)
        vertices, codes = font.get_path()
        box = MathPath(vertices, codes).get_extents()
        if all(math.isfinite(float(v)) for v in box.extents):
            bounds.append((float(x + box.xmin), float(y + box.ymin),
                           float(x + box.xmax), float(y + box.ymax)))
    bounds.extend((float(x), float(y), float(x + width), float(y + height))
                  for x, y, width, height in parsed.rects)
    if not bounds:
        raise ValueError('Inline math must contain a visible mathematical glyph.')
    return (min(b[0] for b in bounds), min(b[1] for b in bounds),
            max(b[2] for b in bounds), max(b[3] for b in bounds))


@dataclass(frozen=True)
class _VectorMath:
    formula: object
    bounds: tuple
    width: float
    height: float
    bottom: float
    left: float
    color: object

    @classmethod
    def create(cls, formula, color):
        bounds = glyph_bounds(formula.parsed)
        xmin, ymin, xmax, ymax = bounds
        # A thin horizontal gap lets mathematics read naturally beside Chinese;
        # authored spaces still belong to the prose and remain untouched.
        gap = formula.font_size * .08
        safety = formula.font_size * .03
        left_bearing = min(0., xmin)
        width = max(float(formula.parsed.width), xmax) - left_bearing + 2 * gap
        return cls(formula, bounds, width, ymax - ymin + 2 * safety,
                   ymin - safety, gap - left_bearing, color)

    def draw(self, canvas, x, y, width, height):
        if not (math.isclose(width, self.width) and math.isclose(height, self.height)):
            raise ValueError('Inline formula size must be preserved during drawing.')
        self.formula.draw_at_baseline(canvas, x + self.left, y - self.bottom,
                                      text_color=self.color)


class InlineMathParagraph(Paragraph):
    """Paragraph whose internal inline payloads draw MathFormula vector paths."""
    def _get_split_blParaFunc(self):
        if self.style.wordWrap == 'CJK' and self.blPara.kind == 1:
            return self._split_inline_lines
        return super()._get_split_blParaFunc()

    def _split_inline_lines(self, bl_para, start, stop):
        fragments = []
        lines = bl_para.lines[start:stop]
        for line in lines:
            # Native split mutates its original line objects; independent copies
            # keep rewrapping one split portion from altering another portion.
            fragments.extend(fragment.clone() for fragment in line.words)
            if line is lines[-1]:
                continue
            index = len(fragments) - 1
            while index >= 0 and hasattr(fragments[index], 'cbDefn') and not getattr(fragments[index].cbDefn, 'width', 0):
                index -= 1
            if index < 0:
                continue
            fragment = fragments[index]
            payload = getattr(getattr(fragment, 'cbDefn', None), 'image', None)
            if isinstance(payload, _VectorMath):
                # Native _split_blParaHard appends a space to the callback text.
                # CJK rewrap would then count/draw that callback for both chars.
                # Keep one atomic placeholder and preserve the separating space
                # as ordinary prose with ordinary font metrics instead.
                fragment.text = '\ufffc'
                separator = fragment.clone(text=' ')
                del separator.cbDefn
                fragments.insert(index + 1, separator)
            elif not fragment.text:
                fragment.text = ' '
            elif not fragment.text.endswith(' '):
                fragment.text += ' '
        return fragments

    def wrap(self, available_width, available_height):
        later = available_width - self.style.leftIndent - self.style.rightIndent
        first = later - self.style.firstLineIndent
        def payloads(fragments):
            for fragment in fragments:
                if isinstance(fragment, (tuple, list)):
                    yield from payloads(fragment)
                else:
                    definition = getattr(fragment, 'cbDefn', None)
                    payload = getattr(definition, 'image', None)
                    if isinstance(payload, _VectorMath):
                        yield payload

        for payload in payloads(self.frags):
            if payload.width > max(first, later):
                raise ValueError('Inline formula exceeds available paragraph width; '
                                 'use a separate formula block. Font size is preserved.')
        result = super().wrap(available_width, available_height)
        if self.blPara.kind == 1:
            # ReportLab's draw step uses these minimum ascent/descent shares
            # independently.  Store the same bounds in its line objects so wrap,
            # split and drawing agree even for an asymmetric tall fraction.
            for line in self.blPara.lines:
                # Its Western breaker misses image bounds when an image starts
                # a new line; re-merge only our controlled vector payloads.
                for payload in payloads(line.words):
                    line.ascent = max(line.ascent, payload.bottom + payload.height)
                    line.descent = min(line.descent, payload.bottom)
                line.ascent = max(self.style.leading * 5 / 6, line.ascent)
                line.descent = min(-self.style.leading / 6, line.descent)
            self.height = sum(line.ascent - line.descent for line in self.blPara.lines)
            return result[0], self.height
        return result

    def draw(self):
        canvas = self.canv
        original = canvas.drawImage
        had_override = 'drawImage' in canvas.__dict__

        def draw_inline(image, x, y, width=None, height=None, *args, **kwargs):
            if isinstance(image, _VectorMath):
                image.draw(canvas, x, y, width, height)
                return
            return original(image, x, y, width, height, *args, **kwargs)

        canvas.drawImage = draw_inline
        canvas.saveState()
        try:
            # ReportLab defaults the first baseline to height - fontSize even
            # when autoLeading measured a taller first-line ascent.  Shift its
            # complete draw step to fit the measured box, including callbacks,
            # without modifying global ReportLab settings.
            if paraFontSizeHeightOffset and self.blPara.kind == 1 and self.blPara.lines:
                first = self.blPara.lines[0]
                canvas.translate(0, first.fontSize - first.ascent)
            super().draw()
        finally:
            canvas.restoreState()
            if had_override:
                canvas.drawImage = original
            else:
                del canvas.drawImage


def inline_math_paragraph(text, style, formula_class, markup_validator):
    """Keep ordinary paragraphs identical; convert only explicit delimiters."""
    parts = inline_parts(text)
    # This runs before *any* ReportLab callback markup is created.  Thus user
    # onDraw/img/font/link attributes cannot acquire the trusted vector path.
    validator = markup_validator()
    validator.feed(''.join(content for is_math, content in parts if not is_math))
    validator.close()
    if validator.stack:
        raise ValueError('Unclosed paragraph formatting tag.')
    if not any(is_math for is_math, _ in parts):
        return Paragraph(str(text), style)

    formulas, markup = [], []
    for is_math, content in parts:
        if is_math:
            formulas.append(content)
            markup.append(f'<onDraw name="_study_inline_math_{len(formulas) - 1}"/>')
        else:
            markup.append(content)
    paragraph = InlineMathParagraph(''.join(markup), style)
    paragraph.autoLeading = 'max'
    for frag in paragraph.frags:
        definition = getattr(frag, 'cbDefn', None)
        if definition is None:
            continue
        index = int(definition.name.removeprefix('_study_inline_math_'))
        formula = formula_class(formulas[index], frag.fontSize)
        payload = _VectorMath.create(formula, frag.textColor)
        frag.cbDefn = ABag(kind='img', image=payload, width=payload.width,
                          height=payload.height, valign=payload.bottom)
        # ReportLab's CJK breaker calls ord() at a wrap boundary.  Its native
        # empty image fragment crashes there; one internal object character is
        # atomic and measured using cbDefn.width, never drawn as a text glyph.
        frag.text = '\ufffc' if style.wordWrap == 'CJK' else ''
    return paragraph
