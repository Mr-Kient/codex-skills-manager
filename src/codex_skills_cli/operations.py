from __future__ import annotations

import shutil
from dataclasses import dataclass

from codex_skills_cli.aliases import group_by_alias
from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.paths import PathConfig, SkillDirPair


@dataclass(frozen=True)
class OperationResult:
    changed: list[str]
    unchanged: list[str]
    missing: list[str]
    messages: list[str]


def _pair_for_managed_dir(config: PathConfig, managed_dir) -> SkillDirPair:
    for pair in config.skill_dirs:
        if pair.skills_dir.resolve(strict=False) == managed_dir.resolve(strict=False):
            return pair
    raise ValueError(f"no managed pair found for {managed_dir}")


def resolve_targets(targets: list[str], skill_names: list[str], aliases: dict[str, str]) -> list[str]:
    grouped = group_by_alias(skill_names, aliases)
    resolved: list[str] = []
    for target in targets:
        members = grouped.get(target, [target])
        for member in members:
            if member not in resolved:
                resolved.append(member)
    return resolved


def enable_targets(config: PathConfig, targets: list[str], aliases: dict[str, str]) -> OperationResult:
    return _toggle(config, targets, aliases, enable=True)


def disable_targets(config: PathConfig, targets: list[str], aliases: dict[str, str]) -> OperationResult:
    return _toggle(config, targets, aliases, enable=False)


def _toggle(config: PathConfig, targets: list[str], aliases: dict[str, str], *, enable: bool) -> OperationResult:
    skills, _warnings = discover_skills(config, aliases)
    skills_by_name = {skill.name: skill for skill in skills}
    skill_names = [skill.name for skill in skills]
    changed: list[str] = []
    unchanged: list[str] = []
    missing: list[str] = []
    messages: list[str] = []
    desired = "ON" if enable else "OFF"
    for skill_name in resolve_targets(targets, skill_names, aliases):
        skill = skills_by_name.get(skill_name)
        if skill is None:
            missing.append(skill_name)
            messages.append(f"{skill_name} skill not found")
            continue
        if (enable and skill.status == "on") or (not enable and skill.status == "off"):
            unchanged.append(skill_name)
            messages.append(f"{skill_name} is already {desired}")
            continue

        pair = _pair_for_managed_dir(config, skill.managed_dir)
        source_root = pair.disabled_dir if enable else pair.skills_dir
        dest_root = pair.skills_dir if enable else pair.disabled_dir
        source = source_root / skill_name
        if source.is_dir():
            dest_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest_root / skill_name))
            changed.append(skill_name)
            messages.append(f"{skill_name} turned {desired}")
            continue
        missing.append(skill_name)
        messages.append(f"{skill_name} skill not found")
    return OperationResult(changed=changed, unchanged=unchanged, missing=missing, messages=messages)
