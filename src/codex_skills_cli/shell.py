from __future__ import annotations

from codex_skills_cli.aliases import is_alias_safe


def shell_init(alias_names: list[str]) -> str:
    lines: list[str] = []
    for alias_name in sorted(set(alias_names)):
        if not is_alias_safe(alias_name):
            continue
        lines.append(f"{alias_name}-on() {{ skills on {alias_name}; }}")
        lines.append(f"{alias_name}-off() {{ skills off {alias_name}; }}")
    return "\n".join(lines) + ("\n" if lines else "")
