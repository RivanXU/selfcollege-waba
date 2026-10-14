# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Acceptance checks for real inline vector mathematics."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader
from pypdf.generic import ContentStream
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

import inline_math
import render_study_pdfs as renderer

BASE = Path(__file__).resolve().parent


def render_paragraph(paragraph, width=400):
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=(480, 640), invariant=1)
    paragraph.wrap(width, 560)
    paragraph.drawOn(c, 36, 600 - paragraph.height)
    c.save()
    return output.getvalue()


def source_pdf(path, text):
    c = canvas.Canvas(str(path), pagesize=(720, 405), invariant=1)
    c.setFont('Helvetica', 16)
    c.drawString(30, 330, text)
    c.save()


class InlineMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        renderer.configure_style()
        pdfmetrics.registerFont(TTFont('StudyCN', str(renderer.DEFAULT_FONT)))
        pdfmetrics.registerFontFamily('StudyCN', normal='StudyCN', bold='StudyCN',
                                      italic='StudyCN', boldItalic='StudyCN')

    def setUp(self):
        self.styles = renderer.make_styles()
        self.temp = tempfile.TemporaryDirectory(prefix='qa-', dir=BASE)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_real_vector_paths_and_peer_fraction_sizes(self):
        paragraph = renderer.para(r'令\(a=100\)，then \(q=\frac{C}{P}+x^2\) remains readable.', self.styles)
        pdf = PdfReader(io.BytesIO(render_paragraph(paragraph)))
        operations = ContentStream(pdf.pages[0].get_contents(), pdf).operations
        operators = [op for _, op in operations]
        self.assertGreater(operators.count(b'c'), 5)
        self.assertGreater(operators.count(b'f') + operators.count(b'f*'), 5)
        self.assertIn(b're', operators)  # Fraction rule is a vector rectangle.
        self.assertNotIn(b'Do', operators)
        self.assertNotIn('/XObject', pdf.pages[0]['/Resources'])
        payloads = [frag.cbDefn.image for frag in paragraph.frags if hasattr(frag, 'cbDefn')]
        self.assertEqual(payloads[0].formula.font_size, self.styles['body'].fontSize)
        glyphs = payloads[1].formula.parsed.glyphs
        sizes = {chr(g[2]): g[1] for g in glyphs}
        self.assertEqual(sizes['q'], sizes['C'])
        self.assertEqual(sizes['q'], sizes['P'])
        self.assertLess(sizes['2'], sizes['q'])

    def test_width_reflow_multiline_baselines_and_split_geometry(self):
        text = r'中英混排 \(a=100\) between prose. ' * 3
        wide = renderer.para(text, self.styles)
        wide.wrap(360, 560)
        narrow = renderer.para(text, self.styles)
        narrow.wrap(140, 560)
        self.assertGreater(len(narrow.blPara.lines), len(wide.blPara.lines))
        for line in narrow.blPara.lines:
            reserved = sum(getattr(getattr(f, 'cbDefn', None), 'width', 0)
                           for f in line.words)
            self.assertLessEqual(reserved, 140)
            # The fragment's full reserve takes part in native line breaking.
            for frag in line.words:
                if hasattr(frag, 'cbDefn'):
                    self.assertGreater(frag.cbDefn.width, frag.cbDefn.image.formula.parsed.width)

        paragraph = renderer.para(
            r'首行 \(q=\frac{C}{P}\) end.<br/>第二行 \(x^2+y_1\) end.<br/>第三行 \(\frac{1}{\frac{1}{x}}\) end.',
            self.styles)
        traces = []
        real_draw = renderer.MathFormula.draw_at_baseline

        def trace(formula, c, x=0, baseline=0, text_color=None):
            traces.append((baseline + c._currentMatrix[5], inline_math.glyph_bounds(formula.parsed)))
            return real_draw(formula, c, x, baseline, text_color)

        with patch.object(renderer.MathFormula, 'draw_at_baseline', trace):
            render_paragraph(paragraph, 280)
        self.assertEqual(len(traces), 3)
        lines = paragraph.blPara.lines
        expected = 600 - lines[0].ascent
        self.assertAlmostEqual(traces[0][0], expected)
        for index in range(1, len(traces)):
            expected += lines[index - 1].descent - lines[index].ascent
            self.assertAlmostEqual(traces[index][0], expected)
            previous_bottom = traces[index - 1][0] + traces[index - 1][1][1]
            current_top = traces[index][0] + traces[index][1][3]
            self.assertGreater(previous_bottom, current_top)
        last_bottom = traces[-1][0] + traces[-1][1][1]
        self.assertGreater(last_bottom, 600 - paragraph.height)
        split = paragraph.split(280, lines[0].ascent - lines[0].descent + .1)
        # Avoid an orphaned first line while still checking a real split.
        if not split:
            split = paragraph.split(280, sum(l.ascent - l.descent for l in lines[:2]) + .1)
        self.assertEqual(len(split), 2)
        self.assertTrue(all(isinstance(p, inline_math.InlineMathParagraph) for p in split))
        for part in split:
            render_paragraph(part, 280)
        western_styles = {**self.styles, 'body': ParagraphStyle(
            'western-inline', parent=self.styles['body'], wordWrap='LTR')}
        western = renderer.para(
            r'The value \(a=100\) occupies a full vector reserve and \(q=\frac{C}{P}\) remains legible as the body reflows.',
            western_styles)
        western.wrap(300, 500)
        fraction_line = next(line for line in western.blPara.lines
                             if any(hasattr(f, 'cbDefn') and f.cbDefn.height > 20 for f in line.words))
        fraction = next(f.cbDefn for f in fraction_line.words
                        if hasattr(f, 'cbDefn') and f.cbDefn.height > 20)
        self.assertGreaterEqual(fraction_line.ascent, fraction.valign + fraction.height)
        self.assertLessEqual(fraction_line.descent, fraction.valign)
        render_paragraph(western, 300)
        with self.assertRaisesRegex(ValueError, 'exceeds available paragraph width'):
            western.wrap(20, 500)

    def test_plain_prose_and_code_preserve_existing_pdf_and_input(self):
        text = '正文 a=100、x / 2。Code: if a == 100: print(a / 2). <b>Bold</b> &amp; ordinary prose.'
        actual = renderer.para(text, self.styles)
        expected = Paragraph(text, self.styles['body'])
        self.assertIs(type(actual), Paragraph)
        self.assertEqual(actual.text, text)
        self.assertEqual(render_paragraph(actual), render_paragraph(expected))
        escaped = r'Literal code marker \\(a=100\\) stays literal.'
        self.assertIs(type(renderer.para(escaped, self.styles)), Paragraph)
        self.assertEqual(inline_math.inline_parts(escaped), [(False, escaped)])
        # Migration once confused the t of to/through/tends with a phase factor.
        # Explicit runtime runs must preserve words and their exact math source.
        rate = r'\omega_{\mathrm{d}}'
        for word in ('to', 'through', 'tends'):
            sentence = r'Rate \(' + rate + r'\) ' + word + ' the next idea.'
            paragraph = renderer.para(sentence, self.styles)
            payload = next(f.cbDefn.image for f in paragraph.frags if hasattr(f, 'cbDefn'))
            self.assertEqual(payload.formula.latex, rate)
            text = PdfReader(io.BytesIO(render_paragraph(paragraph))).pages[0].extract_text()
            self.assertIn(word + ' the next idea.', text)
            literal = 'Literal ωd ' + word + ' the next idea.'
            untouched = renderer.para(literal, self.styles)
            self.assertIs(type(untouched), Paragraph)
            self.assertEqual(render_paragraph(untouched),
                             render_paragraph(Paragraph(literal, self.styles['body'])))
        phase = renderer.para(r'The phase is \(\omega_{\mathrm{d}}t\).', self.styles)
        payload = next(f.cbDefn.image for f in phase.frags if hasattr(f, 'cbDefn'))
        self.assertEqual(payload.formula.latex, rate + 't')
        render_paragraph(phase)

    def test_malformed_unsupported_guard_and_scoped_callback_restoration(self):
        for text in [r'\(a=100', r'a=100\)', r'\(\)', r'\(a\(b\)\)',
                     r'\(\unsupportedcommand{a}\)', r'\(a\)' + '<onDraw name="anything"/>',
                     r'\(a\)' + '<img src="https://example.com/a.png"/>',
                     'missing text glyph ' + chr(0x10FFFF), r'\(' + chr(0x10FFFF) + r'\)']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                renderer.para(text, self.styles)
        paragraph = renderer.para(r'正常 \(a=100\) text.', self.styles)
        paragraph.wrap(300, 500)
        c = canvas.Canvas(io.BytesIO())
        original = c.drawImage
        with patch.object(renderer.MathFormula, 'draw_at_baseline', side_effect=RuntimeError('probe')):
            with self.assertRaisesRegex(RuntimeError, 'probe'):
                paragraph.drawOn(c, 10, 100)
        self.assertEqual(c.drawImage, original)
        self.assertNotIn('drawImage', c.__dict__)

    def test_two_output_transaction_and_source_pair_are_preserved(self):
        source, translated = self.root / 'source.pdf', self.root / 'translated.pdf'
        source_pdf(source, 'ORIGINAL SOURCE CONTENT')
        source_pdf(translated, 'EXACT TRANSLATED CONTENT')
        originals = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, translated]}
        output = self.root / 'output'
        output.mkdir()
        destinations = [output / 'InlineQA_study-guide.pdf', output / 'InlineQA_slide-companion.pdf']
        for index, path in enumerate(destinations):
            path.write_bytes(f'old output {index}'.encode())
        old = {p: p.read_bytes() for p in destinations}
        spec = {'file_stem': 'InlineQA', 'course_code': 'QA', 'lecture': 'Inline math',
                'source_pdf': str(source), 'translated_pdf': str(translated),
                'guide': [{'title': 'QA guide', 'blocks': [{'type': 'text', 'text': r'令\(a=100\)，read normally.'}]}],
                'bilingual': [{'source_page': 1, 'title': 'QA companion',
                               'notes': [{'label': 'Explanation', 'text': r'Failure \(\unsupportedcommand\)'}]}]}
        spec_path = self.root / 'spec.json'
        spec_path.write_text(json.dumps(spec), encoding='utf-8')
        argv = ['render_study_pdfs.py', '--spec', str(spec_path), '--output-dir', str(output)]
        with patch('sys.argv', argv), self.assertRaises(ValueError):
            renderer.main()
        self.assertEqual({p: p.read_bytes() for p in destinations}, old)
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}, originals)
        spec['bilingual'][0]['notes'][0]['text'] = r'令\(a=100\)，with full source slides above.'
        spec_path.write_text(json.dumps(spec), encoding='utf-8')
        with patch('sys.argv', argv), patch('sys.stdout', io.StringIO()) as result:
            renderer.main()
        report = json.loads(result.getvalue())
        self.assertEqual([o['kind'] for o in report['outputs']], ['guide', 'bilingual'])
        self.assertEqual(len(list(output.glob('*.pdf'))), 2)
        companion = PdfReader(destinations[1])
        content = companion.pages[0].extract_text()
        self.assertIn('ORIGINAL SOURCE CONTENT', content)
        self.assertIn('EXACT TRANSLATED CONTENT', content)
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}, originals)

    def test_middle_line_math_stays_atomic_after_split_and_narrow_rewrap(self):
        text = '甲' * 14 + '乙' * 4 + r'\(a=100\)' + ' 原有 空格 ' + '丙' * 20
        paragraph = renderer.para(text, self.styles)
        formula_frag = next(f for f in paragraph.frags if hasattr(f, 'cbDefn'))
        payload = formula_frag.cbDefn.image
        width = 4 * pdfmetrics.stringWidth('乙', 'StudyCN', self.styles['body'].fontSize) + payload.width
        paragraph.wrap(width, 1000)
        lines = paragraph.blPara.lines
        self.assertGreaterEqual(len(lines), 5)
        math_index = next(index for index, line in enumerate(lines)
                          if any(hasattr(f, 'cbDefn') for f in line.words))
        self.assertEqual(math_index, 2)
        self.assertTrue(hasattr(lines[math_index].words[-1], 'cbDefn'))
        available = sum(line.ascent - line.descent for line in lines[:2]) + .1
        parts = paragraph.split(width, available)
        self.assertEqual(len(parts), 2)
        remainder = parts[1]
        remainder_math = [f for f in remainder.frags if hasattr(f, 'cbDefn')]
        self.assertEqual(len(remainder_math), 1)
        self.assertEqual(remainder_math[0].text, '\ufffc')
        # Both ReportLab's line separator and all existing prose spaces have
        # normal text geometry instead of inheriting the formula callback width.
        prose = ''.join(f.text for f in remainder.frags if not hasattr(f, 'cbDefn'))
        self.assertIn(' 原有 空格 ', prose)
        index = remainder.frags.index(remainder_math[0])
        self.assertFalse(hasattr(remainder.frags[index + 1], 'cbDefn'))
        self.assertEqual(remainder.frags[index + 1].text, ' ')
        draws = []
        real_draw = renderer.MathFormula.draw_at_baseline

        def trace(formula, c, x=0, baseline=0, text_color=None):
            draws.append(formula)
            return real_draw(formula, c, x, baseline, text_color)

        with patch.object(renderer.MathFormula, 'draw_at_baseline', trace):
            render_paragraph(remainder, payload.width + .1)
        self.assertEqual(draws, [payload.formula])
        # Splitting must not alter the original line's controlled placeholder.
        self.assertEqual(lines[math_index].words[-1].text, '\ufffc')


if __name__ == '__main__':
    unittest.main(verbosity=2)
