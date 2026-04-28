from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.paths import PathConfig


def test_discovers_enabled_and_disabled_skills(fake_codex_home, make_skill):
    make_skill("enabled-one", status="on", description="Enabled skill. Second sentence.")
    make_skill("disabled-one", status="off", description='"Disabled skill."')
    config = PathConfig(
        skills_dir=fake_codex_home / "skills",
        disabled_dir=fake_codex_home / "skills_disabled",
        alias_file=fake_codex_home / "skill_aliases",
    )

    skills, warnings = discover_skills(config, {"disabled-one": "group"})

    assert warnings == []
    assert [(skill.name, skill.status, skill.effective_alias, skill.description) for skill in skills] == [
        ("disabled-one", "off", "group", "Disabled skill."),
        ("enabled-one", "on", "enabled-one", "Enabled skill."),
    ]


def test_ignores_system_and_hidden_skills(fake_codex_home, make_skill):
    make_skill(".system/system-skill", status="on", description="System.")
    make_skill(".hidden", status="on", description="Hidden.")
    make_skill("external", status="on", description="External.")
    config = PathConfig(
        skills_dir=fake_codex_home / "skills",
        disabled_dir=fake_codex_home / "skills_disabled",
        alias_file=fake_codex_home / "skill_aliases",
    )

    skills, warnings = discover_skills(config, {})

    assert [skill.name for skill in skills] == ["external"]
    assert warnings == []


def test_warns_when_skill_exists_in_both_dirs(fake_codex_home, make_skill):
    make_skill("duplicate", status="on", description="On.")
    make_skill("duplicate", status="off", description="Off.")
    config = PathConfig(
        skills_dir=fake_codex_home / "skills",
        disabled_dir=fake_codex_home / "skills_disabled",
        alias_file=fake_codex_home / "skill_aliases",
    )

    skills, warnings = discover_skills(config, {})

    assert [skill.status for skill in skills if skill.name == "duplicate"] == ["on"]
    assert warnings == ["skill 'duplicate' exists in both enabled and disabled directories; using enabled copy"]
