from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    skills_dir: Path
    disabled_dir: Path
    alias_file: Path


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser()


def resolve_paths(
    *,
    skills_dir: str | Path | None = None,
    disabled_dir: str | Path | None = None,
    alias_file: str | Path | None = None,
) -> PathConfig:
    codex_home = _expand(os.environ.get("CODEX_HOME", "~/.codex"))
    resolved = PathConfig(
        skills_dir=_expand(skills_dir or os.environ.get("CODEX_SKILLS_DIR", codex_home / "skills")),
        disabled_dir=_expand(
            disabled_dir or os.environ.get("CODEX_SKILLS_DISABLED_DIR", codex_home / "skills_disabled")
        ),
        alias_file=_expand(alias_file or os.environ.get("CODEX_SKILL_ALIASES_FILE", codex_home / "skill_aliases")),
    )
    if resolved.skills_dir.resolve(strict=False) == resolved.disabled_dir.resolve(strict=False):
        raise ValueError("enabled and disabled skill directories must be different")
    return resolved
