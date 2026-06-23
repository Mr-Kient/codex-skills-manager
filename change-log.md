# Project Context Change Log

## 2026-06-11

### Current Purpose

This repository contains `codex-skills-cli`, a Python CLI for managing external
Codex skills and aliases.

The tool manages:

- Enabled skills directory, defaulting to `~/.codex/skills`
- Disabled skills directory, defaulting to `~/.codex/skills_disabled`
- Alias mapping file, defaulting to `~/.codex/skill_aliases`

The main executable is `skills`.

### Implemented Capabilities

- `skills ls` lists external skills with alias, skill name, status, and
  description.
- `skills on <alias-or-skill>...` enables one or more skills by moving
  directories into the enabled directory.
- `skills off <alias-or-skill>...` disables one or more skills by moving
  directories into the disabled directory.
- `skills alias ls` groups discovered skills by effective alias.
- `skills alias set` starts an interactive alias assignment flow.
- `skills alias edit` currently reuses the `set` flow.
- `skills alias unset` removes explicit aliases from selected skills.
- `skills shell init` generates optional bash/zsh helper functions such as
  `langchain-on` and `langchain-off`.

### Path Configuration

Path resolution order is:

1. CLI flags: `--skills-dir`, `--disabled-dir`, `--alias-file`
2. Environment variables: `CODEX_SKILLS_DIR`,
   `CODEX_SKILLS_DISABLED_DIR`, `CODEX_SKILL_ALIASES_FILE`
3. `CODEX_HOME`, defaulting to `~/.codex`
4. Built-in defaults under `~/.codex`

### Packaging And Installation

The project uses:

- Python 3.12+
- `uv`
- Typer
- Rich
- Questionary
- pytest

Development commands:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --dev
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
UV_CACHE_DIR=/tmp/uv-cache uv run skills --help
```

Install or refresh the local CLI:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall .
```

The installed command must run directly from `PATH` as `skills`; normal use
must not require activating a virtual environment.

### Documentation Added

- `docs/user-manual.md`: end-user usage guide.
- `docs/packaging-and-install.md`: development, packaging, and reinstall guide.
- `README.md`: links to both documents.

### Recent Fixes

- Fixed `skills alias` with no subcommand so it shows help and exits cleanly.
- Fixed alias prompt cancellation so cancelled selection exits cleanly.
- Fixed Questionary checkbox handling by omitting `default` when no skills are
  preselected.
- Bumped package version to `0.1.2` after the prompt fixes.

### Important Operational Notes

- A legacy shell function named `skills()` in `~/.bash_aliases` can shadow the
  installed `skills` executable.
- To verify which command is being used:

```bash
type -a skills
command -V skills
```

- Temporary shell cleanup:

```bash
unset -f skills
hash -r
```

### Current Repository State Notes

At the time this context log was created, these files were intentionally left
untracked because they are local/user context rather than committed project
source:

- `.codex`
- `bash_aliases.example`
- `skill_aliases.example`

The project also has a local CodeGraph index under `.codegraph/`, created with:

```bash
codegraph init
codegraph index
```

### Verification Reference

The most recent full verification after code fixes reported:

```text
27 passed
```

Command used:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
```
