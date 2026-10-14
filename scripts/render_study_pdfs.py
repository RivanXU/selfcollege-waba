#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Render source-preserving bilingual slides and the user's study-guide style.

This is a layout engine, not a translator or a source verifier. See pdf-style.md.
All requested outputs are rendered in a staging folder before replacing outputs.
"""
import argparse
import io
import json
import logging
import math
import os
import re
import string
import tempfile
import unicodedata
import warnings
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle
from inline_math import inline_math_paragraph
from matplotlib.font_manager import FontProperties
from matplotlib.ft2font import LoadFlags
from matplotlib.mathtext import MathTextParser
from matplotlib.path import Path as MathPath

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / 'assets/fonts/NotoSansSC-Regular.ttf'
TOKENS = json.loads((ROOT / 'assets/style_tokens.json').read_text())
C = {k: colors.HexColor(v) for k, v in TOKENS.items() if isinstance(v, str)}
DEFAULT_LABELS = {
    'source_heading': 'Source slide',
    'translation_heading': 'Translated slide',
    'terms_heading': 'Vocabulary',
    'symbol_heading': 'Symbol',
    'symbol_meaning_heading': 'Meaning in this step',
    'guide_name': 'study-guide',
    'bilingual_name': 'slide-companion',
    'guide_header': 'Study guide',
    'bilingual_header': 'Slide companion',
    'source_footer': 'Source: {filename}, page {page}',
    'guide_reference_footer': 'Study guide: pages {pages}',
}


class LayoutError(ValueError):
    pass


def require_glyphs(text):
    """Fail before publication instead of silently drawing missing characters."""
    text = str(text)
    if any(unicodedata.bidirectional(char) in {'R', 'AL', 'RLE', 'RLO', 'RLI'} for char in text):
        raise ValueError('Right-to-left text requires a shaping-aware typesetting engine. '
                         'A font override alone cannot provide correct direction or joined glyphs; '
                         'use a verified local PDF from a capable engine.')
    glyphs = pdfmetrics.getFont('StudyCN').face.charToGlyph
    missing = sorted({char for char in text
                      if char not in '\n\r\t' and not glyphs.get(ord(char))})
    if missing:
        details = ', '.join(f'{char!r} (U+{ord(char):04X})' for char in missing)
        raise ValueError(f'Font is missing characters: {details}. '
                         'Use --font with a font covering these characters, or '
                         'use a formula block with LaTeX for mathematics. '
                         'Do not replace or omit source symbols.')


class SafeMarkup(HTMLParser):
    """Only formatting tags may enter ReportLab's richer paragraph parser."""
    allowed = {'b', 'strong', 'i', 'em', 'u', 'strike', 'sub', 'super', 'sup', 'br'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.allowed or attrs:
            raise ValueError(f'Unsupported text markup: <{tag}>. Only simple formatting '
                             'tags without attributes are allowed; use an image block '
                             'with a local file for images. External resources are not allowed.')
        if tag != 'br':
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == 'br' and not self.stack:
            raise ValueError('Use <br/> for a line break.')
        if not self.stack or self.stack.pop() != tag:
            raise ValueError(f'Unbalanced text markup: </{tag}>.')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != 'br':
            raise ValueError('Only <br/> may be a self-closing formatting tag.')

    def handle_data(self, data):
        require_glyphs(data)

    def handle_comment(self, data):
        raise ValueError('Comments are not allowed in paragraph markup.')

    def handle_decl(self, decl):
        raise ValueError('Declarations are not allowed in paragraph markup.')

    def handle_pi(self, data):
        raise ValueError('Processing instructions are not allowed in paragraph markup.')

    def unknown_decl(self, data):
        raise ValueError('Declarations are not allowed in paragraph markup.')


def local_input(value, field):
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f'{field} must be a local file path.')
    if re.match(r'^(?:https?|ftp|file|data):', str(value), re.IGNORECASE) or '://' in str(value):
        raise ValueError(f'{field} must be a local file path, not a URL.')
    path = Path(value).resolve()
    if not path.is_file():
        raise ValueError(f'{field} does not name an existing local file: {path}')
    return path


def referenced_inputs(spec, args):
    paths = [local_input(args.spec, '--spec'), Path(__file__).resolve(),
             ROOT / 'assets/style_tokens.json']
    for name in ('font', 'style'):
        if getattr(args, name) is not None:
            paths.append(local_input(getattr(args, name), f'--{name}'))
    if args.font is None:
        paths.append(local_input(DEFAULT_FONT, 'bundled font'))
    for name in ('source_pdf', 'translated_pdf'):
        if spec.get(name):
            paths.append(local_input(spec[name], name))
    def collect(blocks):
        for block in blocks:
            if block.get('type') == 'source_crop':
                paths.append(local_input(block['source_pdf'], 'source_crop.source_pdf'))
            elif block.get('type') == 'image':
                paths.append(local_input(block['path'], 'image.path'))
            elif block.get('type') == 'concept':
                collect(block.get('blocks', []))
    for page in spec.get('guide', []):
        collect(page.get('blocks', []))
    return paths


def same_file(left, right):
    return left.resolve() == right.resolve() or (
        left.exists() and right.exists() and os.path.samefile(left, right))


def protect_inputs(final, inputs):
    if any(same_file(final, source) for source in inputs):
        raise ValueError(f'Output must never overwrite a referenced input file: {final}')


def source_page(path, number, clip=None):
    """Return visible page content with rotation applied; clips use top-left points."""
    reader = PdfReader(io.BytesIO(Path(path).read_bytes()))
    if reader.is_encrypted:
        raise ValueError('Use an unlocked local copy of the source PDF.')
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(reader.pages):
        raise ValueError('Source PDF page must be an integer in the document page range.')
    for reference in reader.pages[number - 1].get('/Annots', []):
        annotation = reference.get_object()
        flags = int(annotation.get('/F', 0))
        # Links have no teaching appearance. Other visible annotations can contain
        # instructor handwriting, highlights, comments, stamps, or form values.
        if annotation.get('/Subtype') != '/Link' and not flags & (1 | 2 | 32):
            raise ValueError(f'Source page {number} contains a visible annotation '
                             f'({annotation.get("/Subtype", "unknown type")}). Flatten '
                             'legitimate annotations in a separate verified copy before '
                             'composition; otherwise instructor material could be lost.')
    # Attach the page to a writer before changing its content stream or boxes.
    # This also isolates normalization from the caller's original document.
    working = PdfWriter()
    page = working.add_page(reader.pages[number - 1])
    page.transfer_rotation_to_content()
    unit = float(page.get('/UserUnit', 1))
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('Source PDF has an invalid UserUnit.')
    if unit != 1:
        page.scale_by(unit)
        if '/UserUnit' in page:
            del page['/UserUnit']
    media, crop = page.mediabox, page.cropbox
    left = max(float(media.left), float(crop.left))
    bottom = max(float(media.bottom), float(crop.bottom))
    right = min(float(media.right), float(crop.right))
    top = min(float(media.top), float(crop.top))
    if right <= left or top <= bottom:
        raise ValueError('Source PDF has an invalid visible page box.')
    if clip is not None:
        if (not isinstance(clip, (list, tuple)) or len(clip) != 4
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in clip)):
            raise ValueError('source_crop.clip must contain four finite coordinates.')
        x0, y0, x1, y1 = clip
        if not (0 <= x0 < x1 <= right - left and 0 <= y0 < y1 <= top - bottom):
            raise ValueError('source_crop.clip must be within the visible source page.')
        left, bottom, right, top = left + x0, top - y1, left + x1, top - y0
    page.cropbox = RectangleObject((left, bottom, right, top))
    # Copy page graphics only, not active annotations, links, or form fields.
    for key in ('/Annots', '/AA'):
        if key in page:
            del page[key]
    return page, (left, bottom, right, top)


def merge_sources(path, placements):
    if not placements:
        return
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(path.read_bytes())))
    for placement in placements:
        page, (left, bottom, right, top) = source_page(
            placement['source_pdf'], placement['source_page'], placement.get('clip'))
        scale = placement.get('scale', min(placement['width'] / (right - left), placement['height'] / (top - bottom)))
        x = placement['x'] + (placement['width'] - (right - left) * scale) / 2
        y = placement['y'] + (placement['height'] - (top - bottom) * scale) / 2
        transform = Transformation().translate(-left, -bottom).scale(scale).translate(x, y)
        writer.pages[placement['page']].merge_transformed_page(page, transform, over=True)
    for page in writer.pages:
        page.compress_content_streams()
    with path.open('wb') as stream:
        writer.write(stream)


class PDFSource(Flowable):
    """Reserve guide layout space and place the PDF graphics after typesetting."""
    def __init__(self, block, width, placements):
        super().__init__()
        _, (left, bottom, right, top) = source_page(block['source_pdf'], block['page'], block.get('clip'))
        maximum_height = block.get('height', 300)
        if (isinstance(maximum_height, bool) or not isinstance(maximum_height, (int, float))
                or not math.isfinite(maximum_height) or maximum_height <= 0):
            raise ValueError('source_crop.height must be a finite positive number.')
        scale = min(width / (right - left), maximum_height / (top - bottom))
        self.width = (right - left) * scale
        self.height = (top - bottom) * scale
        self.block = block
        self.placements = placements

    def draw(self):
        x, y = self.canv.absolutePosition(0, 0)
        self.placements.append({'page': self.canv.getPageNumber() - 1,
            'source_pdf': self.block['source_pdf'], 'source_page': self.block['page'],
            'clip': self.block.get('clip'), 'x': x, 'y': y,
            'width': self.width, 'height': self.height})


def has_fraction_slash(latex):
    """Reject fraction shorthand while preserving explicitly literal units/code."""
    position = 0
    literal_command = re.compile(r'\\(?:text|mathrm|mathtt|operatorname)\s*\{')
    while position < len(latex):
        command = literal_command.match(latex, position)
        if command:
            position = command.end()
            depth = 1
            while position < len(latex) and depth:
                if latex[position] == '\\':
                    position += 2
                    continue
                if latex[position] == '{':
                    depth += 1
                elif latex[position] == '}':
                    depth -= 1
                position += 1
            continue
        if latex[position] == '/':
            return True
        position += 1
    return False


def display_fraction_latex(expression):
    """Give display-level fractions full-size operands; preserve script nesting.

    MathText treats ``\\frac`` as a text-style fraction even in a standalone
    block. Promote only ordinary fractions at the current display level. Leave
    explicitly requested styles, nested fractions, scripts and literal text
    alone. The MathText parser remains responsible for syntax validation.
    """
    command = re.compile(r'\\[A-Za-z]+|\\.')
    literals = {'text', 'mathrm', 'mathtt', 'operatorname'}

    def group_end(start, limit):
        depth, pos = 1, start + 1
        while pos < limit and depth:
            if expression[pos] == '\\':
                match = command.match(expression, pos)
                pos = match.end() if match else pos + 1
                continue
            depth += (expression[pos] == '{') - (expression[pos] == '}')
            pos += 1
        return pos, depth == 0

    def argument(pos, display, limit):
        start = pos
        while pos < limit and expression[pos].isspace():
            pos += 1
        prefix = expression[start:pos]
        if pos >= limit:
            return prefix, pos
        if expression[pos] == '{':
            end, closed = group_end(pos, limit)
            if not closed:
                # Never repair malformed source silently. Let MathText reject it.
                return expression[start:end], end
            return prefix + '{' + walk(pos + 1, end - 1, display) + '}', end
        if expression[pos] == '\\':
            match = command.match(expression, pos)
            end = match.end() if match else pos + 1
            # MathText requires braced fraction operands. Leave invalid unbraced
            # commands intact for its normal explicit unsupported-input error.
            return prefix + expression[pos:end], end
        return prefix + expression[pos], pos + 1

    def walk(start, end, display):
        result, pos = [], start
        while pos < end:
            char = expression[pos]
            if char in '^_':
                value, pos = argument(pos + 1, False, end)
                result.extend([char, value])
            elif char == '{':
                value, pos = argument(pos, display, end)
                result.append(value)
            elif char == '\\':
                match = command.match(expression, pos)
                if not match:
                    result.append(char)
                    pos += 1
                    continue
                token = match.group()
                name = token[1:]
                pos = match.end()
                result.append(r'\dfrac' if name == 'frac' and display else token)
                if name in {'frac', 'dfrac', 'tfrac'}:
                    for _ in range(2):
                        value, pos = argument(pos, False, end)
                        result.append(value)
                elif name in {'genfrac', 'binom'}:
                    # Explicit style/thickness/delimiters own the complete
                    # fraction. Preserve its arguments verbatim, including any
                    # nested fractions, rather than overriding the author's style.
                    begin = pos
                    for _ in range(6 if name == 'genfrac' else 2):
                        while pos < end and expression[pos].isspace():
                            pos += 1
                        if pos < end and expression[pos] == '{':
                            pos, closed = group_end(pos, end)
                            if not closed:
                                break
                        elif pos < end:
                            match = command.match(expression, pos)
                            pos = match.end() if match else pos + 1
                    result.append(expression[begin:pos])
                elif name in literals:
                    begin = pos
                    while pos < end and expression[pos].isspace():
                        pos += 1
                    if pos < end and expression[pos] == '{':
                        pos, _ = group_end(pos, end)
                    result.append(expression[begin:pos])
            else:
                result.append(char)
                pos += 1
        return ''.join(result)

    return walk(0, len(expression), True)


class MathFormula(Flowable):
    """Draw MathText's glyph outlines and rules directly as PDF vector paths."""
    def __init__(self, latex, font_size=None):
        super().__init__()
        if not isinstance(latex, str) or not latex.strip():
            raise ValueError('formula.latex must contain a LaTeX math expression.')
        latex = latex.strip()
        if latex.startswith('$') and latex.endswith('$'):
            latex = latex[1:-1]
        if '$' in latex or '\n' in latex:
            raise ValueError('Use one formula.latex expression per block, without embedded dollar signs or line breaks.')
        if has_fraction_slash(latex):
            raise ValueError('Typeset division using \\frac{numerator}{denominator}; slash fractions are not accepted.')
        self.latex = latex
        self.render_latex = display_fraction_latex(latex)
        self.font_size = font_size or TOKENS['formula_size']
        math_logger = logging.getLogger('matplotlib.mathtext')
        log_buffer = io.StringIO()
        handler = logging.StreamHandler(log_buffer)
        handler.setLevel(logging.WARNING)
        math_logger.addHandler(handler)
        previous_propagation = math_logger.propagate
        math_logger.propagate = False
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            try:
                self.parsed = MathTextParser('path').parse(
                    '$' + self.render_latex + '$', dpi=72,
                    prop=FontProperties(size=self.font_size, math_fontfamily='cm'))
            except (ValueError, RuntimeError) as error:
                raise ValueError(f'Unsupported mathematical expression: {latex}. '
                                 'Rewrite it in supported MathText LaTeX or use a verified vector source crop.') from error
            finally:
                math_logger.removeHandler(handler)
                math_logger.propagate = previous_propagation
            if caught or log_buffer.getvalue():
                details = '; '.join(str(w.message) for w in caught) + log_buffer.getvalue().strip()
                raise ValueError('Mathematical typesetting emitted a warning or missing glyph: ' + details)
        self.width = float(self.parsed.width)
        self.height = float(self.parsed.height) + 6

    def wrap(self, available_width, available_height):
        if self.width > available_width:
            raise LayoutError('Formula exceeds its available width; split the derivation into separate formulas. Font size is preserved.')
        return self.width, self.height

    def draw(self):
        self.draw_at_baseline(self.canv, baseline=float(self.parsed.depth) + 3)

    def draw_at_baseline(self, canvas, x=0, baseline=0, text_color=None):
        """Draw at a text baseline; inline placement uses actual glyph bounds."""
        c = canvas
        c.saveState()
        c.translate(x, baseline)
        c.setFillColor(text_color if text_color is not None else C['ink'])
        baseline = 0
        for glyph in self.parsed.glyphs:
            # Matplotlib 3.8-3.10 expose five entries; newer releases add a glyph index.
            font, size, char, x, y = glyph[0], glyph[1], glyph[2], glyph[-2], glyph[-1]
            font.set_size(size, 72)
            font.load_char(char, flags=LoadFlags.NO_HINTING)
            vertices, codes = font.get_path()
            outline = MathPath(vertices, codes)
            path = c.beginPath()
            for points, command in outline.iter_segments(curves=True):
                if command == MathPath.MOVETO:
                    path.moveTo(x + points[0], baseline + y + points[1])
                elif command == MathPath.LINETO:
                    path.lineTo(x + points[0], baseline + y + points[1])
                elif command == MathPath.CURVE3:
                    # Quadratic Bezier -> cubic Bezier, preserving the glyph outline.
                    end_x, end_y = x + points[2], baseline + y + points[3]
                    control_x, control_y = x + points[0], baseline + y + points[1]
                    path.curveTo(current_x + 2 / 3 * (control_x - current_x),
                                 current_y + 2 / 3 * (control_y - current_y),
                                 end_x + 2 / 3 * (control_x - end_x),
                                 end_y + 2 / 3 * (control_y - end_y), end_x, end_y)
                elif command == MathPath.CURVE4:
                    path.curveTo(x + points[0], baseline + y + points[1],
                                 x + points[2], baseline + y + points[3],
                                 x + points[4], baseline + y + points[5])
                elif command == MathPath.CLOSEPOLY:
                    path.close()
                if command in (MathPath.MOVETO, MathPath.LINETO):
                    current_x, current_y = x + points[0], baseline + y + points[1]
                elif command == MathPath.CURVE3:
                    current_x, current_y = end_x, end_y
                elif command == MathPath.CURVE4:
                    current_x, current_y = x + points[4], baseline + y + points[5]
            c.drawPath(path, stroke=0, fill=1)
        for x, y, width, height in self.parsed.rects:
            c.rect(float(x), baseline + float(y), float(width), float(height), stroke=0, fill=1)
        c.restoreState()


def plain_filename(value, field):
    if (not isinstance(value, str) or not value.strip() or value in ('.', '..')
            or any(char in value for char in '/\\')
            or any(ord(char) < 32 for char in value)):
        raise ValueError(f'{field} must be a plain nonempty filename stem.')
    return value


def configure_style(path=None):
    """Read an optional course-owned override without changing bundled defaults."""
    global TOKENS, C
    defaults = json.loads((ROOT / 'assets/style_tokens.json').read_text(encoding='utf-8'))
    override = json.loads(path.read_text(encoding='utf-8')) if path else {}
    if not isinstance(override, dict):
        raise ValueError('Style override must be a JSON object.')
    unknown = override.keys() - defaults.keys()
    if unknown:
        raise ValueError(f'Unknown style keys: {", ".join(sorted(unknown))}')
    values = {**defaults, **override}
    for key, default in defaults.items():
        value = values[key]
        if isinstance(default, str):
            if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                raise ValueError(f'Style {key} must be a six-digit hexadecimal color, e.g. #17334D.')
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'Style {key} must be a finite positive number.')
    for prefix in ('guide', 'bilingual', 'annotation'):
        if values[f'{prefix}_body_leading'] < values[f'{prefix}_body_size']:
            raise ValueError(f'{prefix}_body_leading must be at least {prefix}_body_size.')
    if not values['guide_body_size'] <= values['formula_size'] <= values['guide_body_size'] * 1.5:
        raise ValueError('formula_size must be between the guide body size and 1.5 times '
                         'that size. Keep display mathematics proportionate to the text; '
                         'split long expressions rather than changing one formula to fit.')
    TOKENS = values
    C = {key: colors.HexColor(value) for key, value in values.items() if isinstance(value, str)}


def configure_labels(spec):
    override = spec.get('labels', {})
    if not isinstance(override, dict):
        raise ValueError('labels must be a JSON object.')
    unknown = override.keys() - DEFAULT_LABELS.keys()
    if unknown:
        raise ValueError(f'Unknown label keys: {", ".join(sorted(unknown))}')
    labels = {**DEFAULT_LABELS, **override}
    for key, value in labels.items():
        if not isinstance(value, str) or not value.strip() or any(ord(char) < 32 for char in value):
            raise ValueError(f'Label {key} must be nonempty text without control characters.')
    for kind in ('guide', 'bilingual'):
        plain_filename(labels[f'{kind}_name'], f'labels.{kind}_name')
        if f'{kind}_header' not in override:
            labels[f'{kind}_header'] = labels[f'{kind}_name']
    if labels['guide_name'] == labels['bilingual_name']:
        raise ValueError('guide_name and bilingual_name must differ to avoid output filename collisions.')
    for key, allowed in [('source_footer', {'filename', 'page'}), ('guide_reference_footer', {'pages'})]:
        try:
            fields = list(string.Formatter().parse(labels[key]))
        except ValueError as error:
            raise ValueError(f'Invalid label template {key}: {error}') from error
        for _, field, format_spec, conversion in fields:
            if field is not None and (field not in allowed or format_spec or conversion):
                raise ValueError(f'{key} permits only these plain placeholders: {", ".join(sorted(allowed))}')
    spec['labels'] = labels


def make_styles():
    common = dict(fontName='StudyCN', wordWrap='CJK', textColor=C['ink'])
    return {
        'body': ParagraphStyle('body', fontSize=TOKENS['guide_body_size'],
            leading=TOKENS['guide_body_leading'], spaceAfter=10, **common),
        'heading': ParagraphStyle('heading', fontSize=13.2, leading=20,
            spaceBefore=12, spaceAfter=9, **{**common, 'textColor': C['teal']}),
        'small': ParagraphStyle('small', fontSize=9.1, leading=14.4,
            spaceAfter=6, **{**common, 'textColor': C['muted']}),
        'title': ParagraphStyle('title', fontSize=21, leading=29,
            **{**common, 'textColor': C['navy']}),
        'subtitle': ParagraphStyle('subtitle', fontSize=10, leading=15,
            **{**common, 'textColor': C['muted']}),
        'table': ParagraphStyle('table', fontSize=9.5, leading=14.5, **common),
        'th': ParagraphStyle('th', fontSize=9.5, leading=14.5,
            **{**common, 'textColor': colors.white}),
        'formula': ParagraphStyle('formula', fontSize=12.2, leading=22,
            alignment=1, spaceAfter=8, **common),
        'translation': ParagraphStyle('translation', fontSize=TOKENS['bilingual_body_size'],
            leading=TOKENS['bilingual_body_leading'], spaceAfter=12, **common),
        'annotation': ParagraphStyle('annotation', fontSize=TOKENS['annotation_body_size'],
            leading=TOKENS['annotation_body_leading'], spaceAfter=6, **common),
    }


def para(text, styles, kind='body'):
    return inline_math_paragraph(str(text), styles[kind], MathFormula, SafeMarkup)


def draw_item(c, item, x, top, width, floor=56, context='page'):
    top -= getattr(getattr(item, 'style', None), 'spaceBefore', 0)
    measured_width, height = item.wrap(width, max(1, top - floor))
    if measured_width > width + .01 or top - height < floor:
        raise LayoutError(f'{context}: content overflow; split guide content or increase the annotation/page dimensions. Preserve text and font sizes.')
    item.drawOn(c, x, top - height)
    return top - height - getattr(getattr(item, 'style', None), 'spaceAfter', 0)


def table(header, rows, width, styles, ratios=None):
    count = len(header) if header else (len(rows[0]) if rows else 0)
    if not count or any(len(row) != count for row in rows):
        raise ValueError('Table must contain consistently sized rows.')
    ratios = [1] * count if ratios is None else ratios
    if (not isinstance(ratios, (list, tuple)) or len(ratios) != count
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) or v <= 0 for v in ratios)):
        raise ValueError('Table widths must be finite positive numbers and match its columns.')
    data = ([[para(x, styles, 'th') for x in header]] if header else [])
    data += [[para(x, styles, 'table') for x in row] for row in rows]
    t = Table(data, colWidths=[width * v / sum(ratios) for v in ratios], hAlign='LEFT')
    style = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 0), (-1, -1), .3, C['line']),
        ('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [colors.white, C['stripe']])]
    if header:
        style.append(('BACKGROUND', (0, 0), (-1, 0), C['navy']))
    t.setStyle(TableStyle(style))
    return t


def symbol_table(rows, width, styles, labels=None):
    if not isinstance(rows, list) or any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in rows):
        raise ValueError('formula.symbols must be pairs of LaTeX symbol and explanatory text.')
    labels = labels or DEFAULT_LABELS
    data = [[para(labels['symbol_heading'], styles, 'th'),
             para(labels['symbol_meaning_heading'], styles, 'th')]]
    data.extend([[MathFormula(symbol, styles['table'].fontSize * 1.2),
                  para(definition, styles, 'table')] for symbol, definition in rows])
    result = Table(data, colWidths=[width / 4, width * 3 / 4], hAlign='LEFT')
    result.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), C['navy']),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, C['stripe']]),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), .3, C['line'])]))
    return result


def box(label, text, width, styles, tone='green'):
    if tone not in ('green', 'blue', 'amber'):
        raise ValueError('Box tone must be green, blue, or amber.')
    t = Table([[para(label, styles, 'heading')], [para(text, styles)]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C[tone]),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 8), ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 1), (-1, 1), 0), ('BOTTOMPADDING', (0, -1), (-1, -1), 10)]))
    return t


def furniture(c, width, height, margin, spec, number, total, kind, styles):
    c.setFillColor(C['navy']); c.rect(0, height - 9, width, 9, stroke=0, fill=1)
    c.setFont('StudyCN', 8.5)
    header = f"{spec.get('course_code', '')} / {spec.get('lecture', '')}"
    require_glyphs(header); require_glyphs(kind)
    usable = width - 2 * margin
    if (pdfmetrics.stringWidth(header, 'StudyCN', 8.5)
            + pdfmetrics.stringWidth(kind, 'StudyCN', 8.5) + 12 > usable):
        raise LayoutError('Header exceeds available space; shorten course_code, lecture, '
                          'or the header label. Keep the full title in the page body.')
    c.drawString(margin, height - 32, header)
    c.setFillColor(C['muted']); c.drawRightString(width - margin, height - 32, kind)
    c.setStrokeColor(C['line']); c.line(margin, height - 43, width - margin, height - 43)
    c.line(margin, 40, width - margin, 40)
    c.setFont('StudyCN', 8)
    counter = f'{number:02d} / {total:02d}'
    footer_space = usable - pdfmetrics.stringWidth(counter, 'StudyCN', 8) - 12
    footer = spec.get('course_name', '')
    if pdfmetrics.stringWidth(footer, 'StudyCN', 8) > footer_space:
        footer = spec.get('course_code', '')
    require_glyphs(footer)
    if pdfmetrics.stringWidth(footer, 'StudyCN', 8) > footer_space:
        raise LayoutError('Course footer exceeds available space; shorten course_name '
                          'or course_code without changing the body title.')
    c.drawString(margin, 25, footer)
    c.drawRightString(width - margin, 25, counter)


def guide_blocks(block, width, styles, placements, labels=None):
    kind = block['type']
    if kind in ('text', 'heading', 'small'):
        return [para(block['text'], styles, 'body' if kind == 'text' else kind)]
    if kind == 'formula':
        if 'text' in block:
            raise ValueError('formula.text is no longer accepted. Use formula.latex for stacked fractions and scripts.')
        if not isinstance(block.get('reason'), str) or not block['reason'].strip():
            raise ValueError('Every formula requires a nearby reason explaining why this step follows.')
        result = []
        if block.get('label'):
            result.append(para(block['label'], styles, 'heading'))
        result.extend([MathFormula(block.get('latex')), Spacer(1, 4), para(block['reason'], styles)])
        if block.get('symbols'):
            result.extend([symbol_table(block['symbols'], width, styles, labels), Spacer(1, 10)])
        return result
    if kind == 'concept':
        if not block.get('title') or not block.get('blocks'):
            raise ValueError('A concept group requires a title and nonempty blocks.')
        result = [para(block['title'], styles, 'heading')]
        for child in block['blocks']:
            result.extend(guide_blocks(child, width, styles, placements, labels))
        result.append(Spacer(1, TOKENS['concept_gap']))
        return result
    if kind == 'box':
        return [box(block['label'], block['text'], width, styles, block.get('tone', 'green')), Spacer(1, 7)]
    if kind == 'table':
        return [table(block.get('header'), block['rows'], width, styles, block.get('widths')), Spacer(1, 8)]
    if kind in ('image', 'source_crop'):
        if kind == 'image':
            image = Image(str(Path(block['path']).resolve()))
            maximum_height = block.get('height', 300)
            if (isinstance(maximum_height, bool) or not isinstance(maximum_height, (int, float))
                    or not math.isfinite(maximum_height) or maximum_height <= 0):
                raise ValueError('image.height must be a finite positive number.')
            factor = min(width / image.imageWidth, maximum_height / image.imageHeight)
            image.drawWidth = image.imageWidth * factor
            image.drawHeight = image.imageHeight * factor
        else:
            image = PDFSource(block, width, placements)
        result = [image, Spacer(1, 5)]
        if block.get('caption'):
            result.append(para(block['caption'], styles, 'small'))
        return result
    raise ValueError(f'Unsupported guide block: {kind}')


def render_guide(spec, path, styles):
    pages = spec['guide']; w, h, m = 595.276, 841.89, 47
    placements = []
    if not pages:
        raise ValueError('guide cannot be empty')
    c = canvas.Canvas(str(path), pagesize=(w, h))
    labels = spec['labels']
    c.setTitle(f"{spec.get('course_code', '')} {spec.get('lecture', '')} {labels['guide_name']}")
    for number, page in enumerate(pages, 1):
        furniture(c, w, h, m, spec, number, len(pages), labels['guide_header'], styles)
        c.bookmarkPage(f'p{number}'); c.addOutlineEntry(page['title'], f'p{number}', level=0)
        top = draw_item(c, para(page['title'], styles, 'title'), m, h - 57, w - 2 * m)
        for name in ('subtitle', 'source'):
            if page.get(name):
                top = draw_item(c, para(escape(page[name]), styles, 'small'), m, top - 6, w - 2 * m)
        top -= 10
        for block in page['blocks']:
            for item in guide_blocks(block, w - 2 * m, styles, placements, spec['labels']):
                top = draw_item(c, item, m, top, w - 2 * m, context=f'Guide page {number}')
        c.showPage()
    c.save()
    merge_sources(path, placements)


def page_dimensions(path, number):
    _, (left, bottom, right, top) = source_page(path, number)
    return right - left, top - bottom


def bilingual_geometry(spec):
    """Validate pairs and return auditable viewport coordinates in PDF points."""
    source = local_input(spec.get('source_pdf'), 'source_pdf')
    original = PdfReader(io.BytesIO(source.read_bytes()))
    if original.is_encrypted:
        raise ValueError('Use an unlocked local copy of the source PDF.')
    pages = spec['bilingual']
    if not isinstance(pages, list) or not pages or [p.get('source_page') for p in pages] != list(range(1, len(original.pages) + 1)):
        raise ValueError('bilingual must list every source page exactly once in original order (1..N).')
    mode = spec.get('bilingual_mode', 'paired_pdf')
    if mode not in ('paired_pdf', 'reflow'):
        raise ValueError('bilingual_mode must be paired_pdf or explicit reflow.')
    translated = None
    if mode == 'paired_pdf':
        if not spec.get('translated_pdf'):
            raise ValueError('Exact-layout bilingual mode requires translated_pdf, a layout-matched PDF with one translated page per source page. Legacy translation arrays require explicit bilingual_mode="reflow", which is labeled as a layout-different fallback.')
        translated = local_input(spec['translated_pdf'], 'translated_pdf')
        translated_reader = PdfReader(io.BytesIO(translated.read_bytes()))
        if translated_reader.is_encrypted or original.is_encrypted:
            raise ValueError('Use unlocked local copies of both PDFs.')
        if len(translated_reader.pages) != len(original.pages):
            raise ValueError('Source and translated PDFs must have identical page counts.')
        if any('translation' in page for page in pages):
            raise ValueError('Paired-PDF mode uses translated_pdf. Move all translation text into its matched slide layouts; put supplementary explanations in notes.')
    elif spec.get('translated_pdf'):
        raise ValueError('reflow mode accepts translation arrays; omit translated_pdf or select paired_pdf.')
    layout = spec.get('bilingual_layout', {})
    if not isinstance(layout, dict) or layout.keys() - {'page_width', 'page_height', 'annotation_height'}:
        raise ValueError('bilingual_layout accepts only page_width, page_height, and annotation_height.')
    values = {'page_width': 1190.551, 'page_height': 841.89, 'annotation_height': 200, **layout}
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'bilingual_layout.{name} must be a finite positive number.')
    width, height, annotation_height = values.values()
    margin, gap, floor = 36, 32, 75
    viewport_width = (width - 2 * margin - gap) / 2
    annotation_top = floor + annotation_height
    viewport_top = height - 128
    viewport_height = viewport_top - annotation_top - 20
    if viewport_width < 72 or viewport_height < 72:
        raise LayoutError('Bilingual page dimensions leave insufficient space for equal slide viewports. Increase the page size or reduce annotation_height without shrinking annotation text.')
    report = []
    for number in range(1, len(pages) + 1):
        sw, sh = page_dimensions(source, number)
        if translated:
            tw, th = page_dimensions(translated, number)
            if abs(sw - tw) > .01 or abs(sh - th) > .01:
                raise ValueError(f'Page {number}: source and translated visible dimensions must match after rotation and UserUnit normalization; got {sw:g} x {sh:g} and {tw:g} x {th:g} points.')
        scale = min(viewport_width / sw, viewport_height / sh)
        left = {'x': margin, 'y': annotation_top + 20, 'width': viewport_width, 'height': viewport_height}
        right = {**left, 'x': margin + viewport_width + gap}
        report.append({'source_page': number, 'source_dimensions': [sw, sh], 'scale': scale,
                       'left_viewport': left, 'right_viewport': right,
                       'annotation_band': {'x': margin, 'y': floor, 'width': width - 2 * margin, 'height': annotation_height}})
    return source, translated, mode, values, report


def annotation_items(page, width, styles, labels):
    if page.get('terms'):
        yield para('<b>' + escape(labels['terms_heading']) + '</b>', styles, 'annotation')
        yield table(None, page['terms'], width, styles, [1, 3])
        yield Spacer(1, 6)
    for field in ('notes', 'transcript', 'homework'):
        for note in page.get(field, []):
            if not note.get('label') or not note.get('text'):
                raise ValueError(f'{field} entries require a label and text.')
            body = '<b>' + escape(note['label']) + ':</b> ' + note['text']
            if note.get('source'):
                body += ' <i>(' + escape(note['source']) + ')</i>'
            yield para(body, styles, 'annotation')


def render_bilingual(spec, path, styles):
    source, translated, mode, layout, report = bilingual_geometry(spec)
    pages, labels = spec['bilingual'], spec['labels']
    w, h, m = layout['page_width'], layout['page_height'], 36
    c = canvas.Canvas(str(path), pagesize=(w, h))
    c.setTitle(f"{spec.get('course_code', '')} {spec.get('lecture', '')} {labels['bilingual_name']}")
    placements = []
    for number, (page, geometry) in enumerate(zip(pages, report), 1):
        title = page.get('title') or page.get('title_zh') or page.get('title_en') or f'Slide {number}'
        c.bookmarkPage(f'p{number}'); c.addOutlineEntry(title, f'p{number}', level=0)
        furniture(c, w, h, m, spec, number, len(pages), labels['bilingual_header'], styles)
        draw_item(c, para(title, styles, 'title'), m, h - 57, w - 2 * m, floor=h - 100,
                  context=f'Bilingual title page {number}')
        for heading, viewport in ((labels['source_heading'], geometry['left_viewport']),
                                  (labels['translation_heading'], geometry['right_viewport'])):
            draw_item(c, para(escape(heading), styles, 'annotation'), viewport['x'],
                      viewport['y'] + viewport['height'] + 22, viewport['width'],
                      floor=viewport['y'] + viewport['height'] + 2, context=f'Slide heading page {number}')
            c.setStrokeColor(C['line'])
            c.rect(viewport['x'] - 1, viewport['y'] - 1, viewport['width'] + 2, viewport['height'] + 2)
        placements.append({'page': number - 1, 'source_pdf': source, 'source_page': number,
                           'scale': geometry['scale'], **geometry['left_viewport']})
        if mode == 'paired_pdf':
            placements.append({'page': number - 1, 'source_pdf': translated, 'source_page': number,
                               'scale': geometry['scale'], **geometry['right_viewport']})
        else:
            right = geometry['right_viewport']
            top = draw_item(c, para('<b>Reflow fallback - layout differs from source</b>', styles, 'annotation'),
                            right['x'], right['y'] + right['height'], right['width'], right['y'])
            if not page.get('translation'):
                raise ValueError(f'Reflow page {number} requires a nonempty translation array.')
            for text in page['translation']:
                top = draw_item(c, para(text, styles, 'translation'), right['x'], top,
                                right['width'], right['y'], context=f'Reflow translation page {number}')
        band = geometry['annotation_band']
        c.setStrokeColor(C['line']); c.line(m, band['y'] + band['height'] + 6, w - m, band['y'] + band['height'] + 6)
        top = band['y'] + band['height']
        for item in annotation_items(page, band['width'], styles, labels):
            top = draw_item(c, item, m, top, band['width'], floor=band['y'], context=f'Annotation band page {number}')
        c.setFont('StudyCN', 9); c.setFillColor(C['muted'])
        footer = labels['source_footer'].format(filename=source.name, page=number)
        require_glyphs(footer)
        if pdfmetrics.stringWidth(footer, 'StudyCN', 9) > (w - 2 * m) * .65:
            raise LayoutError('Source footer exceeds available space; shorten its label or filename.')
        c.drawString(m, 57, footer)
        if page.get('guide_pages'):
            reference = labels['guide_reference_footer'].format(pages=page['guide_pages'])
            require_glyphs(reference)
            if (pdfmetrics.stringWidth(footer, 'StudyCN', 9)
                    + pdfmetrics.stringWidth(reference, 'StudyCN', 9) + 12 > w - 2 * m):
                raise LayoutError('Guide reference footer exceeds available space; '
                                  'use compact page ranges or move detailed locators to the annotation band.')
            c.drawRightString(w - m, 57, reference)
        c.showPage()
    c.save()
    merge_sources(path, placements)
    return {'mode': mode, 'pages': report,
            'layout_fidelity_review_required': mode == 'paired_pdf',
            'geometry_checks_are_not_content_fidelity_proof': True}


def publish_outputs(outputs, inputs, work):
    """Publish after every render passes, restoring previous files on failure."""
    backups, published = {}, []
    try:
        for index, item in enumerate(outputs):
            final = Path(item['path'])
            protect_inputs(final, inputs)
            if final.exists():
                backup = Path(work) / f'backup-{index}.pdf'
                backup.write_bytes(final.read_bytes())
                backups[final] = backup
            os.replace(item['stage'], final)
            published.append(final)
    except BaseException:
        for final in reversed(published):
            if final in backups:
                os.replace(backups[final], final)
            else:
                final.unlink(missing_ok=True)
        raise
    for item in outputs:
        item.pop('stage')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--font', type=Path)
    parser.add_argument('--style', type=Path, help='Course-owned JSON overrides for known style tokens; bundled defaults remain unchanged.')
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    configure_style(args.style)
    configure_labels(spec)
    stem = plain_filename(spec.get('file_stem', 'Course_Lecture'), 'file_stem')
    if not any(k in spec for k in ('guide', 'bilingual')):
        raise ValueError('Provide guide and/or bilingual content.')
    inputs = referenced_inputs(spec, args)
    destinations = {}
    for key in ('guide', 'bilingual'):
        if key in spec:
            final = (args.output_dir / f'{stem}_{spec["labels"][f"{key}_name"]}.pdf').resolve()
            protect_inputs(final, inputs)
            if any(same_file(final, other) for other in destinations.values()):
                raise ValueError('Output files must not refer to the same file.')
            destinations[key] = final
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    with tempfile.TemporaryDirectory(prefix='.study-render-', dir=args.output_dir) as work:
        font = args.font or DEFAULT_FONT
        pdfmetrics.registerFont(TTFont('StudyCN', str(font)))
        pdfmetrics.registerFontFamily('StudyCN', normal='StudyCN', bold='StudyCN', italic='StudyCN', boldItalic='StudyCN')
        styles = make_styles()
        for key in ('guide', 'bilingual'):
            if key not in spec:
                continue
            final = destinations[key]
            stage = Path(work) / f'{key}.pdf'
            if key == 'guide':
                render_guide(spec, stage, styles)
            else:
                positioning = render_bilingual(spec, stage, styles)
            doc = PdfReader(io.BytesIO(stage.read_bytes()))
            outputs.append({'kind': key, 'path': str(final), 'pages': len(doc.pages), 'stage': str(stage)})
            if key == 'bilingual':
                outputs[-1]['positioning'] = positioning
        publish_outputs(outputs, inputs, work)
    print(json.dumps({'outputs': outputs, 'visual_review_required': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
