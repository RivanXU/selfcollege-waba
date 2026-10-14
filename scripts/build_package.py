#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 RivanXU. See LICENSE and NOTICE.
"""Build a skill ZIP and checksum manifest from the maintained package files."""
import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_FILES = ('SKILL.md', 'README.md', 'LICENSE', 'NOTICE',
             'THIRD_PARTY_NOTICES.md', 'requirements.txt', '.gitignore', '.gitattributes')
DIRECTORIES = ('agents', 'assets', 'examples', 'licenses', 'references', 'scripts', 'tests')
EXCLUDED = {'__pycache__', '.DS_Store'}
REQUIRED_FILES = (*TOP_FILES, 'agents/openai.yaml', 'assets/metadata.json',
                  'assets/style_tokens.json', 'assets/fonts/NotoSansSC-Regular.ttf',
                  'assets/fonts/OFL.txt', 'scripts/inline_math.py', 'scripts/render_study_pdfs.py',
                  'assets/fonts/LiberationSans-Regular.ttf', 'assets/fonts/LiberationSans-Bold.ttf',
                  'licenses/DEJAVU.txt', 'licenses/LIBERATION.txt', 'licenses/BAKOMA.txt', 'examples/demo-content.json',
                  'scripts/build_package.py', 'scripts/verify_package.py')


def package_files():
    files = [ROOT / name for name in TOP_FILES]
    for name in DIRECTORIES:
        directory = ROOT / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError(f'Expected a regular package directory: {directory}')
        for p in directory.rglob('*'):
            # rglob does not descend into symlink directories, so checking only
            # files would silently omit a linked subtree from the package.
            if p.is_symlink():
                raise ValueError(f'Package symlinks are not allowed: {p}')
            if (p.is_file() and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts)
                    and p.suffix not in {'.pyc', '.pyo'}
                    and p != ROOT / 'assets/manifest.sha256'):
                files.append(p)
    for p in files:
        if not p.is_file() or p.is_symlink():
            raise ValueError(f'Expected a regular package file: {p}')
        name = p.relative_to(ROOT).as_posix()
        if not name.isascii() or '\\' in name or any(ord(char) < 32 for char in name):
            raise ValueError(f'Package filenames must be ASCII without backslashes or control characters: {p}')
    included = {p.relative_to(ROOT).as_posix() for p in files}
    missing = set(REQUIRED_FILES) - included
    if missing:
        raise ValueError(f'Missing required package files: {", ".join(sorted(missing))}')
    return sorted(set(files), key=lambda p: p.relative_to(ROOT).as_posix())


def build(output_dir):
    # Preflight before changing the maintained manifest or published outputs.
    root = ROOT.resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir == root or root in output_dir.parents:
        raise ValueError('Choose an output directory outside the skill package.')
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('The output directory must be a directory.')
    files = package_files()
    manifest = ROOT / 'assets/manifest.sha256'
    output = output_dir / 'selfcollege-waba.zip'
    checksum = output_dir / 'selfcollege-waba.zip.sha256'
    for final in (manifest, output, checksum):
        if final.is_symlink() or (final.exists() and not final.is_file()):
            raise ValueError(f'Publication destination must be a regular file: {final}')
        if final.exists() and any(os.path.samefile(final, p) for p in files):
            raise ValueError(f'Publication must not overwrite a package input: {final}')
    destinations = (manifest, output, checksum)
    if any(left.exists() and right.exists() and os.path.samefile(left, right)
           for index, left in enumerate(destinations) for right in destinations[index + 1:]):
        raise ValueError('Manifest, ZIP and checksum destinations must be distinct files.')
    # Hash and archive the same byte snapshots, even if an input changes later.
    payload = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    lines = [f'{hashlib.sha256(data).hexdigest()}  {name}' for name, data in payload.items()]
    payload['assets/manifest.sha256'] = ('\n'.join(lines) + '\n').encode('utf-8')
    output_dir.mkdir(parents=True, exist_ok=True)
    with (tempfile.TemporaryDirectory(dir=output_dir, prefix='.package-') as work,
          tempfile.TemporaryDirectory(dir=root.parent, prefix='.package-manifest-') as manifest_work):
        work = Path(work)
        manifest_work = Path(manifest_work)
        stage = work / output.name
        with zipfile.ZipFile(stage, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(payload.items()):
                info = zipfile.ZipInfo('selfcollege-waba/' + name,
                                       date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        digest = hashlib.sha256(stage.read_bytes()).hexdigest()
        stage_checksum = work / 'checksum'
        stage_checksum.write_text(f'{digest}  {output.name}\n', encoding='ascii')
        # The manifest stage and backup share its filesystem, even when the
        # ZIP output lives on another volume.
        stage_manifest = manifest_work / 'manifest'
        stage_manifest.write_bytes(payload['assets/manifest.sha256'])
        publications = [(stage, output), (stage_checksum, checksum), (stage_manifest, manifest)]
        backups, published = {}, []
        try:
            for index, (prepared, final) in enumerate(publications):
                if final.exists():
                    backup = (manifest_work if final == manifest else work) / f'backup-{index}'
                    backup.write_bytes(final.read_bytes())
                    backups[final] = backup
                os.replace(prepared, final)
                published.append(final)
        except BaseException:
            for final in reversed(published):
                if final in backups:
                    os.replace(backups[final], final)
                else:
                    final.unlink(missing_ok=True)
            raise
    print(f'Built {output} ({len(files) + 1} files)')
    print(f'SHA-256: {digest}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    build(args.output_dir)


if __name__ == '__main__':
    main()
