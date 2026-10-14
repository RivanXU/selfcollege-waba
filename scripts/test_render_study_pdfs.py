#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Regression checks for page parity, vector mathematics, and safe publication."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream, FloatObject, NameObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

SCRIPT = Path(__file__).with_name('render_study_pdfs.py')
module_spec = importlib.util.spec_from_file_location('study_renderer', SCRIPT)
renderer = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(renderer)


def make_pdf(path, count=1, dimensions=(720, 405)):
    c = canvas.Canvas(str(path), pagesize=dimensions)
    for page in range(count):
        c.setFillColorRGB(.1, .4, .5)
        c.rect(30, 35, 100, 50, fill=1)
        c.setFont('Helvetica', 20)
        c.drawString(30, dimensions[1] - 50, f'Matched geometry {page + 1}')
        c.showPage()
    c.save()


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        renderer.configure_style()
        pdfmetrics.registerFont(TTFont('StudyCN', str(renderer.DEFAULT_FONT)))
        pdfmetrics.registerFontFamily('StudyCN', normal='StudyCN', bold='StudyCN', italic='StudyCN', boldItalic='StudyCN')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source, self.translated = self.root / 'source.pdf', self.root / 'translated.pdf'
        make_pdf(self.source)
        make_pdf(self.translated)
        self.styles = renderer.make_styles()

    def tearDown(self):
        self.temp.cleanup()

    def paired(self):
        spec = {'source_pdf': str(self.source), 'translated_pdf': str(self.translated),
                'bilingual': [{'source_page': 1, 'title': 'Equal layouts',
                               'notes': [{'label': 'Prerequisite', 'text': 'All supplementary notes belong below both slides.'}]}]}
        renderer.configure_labels(spec)
        return spec

    def test_legacy_translation_requires_labeled_opt_in(self):
        spec = self.paired()
        del spec['translated_pdf']
        spec['bilingual'][0]['translation'] = ['Translated paragraph']
        with self.assertRaisesRegex(ValueError, 'requires translated_pdf'):
            renderer.bilingual_geometry(spec)
        spec['bilingual_mode'] = 'reflow'
        target = self.root / 'reflow.pdf'
        renderer.render_bilingual(spec, target, self.styles)
        text = PdfReader(target).pages[0].extract_text()
        self.assertIn('Reflow fallback - layout differs from source', text)

    def test_source_page_order_and_count_are_exhaustive(self):
        spec = self.paired()
        spec['bilingual'] = [{'source_page': 2}]
        with self.assertRaisesRegex(ValueError, 'every source page'):
            renderer.bilingual_geometry(spec)
        spec['bilingual'] = [{'source_page': 1}, {'source_page': 1}]
        with self.assertRaisesRegex(ValueError, 'every source page'):
            renderer.bilingual_geometry(spec)
        spec['bilingual'] = [{'source_page': 1}]
        make_pdf(self.translated, count=2)
        with self.assertRaisesRegex(ValueError, 'identical page counts'):
            renderer.bilingual_geometry(spec)

    def test_dimension_mismatch_is_rejected(self):
        make_pdf(self.translated, dimensions=(719, 405))
        with self.assertRaisesRegex(ValueError, 'visible dimensions must match'):
            renderer.bilingual_geometry(self.paired())

    def test_rotation_and_userunit_are_measured_in_physical_points(self):
        make_pdf(self.translated, dimensions=(202.5, 360))
        writer = PdfWriter(clone_from=self.translated)
        writer.pages[0].rotate(90)
        writer.pages[0][NameObject('/UserUnit')] = FloatObject(2)
        with self.translated.open('wb') as stream:
            writer.write(stream)
        _, _, _, _, report = renderer.bilingual_geometry(self.paired())
        self.assertEqual(report[0]['source_dimensions'], [720, 405])

    def test_equal_geometry_and_actual_merge_scales(self):
        target = self.root / 'paired.pdf'
        output = renderer.render_bilingual(self.paired(), target, self.styles)
        geometry = output['pages'][0]
        left, right = geometry['left_viewport'], geometry['right_viewport']
        self.assertEqual([left[k] for k in ('y', 'width', 'height')], [right[k] for k in ('y', 'width', 'height')])
        self.assertGreater(left['y'], geometry['annotation_band']['y'] + geometry['annotation_band']['height'])
        reader = PdfReader(target)
        transforms = [args for args, operator in ContentStream(reader.pages[0].get_contents(), reader).operations
                      if operator == b'cm' and abs(float(args[0]) - geometry['scale']) < .00001]
        self.assertEqual(len(transforms), 2)
        self.assertAlmostEqual(float(transforms[0][3]), float(transforms[1][3]))
        self.assertAlmostEqual(float(transforms[1][4]) - float(transforms[0][4]), right['x'] - left['x'])
        text = reader.pages[0].extract_text()
        self.assertIn('All supplementary notes belong below both slides.', text)

    def test_fraction_uses_a_real_vector_rule_and_script_positions(self):
        formula = renderer.MathFormula(r'\frac{a}{b}=c^2')
        self.assertEqual(len(formula.parsed.rects), 1)
        bar = formula.parsed.rects[0]
        positions = {glyph[2]: glyph[-1] for glyph in formula.parsed.glyphs}
        self.assertGreater(positions[ord('a')], bar[1])
        self.assertLess(positions[ord('b')], bar[1])
        self.assertGreater(positions[ord('2')], positions[ord('c')])
        target = self.root / 'formula.pdf'
        c = canvas.Canvas(str(target))
        formula.drawOn(c, 40, 650)
        c.save()
        reader = PdfReader(target)
        operations = ContentStream(reader.pages[0].get_contents(), reader).operations
        rules = [args for args, op in operations if op == b're']
        self.assertEqual(len(rules), 1)
        self.assertGreater(float(rules[0][2]), float(rules[0][3]) * 3)
        self.assertTrue(any(op == b'c' for _, op in operations))
        self.assertNotIn('/XObject', reader.pages[0]['/Resources'])

    def test_untyped_unsupported_and_slash_formulas_fail(self):
        with self.assertRaisesRegex(ValueError, 'slash fractions'):
            renderer.MathFormula('a/b')
        with self.assertRaisesRegex(ValueError, 'Unsupported mathematical'):
            renderer.MathFormula(r'\notarealcommand{x}')
        with self.assertRaisesRegex(ValueError, 'missing glyph'):
            renderer.MathFormula('a+\U0001f600')
        with self.assertRaisesRegex(ValueError, 'formula.text'):
            renderer.guide_blocks({'type': 'formula', 'text': 'a/b'}, 400, self.styles, [])
        with self.assertRaisesRegex(ValueError, 'nearby reason'):
            renderer.guide_blocks({'type': 'formula', 'latex': 'a=b'}, 400, self.styles, [])

    def test_formula_width_is_never_silently_shrunk(self):
        formula = renderer.MathFormula('a+b+c+d+e+f+g+h+i+j')
        with self.assertRaisesRegex(renderer.LayoutError, 'Font size is preserved'):
            formula.wrap(40, 500)

    def test_literal_code_units_and_source_slashes_are_preserved(self):
        for latex in (r'v=3\,\mathrm{m/s}', r'\mathtt{a/b}', r'\text{path/to/file}'):
            formula = renderer.MathFormula(latex)
            self.assertIn(ord('/'), [glyph[2] for glyph in formula.parsed.glyphs])
        for latex in ('dy/dx', r'\mathrm{d}y/\mathrm{d}x', r'\frac{a/b}{c}'):
            with self.assertRaisesRegex(ValueError, 'slash fractions'):
                renderer.MathFormula(latex)

    def test_annotation_and_guide_overflow_fail(self):
        spec = self.paired()
        spec['bilingual'][0]['notes'][0]['text'] = 'Long explanation. ' * 1500
        with self.assertRaisesRegex(renderer.LayoutError, 'Annotation band'):
            renderer.render_bilingual(spec, self.root / 'overflow.pdf', self.styles)
        spec = {'guide': [{'title': 'One concept', 'blocks': [{'type': 'text', 'text': 'Readable learning text. ' * 900}]}]}
        renderer.configure_labels(spec)
        with self.assertRaisesRegex(renderer.LayoutError, 'Guide page 1'):
            renderer.render_guide(spec, self.root / 'overflow-guide.pdf', self.styles)

    def test_failed_second_render_preserves_all_previous_outputs(self):
        outputs = self.root / 'outputs'
        outputs.mkdir()
        old_guide, old_companion = outputs / 'demo_study-guide.pdf', outputs / 'demo_slide-companion.pdf'
        old_guide.write_bytes(b'previous guide')
        old_companion.write_bytes(b'previous companion')
        spec = self.paired()
        spec.update(file_stem='demo', guide=[{'title': 'Ready guide', 'blocks': [{'type': 'text', 'text': 'This first output succeeds.'}]}])
        spec['bilingual'][0]['translation'] = ['Legacy content rejected in paired mode']
        spec_path = self.root / 'spec.json'
        spec_path.write_text(json.dumps(spec))
        completed = subprocess.run([sys.executable, str(SCRIPT), '--spec', str(spec_path), '--output-dir', str(outputs)], capture_output=True, text=True)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(old_guide.read_bytes(), b'previous guide')
        self.assertEqual(old_companion.read_bytes(), b'previous companion')
        self.assertEqual(len(list(outputs.iterdir())), 2)

    def test_publication_failure_rolls_back_replaced_files(self):
        work = self.root / 'work'; work.mkdir()
        first, second = self.root / 'first.pdf', self.root / 'second.pdf'
        first.write_bytes(b'old first'); second.write_bytes(b'old second')
        stage1, stage2 = work / 'one.pdf', work / 'two.pdf'
        stage1.write_bytes(b'new first'); stage2.write_bytes(b'new second')
        outputs = [{'path': str(first), 'stage': str(stage1)}, {'path': str(second), 'stage': str(stage2)}]
        original_replace = os.replace
        def fail_second(source, destination):
            if Path(source) == stage2:
                raise OSError('Simulated second-file publication failure')
            return original_replace(source, destination)
        with patch.object(renderer.os, 'replace', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'publication failure'):
                renderer.publish_outputs(outputs, [], work)
        self.assertEqual(first.read_bytes(), b'old first')
        self.assertEqual(second.read_bytes(), b'old second')

    def test_output_alias_and_remote_inputs_are_rejected(self):
        alias = self.root / 'alias.pdf'; os.link(self.source, alias)
        with self.assertRaisesRegex(ValueError, 'overwrite a referenced input'):
            renderer.protect_inputs(alias, [self.source])
        with self.assertRaisesRegex(ValueError, 'not a URL'):
            renderer.local_input('https://example.com/source.pdf', 'source_pdf')


if __name__ == '__main__':
    unittest.main()
