from codex_skills_cli.operations import disable_targets, enable_targets, resolve_targets
from codex_skills_cli.paths import PathConfig


def _config(home):
    return PathConfig(
        skills_dir=home / "skills",
        disabled_dir=home / "skills_disabled",
        alias_file=home / "skill_aliases",
    )


def test_resolves_alias_to_multiple_skills(fake_codex_home, make_skill):
    make_skill("one", status="off", description="One.")
    make_skill("two", status="off", description="Two.")
    skills = ["one", "two"]

    assert resolve_targets(["group"], skills, {"one": "group", "two": "group"}) == ["one", "two"]


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


def test_enable_reports_missing_target(fake_codex_home):
    result = enable_targets(_config(fake_codex_home), ["missing"], {})

    assert result.changed == []
    assert result.missing == ["missing"]
    assert result.messages == ["missing skill not found"]
