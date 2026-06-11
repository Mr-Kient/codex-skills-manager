from __future__ import annotations

import os
import tempfile
from pathlib import Path


MANAGED_DIRS_FILENAME = "managed_dirs"


def derive_disabled_dir(skills_dir: Path) -> Path:
    expanded = skills_dir.expanduser()
    if expanded.name == "skills":
        return expanded.with_name("skills_disabled")
    return expanded.with_name(f"{expanded.name}_disabled")


def _path_key(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        key = _path_key(expanded)
        if key in seen:
            continue
        seen.add(key)
        unique.append(expanded)
    return unique


def read_managed_dirs(managed_dirs_file: Path) -> tuple[list[Path], list[str]]:
    if not managed_dirs_file.exists():
        return [], []
    paths: list[Path] = []
    duplicate_warnings: list[str] = []
    invalid_warnings: list[str] = []
    seen: set[Path] = set()
    for line_number, raw_line in enumerate(managed_dirs_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 1:
            invalid_warnings.append(f"invalid managed_dirs entry on line {line_number}: expected one path")
            continue
        path = Path(parts[0]).expanduser()
        key = _path_key(path)
        if key in seen:
            duplicate_warnings.append(f"duplicate managed directory ignored: {path}")
            continue
        seen.add(key)
        paths.append(path)
    return paths, [*duplicate_warnings, *invalid_warnings]


def write_managed_dirs(managed_dirs_file: Path, paths: list[Path]) -> None:
    managed_dirs_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{path.expanduser()}\n" for path in unique_paths(paths))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=managed_dirs_file.parent, delete=False) as handle:
        handle.write(content)
        tmp_name = handle.name
    os.replace(tmp_name, managed_dirs_file)
