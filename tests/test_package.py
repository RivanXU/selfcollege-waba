#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Exercise complete release archives and failure-safe package publication."""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script('build_package')
verifier = load_script('verify_package')


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.work = Path(self.temporary.name)
        self.root = self.work / 'skill'
        self.root.mkdir()
        for name in builder.DIRECTORIES:
            (self.root / name).mkdir()
        for name in builder.REQUIRED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('Fixture bytes for ' + name).encode('ascii'))
        (self.root / 'references/lesson.md').write_text('A complete lesson fixture.\n')
        (self.root / 'tests/test_fixture.py').write_text('print("fixture")\n')
        self.manifest = self.root / 'assets/manifest.sha256'
        self.manifest.write_bytes(b'previous manifest\n')
        self.output_dir = self.work / 'output'
        self.output_dir.mkdir()
        self.archive = self.output_dir / 'selfcollege-waba.zip'
        self.checksum = self.output_dir / 'selfcollege-waba.zip.sha256'
        self.root_patch = patch.object(builder, 'ROOT', self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temporary.cleanup()

    def build(self, destination=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return builder.build(destination or self.output_dir)

    def write_inventory_manifest(self):
        lines = []
        for path in sorted(self.root.rglob('*')):
            if path.is_file() and path != self.manifest:
                lines.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  '
                             f'{path.relative_to(self.root).as_posix()}')
        self.manifest.write_text('\n'.join(lines) + '\n')

    def test_archive_roundtrip_checks_every_file_and_is_reproducible(self):
        self.build()
        archive_bytes = self.archive.read_bytes()
        expected_digest = hashlib.sha256(archive_bytes).hexdigest()
        self.assertEqual(self.checksum.read_text(),
                         f'{expected_digest}  selfcollege-waba.zip\n')
        extracted = self.work / 'extracted'
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))
            self.assertIn('selfcollege-waba/tests/test_fixture.py', archive.namelist())
            archive.extractall(extracted)
        self.assertEqual(verifier.verify(extracted / 'selfcollege-waba'), [])
        self.assertEqual(verifier.verify(self.root), [])
        self.build()
        self.assertEqual(self.archive.read_bytes(), archive_bytes)

    def test_invalid_output_directory_preserves_manifest(self):
        previous = self.manifest.read_bytes()
        for destination in (self.root, self.root / 'nested-output'):
            with self.subTest(destination=destination):
                with self.assertRaisesRegex(ValueError, 'outside the skill package'):
                    self.build(destination)
                self.assertEqual(self.manifest.read_bytes(), previous)
                self.assertFalse((self.root / 'nested-output').exists())
        destination = self.work / 'not-a-directory'
        destination.write_text('existing file')
        with self.assertRaisesRegex(ValueError, 'must be a directory'):
            self.build(destination)
        self.assertEqual(self.manifest.read_bytes(), previous)

    def test_missing_required_asset_prevents_build(self):
        (self.root / 'assets/fonts/NotoSansSC-Regular.ttf').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing required package files'):
            self.build()
        self.assertEqual(self.manifest.read_bytes(), b'previous manifest\n')

    def test_filename_cannot_create_an_invalid_manifest_record(self):
        for name in ('noncanonical\\file.py', 'split\nrecord.py', '\u4e2d\u6587.py'):
            with self.subTest(name=name):
                path = self.root / 'scripts' / name
                path.write_text('unexpected code')
                with self.assertRaisesRegex(ValueError, 'filenames must be ASCII'):
                    self.build()
                self.assertEqual(self.manifest.read_bytes(), b'previous manifest\n')
                path.unlink()

    def test_symlink_directories_and_files_are_rejected(self):
        target = self.work / 'external'
        target.mkdir()
        (target / 'code.py').write_text('external bytes')
        link = self.root / 'scripts/linked-directory'
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            self.build()
        link.unlink()
        link.symlink_to(target / 'code.py')
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            self.build()
        link.unlink()
        link.symlink_to(target / 'missing.py')
        with self.assertRaisesRegex(ValueError, 'symlinks are not allowed'):
            self.build()

    def test_symlink_or_input_alias_publication_destination_is_rejected(self):
        self.archive.symlink_to(self.root / 'README.md')
        with self.assertRaisesRegex(ValueError, 'regular file'):
            self.build()
        self.archive.unlink()
        os.link(self.root / 'README.md', self.archive)
        with self.assertRaisesRegex(ValueError, 'overwrite a package input'):
            self.build()
        self.archive.unlink()
        os.link(self.manifest, self.archive)
        with self.assertRaisesRegex(ValueError, 'must be distinct files'):
            self.build()

    def test_zip_failure_preserves_manifest_and_previous_deliverables(self):
        self.archive.write_bytes(b'previous archive')
        self.checksum.write_bytes(b'previous checksum')
        with patch.object(zipfile.ZipFile, 'writestr', side_effect=OSError('ZIP write failure')):
            with self.assertRaisesRegex(OSError, 'ZIP write failure'):
                self.build()
        self.assertEqual(self.manifest.read_bytes(), b'previous manifest\n')
        self.assertEqual(self.archive.read_bytes(), b'previous archive')
        self.assertEqual(self.checksum.read_bytes(), b'previous checksum')
        self.assertEqual(sorted(path.name for path in self.output_dir.iterdir()),
                         ['selfcollege-waba.zip', 'selfcollege-waba.zip.sha256'])

    def test_publication_failure_rolls_back_archive_checksum_and_manifest(self):
        original_replace = os.replace
        for failing_stage in ('checksum', 'manifest'):
            with self.subTest(failing_stage=failing_stage):
                self.archive.write_bytes(b'previous archive')
                self.checksum.write_bytes(b'previous checksum')
                self.manifest.write_bytes(b'previous manifest\n')

                def fail(source, destination):
                    if Path(source).name == failing_stage:
                        raise OSError('Injected publication failure')
                    return original_replace(source, destination)

                with patch.object(builder.os, 'replace', side_effect=fail):
                    with self.assertRaisesRegex(OSError, 'Injected publication failure'):
                        self.build()
                self.assertEqual(self.archive.read_bytes(), b'previous archive')
                self.assertEqual(self.checksum.read_bytes(), b'previous checksum')
                self.assertEqual(self.manifest.read_bytes(), b'previous manifest\n')

    def test_failure_removes_newly_published_archive(self):
        original_replace = os.replace

        def fail(source, destination):
            if Path(source).name == 'checksum':
                raise OSError('Injected publication failure')
            return original_replace(source, destination)

        with patch.object(builder.os, 'replace', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'Injected publication failure'):
                self.build()
        self.assertFalse(self.archive.exists())
        self.assertFalse(self.checksum.exists())
        self.assertEqual(self.manifest.read_bytes(), b'previous manifest\n')

    def test_changed_and_missing_files_fail_verification(self):
        self.build()
        path = self.root / 'references/lesson.md'
        path.write_text('Changed lesson.\n')
        self.assertIn('File changed: references/lesson.md', verifier.verify(self.root))
        path.unlink()
        self.assertIn('Missing file: references/lesson.md', verifier.verify(self.root))

    def test_omitted_entrypoints_and_unlisted_code_fail_verification(self):
        minimal = self.work / 'minimal'
        (minimal / 'assets').mkdir(parents=True)
        (minimal / 'README.md').write_text('README only')
        digest = hashlib.sha256((minimal / 'README.md').read_bytes()).hexdigest()
        (minimal / 'assets/manifest.sha256').write_text(f'{digest}  README.md\n')
        self.assertIn('Required package file is not listed: SKILL.md', verifier.verify(minimal))
        self.build()
        (self.root / 'scripts/unlisted.py').write_text('Unexpected code')
        (self.root / 'unlisted-root.py').write_text('Unexpected root code')
        errors = verifier.verify(self.root)
        self.assertIn('Unlisted package file: scripts/unlisted.py', errors)
        self.assertIn('Unlisted package file: unlisted-root.py', errors)

    def test_manifest_aliases_duplicates_and_unsafe_paths_are_rejected(self):
        self.build()
        previous = self.manifest.read_text()
        digest = hashlib.sha256((self.root / 'README.md').read_bytes()).hexdigest()
        for name in ('README.md', './README.md', 'assets//style_tokens.json',
                     '../README.md', '/README.md', 'assets\\style_tokens.json',
                     '\u975e\u82f1\u6587.md', 'assets/manifest.sha256'):
            with self.subTest(name=name):
                self.manifest.write_text(previous + f'{digest}  {name}\n')
                self.assertIn(f'Invalid manifest path: {name}', verifier.verify(self.root))

    def test_listed_and_unlisted_symlinks_are_rejected(self):
        self.build()
        external = self.work / 'external-code.py'
        external.write_text('external')
        unlisted = self.root / 'scripts/unlisted-link.py'
        unlisted.symlink_to(external)
        self.assertTrue(any('unlisted-link.py' in message
                            and 'regular package file' in message
                            for message in verifier.verify(self.root)))
        unlisted.unlink()
        linked_directory = self.root / 'scripts/linked-directory'
        linked_directory.symlink_to(self.work / 'output', target_is_directory=True)
        self.assertTrue(any('linked-directory' in message and 'symlinks' in message
                            for message in verifier.verify(self.root)))
        linked_directory.unlink()
        listed = self.root / 'README.md'
        previous = listed.read_bytes()
        listed.unlink()
        external.write_bytes(previous)
        listed.symlink_to(external)
        self.assertIn('Not a regular package file: README.md', verifier.verify(self.root))

    def test_documented_development_and_runtime_noise_is_excluded(self):
        for name in ('.git/config', '.venv/local.txt', 'tmp/preview.png',
                     'dist/build.zip', 'scripts/__pycache__/cache.pyc',
                     'examples/.DS_Store'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('local generated bytes')
        self.build()
        self.assertEqual(verifier.verify(self.root), [])
        with zipfile.ZipFile(self.archive) as archive:
            self.assertFalse(any('__pycache__' in name or '.DS_Store' in name
                                 for name in archive.namelist()))


if __name__ == '__main__':
    unittest.main()
