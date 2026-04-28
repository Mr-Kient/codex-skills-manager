# Codex Skills CLI

Manage external Codex skills and aliases.

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

## Development

```bash
uv sync --dev
uv run pytest
uv run skills --help
```

Installed usage must run as `skills` from `PATH`; users do not activate this
project's virtual environment.
