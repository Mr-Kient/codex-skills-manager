# Skills CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI named `skills` for managing external Codex skill aliases and enabled/disabled state.

**Architecture:** Core behavior lives in importable modules with no Typer dependency. Typer, Rich, and Questionary are thin adapters over the core API so a future Rust rewrite can preserve the same behavior contract.

**Tech Stack:** Python 3.12, uv, Typer, Rich, Questionary, pytest.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, console script, pytest configuration.
- Create `README.md`: short usage and development notes.
- Create `src/codex_skills_cli/__init__.py`: package version.
- Create `src/codex_skills_cli/models.py`: dataclasses and status literals.
- Create `src/codex_skills_cli/paths.py`: path configuration precedence and validation.
- Create `src/codex_skills_cli/aliases.py`: alias file parsing, validation, grouping, and atomic writes.
- Create `src/codex_skills_cli/discovery.py`: skill discovery and description parsing.
- Create `src/codex_skills_cli/operations.py`: target resolution and directory moves.
- Create `src/codex_skills_cli/shell.py`: bash/zsh shell snippet generation.
- Create `src/codex_skills_cli/interactive.py`: Questionary-based multi-select flows.
- Create `src/codex_skills_cli/cli.py`: Typer command surface and Rich output.
- Create `tests/conftest.py`: fake Codex home fixtures and helper builders.
- Create `tests/test_paths.py`: path precedence and validation tests.
- Create `tests/test_aliases.py`: alias parsing, fallback, grouping, and writes.
- Create `tests/test_discovery.py`: discovery and description tests.
- Create `tests/test_operations.py`: enable/disable and target resolution tests.
- Create `tests/test_shell.py`: shell init output tests.
- Create `tests/test_cli.py`: CLI smoke and console-script behavior tests.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/codex_skills_cli/__init__.py`
- Test: packaging smoke via `uv run skills --help`

- [ ] **Step 1: Create package metadata**

```toml
[project]
name = "codex-skills-cli"
version = "0.1.0"
description = "Manage external Codex skills and aliases"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "questionary>=2.0.1",
    "rich>=13.7.0",
    "typer>=0.12.3",
]

[project.scripts]
skills = "codex_skills_cli.cli:app"

[dependency-groups]
dev = [
    "pytest>=8.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create the initial package and README**

```python
__version__ = "0.1.0"
```

```markdown
# Codex Skills CLI

Manage external Codex skills and aliases.

## Development

```bash
uv sync --dev
uv run pytest
uv run skills --help
```

Installed usage must run as `skills` from `PATH`; users do not activate this
project's virtual environment.
```

- [ ] **Step 3: Add a minimal Typer app**

```python
import typer

app = typer.Typer(help="Manage external Codex skills and aliases.")
```

- [ ] **Step 4: Sync and verify the console script**

Run: `UV_CACHE_DIR=/tmp/uv-cache uv sync --dev`

Expected: dependencies install successfully into `.venv`.

Run: `uv run skills --help`

Expected: exit 0 and help text includes `Manage external Codex skills and aliases.`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/codex_skills_cli/__init__.py src/codex_skills_cli/cli.py uv.lock
git commit -m "chore: scaffold skills CLI package"
```

## Task 2: Path Configuration

**Files:**
- Create: `src/codex_skills_cli/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write failing path tests**

```python
from pathlib import Path

import pytest

from codex_skills_cli.paths import PathConfig, resolve_paths


def test_defaults_are_derived_from_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config = resolve_paths()

    assert config == PathConfig(
        skills_dir=home / ".codex" / "skills",
        disabled_dir=home / ".codex" / "skills_disabled",
        alias_file=home / ".codex" / "skill_aliases",
    )


def test_env_overrides_codex_home(monkeypatch, tmp_path):
    codex_home = tmp_path / "codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "aliases"))

    config = resolve_paths()

    assert config.skills_dir == tmp_path / "enabled"
    assert config.disabled_dir == tmp_path / "off"
    assert config.alias_file == tmp_path / "aliases"


def test_cli_options_override_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "env-enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "env-off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "env-aliases"))

    config = resolve_paths(
        skills_dir=tmp_path / "cli-enabled",
        disabled_dir=tmp_path / "cli-off",
        alias_file=tmp_path / "cli-aliases",
    )

    assert config.skills_dir == tmp_path / "cli-enabled"
    assert config.disabled_dir == tmp_path / "cli-off"
    assert config.alias_file == tmp_path / "cli-aliases"


def test_enabled_and_disabled_paths_must_differ(tmp_path):
    with pytest.raises(ValueError, match="must be different"):
        resolve_paths(skills_dir=tmp_path / "same", disabled_dir=tmp_path / "same")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_paths.py -v`

Expected: FAIL because `codex_skills_cli.paths` does not exist.

- [ ] **Step 3: Implement path resolution**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    skills_dir: Path
    disabled_dir: Path
    alias_file: Path


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser()


def resolve_paths(
    *,
    skills_dir: str | Path | None = None,
    disabled_dir: str | Path | None = None,
    alias_file: str | Path | None = None,
) -> PathConfig:
    codex_home = _expand(os.environ.get("CODEX_HOME", "~/.codex"))
    resolved = PathConfig(
        skills_dir=_expand(skills_dir or os.environ.get("CODEX_SKILLS_DIR", codex_home / "skills")),
        disabled_dir=_expand(
            disabled_dir or os.environ.get("CODEX_SKILLS_DISABLED_DIR", codex_home / "skills_disabled")
        ),
        alias_file=_expand(alias_file or os.environ.get("CODEX_SKILL_ALIASES_FILE", codex_home / "skill_aliases")),
    )
    if resolved.skills_dir.resolve(strict=False) == resolved.disabled_dir.resolve(strict=False):
        raise ValueError("enabled and disabled skill directories must be different")
    return resolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_paths.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/paths.py tests/test_paths.py
git commit -m "feat: add skills path configuration"
```

## Task 3: Alias File Handling

**Files:**
- Create: `src/codex_skills_cli/models.py`
- Create: `src/codex_skills_cli/aliases.py`
- Test: `tests/test_aliases.py`

- [ ] **Step 1: Write failing alias tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_aliases.py -v`

Expected: FAIL because `codex_skills_cli.aliases` does not exist.

- [ ] **Step 3: Implement alias model and functions**

Create `models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SkillStatus = Literal["on", "off", "missing"]


@dataclass(frozen=True)
class Skill:
    name: str
    status: SkillStatus
    explicit_alias: str | None
    effective_alias: str
    description: str
    path: Path | None
```

Create `aliases.py`:

```python
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

SAFE_ALIAS = re.compile(r"^[A-Za-z0-9._-]+$")


class AliasParseError(ValueError):
    pass


def is_alias_safe(alias: str) -> bool:
    return bool(SAFE_ALIAS.fullmatch(alias))


def read_aliases(alias_file: Path) -> tuple[dict[str, str], list[str]]:
    if not alias_file.exists():
        return {}, []
    aliases: dict[str, str] = {}
    warnings: list[str] = []
    for line_number, raw_line in enumerate(alias_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise AliasParseError(f"invalid alias entry on line {line_number}: expected 'skill alias'")
        skill, alias = parts
        if skill in aliases:
            warnings.append(f"duplicate alias entry for skill '{skill}' on line {line_number}; keeping first value")
            continue
        aliases[skill] = alias
    return aliases, warnings


def write_aliases(alias_file: Path, aliases: dict[str, str]) -> None:
    alias_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{skill} {alias}\n" for skill, alias in sorted(aliases.items()))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=alias_file.parent, delete=False) as handle:
        handle.write(content)
        tmp_name = handle.name
    os.replace(tmp_name, alias_file)


def alias_for(skill_name: str, aliases: dict[str, str]) -> str:
    return aliases.get(skill_name, skill_name)


def group_by_alias(skill_names: list[str], aliases: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for skill_name in skill_names:
        grouped.setdefault(alias_for(skill_name, aliases), []).append(skill_name)
    return grouped
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_aliases.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/models.py src/codex_skills_cli/aliases.py tests/test_aliases.py
git commit -m "feat: add skill alias file handling"
```

## Task 4: Skill Discovery

**Files:**
- Create: `src/codex_skills_cli/discovery.py`
- Create: `tests/conftest.py`
- Test: `tests/test_discovery.py`

- [ ] **Step 1: Write failing discovery tests**

```python
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
```

Create `conftest.py` helper:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discovery.py -v`

Expected: FAIL because `codex_skills_cli.discovery` does not exist.

- [ ] **Step 3: Implement skill discovery**

```python
from __future__ import annotations

from pathlib import Path

from codex_skills_cli.aliases import alias_for
from codex_skills_cli.models import Skill, SkillStatus
from codex_skills_cli.paths import PathConfig


def _description(skill_dir: Path) -> str:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return "No SKILL.md found"
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            value = stripped.removeprefix("description:").strip().strip("\"'")
            if ". " in value:
                value = value.split(". ", 1)[0] + "."
            return value[:107] + "..." if len(value) > 110 else value
    return "No description found"


def _iter_skill_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))


def discover_skills(config: PathConfig, aliases: dict[str, str]) -> tuple[list[Skill], list[str]]:
    found: dict[str, tuple[Path, SkillStatus]] = {}
    warnings: list[str] = []
    for status, root in (("on", config.skills_dir), ("off", config.disabled_dir)):
        for skill_dir in _iter_skill_dirs(root):
            if not (skill_dir / "SKILL.md").exists():
                continue
            if skill_dir.name in found:
                warnings.append(
                    f"skill '{skill_dir.name}' exists in both enabled and disabled directories; using enabled copy"
                )
                continue
            found[skill_dir.name] = (skill_dir, status)  # type: ignore[assignment]
    skills = [
        Skill(
            name=name,
            status=status,
            explicit_alias=aliases.get(name),
            effective_alias=alias_for(name, aliases),
            description=_description(path),
            path=path,
        )
        for name, (path, status) in found.items()
    ]
    return sorted(skills, key=lambda skill: skill.name), warnings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discovery.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/discovery.py tests/conftest.py tests/test_discovery.py
git commit -m "feat: discover external codex skills"
```

## Task 5: Enable and Disable Operations

**Files:**
- Create: `src/codex_skills_cli/operations.py`
- Test: `tests/test_operations.py`

- [ ] **Step 1: Write failing operation tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_operations.py -v`

Expected: FAIL because `codex_skills_cli.operations` does not exist.

- [ ] **Step 3: Implement operations**

```python
from __future__ import annotations

import shutil
from dataclasses import dataclass

from codex_skills_cli.aliases import group_by_alias
from codex_skills_cli.paths import PathConfig


@dataclass(frozen=True)
class OperationResult:
    changed: list[str]
    unchanged: list[str]
    missing: list[str]
    messages: list[str]


def _all_skill_names(config: PathConfig) -> list[str]:
    names = set()
    for root in (config.skills_dir, config.disabled_dir):
        if root.exists():
            names.update(path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))
    return sorted(names)


def resolve_targets(targets: list[str], skill_names: list[str], aliases: dict[str, str]) -> list[str]:
    grouped = group_by_alias(skill_names, aliases)
    resolved: list[str] = []
    for target in targets:
        members = grouped.get(target, [target])
        for member in members:
            if member not in resolved:
                resolved.append(member)
    return resolved


def enable_targets(config: PathConfig, targets: list[str], aliases: dict[str, str]) -> OperationResult:
    return _toggle(config, targets, aliases, enable=True)


def disable_targets(config: PathConfig, targets: list[str], aliases: dict[str, str]) -> OperationResult:
    return _toggle(config, targets, aliases, enable=False)


def _toggle(config: PathConfig, targets: list[str], aliases: dict[str, str], *, enable: bool) -> OperationResult:
    skill_names = _all_skill_names(config)
    changed: list[str] = []
    unchanged: list[str] = []
    missing: list[str] = []
    messages: list[str] = []
    source_root = config.disabled_dir if enable else config.skills_dir
    dest_root = config.skills_dir if enable else config.disabled_dir
    already_root = config.skills_dir if enable else config.disabled_dir
    desired = "ON" if enable else "OFF"
    for skill in resolve_targets(targets, skill_names, aliases):
        if (already_root / skill).is_dir():
            unchanged.append(skill)
            messages.append(f"{skill} is already {desired}")
            continue
        source = source_root / skill
        if source.is_dir():
            dest_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest_root / skill))
            changed.append(skill)
            messages.append(f"{skill} turned {desired}")
            continue
        missing.append(skill)
        messages.append(f"{skill} skill not found")
    return OperationResult(changed=changed, unchanged=unchanged, missing=missing, messages=messages)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_operations.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/operations.py tests/test_operations.py
git commit -m "feat: toggle skills by name or alias"
```

## Task 6: Shell Integration

**Files:**
- Create: `src/codex_skills_cli/shell.py`
- Test: `tests/test_shell.py`

- [ ] **Step 1: Write failing shell tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_shell.py -v`

Expected: FAIL because `codex_skills_cli.shell` does not exist.

- [ ] **Step 3: Implement shell snippet generation**

```python
from __future__ import annotations

from codex_skills_cli.aliases import is_alias_safe


def shell_init(alias_names: list[str]) -> str:
    lines: list[str] = []
    for alias_name in sorted(set(alias_names)):
        if not is_alias_safe(alias_name):
            continue
        lines.append(f"{alias_name}-on() {{ skills on {alias_name}; }}")
        lines.append(f"{alias_name}-off() {{ skills off {alias_name}; }}")
    return "\n".join(lines) + ("\n" if lines else "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_shell.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/shell.py tests/test_shell.py
git commit -m "feat: generate optional shell helpers"
```

## Task 7: CLI Commands

**Files:**
- Modify: `src/codex_skills_cli/cli.py`
- Create: `src/codex_skills_cli/interactive.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI smoke tests**

```python
from typer.testing import CliRunner

from codex_skills_cli.cli import app

runner = CliRunner()


def test_ls_displays_skills(fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")
    result = runner.invoke(
        app,
        [
            "--skills-dir",
            str(fake_codex_home / "skills"),
            "--disabled-dir",
            str(fake_codex_home / "skills_disabled"),
            "--alias-file",
            str(fake_codex_home / "skill_aliases"),
            "ls",
        ],
    )

    assert result.exit_code == 0
    assert "one" in result.output
    assert "on" in result.output


def test_on_by_alias(fake_codex_home, make_skill):
    make_skill("one", status="off", description="One.")
    (fake_codex_home / "skill_aliases").write_text("one group\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "--skills-dir",
            str(fake_codex_home / "skills"),
            "--disabled-dir",
            str(fake_codex_home / "skills_disabled"),
            "--alias-file",
            str(fake_codex_home / "skill_aliases"),
            "on",
            "group",
        ],
    )

    assert result.exit_code == 0
    assert "one turned ON" in result.output
    assert "restart Codex to reload skills" in result.output


def test_shell_init_outputs_helpers(fake_codex_home):
    (fake_codex_home / "skill_aliases").write_text("one group\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "--skills-dir",
            str(fake_codex_home / "skills"),
            "--disabled-dir",
            str(fake_codex_home / "skills_disabled"),
            "--alias-file",
            str(fake_codex_home / "skill_aliases"),
            "shell",
            "init",
        ],
    )

    assert result.exit_code == 0
    assert "group-on()" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`

Expected: FAIL because CLI commands are not implemented.

- [ ] **Step 3: Implement CLI commands and interactive adapters**

`interactive.py`:

```python
from __future__ import annotations

import questionary


def select_alias(existing_aliases: list[str]) -> tuple[str, bool]:
    choices = [*existing_aliases, "<create new alias>"]
    selected = questionary.select("Choose alias", choices=choices).ask()
    if selected == "<create new alias>":
        alias_name = questionary.text("Alias").ask()
        return alias_name or "", True
    return selected or "", False


def select_skills(skill_names: list[str], *, preselected: list[str] | None = None) -> list[str]:
    selected = questionary.checkbox("Choose skills", choices=skill_names, default=preselected or []).ask()
    return list(selected or [])
```

`cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from codex_skills_cli.aliases import group_by_alias, is_alias_safe, read_aliases, write_aliases
from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.interactive import select_alias, select_skills
from codex_skills_cli.operations import disable_targets, enable_targets
from codex_skills_cli.paths import PathConfig, resolve_paths
from codex_skills_cli.shell import shell_init

app = typer.Typer(help="Manage external Codex skills and aliases.")
alias_app = typer.Typer(help="Manage skill aliases.")
shell_app = typer.Typer(help="Generate shell integration.")
app.add_typer(alias_app, name="alias")
app.add_typer(shell_app, name="shell")
console = Console()


def _config(ctx: typer.Context) -> PathConfig:
    return resolve_paths(
        skills_dir=ctx.obj.get("skills_dir"),
        disabled_dir=ctx.obj.get("disabled_dir"),
        alias_file=ctx.obj.get("alias_file"),
    )


@app.callback()
def main(
    ctx: typer.Context,
    skills_dir: Path | None = typer.Option(None, "--skills-dir"),
    disabled_dir: Path | None = typer.Option(None, "--disabled-dir"),
    alias_file: Path | None = typer.Option(None, "--alias-file"),
) -> None:
    ctx.obj = {"skills_dir": skills_dir, "disabled_dir": disabled_dir, "alias_file": alias_file}


@app.command("ls")
def list_skills(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, warnings = read_aliases(config.alias_file)
    skills, discovery_warnings = discover_skills(config, aliases)
    for warning in [*warnings, *discovery_warnings]:
        console.print(f"warning: {warning}", style="yellow")
    table = Table()
    table.add_column("ALIAS")
    table.add_column("SKILL")
    table.add_column("STATUS")
    table.add_column("DESCRIPTION")
    for skill in skills:
        table.add_row(skill.effective_alias, skill.name, skill.status, skill.description)
    console.print(table)


@app.command("on")
def on(ctx: typer.Context, targets: list[str] = typer.Argument(...)) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    result = enable_targets(config, targets, aliases)
    for message in result.messages:
        console.print(message)
    if result.changed:
        console.print("restart Codex to reload skills")
    raise typer.Exit(1 if result.missing else 0)


@app.command("off")
def off(ctx: typer.Context, targets: list[str] = typer.Argument(...)) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    result = disable_targets(config, targets, aliases)
    for message in result.messages:
        console.print(message)
    if result.changed:
        console.print("restart Codex to reload skills")
    raise typer.Exit(1 if result.missing else 0)


@alias_app.command("ls")
def alias_ls(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    grouped = group_by_alias([skill.name for skill in skills], aliases)
    for alias_name, members in grouped.items():
        console.print(f"{alias_name}: {', '.join(members)}")


@alias_app.command("set")
def alias_set(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    alias_name, _created = select_alias(sorted(set(aliases.values())))
    if not is_alias_safe(alias_name):
        raise typer.BadParameter("alias contains unsafe characters")
    selected = select_skills([skill.name for skill in skills])
    for skill_name in selected:
        aliases[skill_name] = alias_name
    write_aliases(config.alias_file, aliases)


@alias_app.command("edit")
def alias_edit(ctx: typer.Context) -> None:
    alias_set(ctx)


@alias_app.command("unset")
def alias_unset(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    selected = select_skills([skill.name for skill in skills if skill.name in aliases])
    for skill_name in selected:
        aliases.pop(skill_name, None)
    write_aliases(config.alias_file, aliases)


@shell_app.command("init")
def shell_init_command(ctx: typer.Context) -> None:
    config = _config(ctx)
    aliases, _ = read_aliases(config.alias_file)
    skills, _ = discover_skills(config, aliases)
    console.print(shell_init([skill.effective_alias for skill in skills]), end="")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/codex_skills_cli/cli.py src/codex_skills_cli/interactive.py tests/test_cli.py
git commit -m "feat: expose skills CLI commands"
```

## Task 8: Full Verification and Usage Smoke

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Verify the console script without manual virtualenv activation**

Run: `uv run skills --help`

Expected: exit 0 and help output includes `Manage external Codex skills and aliases.`

- [ ] **Step 3: Add final README usage examples**

```markdown
## Usage

```bash
skills ls
skills on langchain
skills off langchain
skills alias ls
skills shell init
```

Use custom paths when your Codex skill directories are not in the default
location:

```bash
skills --skills-dir /path/to/skills --disabled-dir /path/to/skills_disabled --alias-file /path/to/skill_aliases ls
```

You can also configure paths with `CODEX_SKILLS_DIR`,
`CODEX_SKILLS_DISABLED_DIR`, and `CODEX_SKILL_ALIASES_FILE`.
```

- [ ] **Step 4: Run README-adjacent smoke tests**

Run: `uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add skills CLI usage"
```
