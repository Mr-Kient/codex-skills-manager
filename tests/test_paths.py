import pytest

from codex_skills_cli.paths import PathConfig, resolve_paths


def test_defaults_are_derived_from_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config = resolve_paths()

    assert config == PathConfig(
        skills_dir=home / ".codex" / "skills",
        disabled_dir=home / ".codex" / "skills_disabled",
        alias_file=home / ".codex" / "skill_aliases",
    )


def test_env_overrides_codex_home(monkeypatch, tmp_path):
    codex_home = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "aliases"))

    config = resolve_paths()

    assert config.skills_dir == tmp_path / "enabled"
    assert config.disabled_dir == tmp_path / "off"
    assert config.alias_file == tmp_path / "aliases"


def test_cli_options_override_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "env-enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "env-off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "env-aliases"))

    config = resolve_paths(
        skills_dir=tmp_path / "cli-enabled",
        disabled_dir=tmp_path / "cli-off",
        alias_file=tmp_path / "cli-aliases",
    )

    assert config.skills_dir == tmp_path / "cli-enabled"
    assert config.disabled_dir == tmp_path / "cli-off"
    assert config.alias_file == tmp_path / "cli-aliases"


def test_enabled_and_disabled_paths_must_differ(tmp_path):
    with pytest.raises(ValueError, match="must be different"):
        resolve_paths(skills_dir=tmp_path / "same", disabled_dir=tmp_path / "same")
