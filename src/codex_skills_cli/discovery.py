from __future__ import annotations

from pathlib import Path

from codex_skills_cli.aliases import alias_for
from codex_skills_cli.models import Skill, SkillStatus
from codex_skills_cli.paths import PathConfig


def _description(skill_dir: Path) -> str:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return "No SKILL.md found"
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            value = stripped.removeprefix("description:").strip().strip("\"'")
            if ". " in value:
                value = value.split(". ", 1)[0] + "."
            return value[:107] + "..." if len(value) > 110 else value
    return "No description found"


def _iter_skill_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))


def discover_skills(config: PathConfig, aliases: dict[str, str]) -> tuple[list[Skill], list[str]]:
    found: dict[str, tuple[Path, SkillStatus, Path]] = {}
    warnings: list[str] = []
    for pair in config.skill_dirs:
        for status, root in (("on", pair.skills_dir), ("off", pair.disabled_dir)):
            for skill_dir in _iter_skill_dirs(root):
                if not (skill_dir / "SKILL.md").exists():
                    continue
                if skill_dir.name in found:
                    kept_path = found[skill_dir.name][0]
                    warnings.append(f"skill '{skill_dir.name}' at {skill_dir} ignored; already using {kept_path}")
                    continue
                found[skill_dir.name] = (skill_dir, status, pair.skills_dir)  # type: ignore[assignment]
    skills = [
        Skill(
            name=name,
            status=status,
            explicit_alias=aliases.get(name),
            effective_alias=alias_for(name, aliases),
            description=_description(path),
            path=path,
            managed_dir=managed_dir,
        )
        for name, (path, status, managed_dir) in found.items()
    ]
    return sorted(skills, key=lambda skill: skill.name), warnings
