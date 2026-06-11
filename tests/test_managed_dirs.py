from pathlib import Path

from codex_skills_cli.managed_dirs import (
    derive_disabled_dir,
    read_managed_dirs,
    unique_paths,
    write_managed_dirs,
)


def test_derive_disabled_dir_replaces_final_skills_segment():
    assert derive_disabled_dir(Path("/tmp/home/.agents/skills")) == Path("/tmp/home/.agents/skills_disabled")


def test_derive_disabled_dir_appends_suffix_for_custom_name():
    assert derive_disabled_dir(Path("/tmp/team/custom-skills")) == Path("/tmp/team/custom-skills_disabled")


def test_read_managed_dirs_ignores_comments_blank_lines_and_duplicates(tmp_path):
    managed_file = tmp_path / "managed_dirs"
    first = tmp_path / "one" / "skills"
    second = tmp_path / "two" / "skills"
    managed_file.write_text(
        f"# comment\n\n{first}\n{first}\n{second} extra-column\n{second}\n",
        encoding="utf-8",
    )

    paths, warnings = read_managed_dirs(managed_file)

    assert paths == [first, second]
    assert warnings == [
        f"duplicate managed directory ignored: {first}",
        "invalid managed_dirs entry on line 5: expected one path",
    ]


def test_read_managed_dirs_missing_file_returns_empty(tmp_path):
    paths, warnings = read_managed_dirs(tmp_path / "managed_dirs")

    assert paths == []
    assert warnings == []


def test_write_managed_dirs_creates_parent_and_deduplicates(tmp_path):
    managed_file = tmp_path / "project" / "managed_dirs"
    first = tmp_path / "one" / "skills"
    second = tmp_path / "two" / "skills"

    write_managed_dirs(managed_file, [first, first, second])

    assert managed_file.read_text(encoding="utf-8") == f"{first}\n{second}\n"


def test_unique_paths_deduplicates_by_resolved_path(tmp_path):
    first = tmp_path / "skills"
    same = tmp_path / "." / "skills"

    assert unique_paths([first, same]) == [first]


def _skill(root: Path, name: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(f"---\nname: {name}\ndescription: {name}.\n---\n", encoding="utf-8")
    return skill_dir


def test_add_managed_dir_writes_file_and_creates_enabled_and_disabled(tmp_path):
    from codex_skills_cli.managed_dirs import add_managed_dir

    managed_file = tmp_path / "project" / "managed_dirs"
    enabled = tmp_path / "agents" / "skills"

    result = add_managed_dir(managed_file, enabled)

    assert not result.error
    assert result.changed
    assert enabled.is_dir()
    assert (tmp_path / "agents" / "skills_disabled").is_dir()
    assert managed_file.read_text(encoding="utf-8") == f"{enabled}\n"


def test_remove_managed_dir_restores_disabled_skills_and_deletes_disabled_dir(tmp_path):
    from codex_skills_cli.managed_dirs import remove_managed_dir

    managed_file = tmp_path / "project" / "managed_dirs"
    enabled = tmp_path / "agents" / "skills"
    disabled = tmp_path / "agents" / "skills_disabled"
    write_managed_dirs(managed_file, [enabled])
    _skill(disabled, "off-one")

    result = remove_managed_dir(managed_file, tmp_path / "codex" / "skills", enabled)

    assert not result.error
    assert result.changed
    assert (enabled / "off-one" / "SKILL.md").exists()
    assert not disabled.exists()
    assert managed_file.read_text(encoding="utf-8") == ""


def test_remove_managed_dir_rejects_default_dir(tmp_path):
    from codex_skills_cli.managed_dirs import remove_managed_dir

    managed_file = tmp_path / "project" / "managed_dirs"
    default = tmp_path / "codex" / "skills"

    result = remove_managed_dir(managed_file, default, default)

    assert result.error
    assert not result.changed
    assert not managed_file.exists()


def test_remove_managed_dir_rejects_restore_conflict_without_changing_file(tmp_path):
    from codex_skills_cli.managed_dirs import remove_managed_dir

    managed_file = tmp_path / "project" / "managed_dirs"
    enabled = tmp_path / "agents" / "skills"
    disabled = tmp_path / "agents" / "skills_disabled"
    write_managed_dirs(managed_file, [enabled])
    _skill(enabled, "same")
    _skill(disabled, "same")

    result = remove_managed_dir(managed_file, tmp_path / "codex" / "skills", enabled)

    assert result.error
    assert not result.changed
    assert (disabled / "same" / "SKILL.md").exists()
    assert managed_file.read_text(encoding="utf-8") == f"{enabled}\n"
