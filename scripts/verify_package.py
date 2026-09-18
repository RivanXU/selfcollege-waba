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
        return ["缺少有效的 assets/manifest.sha256。"]
    errors = []
    entries = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append("校验清单格式无效。")
            continue
        expected, name = match.groups()
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or name in entries:
            errors.append(f"无效的清单路径：{name}")
            continue
        entries.add(name)
        path = root.joinpath(*relative.parts)
        if any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents):
            errors.append(f"不是发布包中的普通文件：{name}")
        elif not path.is_file():
            errors.append(f"缺少文件：{name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f"文件已更改：{name}")
    if not entries:
        errors.append("校验清单为空。")
    return errors


def main():
    root = Path(__file__).resolve().parent.parent
    try:
        errors = verify(root)
    except (OSError, UnicodeError) as error:
        errors = [f"无法完成校验：{error}"]
    if errors:
        print("校验未通过：\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print("校验通过：清单中列出的所有文件均完整且一致。")
    print("此检查不验证清单本身的来源；请从作者仓库获取发布包。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
