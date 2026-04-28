from codex_skills_cli.interactive import select_skills


def test_select_skills_omits_default_when_nothing_is_preselected(monkeypatch):
    captured = {}

    class Prompt:
        def ask(self):
            return ["one"]

    def fake_checkbox(message, *, choices, **kwargs):
        captured["message"] = message
        captured["choices"] = choices
        captured["kwargs"] = kwargs
        return Prompt()

    monkeypatch.setattr("codex_skills_cli.interactive.questionary.checkbox", fake_checkbox)

    selected = select_skills(["one"])

    assert selected == ["one"]
    assert captured == {
        "message": "Choose skills",
        "choices": ["one"],
        "kwargs": {},
    }


def test_select_skills_passes_default_when_preselected(monkeypatch):
    captured = {}

    class Prompt:
        def ask(self):
            return ["one"]

    def fake_checkbox(message, *, choices, **kwargs):
        captured["kwargs"] = kwargs
        return Prompt()

    monkeypatch.setattr("codex_skills_cli.interactive.questionary.checkbox", fake_checkbox)

    selected = select_skills(["one", "two"], preselected=["one"])

    assert selected == ["one"]
    assert captured["kwargs"] == {"default": ["one"]}
