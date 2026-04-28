from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

SAFE_ALIAS = re.compile(r"^[A-Za-z0-9._-]+$")


class AliasParseError(ValueError):
    pass


def is_alias_safe(alias: str) -> bool:
    return bool(SAFE_ALIAS.fullmatch(alias))


def read_aliases(alias_file: Path) -> tuple[dict[str, str], list[str]]:
    if not alias_file.exists():
        return {}, []
    aliases: dict[str, str] = {}
    warnings: list[str] = []
    for line_number, raw_line in enumerate(alias_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise AliasParseError(f"invalid alias entry on line {line_number}: expected 'skill alias'")
        skill, alias = parts
        if skill in aliases:
            warnings.append(f"duplicate alias entry for skill '{skill}' on line {line_number}; keeping first value")
            continue
        aliases[skill] = alias
    return aliases, warnings


def write_aliases(alias_file: Path, aliases: dict[str, str]) -> None:
    alias_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{skill} {alias}\n" for skill, alias in sorted(aliases.items()))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=alias_file.parent, delete=False) as handle:
        handle.write(content)
        tmp_name = handle.name
    os.replace(tmp_name, alias_file)


def alias_for(skill_name: str, aliases: dict[str, str]) -> str:
    return aliases.get(skill_name, skill_name)


def group_by_alias(skill_names: list[str], aliases: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for skill_name in skill_names:
        grouped.setdefault(alias_for(skill_name, aliases), []).append(skill_name)
    return grouped
