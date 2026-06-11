# 使用手册

## 1. 工具作用

`skills` 用来管理外部 Codex skills：

- 查看所有 skills、alias、状态和描述
- 按 skill 名或 alias 批量开启/关闭 skills
- 管理项目内 `skill_aliases` 映射
- 生成 bash/zsh 可选快捷函数

默认管理的目录和文件：

- 始终管理：`~/.codex/skills`
- 当前项目额外目录列表：`./managed_dirs`
- 当前项目 alias 文件：`./skill_aliases`

## 2. 安装后如何运行

安装后直接运行：

```bash
skills --help
```

开发时也可以在仓库里直接运行：

```bash
uv run skills --help
```

## 3. 查看当前 skills

查看所有 skills：

```bash
skills ls
```

输出包含五列：

- `ALIAS`
- `SKILL`
- `STATUS`
- `DIR`
- `DESCRIPTION`

其中：

- `on` 表示 skill 在启用目录里
- `off` 表示 skill 在禁用目录里
- `DIR` 表示该 skill 所属的启用根目录

## 3.1 添加和移除被管理目录

添加额外 skills 目录：

```bash
skills --add-dir ~/.agents/skills
```

这会创建：

- `~/.agents/skills`
- `~/.agents/skills_disabled`

移除已管理目录：

```bash
skills --remove-dir ~/.agents/skills
```

移除时会先把 `~/.agents/skills_disabled` 里的 skill 目录恢复到
`~/.agents/skills`，然后从 `./managed_dirs` 删除该目录。之后
`skills ls` 和 `skills alias ls` 不再显示该目录中的 skills。

## 4. 开启和关闭 skills

按 skill 名操作：

```bash
skills on langchain-rag
skills off langchain-rag
```

按 alias 批量操作：

```bash
skills on langchain
skills off langchain
```

说明：

- 一个 alias 可以对应多个 skills
- 执行 `on` 或 `off` 后，CLI 会提示重启 Codex 重新加载 skills

## 5. alias 管理

查看 alias 分组：

```bash
skills alias ls
```

输出会按 alias 分组，并显示每个 skill 所属的启用目录。

新增或批量设置 alias：

```bash
skills alias set
```

交互流程：

1. 先选择已有 alias，或者选择 `<create new alias>`
2. 只有在选择新建 alias 时，才会要求输入 alias 名
3. 进入 skills 多选列表
4. 用空格勾选，用回车确认

编辑 alias：

```bash
skills alias edit
```

当前实现里，`edit` 和 `set` 共用同一套交互流程，适合重新给一批 skill 指定 alias。

移除显式 alias：

```bash
skills alias unset
```

移除后，该 skill 会退回到“skill 名即 alias”的默认行为。

## 6. 自定义路径

如果你只想让某一条命令临时使用自定义路径，可以显式传入：

```bash
skills \
  --skills-dir /path/to/skills \
  --disabled-dir /path/to/skills_disabled \
  --alias-file /path/to/skill_aliases \
  ls
```

也可以用环境变量：

```bash
export CODEX_SKILLS_DIR=/path/to/skills
export CODEX_SKILLS_DISABLED_DIR=/path/to/skills_disabled
export CODEX_SKILL_ALIASES_FILE=/path/to/skill_aliases
skills ls
```

路径优先级：

1. 命令行参数
2. 环境变量
3. 项目默认值：
   `./skill_aliases` 和 `./managed_dirs`
4. `CODEX_HOME`
5. 默认值 `~/.codex/...`

说明：

- `--skills-dir`、`--disabled-dir`、`--alias-file` 只影响当前命令
- 这些参数不会写入 `./managed_dirs`
- 平时新增长期管理目录应使用 `--add-dir`

## 7. shell 快捷函数

生成可选 shell 快捷函数：

```bash
skills shell init
```

当前 shell 临时启用：

```bash
eval "$(skills shell init)"
```

之后可以直接用：

```bash
langchain-on
langchain-off
```

## 8. 注意事项

- `skills on/off` 会直接移动真实 skill 目录，不是模拟操作
- `skills --remove-dir` 不能移除默认的 `~/.codex/skills`
- alias 名只能包含这些字符：
  - `A-Z`
  - `a-z`
  - `0-9`
  - `.`
  - `_`
  - `-`

## 9. 常见问题

### 9.1 `skills alias` 仍然显示旧的 shell 函数用法

如果你以前在 `~/.bash_aliases` 里定义过旧版 `skills()` shell function，shell 会优先执行那个函数，而不是新安装的 CLI。

当前 shell 临时修复：

```bash
unset -f skills
hash -r
skills alias
```

长期修复：

- 删除 `~/.bash_aliases` 里旧的 `skills()` 函数
- 重新打开终端

### 9.2 想确认现在调用的是哪个 `skills`

```bash
type -a skills
command -V skills
```

### 9.3 取消交互选择

在 `alias set` / `alias edit` 里取消选择时，程序会直接退出，不会写入任何内容。
