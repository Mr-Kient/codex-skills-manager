from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


MANAGED_DIRS_FILENAME = "managed_dirs"


@dataclass(frozen=True)
class ManagedDirActionResult:
    changed: bool
    error: bool
    messages: list[str]


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


def add_managed_dir(managed_dirs_file: Path, skills_dir: Path) -> ManagedDirActionResult:
    enabled = skills_dir.expanduser()
    disabled = derive_disabled_dir(enabled)
    current, warnings = read_managed_dirs(managed_dirs_file)
    enabled.mkdir(parents=True, exist_ok=True)
    disabled.mkdir(parents=True, exist_ok=True)
    if _path_key(enabled) in {_path_key(path) for path in current}:
        return ManagedDirActionResult(
            changed=False,
            error=False,
            messages=[*warnings, f"{enabled} is already managed"],
        )
    write_managed_dirs(managed_dirs_file, [*current, enabled])
    return ManagedDirActionResult(
        changed=True,
        error=False,
        messages=[*warnings, f"added managed skills directory: {enabled}"],
    )


def remove_managed_dir(managed_dirs_file: Path, default_skills_dir: Path, skills_dir: Path) -> ManagedDirActionResult:
    enabled = skills_dir.expanduser()
    disabled = derive_disabled_dir(enabled)
    if _path_key(enabled) == _path_key(default_skills_dir):
        return ManagedDirActionResult(
            changed=False,
            error=True,
            messages=[f"cannot remove default managed skills directory: {enabled}"],
        )

    current, warnings = read_managed_dirs(managed_dirs_file)
    remaining = [path for path in current if _path_key(path) != _path_key(enabled)]
    if len(remaining) == len(current):
        return ManagedDirActionResult(
            changed=False,
            error=False,
            messages=[*warnings, f"{enabled} is not managed"],
        )

    restore_sources = sorted(path for path in disabled.iterdir() if path.is_dir()) if disabled.exists() else []
    conflicts = [path.name for path in restore_sources if (enabled / path.name).exists()]
    if conflicts:
        return ManagedDirActionResult(
            changed=False,
            error=True,
            messages=[*warnings, f"cannot remove {enabled}; restore conflicts: {', '.join(conflicts)}"],
        )

    enabled.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    for source in restore_sources:
        shutil.move(str(source), str(enabled / source.name))
        restored.append(source.name)

    write_managed_dirs(managed_dirs_file, remaining)

    removed_disabled = False
    if disabled.exists() and not any(disabled.iterdir()):
        disabled.rmdir()
        removed_disabled = True

    messages = [*warnings, f"removed managed skills directory: {enabled}"]
    if restored:
        messages.append(f"restored disabled skills: {', '.join(restored)}")
    if removed_disabled:
        messages.append(f"removed disabled directory: {disabled}")
    return ManagedDirActionResult(changed=True, error=False, messages=messages)
