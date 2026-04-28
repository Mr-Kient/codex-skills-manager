from codex_skills_cli.shell import shell_init


def test_shell_init_generates_alias_functions():
    snippet = shell_init(["langchain", "agent-tools"])

    assert "langchain-on()" in snippet
    assert "skills on langchain" in snippet
    assert "agent-tools-off()" in snippet
    assert "skills off agent-tools" in snippet


def test_shell_init_skips_unsafe_aliases():
    snippet = shell_init(["good", "bad alias"])

    assert "good-on()" in snippet
    assert "bad alias-on()" not in snippet
