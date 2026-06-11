# Managed Skill Directories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add project-local management of multiple skill directories, project-local aliases, persistent add/remove directory actions, source-directory display, and correct per-root enable/disable behavior.

**Architecture:** Add a small `managed_dirs` module for reading/writing `./managed_dirs`, deriving sibling disabled directories, and performing add/remove directory lifecycle actions. Extend `PathConfig` to carry ordered managed directory pairs, then update discovery and operations to work from the discovered owning pair instead of one global enabled/disabled pair. CLI commands remain thin: they resolve config, call the core functions, and render tables or messages.

**Tech Stack:** Python 3.12, Typer CLI, Rich tables, pytest, pathlib, shutil.

---

## Strict Acceptance Criteria

- Every production behavior change is introduced by a failing pytest first.
- The failing test for each task must fail for the expected reason before code is changed.
- `uv run pytest` passes with no failures at the end.
- `skills --add-dir ~/.agents/skills` writes `./managed_dirs`, creates `~/.agents/skills`, and creates `~/.agents/skills_disabled`.
- `skills --remove-dir ~/.agents/skills` restores disabled skills from `~/.agents/skills_disabled` into `~/.agents/skills`, removes the entry from `./managed_dirs`, and deletes the empty disabled directory.
- `skills --remove-dir ~/.codex/skills` exits non-zero and does not change `./managed_dirs`.
- A remove restore conflict exits non-zero and leaves `./managed_dirs` plus the disabled directory unchanged.
- Default alias storage is `./skill_aliases`; `--alias-file` still overrides it.
- `~/.codex/skills` is always included even when `./managed_dirs` is missing.
- `skills ls` includes a `DIR` column with each skill's owning enabled root.
- `skills alias ls` shows every skill under each alias with its owning enabled root.
- Removed managed directories no longer contribute skills to `skills ls`, `skills alias ls`, `skills on`, or `skills off`.
- `--skills-dir`, `--disabled-dir`, and `--alias-file` remain supported as single-pair compatibility overrides.
- No command moves a skill from one managed root into another managed root.

## File Structure

- Create `src/codex_skills_cli/managed_dirs.py`: project-local managed directory file parsing, disabled-dir derivation, add/remove lifecycle functions.
- Modify `src/codex_skills_cli/paths.py`: add `SkillDirPair`, expand `PathConfig`, move default alias file to `./skill_aliases`, and resolve ordered managed directory pairs.
- Modify `src/codex_skills_cli/models.py`: add `managed_dir` to `Skill`.
- Modify `src/codex_skills_cli/discovery.py`: scan all `PathConfig.skill_dirs`, keep priority order, record owning enabled root, and warn on duplicates.
- Modify `src/codex_skills_cli/operations.py`: resolve targets against discovered skills and move within the owning pair.
- Modify `src/codex_skills_cli/cli.py`: add `--add-dir`, `--remove-dir`, `DIR` column, and grouped `alias ls` output with directories.
- Modify `tests/conftest.py`: add helpers for creating skills in arbitrary enabled/disabled roots.
- Add `tests/test_managed_dirs.py`: direct unit tests for managed directory helpers.
- Modify `tests/test_paths.py`, `tests/test_discovery.py`, `tests/test_operations.py`, and `tests/test_cli.py`: behavior coverage for the new model.
- Modify `README.md` and `docs/user-manual.md`: document project-local `managed_dirs`, project-local `skill_aliases`, add/remove, and compatibility overrides.

## TDD Execution Rules

- Run the exact RED command before each implementation step.
- If the RED test passes immediately, rewrite the test before changing production code.
- If the RED test errors because of a typo or import mistake, fix the test and rerun until it fails because the feature is missing.
- Implement only enough code for the current task's tests.
- Run the task's GREEN command after implementation.
- Run the broader regression command listed in each task before committing.

### Task 1: Managed Directory Core And Path Resolution

**Files:**
- Create: `src/codex_skills_cli/managed_dirs.py`
- Modify: `src/codex_skills_cli/paths.py`
- Modify: `tests/test_paths.py`
- Create: `tests/test_managed_dirs.py`

- [ ] **Step 1: Write failing tests for managed directory file parsing and disabled-dir derivation**

Create `tests/test_managed_dirs.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
uv run pytest tests/test_managed_dirs.py -v
```

Expected: FAIL because `codex_skills_cli.managed_dirs` does not exist.

- [ ] **Step 3: Implement `managed_dirs.py`**

Create `src/codex_skills_cli/managed_dirs.py`:

```python
from __future__ import annotations

import os
import tempfile
from pathlib import Path


MANAGED_DIRS_FILENAME = "managed_dirs"


def derive_disabled_dir(skills_dir: Path) -> Path:
    expanded = skills_dir.expanduser()
    if expanded.name == "skills":
        return expanded.with_name("skills_disabled")
    return expanded.with_name(f"{expanded.name}_disabled")


def _path_key(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        key = _path_key(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path.expanduser())
    return unique


def read_managed_dirs(managed_dirs_file: Path) -> tuple[list[Path], list[str]]:
    if not managed_dirs_file.exists():
        return [], []
    paths: list[Path] = []
    warnings: list[str] = []
    seen: set[Path] = set()
    for line_number, raw_line in enumerate(managed_dirs_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 1:
            warnings.append(f"invalid managed_dirs entry on line {line_number}: expected one path")
            continue
        path = Path(parts[0]).expanduser()
        key = _path_key(path)
        if key in seen:
            warnings.append(f"duplicate managed directory ignored: {path}")
            continue
        seen.add(key)
        paths.append(path)
    return paths, warnings


def write_managed_dirs(managed_dirs_file: Path, paths: list[Path]) -> None:
    managed_dirs_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{path.expanduser()}\n" for path in unique_paths(paths))
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=managed_dirs_file.parent, delete=False) as handle:
        handle.write(content)
        tmp_name = handle.name
    os.replace(tmp_name, managed_dirs_file)
```

- [ ] **Step 4: Run managed dir tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_managed_dirs.py -v
```

Expected: PASS.

- [ ] **Step 5: Write failing tests for project-local path resolution**

Replace `tests/test_paths.py` with:

```python
from pathlib import Path

import pytest

from codex_skills_cli.paths import PathConfig, SkillDirPair, resolve_paths


def test_defaults_are_derived_from_home_and_project(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config == PathConfig(
        skills_dir=home / ".codex" / "skills",
        disabled_dir=home / ".codex" / "skills_disabled",
        alias_file=project / "skill_aliases",
        managed_dirs_file=project / "managed_dirs",
        skill_dirs=(
            SkillDirPair(home / ".codex" / "skills", home / ".codex" / "skills_disabled"),
        ),
    )


def test_managed_dirs_are_appended_after_default(monkeypatch, tmp_path):
    home = tmp_path / "home"
    project = tmp_path / "project"
    extra = tmp_path / "agents" / "skills"
    project.mkdir()
    (project / "managed_dirs").write_text(f"{extra}\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILLS_DISABLED_DIR", raising=False)
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.skill_dirs == (
        SkillDirPair(home / ".codex" / "skills", home / ".codex" / "skills_disabled"),
        SkillDirPair(extra, tmp_path / "agents" / "skills_disabled"),
    )


def test_env_overrides_codex_home_but_alias_defaults_to_project(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    codex_home = tmp_path / "codex"
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "off"))
    monkeypatch.delenv("CODEX_SKILL_ALIASES_FILE", raising=False)

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.skills_dir == tmp_path / "enabled"
    assert config.disabled_dir == tmp_path / "off"
    assert config.alias_file == project / "skill_aliases"
    assert config.skill_dirs == (SkillDirPair(tmp_path / "enabled", tmp_path / "off"),)


def test_alias_file_env_override_still_works(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "aliases"))

    config, warnings = resolve_paths()

    assert warnings == []
    assert config.alias_file == tmp_path / "aliases"


def test_cli_options_keep_single_pair_override(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "managed_dirs").write_text(f"{tmp_path / 'extra' / 'skills'}\n", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_SKILLS_DIR", str(tmp_path / "env-enabled"))
    monkeypatch.setenv("CODEX_SKILLS_DISABLED_DIR", str(tmp_path / "env-off"))
    monkeypatch.setenv("CODEX_SKILL_ALIASES_FILE", str(tmp_path / "env-aliases"))

    config, warnings = resolve_paths(
        skills_dir=tmp_path / "cli-enabled",
        disabled_dir=tmp_path / "cli-off",
        alias_file=tmp_path / "cli-aliases",
    )

    assert warnings == []
    assert config.skills_dir == tmp_path / "cli-enabled"
    assert config.disabled_dir == tmp_path / "cli-off"
    assert config.alias_file == tmp_path / "cli-aliases"
    assert config.skill_dirs == (SkillDirPair(tmp_path / "cli-enabled", tmp_path / "cli-off"),)


def test_enabled_and_disabled_paths_must_differ(tmp_path):
    with pytest.raises(ValueError, match="must be different"):
        resolve_paths(skills_dir=tmp_path / "same", disabled_dir=tmp_path / "same")
```

- [ ] **Step 6: Run path tests to verify RED**

Run:

```bash
uv run pytest tests/test_paths.py -v
```

Expected: FAIL because `SkillDirPair` does not exist and `resolve_paths()` still returns a single `PathConfig`.

- [ ] **Step 7: Implement path resolution**

Replace `src/codex_skills_cli/paths.py` with:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from codex_skills_cli.managed_dirs import MANAGED_DIRS_FILENAME, derive_disabled_dir, read_managed_dirs


@dataclass(frozen=True)
class SkillDirPair:
    skills_dir: Path
    disabled_dir: Path


@dataclass(frozen=True)
class PathConfig:
    skills_dir: Path
    disabled_dir: Path
    alias_file: Path
    managed_dirs_file: Path
    skill_dirs: tuple[SkillDirPair, ...]


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser()


def _assert_distinct(pair: SkillDirPair) -> None:
    if pair.skills_dir.resolve(strict=False) == pair.disabled_dir.resolve(strict=False):
        raise ValueError("enabled and disabled skill directories must be different")


def resolve_paths(
    *,
    skills_dir: str | Path | None = None,
    disabled_dir: str | Path | None = None,
    alias_file: str | Path | None = None,
) -> tuple[PathConfig, list[str]]:
    project_dir = Path.cwd()
    codex_home = _expand(os.environ.get("CODEX_HOME", "~/.codex"))
    resolved_skills_dir = _expand(skills_dir or os.environ.get("CODEX_SKILLS_DIR", codex_home / "skills"))
    resolved_disabled_dir = _expand(
        disabled_dir or os.environ.get("CODEX_SKILLS_DISABLED_DIR", codex_home / "skills_disabled")
    )
    resolved_alias_file = _expand(
        alias_file or os.environ.get("CODEX_SKILL_ALIASES_FILE", project_dir / "skill_aliases")
    )
    managed_dirs_file = project_dir / MANAGED_DIRS_FILENAME

    default_pair = SkillDirPair(resolved_skills_dir, resolved_disabled_dir)
    _assert_distinct(default_pair)

    if skills_dir is not None or disabled_dir is not None:
        pairs = (default_pair,)
        warnings: list[str] = []
    else:
        extra_dirs, warnings = read_managed_dirs(managed_dirs_file)
        pairs = (default_pair, *(SkillDirPair(path, derive_disabled_dir(path)) for path in extra_dirs))
        for pair in pairs:
            _assert_distinct(pair)

    return (
        PathConfig(
            skills_dir=resolved_skills_dir,
            disabled_dir=resolved_disabled_dir,
            alias_file=resolved_alias_file,
            managed_dirs_file=managed_dirs_file,
            skill_dirs=pairs,
        ),
        warnings,
    )
```

- [ ] **Step 8: Run path tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_paths.py tests/test_managed_dirs.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit Task 1**

Run:

```bash
git add src/codex_skills_cli/managed_dirs.py src/codex_skills_cli/paths.py tests/test_managed_dirs.py tests/test_paths.py
git commit -m "feat: resolve project managed skill dirs"
```

Expected: commit succeeds.

### Task 2: CLI Add And Remove Directory Lifecycle

**Files:**
- Modify: `src/codex_skills_cli/cli.py`
- Modify: `src/codex_skills_cli/managed_dirs.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_managed_dirs.py`

- [ ] **Step 1: Add failing direct tests for remove lifecycle**

Append to `tests/test_managed_dirs.py`:

```python
from codex_skills_cli.managed_dirs import add_managed_dir, remove_managed_dir


def _skill(root: Path, name: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text(f"---\nname: {name}\ndescription: {name}.\n---\n", encoding="utf-8")
    return skill_dir


def test_add_managed_dir_writes_file_and_creates_enabled_and_disabled(tmp_path):
    managed_file = tmp_path / "project" / "managed_dirs"
    enabled = tmp_path / "agents" / "skills"

    result = add_managed_dir(managed_file, enabled)

    assert not result.error
    assert result.changed
    assert enabled.is_dir()
    assert (tmp_path / "agents" / "skills_disabled").is_dir()
    assert managed_file.read_text(encoding="utf-8") == f"{enabled}\n"


def test_remove_managed_dir_restores_disabled_skills_and_deletes_disabled_dir(tmp_path):
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
    managed_file = tmp_path / "project" / "managed_dirs"
    default = tmp_path / "codex" / "skills"

    result = remove_managed_dir(managed_file, default, default)

    assert result.error
    assert not result.changed
    assert not managed_file.exists()


def test_remove_managed_dir_rejects_restore_conflict_without_changing_file(tmp_path):
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
```

- [ ] **Step 2: Run remove lifecycle tests to verify RED**

Run:

```bash
uv run pytest tests/test_managed_dirs.py -v
```

Expected: FAIL because `add_managed_dir` and `remove_managed_dir` do not exist.

- [ ] **Step 3: Implement lifecycle functions**

Update imports in `src/codex_skills_cli/managed_dirs.py`:

```python
import shutil
from dataclasses import dataclass
```

Add these definitions after `MANAGED_DIRS_FILENAME`:

```python
@dataclass(frozen=True)
class ManagedDirActionResult:
    changed: bool
    error: bool
    messages: list[str]
```

Add these functions after `write_managed_dirs()`:

```python
def add_managed_dir(managed_dirs_file: Path, skills_dir: Path) -> ManagedDirActionResult:
    enabled = skills_dir.expanduser()
    disabled = derive_disabled_dir(enabled)
    current, warnings = read_managed_dirs(managed_dirs_file)
    enabled.mkdir(parents=True, exist_ok=True)
    disabled.mkdir(parents=True, exist_ok=True)
    if _path_key(enabled) in {_path_key(path) for path in current}:
        return ManagedDirActionResult(
            changed=False,
            error=False,
            messages=[*warnings, f"{enabled} is already managed"],
        )
    write_managed_dirs(managed_dirs_file, [*current, enabled])
    return ManagedDirActionResult(
        changed=True,
        error=False,
        messages=[*warnings, f"added managed skills directory: {enabled}"],
    )


def remove_managed_dir(managed_dirs_file: Path, default_skills_dir: Path, skills_dir: Path) -> ManagedDirActionResult:
    enabled = skills_dir.expanduser()
    disabled = derive_disabled_dir(enabled)
    if _path_key(enabled) == _path_key(default_skills_dir):
        return ManagedDirActionResult(
            changed=False,
            error=True,
            messages=[f"cannot remove default managed skills directory: {enabled}"],
        )

    current, warnings = read_managed_dirs(managed_dirs_file)
    remaining = [path for path in current if _path_key(path) != _path_key(enabled)]
    if len(remaining) == len(current):
        return ManagedDirActionResult(
            changed=False,
            error=False,
            messages=[*warnings, f"{enabled} is not managed"],
        )

    restore_sources = sorted(path for path in disabled.iterdir() if path.is_dir()) if disabled.exists() else []
    conflicts = [path.name for path in restore_sources if (enabled / path.name).exists()]
    if conflicts:
        joined = ", ".join(conflicts)
        return ManagedDirActionResult(
            changed=False,
            error=True,
            messages=[*warnings, f"cannot remove {enabled}; restore conflicts: {joined}"],
        )

    enabled.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    for source in restore_sources:
        shutil.move(str(source), str(enabled / source.name))
        restored.append(source.name)

    write_managed_dirs(managed_dirs_file, remaining)

    removed_disabled = False
    if disabled.exists() and not any(disabled.iterdir()):
        disabled.rmdir()
        removed_disabled = True

    messages = [*warnings, f"removed managed skills directory: {enabled}"]
    if restored:
        messages.append(f"restored disabled skills: {', '.join(restored)}")
    if removed_disabled:
        messages.append(f"removed disabled directory: {disabled}")
    return ManagedDirActionResult(changed=True, error=False, messages=messages)
```

- [ ] **Step 4: Run managed dir tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_managed_dirs.py -v
```

Expected: PASS.

- [ ] **Step 5: Write failing CLI tests for `--add-dir` and `--remove-dir`**

Append to `tests/test_cli.py`:

```python
def test_add_dir_persists_project_managed_dir_and_creates_pair(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"

    result = runner.invoke(app, ["--add-dir", str(managed)])

    assert result.exit_code == 0
    assert "added managed skills directory" in result.output
    assert (project / "managed_dirs").read_text(encoding="utf-8") == f"{managed}\n"
    assert managed.is_dir()
    assert (tmp_path / "agents" / "skills_disabled").is_dir()


def test_add_dir_without_action_prints_already_managed(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")

    result = runner.invoke(app, ["--add-dir", str(managed)])

    assert result.exit_code == 0
    assert "already managed" in result.output
    assert (project / "managed_dirs").read_text(encoding="utf-8") == f"{managed}\n"


def test_remove_dir_restores_disabled_skills_and_removes_management(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    managed = tmp_path / "agents" / "skills"
    disabled = tmp_path / "agents" / "skills_disabled"
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")
    skill_dir = disabled / "off-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: off-one\ndescription: Off.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["--remove-dir", str(managed)])

    assert result.exit_code == 0
    assert "removed managed skills directory" in result.output
    assert (managed / "off-one" / "SKILL.md").exists()
    assert not disabled.exists()
    assert (project / "managed_dirs").read_text(encoding="utf-8") == ""


def test_remove_dir_rejects_default(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))

    result = runner.invoke(app, ["--remove-dir", str(home / ".codex" / "skills")])

    assert result.exit_code == 1
    assert "cannot remove default managed skills directory" in result.output
```

- [ ] **Step 6: Run CLI add/remove tests to verify RED**

Run:

```bash
uv run pytest tests/test_cli.py::test_add_dir_persists_project_managed_dir_and_creates_pair tests/test_cli.py::test_remove_dir_restores_disabled_skills_and_removes_management -v
```

Expected: FAIL because the root CLI does not have `--add-dir` or `--remove-dir`.

- [ ] **Step 7: Implement CLI options**

Update `src/codex_skills_cli/cli.py`:

```python
from codex_skills_cli.managed_dirs import add_managed_dir, remove_managed_dir
```

Change the Typer app declaration:

```python
app = typer.Typer(help="Manage external Codex skills and aliases.", invoke_without_command=True)
```

Replace `main()` and `_config()` with:

```python
@app.callback()
def main(
    ctx: typer.Context,
    skills_dir: Path | None = typer.Option(None, "--skills-dir"),
    disabled_dir: Path | None = typer.Option(None, "--disabled-dir"),
    alias_file: Path | None = typer.Option(None, "--alias-file"),
    add_dir: Path | None = typer.Option(None, "--add-dir"),
    remove_dir: Path | None = typer.Option(None, "--remove-dir"),
) -> None:
    """Manage external Codex skills and aliases."""
    ctx.obj = {
        "skills_dir": skills_dir,
        "disabled_dir": disabled_dir,
        "alias_file": alias_file,
    }
    if add_dir is not None and remove_dir is not None:
        raise typer.BadParameter("use only one of --add-dir or --remove-dir")
    if add_dir is not None:
        config, path_warnings = _config(ctx)
        for warning in path_warnings:
            console.print(f"warning: {warning}", style="yellow")
        result = add_managed_dir(config.managed_dirs_file, add_dir)
        for message in result.messages:
            console.print(message)
        raise typer.Exit(1 if result.error else 0)
    if remove_dir is not None:
        config, path_warnings = _config(ctx)
        for warning in path_warnings:
            console.print(f"warning: {warning}", style="yellow")
        result = remove_managed_dir(config.managed_dirs_file, config.skills_dir, remove_dir)
        for message in result.messages:
            console.print(message)
        raise typer.Exit(1 if result.error else 0)
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _config(ctx: typer.Context) -> tuple[PathConfig, list[str]]:
    return resolve_paths(
        skills_dir=ctx.obj.get("skills_dir"),
        disabled_dir=ctx.obj.get("disabled_dir"),
        alias_file=ctx.obj.get("alias_file"),
    )
```

Then update every caller from:

```python
config = _config(ctx)
```

to:

```python
config, path_warnings = _config(ctx)
for warning in path_warnings:
    console.print(f"warning: {warning}", style="yellow")
```

For commands where warnings are already printed, merge path warnings with alias and discovery warnings.

- [ ] **Step 8: Run CLI add/remove tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_managed_dirs.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit Task 2**

Run:

```bash
git add src/codex_skills_cli/cli.py src/codex_skills_cli/managed_dirs.py tests/test_cli.py tests/test_managed_dirs.py
git commit -m "feat: add managed directory lifecycle commands"
```

Expected: commit succeeds.

### Task 3: Multi-Root Discovery With Owning Directory

**Files:**
- Modify: `src/codex_skills_cli/models.py`
- Modify: `src/codex_skills_cli/discovery.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_discovery.py`

- [ ] **Step 1: Update test helpers for arbitrary roots**

Modify `tests/conftest.py`:

```python
import pytest


@pytest.fixture
def fake_codex_home(tmp_path):
    home = tmp_path / "codex"
    (home / "skills").mkdir(parents=True)
    (home / "skills_disabled").mkdir(parents=True)
    return home


@pytest.fixture
def create_skill():
    def _create_skill(root, name: str, *, description: str):
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath("SKILL.md").write_text(
            f"---\nname: {name.split('/')[-1]}\ndescription: {description}\n---\n",
            encoding="utf-8",
        )
        return skill_dir

    return _create_skill


@pytest.fixture
def make_skill(fake_codex_home, create_skill):
    def _make_skill(name: str, *, status: str, description: str):
        root = fake_codex_home / ("skills" if status == "on" else "skills_disabled")
        return create_skill(root, name, description=description)

    return _make_skill
```

- [ ] **Step 2: Write failing discovery tests**

Replace `tests/test_discovery.py` with:

```python
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
```

- [ ] **Step 3: Run discovery tests to verify RED**

Run:

```bash
uv run pytest tests/test_discovery.py -v
```

Expected: FAIL because `Skill.managed_dir` does not exist and discovery only scans one pair.

- [ ] **Step 4: Implement model and discovery**

Update `src/codex_skills_cli/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SkillStatus = Literal["on", "off"]


@dataclass(frozen=True)
class Skill:
    name: str
    status: SkillStatus
    explicit_alias: str | None
    effective_alias: str
    description: str
    path: Path | None
    managed_dir: Path
```

Replace `discover_skills()` in `src/codex_skills_cli/discovery.py`:

```python
def discover_skills(config: PathConfig, aliases: dict[str, str]) -> tuple[list[Skill], list[str]]:
    found: dict[str, tuple[Path, SkillStatus, Path]] = {}
    warnings: list[str] = []
    for pair in config.skill_dirs:
        for status, root in (("on", pair.skills_dir), ("off", pair.disabled_dir)):
            for skill_dir in _iter_skill_dirs(root):
                if not (skill_dir / "SKILL.md").exists():
                    continue
                if skill_dir.name in found:
                    kept_path = found[skill_dir.name][0]
                    warnings.append(
                        f"skill '{skill_dir.name}' at {skill_dir} ignored; already using {kept_path}"
                    )
                    continue
                found[skill_dir.name] = (skill_dir, status, pair.skills_dir)  # type: ignore[assignment]
    skills = [
        Skill(
            name=name,
            status=status,
            explicit_alias=aliases.get(name),
            effective_alias=alias_for(name, aliases),
            description=_description(path),
            path=path,
            managed_dir=managed_dir,
        )
        for name, (path, status, managed_dir) in found.items()
    ]
    return sorted(skills, key=lambda skill: skill.name), warnings
```

- [ ] **Step 5: Run discovery tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_discovery.py -v
```

Expected: PASS.

- [ ] **Step 6: Run existing model users**

Run:

```bash
uv run pytest tests/test_aliases.py tests/test_interactive.py tests/test_shell.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

Run:

```bash
git add src/codex_skills_cli/models.py src/codex_skills_cli/discovery.py tests/conftest.py tests/test_discovery.py
git commit -m "feat: discover skills across managed dirs"
```

Expected: commit succeeds.

### Task 4: Enable And Disable Within Owning Pair

**Files:**
- Modify: `src/codex_skills_cli/operations.py`
- Modify: `tests/test_operations.py`

- [ ] **Step 1: Write failing operation tests**

Replace `tests/test_operations.py` with:

```python
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
    config = _config(fake_codex_home)

    result = enable_targets(config, ["group"], {"one": "group", "two": "group"})

    assert result.changed == ["one", "two"]
    assert (fake_codex_home / "skills" / "one").is_dir()
    assert (fake_codex_home / "skills" / "two").is_dir()


def test_disable_by_skill_moves_enabled_skill(fake_codex_home, make_skill):
    make_skill("one", status="on", description="One.")
    config = _config(fake_codex_home)

    result = disable_targets(config, ["one"], {})

    assert result.changed == ["one"]
    assert (fake_codex_home / "skills_disabled" / "one").is_dir()


def test_enable_uses_owning_extra_pair(fake_codex_home, create_skill, tmp_path):
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_disabled, "agent-off", description="Agent off.")
    config = _config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled))

    result = enable_targets(config, ["agent-off"], {})

    assert result.changed == ["agent-off"]
    assert (extra_enabled / "agent-off" / "SKILL.md").exists()
    assert not (fake_codex_home / "skills" / "agent-off").exists()


def test_disable_uses_owning_extra_pair(fake_codex_home, create_skill, tmp_path):
    extra_enabled = tmp_path / "agents" / "skills"
    extra_disabled = tmp_path / "agents" / "skills_disabled"
    create_skill(extra_enabled, "agent-on", description="Agent on.")
    config = _config(fake_codex_home, SkillDirPair(extra_enabled, extra_disabled))

    result = disable_targets(config, ["agent-on"], {})

    assert result.changed == ["agent-on"]
    assert (extra_disabled / "agent-on" / "SKILL.md").exists()
    assert not (fake_codex_home / "skills_disabled" / "agent-on").exists()


def test_enable_reports_missing_target(fake_codex_home):
    config = _config(fake_codex_home)

    result = enable_targets(config, ["missing"], {})

    assert result.missing == ["missing"]
    assert result.messages == ["missing skill not found"]
```

- [ ] **Step 2: Run operation tests to verify RED**

Run:

```bash
uv run pytest tests/test_operations.py -v
```

Expected: FAIL on the extra-pair tests because `_toggle()` still moves through `config.skills_dir` and `config.disabled_dir`.

- [ ] **Step 3: Implement owning-pair operations**

Replace `src/codex_skills_cli/operations.py` with:

```python
from __future__ import annotations

import shutil
from dataclasses import dataclass

from codex_skills_cli.aliases import group_by_alias
from codex_skills_cli.discovery import discover_skills
from codex_skills_cli.paths import PathConfig, SkillDirPair


@dataclass(frozen=True)
class OperationResult:
    changed: list[str]
    unchanged: list[str]
    missing: list[str]
    messages: list[str]


def _pair_for_managed_dir(config: PathConfig, managed_dir) -> SkillDirPair:
    for pair in config.skill_dirs:
        if pair.skills_dir.resolve(strict=False) == managed_dir.resolve(strict=False):
            return pair
    raise ValueError(f"no managed pair found for {managed_dir}")


def _all_skill_names(config: PathConfig, aliases: dict[str, str]) -> list[str]:
    skills, _warnings = discover_skills(config, aliases)
    return [skill.name for skill in skills]


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
    skills, _warnings = discover_skills(config, aliases)
    skills_by_name = {skill.name: skill for skill in skills}
    skill_names = [skill.name for skill in skills]
    changed: list[str] = []
    unchanged: list[str] = []
    missing: list[str] = []
    messages: list[str] = []
    desired = "ON" if enable else "OFF"

    for skill_name in resolve_targets(targets, skill_names, aliases):
        skill = skills_by_name.get(skill_name)
        if skill is None:
            missing.append(skill_name)
            messages.append(f"{skill_name} skill not found")
            continue
        if (enable and skill.status == "on") or (not enable and skill.status == "off"):
            unchanged.append(skill_name)
            messages.append(f"{skill_name} is already {desired}")
            continue

        pair = _pair_for_managed_dir(config, skill.managed_dir)
        source_root = pair.disabled_dir if enable else pair.skills_dir
        dest_root = pair.skills_dir if enable else pair.disabled_dir
        source = source_root / skill_name
        if source.is_dir():
            dest_root.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest_root / skill_name))
            changed.append(skill_name)
            messages.append(f"{skill_name} turned {desired}")
            continue

        missing.append(skill_name)
        messages.append(f"{skill_name} skill not found")

    return OperationResult(changed=changed, unchanged=unchanged, missing=missing, messages=messages)
```

- [ ] **Step 4: Run operation tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_operations.py -v
```

Expected: PASS.

- [ ] **Step 5: Run discovery and operation regression tests**

Run:

```bash
uv run pytest tests/test_discovery.py tests/test_operations.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

Run:

```bash
git add src/codex_skills_cli/operations.py tests/test_operations.py
git commit -m "feat: toggle skills within owning managed dir"
```

Expected: commit succeeds.

### Task 5: CLI Listing, Alias Listing, And Project-Local Alias File

**Files:**
- Modify: `src/codex_skills_cli/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Update `_path_args` helper for compatibility override tests**

Keep the existing helper in `tests/test_cli.py`, but use it only for tests that explicitly verify compatibility overrides. New default-path tests should use `monkeypatch.chdir(project)` and avoid `--alias-file`.

- [ ] **Step 2: Write failing CLI display and alias-file tests**

Append to `tests/test_cli.py`:

```python
def test_ls_displays_dir_column_for_managed_skills(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    skill_dir = extra_enabled / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["ls"])

    assert result.exit_code == 0
    assert "DIR" in result.output
    assert "agent-one" in result.output
    assert str(extra_enabled) in result.output


def test_alias_ls_lists_members_with_dirs(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    extra_enabled = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{extra_enabled}\n", encoding="utf-8")
    (project / "skill_aliases").write_text("agent-one group\n", encoding="utf-8")
    skill_dir = extra_enabled / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    result = runner.invoke(app, ["alias", "ls"])

    assert result.exit_code == 0
    assert "group:" in result.output
    assert "agent-one" in result.output
    assert str(extra_enabled) in result.output


def test_alias_set_uses_project_local_skill_aliases(monkeypatch, fake_codex_home, make_skill, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(fake_codex_home))
    make_skill("one", status="on", description="One.")
    monkeypatch.setattr("codex_skills_cli.cli.select_alias", lambda _aliases: ("group", True))
    monkeypatch.setattr("codex_skills_cli.cli.select_skills", lambda _skills: ["one"])

    result = runner.invoke(app, ["alias", "set"])

    assert result.exit_code == 0
    assert (project / "skill_aliases").read_text(encoding="utf-8") == "one group\n"
    assert not (fake_codex_home / "skill_aliases").exists()


def test_alias_file_override_still_uses_explicit_alias_file(monkeypatch, fake_codex_home, make_skill, tmp_path):
    project = tmp_path / "project"
    explicit_aliases = tmp_path / "explicit_aliases"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("CODEX_HOME", str(fake_codex_home))
    make_skill("one", status="on", description="One.")
    monkeypatch.setattr("codex_skills_cli.cli.select_alias", lambda _aliases: ("group", True))
    monkeypatch.setattr("codex_skills_cli.cli.select_skills", lambda _skills: ["one"])

    result = runner.invoke(app, ["--alias-file", str(explicit_aliases), "alias", "set"])

    assert result.exit_code == 0
    assert explicit_aliases.read_text(encoding="utf-8") == "one group\n"
    assert not (project / "skill_aliases").exists()
```

- [ ] **Step 3: Run CLI display tests to verify RED**

Run:

```bash
uv run pytest tests/test_cli.py::test_ls_displays_dir_column_for_managed_skills tests/test_cli.py::test_alias_ls_lists_members_with_dirs tests/test_cli.py::test_alias_set_uses_project_local_skill_aliases -v
```

Expected: FAIL because `skills ls` has no `DIR` column, `alias ls` does not print directories, or alias defaults still use the old location.

- [ ] **Step 4: Implement CLI display changes**

In `src/codex_skills_cli/cli.py`, update `list_skills()`:

```python
@app.command("ls")
def list_skills(ctx: typer.Context) -> None:
    config, path_warnings = _config(ctx)
    aliases, warnings = read_aliases(config.alias_file)
    skills, discovery_warnings = discover_skills(config, aliases)
    for warning in [*path_warnings, *warnings, *discovery_warnings]:
        console.print(f"warning: {warning}", style="yellow")
    table = Table()
    table.add_column("ALIAS")
    table.add_column("SKILL")
    table.add_column("STATUS")
    table.add_column("DIR")
    table.add_column("DESCRIPTION")
    for skill in skills:
        table.add_row(skill.effective_alias, skill.name, skill.status, str(skill.managed_dir), skill.description)
    console.print(table)
```

Update `alias_ls()`:

```python
@alias_app.command("ls")
def alias_ls(ctx: typer.Context) -> None:
    config, path_warnings = _config(ctx)
    aliases, warnings = read_aliases(config.alias_file)
    skills, discovery_warnings = discover_skills(config, aliases)
    for warning in [*path_warnings, *warnings, *discovery_warnings]:
        console.print(f"warning: {warning}", style="yellow")
    grouped: dict[str, list] = {}
    for skill in skills:
        grouped.setdefault(skill.effective_alias, []).append(skill)
    for alias_name, members in grouped.items():
        console.print(f"{alias_name}:")
        for skill in members:
            console.print(f"  {skill.name}  {skill.managed_dir}")
```

Update `on()`, `off()`, `alias_set()`, `alias_unset()`, and `shell_init_command()` so each unpacks `_config(ctx)` and prints path warnings before reading aliases or discovering skills.

- [ ] **Step 5: Run CLI tests to verify GREEN**

Run:

```bash
uv run pytest tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full Python regression suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add src/codex_skills_cli/cli.py tests/test_cli.py
git commit -m "feat: show managed dirs in cli output"
```

Expected: commit succeeds.

### Task 6: Removed Directories Acceptance Gate

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add end-to-end removal visibility acceptance test**

Append to `tests/test_cli.py`:

```python
def test_removed_dir_disappears_from_ls_and_alias_ls(monkeypatch, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    managed = tmp_path / "agents" / "skills"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))
    (project / "managed_dirs").write_text(f"{managed}\n", encoding="utf-8")
    (project / "skill_aliases").write_text("agent-one group\n", encoding="utf-8")
    skill_dir = managed / "agent-one"
    skill_dir.mkdir(parents=True)
    skill_dir.joinpath("SKILL.md").write_text("---\nname: agent-one\ndescription: Agent.\n---\n", encoding="utf-8")

    remove_result = runner.invoke(app, ["--remove-dir", str(managed)])
    ls_result = runner.invoke(app, ["ls"])
    alias_result = runner.invoke(app, ["alias", "ls"])
    off_result = runner.invoke(app, ["off", "agent-one"])

    assert remove_result.exit_code == 0
    assert ls_result.exit_code == 0
    assert alias_result.exit_code == 0
    assert off_result.exit_code == 1
    assert "agent-one" not in ls_result.output
    assert "agent-one" not in alias_result.output
    assert "agent-one skill not found" in off_result.output
```

- [ ] **Step 2: Run visibility acceptance test**

Run:

```bash
uv run pytest tests/test_cli.py::test_removed_dir_disappears_from_ls_and_alias_ls -v
```

Expected: PASS.

- [ ] **Step 3: Run CLI and operation regression tests**

Run:

```bash
uv run pytest tests/test_cli.py tests/test_operations.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit Task 6**

Run:

```bash
git add tests/test_cli.py
git commit -m "test: verify removed dirs leave active listings"
```

Expected: commit succeeds.

### Task 7: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/user-manual.md`

- [ ] **Step 1: Update README**

Change the Usage section in `README.md` to include:

```markdown
```bash
skills ls
skills --add-dir ~/.agents/skills
skills --remove-dir ~/.agents/skills
skills on langchain
skills off langchain
skills alias ls
skills shell init
```

Additional managed skill directories are stored in `./managed_dirs` in the
current project directory. Alias mappings are stored in `./skill_aliases` by
default and apply to all managed directories.

Use custom paths for one command when testing or migrating:

```bash
skills --skills-dir /path/to/skills --disabled-dir /path/to/skills_disabled --alias-file /path/to/skill_aliases ls
```
```

- [ ] **Step 2: Update user manual**

Update `docs/user-manual.md` so it states:

```markdown
默认管理：

- 始终管理：`~/.codex/skills`
- 当前项目额外目录列表：`./managed_dirs`
- 当前项目 alias 文件：`./skill_aliases`

添加目录：

```bash
skills --add-dir ~/.agents/skills
```

这会创建：

- `~/.agents/skills`
- `~/.agents/skills_disabled`

移除目录：

```bash
skills --remove-dir ~/.agents/skills
```

移除时会先把 `~/.agents/skills_disabled` 里的 skill 目录恢复到
`~/.agents/skills`，然后从 `./managed_dirs` 删除该目录。之后
`skills ls` 和 `skills alias ls` 不再显示该目录中的 skills。

兼容覆盖参数：

```bash
skills --skills-dir /path/to/skills --disabled-dir /path/to/skills_disabled --alias-file /path/to/skill_aliases ls
```

这些参数只影响当前命令，不写入 `./managed_dirs`。
```

- [ ] **Step 3: Run documentation grep checks**

Run:

```bash
rg --line-number "managed_dirs|--add-dir|--remove-dir|skill_aliases|--skills-dir" README.md docs/user-manual.md
```

Expected: output includes all new commands and both project-local files.

- [ ] **Step 4: Run full test suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 5: Run CLI smoke tests in an isolated temporary project**

Run:

```bash
tmp_project="$(mktemp -d)"
tmp_home="$(mktemp -d)"
tmp_agents="$(mktemp -d)/skills"
(
  cd "$tmp_project"
  HOME="$tmp_home" uv run skills --add-dir "$tmp_agents"
  mkdir -p "$tmp_agents/example"
  printf '%s\n' '---' 'name: example' 'description: Example.' '---' > "$tmp_agents/example/SKILL.md"
  HOME="$tmp_home" uv run skills ls
  HOME="$tmp_home" uv run skills off example
  HOME="$tmp_home" uv run skills on example
  HOME="$tmp_home" uv run skills --remove-dir "$tmp_agents"
)
```

Expected:

- `--add-dir` prints `added managed skills directory`.
- `skills ls` output includes `DIR` and `example`.
- `skills off example` prints `example turned OFF`.
- `skills on example` prints `example turned ON`.
- `--remove-dir` prints `removed managed skills directory`.
- The command exits 0.

- [ ] **Step 6: Inspect git diff**

Run:

```bash
git status --short
git diff -- src tests README.md docs/user-manual.md
```

Expected:

- Only planned files are modified.
- No unrelated user changes are reverted.
- No generated cache files are staged.

- [ ] **Step 7: Commit Task 7**

Run:

```bash
git add README.md docs/user-manual.md
git commit -m "docs: document managed skill directories"
```

Expected: commit succeeds.

## Final Acceptance Checklist

- [ ] `uv run pytest` passes.
- [ ] Manual smoke test from Task 7 Step 5 passes.
- [ ] `./managed_dirs` is the only persistent managed-dir config file.
- [ ] `./skill_aliases` is the default alias file.
- [ ] `--alias-file` overrides `./skill_aliases`.
- [ ] `--skills-dir` and `--disabled-dir` keep single-pair behavior.
- [ ] `~/.codex/skills` cannot be removed.
- [ ] Removed extra roots are absent from `skills ls`, `skills alias ls`, `skills on`, and `skills off`.
- [ ] All added production functions are covered by tests that failed before implementation.
- [ ] No production code is committed without its corresponding RED/GREEN test evidence in the task history.
