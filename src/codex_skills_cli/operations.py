from __future__ import annotations

import shutil
from dataclasses import dataclass

from codex_skills_cli.aliases import group_by_alias
from codex_skills_cli.paths import PathConfig


@dataclass(frozen=True)
class OperationResult:
    changed: list[str]
    unchanged: list[str]
    missing: list[str]
    messages: list[str]


def _all_skill_names(config: PathConfig) -> list[str]:
    names = set()
    for root in (config.skills_dir, config.disabled_dir):
        if root.exists():
            names.update(path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))
    return sorted(names)


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
    skill_names = _all_skill_names(config)
    changed: list[str] = []
    unchanged: list[str] = []
    missing: list[str] = []
    messages: list[str] = []
    source_root = config.disabled_dir if enable else config.skills_dir
    dest_root = config.skills_dir if enable else config.disabled_dir
    already_root = config.skills_dir if enable else config.disabled_dir
    desired = "ON" if enable else "OFF"
    for skill in resolve_targets(targets, skill_names, aliases):
        if (already_root / skill).is_dir():
            unchanged.append(skill)
            messages.append(f"{skill} is already {desired}")
            continue
        source = source_root / skill
        if source.is_dir():
            dest_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest_root / skill))
            changed.append(skill)
            messages.append(f"{skill} turned {desired}")
            continue
        missing.append(skill)
        messages.append(f"{skill} skill not found")
    return OperationResult(changed=changed, unchanged=unchanged, missing=missing, messages=messages)
