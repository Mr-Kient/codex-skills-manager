from __future__ import annotations

import questionary


def select_alias(existing_aliases: list[str]) -> tuple[str, bool]:
    choices = [*existing_aliases, "<create new alias>"]
    selected = questionary.select("Choose alias", choices=choices).ask()
    if selected == "<create new alias>":
        alias_name = questionary.text("Alias").ask()
        return alias_name or "", True
    return selected or "", False


def select_skills(skill_names: list[str], *, preselected: list[str] | None = None) -> list[str]:
    selected = questionary.checkbox("Choose skills", choices=skill_names, default=preselected or []).ask()
    return list(selected or [])
