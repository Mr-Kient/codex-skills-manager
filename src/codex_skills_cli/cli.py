from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codex_skills_cli.aliases import group_by_alias, is_alias_safe, read_aliases, write_aliases
from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.interactive import select_alias, select_skills
from codex_skills_cli.operations import disable_targets, enable_targets
from codex_skills_cli.paths import PathConfig, resolve_paths
from codex_skills_cli.shell import shell_init

app = typer.Typer(help="Manage external Codex skills and aliases.")
alias_app = typer.Typer(help="Manage skill aliases.")
shell_app = typer.Typer(help="Generate shell integration.")
app.add_typer(alias_app, name="alias")
app.add_typer(shell_app, name="shell")
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    skills_dir: Path | None = typer.Option(None, "--skills-dir"),
    disabled_dir: Path | None = typer.Option(None, "--disabled-dir"),
    alias_file: Path | None = typer.Option(None, "--alias-file"),
) -> None:
    """Manage external Codex skills and aliases."""
    ctx.obj = {"skills_dir": skills_dir, "disabled_dir": disabled_dir, "alias_file": alias_file}


def _config(ctx: typer.Context) -> PathConfig:
    return resolve_paths(
        skills_dir=ctx.obj.get("skills_dir"),
        disabled_dir=ctx.obj.get("disabled_dir"),
        alias_file=ctx.obj.get("alias_file"),
    )


@app.command("ls")
def list_skills(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, warnings = read_aliases(config.alias_file)
    skills, discovery_warnings = discover_skills(config, aliases)
    for warning in [*warnings, *discovery_warnings]:
        console.print(f"warning: {warning}", style="yellow")
    table = Table()
    table.add_column("ALIAS")
    table.add_column("SKILL")
    table.add_column("STATUS")
    table.add_column("DESCRIPTION")
    for skill in skills:
        table.add_row(skill.effective_alias, skill.name, skill.status, skill.description)
    console.print(table)


@app.command("on")
def on(ctx: typer.Context, targets: list[str] = typer.Argument(...)) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    result = enable_targets(config, targets, aliases)
    for message in result.messages:
        console.print(message)
    if result.changed:
        console.print("restart Codex to reload skills")
    raise typer.Exit(1 if result.missing else 0)


@app.command("off")
def off(ctx: typer.Context, targets: list[str] = typer.Argument(...)) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    result = disable_targets(config, targets, aliases)
    for message in result.messages:
        console.print(message)
    if result.changed:
        console.print("restart Codex to reload skills")
    raise typer.Exit(1 if result.missing else 0)


@alias_app.command("ls")
def alias_ls(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    grouped = group_by_alias([skill.name for skill in skills], aliases)
    for alias_name, members in grouped.items():
        console.print(f"{alias_name}: {', '.join(members)}")


@alias_app.command("set")
def alias_set(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    alias_name, _created = select_alias(sorted(set(aliases.values())))
    if not is_alias_safe(alias_name):
        raise typer.BadParameter("alias contains unsafe characters")
    selected = select_skills([skill.name for skill in skills])
    for skill_name in selected:
        aliases[skill_name] = alias_name
    write_aliases(config.alias_file, aliases)


@alias_app.command("edit")
def alias_edit(ctx: typer.Context) -> None:
    alias_set(ctx)


@alias_app.command("unset")
def alias_unset(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    selected = select_skills([skill.name for skill in skills if skill.name in aliases])
    for skill_name in selected:
        aliases.pop(skill_name, None)
    write_aliases(config.alias_file, aliases)


@shell_app.command("init")
def shell_init_command(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    console.print(shell_init([skill.effective_alias for skill in skills]), end="")
