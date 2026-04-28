# Skills CLI Design

Date: 2026-04-28

## Context

The current workflow is implemented in shell functions copied in
`bash_aliases.example`, backed by `skill_aliases.example`.

Skills are enabled when their directory is under `~/.codex/skills` and
disabled when their directory is under `~/.codex/skills_disabled`. Toggling a
skill moves the whole skill directory between those two locations. Alias data is
stored in `~/.codex/skill_aliases` as whitespace-separated `skill alias` pairs.
Multiple skills can share the same alias, so one alias can represent a batch of
skills. The existing shell setup also dynamically creates `<alias>-on` and
`<alias>-off` shell aliases.

The new CLI will preserve these data semantics while moving the workflow out of
shell aliases and into a portable command-line application.

## Goals

- Manage external Codex skills under `~/.codex/skills` and
  `~/.codex/skills_disabled`.
- Preserve the existing `~/.codex/skill_aliases` format.
- Let users create aliases for skills that do not yet have an explicit alias.
- Let users modify and delete aliases for skills that already have one.
- Support batch alias assignment through an interactive multi-select flow.
- Support batch enable and disable operations.
- Support enable and disable by skill name or alias name.
- Show all external skills with alias, status, and a concise description.
- Work on mainstream Linux distributions and macOS.
- Keep bash and zsh integration optional instead of making shell aliases the
  core runtime.
- Keep the domain model simple enough to rewrite later in Rust without changing
  user-facing data files.

## Non-Goals

- Do not manage built-in system skills under `.system`.
- Do not change Codex's skill loading model.
- Do not introduce a new database or config format.
- Do not require users to edit shell startup files for core functionality.
- Do not implement remote skill installation in this CLI.

## Technology Stack

The first implementation will use Python 3.12 with `uv`.

The CLI layer will use Typer. Table output will use Rich. Interactive
multi-select flows will use `prompt_toolkit` directly or through a thin
dependency such as Questionary if it meets the needed keyboard behavior. Tests
will use pytest.

This stack is chosen for implementation speed and portability. The code will
separate core logic from CLI/UI code so that a future Rust rewrite can preserve
the same command behavior and file semantics.

## Command Surface

The command name is `skills`.

Core commands:

```bash
skills ls
skills on <alias-or-skill>...
skills off <alias-or-skill>...
skills alias ls
skills alias set
skills alias unset
skills alias edit
skills shell init
```

`skills ls` lists external skills with these columns:

```text
ALIAS  SKILL  STATUS  DESCRIPTION
```

`STATUS` is `on`, `off`, or `missing`. Descriptions are read from the
`description:` field in `SKILL.md`, stripped of surrounding quotes, shortened to
the first sentence when possible, and truncated to a fixed display length.

`skills on` and `skills off` accept one or more targets. Each target may be a
skill name or an alias. If a target is an alias, the command applies to all
skills currently mapped to that alias. After moving at least one skill, the CLI
prints a message telling the user to restart Codex to reload skills.

`skills alias ls` prints the current alias mapping grouped by alias.

`skills alias set` starts an interactive assignment flow:

1. Show existing aliases and an option to create a new alias.
2. Only ask for typed alias text when the user chooses to create a new alias.
3. Show a multi-select list of skills.
4. Space toggles selected skills.
5. Enter saves the selected skill-to-alias assignments.

`skills alias edit` starts from an existing alias and lets the user batch change
the skills mapped to that alias.

`skills alias unset` lets the user remove explicit aliases from selected skills.
After removal, each skill falls back to using its skill name as its effective
alias.

`skills shell init` prints shell code for bash or zsh. The generated shell code
is optional and may define `<alias>-on` and `<alias>-off` convenience functions
that call `skills on <alias>` and `skills off <alias>`.

## Architecture

The implementation will be split into small modules with stable boundaries.

`skills.store` owns filesystem paths and file IO:

- Resolve `CODEX_HOME`, defaulting to `~/.codex`.
- Resolve enabled, disabled, and alias config paths.
- Read and write `skill_aliases` atomically.
- Ignore full-line comments and blank lines on read.
- Write a normalized alias file containing sorted `skill alias` entries.

`skills.core` owns domain behavior:

- Discover external skills from enabled and disabled directories.
- Ignore hidden skill names and `.system`.
- Read skill metadata from `SKILL.md`.
- Resolve effective aliases.
- Resolve command targets into concrete skill names.
- Enable and disable skills by moving directories.
- Validate alias names using the existing safe character set:
  `A-Z`, `a-z`, `0-9`, `.`, `_`, and `-`.

`skills.cli` owns Typer command definitions, output formatting, and exit codes.

`skills.interactive` owns keyboard-driven multi-select flows.

`skills.shell` owns generated bash/zsh snippets and keeps shell integration out
of core behavior.

## Data Model

The main in-memory model is deliberately small:

```python
Skill(
    name: str,
    status: Literal["on", "off", "missing"],
    explicit_alias: str | None,
    effective_alias: str,
    description: str,
    path: Path | None,
)
```

The alias file remains line-oriented:

```text
deep-agents-core langchain
langgraph-fundamentals langchain
```

If a skill has no explicit alias entry, its effective alias is the skill name.
Duplicate skill entries in the alias file will be treated as invalid input for
write operations. Read operations will prefer the first entry and report a
warning so the user can fix the file.

## Error Handling

The CLI fails with actionable messages and non-zero exit codes for:

- Unknown skill targets.
- Unknown aliases.
- Unsafe alias names.
- Conflicting enabled and disabled directories for the same skill.
- Missing `SKILL.md` for a candidate skill directory.
- Failed directory moves.
- Alias file parse errors that would make a write unsafe.

Read-only commands print warnings for line-level alias file issues and still
exit successfully when skill discovery can continue. They exit non-zero only
when the Codex home cannot be read or the alias file cannot be parsed safely at
all.

## Portability

The CLI will use only Python standard filesystem primitives and portable
dependencies. It will avoid Linux-only shell behavior. Shell integration output
will be generated for bash and zsh explicitly. The core commands must work
without shell integration on Ubuntu, CentOS, Rocky Linux, and macOS.

## Testing Strategy

Tests will use temporary fake Codex homes instead of the real `~/.codex`.

Coverage includes:

- Discovering enabled and disabled external skills.
- Ignoring `.system` skills.
- Parsing descriptions from `SKILL.md`.
- Preserving the `skill alias` file format.
- Alias fallback behavior.
- Multiple skills sharing one alias.
- Enabling and disabling by skill name.
- Enabling and disabling by alias.
- Batch operations with partial no-op targets.
- Unsafe alias validation.
- Shell init output for bash and zsh.
- CLI smoke tests through Typer's test runner.

Interactive flows will be tested at the core boundary by verifying the mutation
logic separately from keyboard input.

## Future Rust Rewrite

The Python implementation will keep the command surface, data files, and domain
operations stable. If the CLI is later rewritten in Rust, the Rust version can
reuse the same behavior contract:

- Same `~/.codex` directory layout.
- Same `skill_aliases` file format.
- Same target resolution rules.
- Same command names and flags listed in this spec.
- Same shell integration strategy.

The Python code keeps business logic out of Typer callbacks so that the behavior
remains easy to port.
