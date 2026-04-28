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
