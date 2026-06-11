from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.paths import PathConfig, SkillDirPair


def _config(fake_codex_home, *pairs):
    default_pair = SkillDirPair(fake_codex_home / "skills", fake_codex_home / "skills_disabled")
    return PathConfig(
        skills_dir=default_pair.skills_dir,
        disabled_dir=default_pair.disabled_dir,
        alias_file=fake_codex_home / "project" / "skill_aliases",
        managed_dirs_file=fake_codex_home / "project" / "managed_dirs",
        skill_dirs=(default_pair, *pairs),
    )


def test_discovers_enabled_and_disabled_skills(fake_codex_home, make_skill):
    make_skill("enabled-one", status="on", description="Enabled skill. Second sentence.")
    make_skill("disabled-one", status="off", description='"Disabled skill."')
    config = _config(fake_codex_home)

    skills, warnings = discover_skills(config, {"disabled-one": "group"})

    assert warnings == []
    assert [
        (skill.name, skill.status, skill.effective_alias, skill.description, skill.managed_dir)
        for skill in skills
    ] == [
        ("disabled-one", "off", "group", "Disabled skill.", fake_codex_home / "skills"),
        ("enabled-one", "on", "enabled-one", "Enabled skill.", fake_codex_home / "skills"),
    ]


def test_discovers_extra_managed_pair(fake_codex_home, create_skill, tmp_path):
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_enabled, "agent-on", description="Agent on.")
    create_skill(extra_disabled, "agent-off", description="Agent off.")
    config = _config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled))

    skills, warnings = discover_skills(config, {})

    assert warnings == []
    assert [(skill.name, skill.status, skill.managed_dir) for skill in skills] == [
        ("agent-off", "off", extra_enabled),
        ("agent-on", "on", extra_enabled),
    ]


def test_default_pair_wins_duplicate_names_across_pairs(fake_codex_home, make_skill, create_skill, tmp_path):
    make_skill("duplicate", status="on", description="Default.")
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_enabled, "duplicate", description="Extra.")
    config = _config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled))

    skills, warnings = discover_skills(config, {})

    assert [(skill.name, skill.managed_dir) for skill in skills] == [("duplicate", fake_codex_home / "skills")]
    assert warnings == [
        f"skill 'duplicate' at {extra_enabled / 'duplicate'} ignored; already using {fake_codex_home / 'skills' / 'duplicate'}"
    ]


def test_enabled_wins_disabled_within_same_pair(fake_codex_home, make_skill):
    make_skill("duplicate", status="on", description="On.")
    make_skill("duplicate", status="off", description="Off.")
    config = _config(fake_codex_home)

    skills, warnings = discover_skills(config, {})

    assert [skill.status for skill in skills if skill.name == "duplicate"] == ["on"]
    assert warnings == [
        f"skill 'duplicate' at {fake_codex_home / 'skills_disabled' / 'duplicate'} ignored; already using {fake_codex_home / 'skills' / 'duplicate'}"
    ]


def test_ignores_system_and_hidden_skills(fake_codex_home, make_skill):
    make_skill(".system/system-skill", status="on", description="System.")
    make_skill(".hidden", status="on", description="Hidden.")
    make_skill("external", status="on", description="External.")
    config = _config(fake_codex_home)

    skills, warnings = discover_skills(config, {})

    assert [skill.name for skill in skills] == ["external"]
    assert warnings == []
