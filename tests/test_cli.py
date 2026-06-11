from typer.testing import CliRunner
from rich.console import Console

from codex_skills_cli.cli import app

runner = CliRunner()


def _path_args(fake_codex_home):
    return [
        "--skills-dir",
        str(fake_codex_home / "skills"),
        "--disabled-dir",
        str(fake_codex_home / "skills_disabled"),
        "--alias-file",
        str(fake_codex_home / "skill_aliases"),
    ]


def test_ls_displays_skills(fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")

    result = runner.invoke(app, [*_path_args(fake_codex_home), "ls"])

    assert result.exit_code == 0
    assert "one" in result.output
    assert "on" in result.output


def test_on_by_alias(fake_codex_home, make_skill):
    make_skill("one", status="off", description="One.")
    (fake_codex_home / "skill_aliases").write_text("one group\n", encoding="utf-8")

    result = runner.invoke(app, [*_path_args(fake_codex_home), "on", "group"])

    assert result.exit_code == 0
    assert "one turned ON" in result.output
    assert "restart Codex to reload skills" in result.output


def test_shell_init_outputs_helpers(fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")
    (fake_codex_home / "skill_aliases").write_text("one group\n", encoding="utf-8")

    result = runner.invoke(app, [*_path_args(fake_codex_home), "shell", "init"])

    assert result.exit_code == 0
    assert "group-on()" in result.output


def test_alias_without_subcommand_displays_help():
    result = runner.invoke(app, ["alias"])

    assert result.exit_code == 0
    assert "Manage skill aliases." in result.output
    assert "set" in result.output
    assert "unset" in result.output


def test_alias_edit_cancel_exits_cleanly(monkeypatch, fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")
    (fake_codex_home / "skill_aliases").write_text("one group\n", encoding="utf-8")
    monkeypatch.setattr("codex_skills_cli.cli.select_alias", lambda _aliases: ("", False))

    result = runner.invoke(app, [*_path_args(fake_codex_home), "alias", "edit"])

    assert result.exit_code == 0
    assert "Cancelled" in result.output


def test_add_dir_persists_project_managed_dir_and_creates_pair(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"

    result = runner.invoke(app, ["--add-dir", str(managed)])

    assert result.exit_code == 0
    assert "added managed skills directory" in result.output
    assert (project / "managed_dirs").read_text(encoding="utf-8") == f"{managed}\n"
    assert managed.is_dir()
    assert (tmp_path / "agents" / "skills_disabled").is_dir()


def test_add_dir_without_action_prints_already_managed(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")

    result = runner.invoke(app, ["--add-dir", str(managed)])

    assert result.exit_code == 0
    assert "already managed" in result.output
    assert (project / "managed_dirs").read_text(encoding="utf-8") == f"{managed}\n"


def test_remove_dir_restores_disabled_skills_and_removes_management(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"
    disabled = tmp_path / "agents" / "skills_disabled"
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")
    skill_dir = disabled / "off-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: off-one\ndescription: Off.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["--remove-dir", str(managed)])

    assert result.exit_code == 0
    assert "removed managed skills directory" in result.output
    assert (managed / "off-one" / "SKILL.md").exists()
    assert not disabled.exists()
    assert (project / "managed_dirs").read_text(encoding="utf-8") == ""


def test_remove_dir_rejects_default(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))

    result = runner.invoke(app, ["--remove-dir", str(home / ".codex" / "skills")])

    assert result.exit_code == 1
    assert "cannot remove default managed skills directory" in result.output


def test_ls_displays_dir_column_for_managed_skills(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    skill_dir = extra_enabled / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["ls"])

    assert result.exit_code == 0
    assert "DIR" in result.output
    assert "agent-one" in result.output
    assert "agents" in result.output
    assert "skills" in result.output


def test_ls_table_does_not_force_wide_output_in_captured_terminal(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    skill_dir = extra_enabled / "very-long-skill-name"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(
        "---\nname: very-long-skill-name\ndescription: Long path display.\n---\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["ls"])

    assert result.exit_code == 0
    assert max(len(line) for line in result.output.splitlines()) <= 100


def test_ls_uses_stacked_output_when_terminal_is_narrow(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr("codex_skills_cli.cli.console", Console(width=40))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    skill_dir = extra_enabled / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["ls"])

    assert result.exit_code == 0
    assert "agent-one [on]" in result.output
    assert "alias: agent-one" in result.output
    assert "dir:" in result.output
    assert "agents" in result.output
    assert "skills" in result.output
    assert "┏" not in result.output


def test_alias_ls_lists_members_with_dirs(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    (project / "skill_aliases").write_text("agent-one group\n", encoding="utf-8")
    skill_dir = extra_enabled / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["alias", "ls"])

    assert result.exit_code == 0
    assert "group:" in result.output
    assert "agent-one" in result.output
    assert str(extra_enabled) in result.output


def test_alias_set_uses_project_local_skill_aliases(monkeypatch, fake_codex_home, make_skill, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(fake_codex_home))
    make_skill("one", status="on", description="One.")
    monkeypatch.setattr("codex_skills_cli.cli.select_alias", lambda _aliases: ("group", True))
    monkeypatch.setattr("codex_skills_cli.cli.select_skills", lambda _skills: ["one"])

    result = runner.invoke(app, ["alias", "set"])

    assert result.exit_code == 0
    assert (project / "skill_aliases").read_text(encoding="utf-8") == "one group\n"
    assert not (fake_codex_home / "skill_aliases").exists()


def test_alias_file_override_still_uses_explicit_alias_file(monkeypatch, fake_codex_home, make_skill, tmp_path):
    project = tmp_path / "project"
    explicit_aliases = tmp_path / "explicit_aliases"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(fake_codex_home))
    make_skill("one", status="on", description="One.")
    monkeypatch.setattr("codex_skills_cli.cli.select_alias", lambda _aliases: ("group", True))
    monkeypatch.setattr("codex_skills_cli.cli.select_skills", lambda _skills: ["one"])

    result = runner.invoke(app, ["--alias-file", str(explicit_aliases), "alias", "set"])

    assert result.exit_code == 0
    assert explicit_aliases.read_text(encoding="utf-8") == "one group\n"
    assert not (project / "skill_aliases").exists()


def test_removed_dir_disappears_from_ls_and_alias_ls(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    managed = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")
    (project / "skill_aliases").write_text("agent-one group\n", encoding="utf-8")
    skill_dir = managed / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    remove_result = runner.invoke(app, ["--remove-dir", str(managed)])
    ls_result = runner.invoke(app, ["ls"])
    alias_result = runner.invoke(app, ["alias", "ls"])
    off_result = runner.invoke(app, ["off", "agent-one"])

    assert remove_result.exit_code == 0
    assert ls_result.exit_code == 0
    assert alias_result.exit_code == 0
    assert off_result.exit_code == 1
    assert "agent-one" not in ls_result.output
    assert "agent-one" not in alias_result.output
    assert "agent-one skill not found" in off_result.output
