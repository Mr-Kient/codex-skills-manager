from codex_skills_cli.operations import disable_targets, enable_targets, resolve_targets
from codex_skills_cli.paths import PathConfig, SkillDirPair


def _config(home, *pairs):
    default_pair = SkillDirPair(home / "skills", home / "skills_disabled")
    return PathConfig(
        skills_dir=default_pair.skills_dir,
        disabled_dir=default_pair.disabled_dir,
        alias_file=home / "project" / "skill_aliases",
        managed_dirs_file=home / "project" / "managed_dirs",
        skill_dirs=(default_pair, *pairs),
    )


def test_resolves_alias_to_multiple_skills():
    resolved = resolve_targets(["group"], ["one", "two", "three"], {"one": "group", "two": "group"})

    assert resolved == ["one", "two"]


def test_enable_by_alias_moves_all_disabled_members(fake_codex_home, make_skill):
    make_skill("one", status="off", description="One.")
    make_skill("two", status="off", description="Two.")

    result = enable_targets(_config(fake_codex_home), ["group"], {"one": "group", "two": "group"})

    assert result.changed == ["one", "two"]
    assert (fake_codex_home / "skills" / "one").is_dir()
    assert (fake_codex_home / "skills" / "two").is_dir()
    assert not (fake_codex_home / "skills_disabled" / "one").exists()


def test_disable_by_skill_moves_enabled_skill(fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")

    result = disable_targets(_config(fake_codex_home), ["one"], {})

    assert result.changed == ["one"]
    assert (fake_codex_home / "skills_disabled" / "one").is_dir()
    assert not (fake_codex_home / "skills" / "one").exists()


def test_enable_uses_owning_extra_pair(fake_codex_home, create_skill, tmp_path):
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_disabled, "agent-off", description="Agent off.")

    result = enable_targets(_config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled)), ["agent-off"], {})

    assert result.changed == ["agent-off"]
    assert (extra_enabled / "agent-off" / "SKILL.md").exists()
    assert not (fake_codex_home / "skills" / "agent-off").exists()


def test_disable_uses_owning_extra_pair(fake_codex_home, create_skill, tmp_path):
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_enabled, "agent-on", description="Agent on.")

    result = disable_targets(_config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled)), ["agent-on"], {})

    assert result.changed == ["agent-on"]
    assert (extra_disabled / "agent-on" / "SKILL.md").exists()
    assert not (fake_codex_home / "skills_disabled" / "agent-on").exists()


def test_enable_reports_missing_target(fake_codex_home):
    result = enable_targets(_config(fake_codex_home), ["missing"], {})

    assert result.missing == ["missing"]
    assert result.messages == ["missing skill not found"]
