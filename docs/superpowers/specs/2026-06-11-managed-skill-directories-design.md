# Managed Skill Directories Design

## Summary

The `skills` CLI will support multiple managed skill directories. The default
Codex skill directory, `~/.codex/skills`, always remains managed. Users can add
extra enabled skill directories with `skills --add-dir <path>`. Added
directories are persisted in a project-local `managed_dirs` file in the current
working directory.

Each managed enabled directory has a sibling disabled directory. For an enabled
directory named `skills`, the disabled directory is named `skills_disabled` in
the same parent directory. For example, `~/.agents/skills` maps to
`~/.agents/skills_disabled`.

## Goals

- Persist additional managed skill directories in `./managed_dirs`.
- Always include `~/.codex/skills` in discovery and operations.
- Let `skills --add-dir ~/.agents/skills` add a managed directory permanently
  for the current project directory.
- Create both the enabled directory and its sibling disabled directory when a
  directory is added.
- Discover enabled and disabled skills across all managed directory pairs.
- Show each skill's source directory in `skills ls`.
- Show each skill's source directory under each alias in `skills alias ls`.
- Toggle skills only within their own managed directory pair.

## Non-Goals

- Do not change the `skill_aliases` file format.
- Do not add a database or global config file for managed directories.
- Do not move skills across unrelated roots.
- Do not remove the existing `--skills-dir`, `--disabled-dir`, or `--alias-file`
  compatibility path overrides.

## Configuration

The persistent managed directory file is named `managed_dirs` and lives in the
current working directory where the `skills` command is invoked.

Example:

```text
~/.agents/skills
/opt/company/codex-skills
```

The file stores one enabled skills directory per line. Blank lines and lines
starting with `#` are ignored. Paths are expanded with `Path.expanduser()`.

The default enabled directory, `~/.codex/skills`, is always included before any
entries loaded from `./managed_dirs`. This preserves existing behavior and gives
deterministic priority to the default directory.

If `--skills-dir` and `--disabled-dir` are provided, they keep their current
single-pair override behavior for compatibility. Extra managed directories from
`./managed_dirs` are used only when the command is running with default path
resolution.

## Directory Pairs

Each enabled directory maps to a disabled directory by replacing a final
directory name of `skills` with `skills_disabled`.

Examples:

```text
~/.codex/skills          -> ~/.codex/skills_disabled
~/.agents/skills         -> ~/.agents/skills_disabled
/opt/team/skills         -> /opt/team/skills_disabled
```

If the enabled directory name is not exactly `skills`, append `_disabled` to the
final path segment.

Example:

```text
/opt/team/custom-skills  -> /opt/team/custom-skills_disabled
```

The enabled and disabled paths for each pair must resolve to different paths.

## `--add-dir`

`skills --add-dir <path>` is a persistent management action. It:

1. Expands the provided path.
2. Derives the sibling disabled directory.
3. Creates both directories with `mkdir(parents=True, exist_ok=True)`.
4. Adds the enabled directory to `./managed_dirs` if it is not already listed.
5. Leaves `./managed_dirs` unchanged if the directory is already managed.
6. Prints a short message describing whether the directory was added or already
   managed.

`--add-dir` does not run a subcommand. It exits successfully after updating the
project-local configuration.

## Discovery

Discovery scans managed directory pairs in priority order:

1. Default pair derived from `~/.codex/skills`.
2. Extra pairs loaded from `./managed_dirs` in file order.

Within each pair, enabled skills take priority over disabled skills. Across
pairs, the earlier managed pair takes priority. If the same skill name appears
more than once, discovery keeps the first copy and emits a warning that includes
the ignored path.

Each discovered `Skill` records:

- `name`
- `status`
- `explicit_alias`
- `effective_alias`
- `description`
- `path`
- `managed_dir`, the enabled root that owns the skill

For a disabled skill, `managed_dir` is still the enabled root for that pair, not
the disabled directory. This gives stable display and lets operations know where
to move the skill back when enabling it.

## Operations

`skills on <target>` and `skills off <target>` continue to accept skill names or
alias names. Target resolution still uses the alias file.

When toggling a skill:

- If the skill is already in the requested state within its owning pair, report
  that it is already `ON` or `OFF`.
- If enabling, move from the owning disabled directory to the owning enabled
  directory.
- If disabling, move from the owning enabled directory to the owning disabled
  directory.
- If the target cannot be resolved to a discovered skill, report it as missing.

The command never moves a skill into a different managed directory pair.

## CLI Output

`skills ls` adds a `DIR` column:

```text
ALIAS      SKILL             STATUS  DIR                DESCRIPTION
langchain  langchain-rag     on      ~/.agents/skills   Retrieval tools.
core       deep-agents-core  off     ~/.codex/skills    Deep agent basics.
```

The directory column shows the owning enabled root, even for disabled skills.

`skills alias ls` changes from a single-line comma-separated format to a grouped
format that includes each skill's owning directory:

```text
langchain:
  langchain-rag      ~/.agents/skills
  langgraph-core     ~/.codex/skills
deep-agents-core:
  deep-agents-core   ~/.codex/skills
```

## Errors And Warnings

- Duplicate managed directory entries are ignored when writing with
  `--add-dir`.
- Duplicate discovered skill names produce warnings and keep the first copy by
  managed directory priority.
- Invalid `managed_dirs` rows are limited to lines with extra whitespace
  separated columns; those lines produce warnings and are ignored.
- Missing `managed_dirs` is not an error.
- Missing managed directories are skipped during discovery, except `--add-dir`
  creates the directories it adds.

## Testing

Tests will cover:

- Reading `managed_dirs` with comments, blank lines, and duplicate paths.
- `--add-dir` writes `./managed_dirs` and creates enabled and disabled
  directories.
- Default `~/.codex/skills` remains managed without `managed_dirs`.
- Discovery across multiple managed pairs.
- Duplicate skill warnings across enabled and disabled directories and across
  managed pairs.
- `skills ls` includes the `DIR` column and displays owning roots.
- `skills alias ls` lists each alias member with its owning root.
- `skills on/off` move skills within the correct owning pair.
- Existing single-pair path override tests keep passing.
