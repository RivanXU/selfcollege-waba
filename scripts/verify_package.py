#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Check the downloaded files against the bundled SHA-256 manifest, offline."""

import hashlib
import re
import sys
from pathlib import Path, PurePosixPath


def verify(root):
    root = root.resolve()
    manifest = root / "assets" / "manifest.sha256"
    if manifest.is_symlink() or not manifest.is_file():
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
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or name in entries:
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
    print("Verification passed: all manifest-listed files are intact.")
    print("This check does not authenticate the manifest; obtain releases from the author repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
