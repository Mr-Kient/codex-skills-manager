from pathlib import Path

import pytest

from codex_skills_cli.paths import PathConfig, SkillDirPair, resolve_paths


def test_defaults_are_derived_from_home_and_project(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config == PathConfig(
        skills_dir=home / ".codex" / "skills",
        disabled_dir=home / ".codex" / "skills_disabled",
        alias_file=project / "skill_aliases",
        managed_dirs_file=project / "managed_dirs",
        skill_dirs=(
            SkillDirPair(home / ".codex" / "skills", home / ".codex" / "skills_disabled"),
        ),
    )


def test_managed_dirs_are_appended_after_default(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    extra = tmp_path / "agents" / "skills"
    project.mkdir()
    (project / "managed_dirs").write_text(f"{extra}\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.skill_dirs == (
        SkillDirPair(home / ".codex" / "skills", home / ".codex" / "skills_disabled"),
        SkillDirPair(extra, tmp_path / "agents" / "skills_disabled"),
    )


def test_env_overrides_codex_home_but_alias_defaults_to_project(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    codex_home = tmp_path / "codex"
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "off"))
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.skills_dir == tmp_path / "enabled"
    assert config.disabled_dir == tmp_path / "off"
    assert config.alias_file == project / "skill_aliases"
    assert config.skill_dirs == (SkillDirPair(tmp_path / "enabled", tmp_path / "off"),)


def test_alias_file_env_override_still_works(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "aliases"))

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.alias_file == tmp_path / "aliases"


def test_cli_options_keep_single_pair_override(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "managed_dirs").write_text(f"{tmp_path / 'extra' / 'skills'}\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "env-enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "env-off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "env-aliases"))

    config, warnings = resolve_paths(
        skills_dir=tmp_path / "cli-enabled",
        disabled_dir=tmp_path / "cli-off",
        alias_file=tmp_path / "cli-aliases",
    )

    assert warnings == []
    assert config.skills_dir == tmp_path / "cli-enabled"
    assert config.disabled_dir == tmp_path / "cli-off"
    assert config.alias_file == tmp_path / "cli-aliases"
    assert config.skill_dirs == (SkillDirPair(tmp_path / "cli-enabled", tmp_path / "cli-off"),)


def test_enabled_and_disabled_paths_must_differ(tmp_path):
    with pytest.raises(ValueError, match="must be different"):
        resolve_paths(skills_dir=tmp_path / "same", disabled_dir=tmp_path / "same")
