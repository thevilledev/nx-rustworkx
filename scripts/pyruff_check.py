#!/usr/bin/env python3
"""Run pyruff lint and format checks over the repository."""

from __future__ import annotations

import sys
from pathlib import Path

import pyruff

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATHS = [
    ROOT / "nx_rustworkx",
    ROOT / "tests",
    ROOT / "benches",
    ROOT / "scripts",
]


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for path in CHECK_PATHS:
        if path.is_file():
            files.append(path)
            continue
        files.extend(sorted(path.rglob("*.py")))
    return files


def main() -> int:
    failed = False
    results = pyruff.check_paths([str(path) for path in CHECK_PATHS])
    for diagnostics in results.values():
        for diagnostic in diagnostics:
            print(
                f"{diagnostic.filename}: {diagnostic.code}: {diagnostic.message}",
                file=sys.stderr,
            )
            failed = True

    for file in _iter_python_files():
        result = pyruff.format_file(file, write=False)
        if result.changed:
            print(f"{file}: would reformat", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
