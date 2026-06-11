# Codex Skills CLI

Manage external Codex skills and aliases.

详细文档：

- [使用手册](docs/user-manual.md)
- [更改代码后的打包与安装](docs/packaging-and-install.md)

## Usage

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
