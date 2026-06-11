from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from codex_skills_cli.managed_dirs import MANAGED_DIRS_FILENAME, derive_disabled_dir, read_managed_dirs


@dataclass(frozen=True)
class SkillDirPair:
    skills_dir: Path
    disabled_dir: Path


@dataclass(frozen=True)
class PathConfig:
    skills_dir: Path
    disabled_dir: Path
    alias_file: Path
    managed_dirs_file: Path
    skill_dirs: tuple[SkillDirPair, ...]


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser()


def _assert_distinct(pair: SkillDirPair) -> None:
    if pair.skills_dir.resolve(strict=False) == pair.disabled_dir.resolve(strict=False):
        raise ValueError("enabled and disabled skill directories must be different")


def resolve_paths(
    *,
    skills_dir: str | Path | None = None,
    disabled_dir: str | Path | None = None,
    alias_file: str | Path | None = None,
) -> tuple[PathConfig, list[str]]:
    project_dir = Path.cwd()
    codex_home = _expand(os.environ.get("CODEX_HOME", "~/.codex"))
    resolved_skills_dir = _expand(skills_dir or os.environ.get("CODEX_SKILLS_DIR", codex_home / "skills"))
    resolved_disabled_dir = _expand(
        disabled_dir or os.environ.get("CODEX_SKILLS_DISABLED_DIR", codex_home / "skills_disabled")
    )
    resolved_alias_file = _expand(
        alias_file or os.environ.get("CODEX_SKILL_ALIASES_FILE", project_dir / "skill_aliases")
    )
    managed_dirs_file = project_dir / MANAGED_DIRS_FILENAME

    default_pair = SkillDirPair(resolved_skills_dir, resolved_disabled_dir)
    _assert_distinct(default_pair)

    if skills_dir is not None or disabled_dir is not None:
        skill_dirs = (default_pair,)
        warnings: list[str] = []
    else:
        extra_dirs, warnings = read_managed_dirs(managed_dirs_file)
        skill_dirs = (default_pair, *(SkillDirPair(path, derive_disabled_dir(path)) for path in extra_dirs))
        for pair in skill_dirs:
            _assert_distinct(pair)

    return (
        PathConfig(
            skills_dir=resolved_skills_dir,
            disabled_dir=resolved_disabled_dir,
            alias_file=resolved_alias_file,
            managed_dirs_file=managed_dirs_file,
            skill_dirs=skill_dirs,
        ),
        warnings,
    )
