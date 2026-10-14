#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""A failed guide must not leave a partly rebuilt public example bundle."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_examples


class ExamplePublicationTests(unittest.TestCase):
    def test_guide_failure_preserves_previous_source_target_and_previews(self):
        with tempfile.TemporaryDirectory() as work:
            destination = Path(work) / 'examples'
            destination.mkdir()
            expected = {}
            for name in ('source-slides.pdf', 'translated-slides.pdf',
                         'beginner-study-guide.pdf', 'slide-companion.pdf',
                         'demo-spec.json', 'validation.json', 'previews/explanation.png'):
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                expected[name] = ('Previous artifact: ' + name).encode('ascii')
                path.write_bytes(expected[name])
            with (patch.object(build_examples, 'OUT', destination),
                  patch.object(build_examples, 'build_guide',
                               side_effect=ValueError('Injected guide layout failure'))):
                with self.assertRaisesRegex(ValueError, 'guide layout failure'):
                    build_examples.main()
                self.assertEqual(build_examples.OUT, destination)
            self.assertEqual({p.relative_to(destination).as_posix(): p.read_bytes()
                              for p in destination.rglob('*') if p.is_file()}, expected)


if __name__ == '__main__':
    unittest.main()
