import pytest


@pytest.fixture
def fake_codex_home(tmp_path):
    home = tmp_path / "codex"
    (home / "skills").mkdir(parents=True)
    (home / "skills_disabled").mkdir(parents=True)
    return home


@pytest.fixture
def make_skill(fake_codex_home):
    def _make_skill(name: str, *, status: str, description: str):
        root = fake_codex_home / ("skills" if status == "on" else "skills_disabled")
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath("SKILL.md").write_text(
            f"---\nname: {name.split('/')[-1]}\ndescription: {description}\n---\n",
            encoding="utf-8",
        )
        return skill_dir

    return _make_skill
