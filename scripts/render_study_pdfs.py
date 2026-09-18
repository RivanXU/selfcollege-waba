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
import math
import os
import re
import string
import tempfile
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

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FONT = ROOT / 'assets/fonts/NotoSansSC-Regular.ttf'
TOKENS = json.loads((ROOT / 'assets/style_tokens.json').read_text())
C = {k: colors.HexColor(v) for k, v in TOKENS.items() if isinstance(v, str)}
DEFAULT_LABELS = {
    'source_heading': 'ENGLISH ORIGINAL｜完整英文原页',
    'translation_heading': '中文译文｜逐条对应',
    'terms_heading': '本页术语｜English → 中文',
    'guide_name': '零基础精讲',
    'bilingual_name': '逐页中英对照',
    'guide_header': '零基础精讲',
    'bilingual_header': '逐页中英对照',
    'source_footer': '来源：{filename} · 原第{page}页',
    'guide_reference_footer': '精讲版对应：第{pages}页',
}


class LayoutError(ValueError):
    pass


def require_glyphs(text):
    """Fail before publication instead of silently drawing missing characters."""
    glyphs = pdfmetrics.getFont('StudyCN').face.charToGlyph
    missing = sorted({char for char in str(text)
                      if char not in '\n\r\t' and not glyphs.get(ord(char))})
    if missing:
        details = ', '.join(f'{char!r} (U+{ord(char):04X})' for char in missing)
        raise ValueError(f'Font is missing characters: {details}. '
                         'Use --font with a font covering these characters, or render '
                         'the formula with suitable mathematical typesetting as a local image. '
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
    if spec.get('source_pdf'):
        paths.append(local_input(spec['source_pdf'], 'source_pdf'))
    for page in spec.get('guide', []):
        for block in page.get('blocks', []):
            if block.get('type') == 'source_crop':
                paths.append(local_input(block['source_pdf'], 'source_crop.source_pdf'))
            elif block.get('type') == 'image':
                paths.append(local_input(block['path'], 'image.path'))
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
    page = reader.pages[number - 1]
    page.transfer_rotation_to_content()
    media, crop = page.mediabox, page.cropbox
    left = max(float(media.left), float(crop.left))
    bottom = max(float(media.bottom), float(crop.bottom))
    right = min(float(media.right), float(crop.right))
    top = min(float(media.top), float(crop.top))
    unit = float(page.get('/UserUnit', 1))
    if not math.isfinite(unit) or unit <= 0 or right <= left or top <= bottom:
        raise ValueError('Source PDF has an invalid visible page box or UserUnit.')
    if clip is not None:
        if (not isinstance(clip, (list, tuple)) or len(clip) != 4
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in clip)):
            raise ValueError('source_crop.clip must contain four finite coordinates.')
        x0, y0, x1, y1 = [v / unit for v in clip]
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
        scale = min(placement['width'] / (right - left), placement['height'] / (top - bottom))
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
    for prefix in ('guide', 'bilingual'):
        if values[f'{prefix}_body_leading'] < values[f'{prefix}_body_size']:
            raise ValueError(f'{prefix}_body_leading must be at least {prefix}_body_size.')
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
            leading=TOKENS['guide_body_leading'], spaceAfter=7, **common),
        'heading': ParagraphStyle('heading', fontSize=13.2, leading=20,
            spaceBefore=6, spaceAfter=7, **{**common, 'textColor': C['teal']}),
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
    }


def para(text, styles, kind='body'):
    text = str(text)
    validator = SafeMarkup()
    validator.feed(text)
    validator.close()
    if validator.stack:
        raise ValueError('Unclosed paragraph formatting tag.')
    return Paragraph(text, styles[kind])


def draw_item(c, item, x, top, width, floor=56, context='page'):
    top -= getattr(getattr(item, 'style', None), 'spaceBefore', 0)
    _, height = item.wrap(width, max(1, top - floor))
    if top - height < floor:
        raise LayoutError(f'{context}: content overflow; split guide content or enlarge/reflow bilingual layout. Do not omit text.')
    item.drawOn(c, x, top - height)
    return top - height - getattr(getattr(item, 'style', None), 'spaceAfter', 0)


def table(header, rows, width, styles, ratios=None):
    count = len(header) if header else (len(rows[0]) if rows else 0)
    if not count or any(len(row) != count for row in rows):
        raise ValueError('Table must contain consistently sized rows.')
    ratios = ratios or [1] * count
    if len(ratios) != count or any(v <= 0 for v in ratios):
        raise ValueError('Table widths must be positive and match its columns.')
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
    c.drawString(margin, height - 32, header)
    c.setFillColor(C['muted']); c.drawRightString(width - margin, height - 32, kind)
    c.setStrokeColor(C['line']); c.line(margin, height - 43, width - margin, height - 43)
    c.line(margin, 40, width - margin, 40)
    c.setFont('StudyCN', 8)
    footer = spec.get('course_name', '')
    if pdfmetrics.stringWidth(footer, 'StudyCN', 8) > width - 2 * margin - 65:
        footer = spec.get('course_code', '')
    require_glyphs(footer)
    c.drawString(margin, 25, footer)
    c.drawRightString(width - margin, 25, f'{number:02d} / {total:02d}')


def guide_blocks(block, width, styles, placements):
    kind = block['type']
    if kind in ('text', 'heading', 'small', 'formula'):
        return [para(block['text'], styles, 'body' if kind == 'text' else kind)]
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
            for item in guide_blocks(block, w - 2 * m, styles, placements):
                top = draw_item(c, item, m, top, w - 2 * m, context=f'Guide page {number}')
        c.showPage()
    c.save()
    merge_sources(path, placements)


def render_bilingual(spec, path, styles):
    source = Path(spec['source_pdf']).resolve()
    original = PdfReader(io.BytesIO(source.read_bytes()))
    pages = spec['bilingual']
    labels = spec['labels']
    if not pages or [p['source_page'] for p in pages] != list(range(1, len(original.pages) + 1)):
        raise ValueError('bilingual must list every source page exactly once in original order (1..N).')
    w, h, m, lw, rx = 1190.551, 841.89, 36, 540, 608
    rw = w - rx - m
    c = canvas.Canvas(str(path), pagesize=(w, h))
    c.setTitle(f"{spec.get('course_code', '')} {spec.get('lecture', '')} {labels['bilingual_name']}")
    placements = []
    for number, page in enumerate(pages, 1):
        c.bookmarkPage(f'p{number}'); c.addOutlineEntry(page['title_zh'], f'p{number}', level=0)
        furniture(c, w, h, m, spec, number, len(pages), labels['bilingual_header'], styles)
        top = draw_item(c, para(page['title_zh'], styles, 'title'), m, h - 57, w - 2 * m)
        if page.get('title_en'):
            top = draw_item(c, para(escape(page['title_en']), styles, 'subtitle'), m, top - 4, w - 2 * m)
        top -= 14
        draw_item(c, para(escape(labels['source_heading']), styles, 'heading'), m, top, lw)
        draw_item(c, para(escape(labels['translation_heading']), styles, 'heading'), rx, top, rw)
        top -= 34
        viewport_h = 405
        placements.append({'page': number - 1, 'source_pdf': source, 'source_page': number,
                           'x': m, 'y': top - viewport_h, 'width': lw, 'height': viewport_h})
        c.setStrokeColor(C['line']); c.rect(m - 1, top - viewport_h - 1, lw + 2, viewport_h + 2)
        left_top = draw_item(c, para(escape(labels['terms_heading']), styles, 'heading'), m,
            top - viewport_h - 14, lw, floor=68, context=f'Bilingual terms page {number}')
        if page.get('terms'):
            draw_item(c, table(None, page['terms'], lw, styles, [1.2, 1]), m, left_top, lw,
                floor=68, context=f'Bilingual terms page {number}')
        right_top = top
        if not page.get('translation'):
            raise ValueError(f'Missing translation on page {number}; annotate unreadable source explicitly.')
        for text in page['translation']:
            right_top = draw_item(c, para(text, styles, 'translation'), rx, right_top, rw,
                floor=75, context=f'Bilingual translation page {number}')
        for note in page.get('notes', []):
            body = note['text']
            if note.get('source'):
                body += '<br/>' + escape(note['source'])
            right_top = draw_item(c, box(note['label'], body, rw, styles, note.get('tone', 'green')),
                rx, right_top - 7, rw, floor=75, context=f'Bilingual note page {number}')
        c.setFont('StudyCN', 9); c.setFillColor(C['muted'])
        footer = labels['source_footer'].format(filename=source.name, page=number)
        require_glyphs(footer)
        c.drawString(m, 57, footer)
        if page.get('guide_pages'):
            reference = labels['guide_reference_footer'].format(pages=page['guide_pages'])
            require_glyphs(reference)
            c.drawRightString(w - m, 57, reference)
        c.showPage()
    c.save()
    merge_sources(path, placements)


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
                render_bilingual(spec, stage, styles)
            doc = PdfReader(io.BytesIO(stage.read_bytes()))
            outputs.append({'kind': key, 'path': str(final), 'pages': len(doc.pages), 'stage': str(stage)})
        for item in outputs:
            protect_inputs(Path(item['path']), inputs)
            os.replace(item.pop('stage'), item['path'])
    print(json.dumps({'outputs': outputs, 'visual_review_required': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
