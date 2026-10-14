#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 RivanXU. See LICENSE and NOTICE.
"""Build a skill ZIP and checksum manifest from the maintained package files."""
import argparse
import hashlib
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_FILES = ('SKILL.md', 'README.md', 'LICENSE', 'NOTICE',
             'THIRD_PARTY_NOTICES.md', 'requirements.txt', '.gitignore', '.gitattributes')
DIRECTORIES = ('agents', 'assets', 'examples', 'licenses', 'references', 'scripts')
EXCLUDED = {'__pycache__', '.DS_Store'}


def package_files():
    files = [ROOT / name for name in TOP_FILES]
    for name in DIRECTORIES:
        files.extend(p for p in (ROOT / name).rglob('*')
                     if p.is_file() and not any(part in EXCLUDED for part in p.parts)
                     and p.suffix not in {'.pyc', '.pyo'}
                     and p != ROOT / 'assets/manifest.sha256')
    for p in files:
        if not p.is_file() or p.is_symlink():
            raise ValueError(f'Expected a regular package file: {p}')
        if not p.relative_to(ROOT).as_posix().isascii():
            raise ValueError(f'Package filenames must be ASCII: {p}')
    return sorted(set(files), key=lambda p: p.relative_to(ROOT).as_posix())


def build(output_dir):
    files = package_files()
    manifest = ROOT / 'assets/manifest.sha256'
    lines = [f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}'
             for p in files]
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    output_dir = output_dir.resolve()
    if output_dir == ROOT or ROOT in output_dir.parents:
        raise ValueError('Choose an output directory outside the skill package.')
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / 'selfcollege-waba.zip'
    with tempfile.TemporaryDirectory(dir=output_dir, prefix='.package-') as work:
        stage = Path(work) / output.name
        with zipfile.ZipFile(stage, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for p in sorted([*files, manifest]):
                info = zipfile.ZipInfo('selfcollege-waba/' + p.relative_to(ROOT).as_posix(),
                                       date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, p.read_bytes())
        stage.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output_dir / 'selfcollege-waba.zip.sha256').write_text(
        f'{digest}  {output.name}\n', encoding='ascii')
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
