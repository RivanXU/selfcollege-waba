#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Check package completeness and bundled file checksums, offline.

This detects missing, changed and unlisted files; it does not authenticate the
manifest or the author's identity. Development/runtime caches are excluded.
"""

import hashlib
import os
import re
import sys
from pathlib import Path, PurePosixPath

MANIFEST_NAME = 'assets/manifest.sha256'
REQUIRED_FILES = {
    'SKILL.md', 'README.md', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md',
    'requirements.txt', '.gitignore', '.gitattributes', 'agents/openai.yaml',
    'assets/metadata.json', 'assets/style_tokens.json',
    'assets/fonts/NotoSansSC-Regular.ttf', 'assets/fonts/OFL.txt',
    'scripts/render_study_pdfs.py', 'scripts/build_package.py',
    'scripts/verify_package.py',
}
ROOT_IGNORED = {'.git', '.venv', 'tmp', 'dist'}
IGNORED = {'__pycache__', '.DS_Store'}


def ignored(relative):
    return (relative.parts[0] in ROOT_IGNORED
            or any(part in IGNORED for part in relative.parts)
            or relative.suffix in {'.pyc', '.pyo'})


def package_inventory(root):
    """List unsigned additions without following any symlink directories."""
    files, errors = set(), []
    for directory, directories, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        kept = []
        for name in directories:
            path = parent / name
            relative = path.relative_to(root)
            if ignored(relative):
                continue
            if path.is_symlink():
                errors.append(f'Package symlinks are not allowed: {relative.as_posix()}')
            else:
                kept.append(name)
        directories[:] = kept
        for name in names:
            path = parent / name
            relative = path.relative_to(root)
            if ignored(relative):
                continue
            if path.is_symlink() or not path.is_file():
                errors.append(f'Not a regular package file: {relative.as_posix()}')
            else:
                files.add(relative.as_posix())
    return files, errors


def verify(root):
    root = root.resolve()
    manifest = root / MANIFEST_NAME
    if (manifest.is_symlink() or (root / 'assets').is_symlink()
            or not manifest.is_file()):
        return ["Missing a valid assets/manifest.sha256."]
    errors = []
    entries = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append("Invalid checksum manifest format.")
            continue
        expected, name = match.groups()
        relative = PurePosixPath(name)
        if (relative.is_absolute() or not relative.parts or ".." in relative.parts
                or "\\" in name or name != relative.as_posix() or name in entries
                or not name.isascii() or any(ord(char) < 32 for char in name)
                or name == MANIFEST_NAME or ignored(relative)):
            errors.append(f"Invalid manifest path: {name}")
            continue
        entries.add(name)
        path = root.joinpath(*relative.parts)
        if any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents):
            errors.append(f"Not a regular package file: {name}")
        elif not path.is_file():
            errors.append(f"Missing file: {name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f"File changed: {name}")
    if not entries:
        errors.append("Checksum manifest is empty.")
    for name in sorted(REQUIRED_FILES - entries):
        errors.append(f'Required package file is not listed: {name}')
    inventory, inventory_errors = package_inventory(root)
    errors.extend(inventory_errors)
    for name in sorted(inventory - entries - {MANIFEST_NAME}):
        errors.append(f'Unlisted package file: {name}')
    return errors


def main():
    root = Path(__file__).resolve().parent.parent
    try:
        errors = verify(root)
    except (OSError, UnicodeError) as error:
        errors = [f"Could not complete verification: {error}"]
    if errors:
        print("Verification failed:\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print("Verification passed: required files are present, all package files are listed, and checksums match.")
    print("This check does not authenticate the manifest; obtain releases from the author repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
