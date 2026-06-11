from typer.testing import CliRunner

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
