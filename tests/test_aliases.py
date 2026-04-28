from codex_skills_cli.aliases import (
    AliasParseError,
    alias_for,
    group_by_alias,
    is_alias_safe,
    read_aliases,
    write_aliases,
)


def test_read_aliases_ignores_comments_and_blank_lines(tmp_path):
    alias_file = tmp_path / "skill_aliases"
    alias_file.write_text(
        "# comment\n\n"
        "deep-agents-core langchain\n"
        "langgraph-fundamentals langchain\n",
        encoding="utf-8",
    )

    aliases, warnings = read_aliases(alias_file)

    assert aliases == {
        "deep-agents-core": "langchain",
        "langgraph-fundamentals": "langchain",
    }
    assert warnings == []


def test_read_aliases_warns_on_duplicate_skill_and_keeps_first(tmp_path):
    alias_file = tmp_path / "skill_aliases"
    alias_file.write_text("one group-a\none group-b\n", encoding="utf-8")

    aliases, warnings = read_aliases(alias_file)

    assert aliases == {"one": "group-a"}
    assert warnings == ["duplicate alias entry for skill 'one' on line 2; keeping first value"]


def test_read_aliases_rejects_invalid_rows(tmp_path):
    alias_file = tmp_path / "skill_aliases"
    alias_file.write_text("one two three\n", encoding="utf-8")

    try:
        read_aliases(alias_file)
    except AliasParseError as exc:
        assert "line 1" in str(exc)
    else:
        raise AssertionError("expected AliasParseError")


def test_alias_falls_back_to_skill_name():
    assert alias_for("langchain-rag", {}) == "langchain-rag"
    assert alias_for("langchain-rag", {"langchain-rag": "langchain"}) == "langchain"


def test_group_by_alias_uses_effective_aliases():
    grouped = group_by_alias(["one", "two", "three"], {"one": "group", "two": "group"})

    assert grouped == {"group": ["one", "two"], "three": ["three"]}


def test_write_aliases_sorts_entries(tmp_path):
    alias_file = tmp_path / "skill_aliases"

    write_aliases(alias_file, {"z": "group", "a": "group"})

    assert alias_file.read_text(encoding="utf-8") == "a group\nz group\n"


def test_alias_safety_matches_shell_safe_set():
    assert is_alias_safe("langchain.v1-ok")
    assert not is_alias_safe("")
    assert not is_alias_safe("bad alias")
    assert not is_alias_safe("bad/slash")
