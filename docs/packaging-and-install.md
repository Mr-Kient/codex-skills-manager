# 更改代码后的打包与安装

## 1. 目标

改完代码后，需要区分两件事：

- 开发验证：在仓库内跑测试、跑命令
- 安装交付：把当前版本安装成真正可执行的 `skills`

这个项目的要求是：

- 开发时可以用 `uv` 虚拟环境
- 正式使用时不能依赖手动激活虚拟环境

## 2. 开发阶段

首次同步依赖：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --dev
```

开发验证：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
UV_CACHE_DIR=/tmp/uv-cache uv run skills --help
```

如果只是本地调试，直接用：

```bash
uv run skills ...
```

即可，不需要先安装到 `PATH`。

## 3. 改代码后的推荐流程

每次改完代码后，推荐按这个顺序处理：

1. 改代码
2. 跑测试
3. 如有发布意义的变更，更新版本号
4. 重新安装 CLI
5. 验证安装后的 `skills`

## 4. 版本号位置

当前版本号需要保持一致：

- [pyproject.toml](/home/kient/codex-ex_skills-management/pyproject.toml:3)
- [src/codex_skills_cli/__init__.py](/home/kient/codex-ex_skills-management/src/codex_skills_cli/__init__.py:1)

例如从 `0.1.2` 升到 `0.1.3`。

如果只是你本地临时改动、不需要保留安装历史，可以不改版本号，直接重装时使用 `--reinstall`。

## 5. 本地重新安装

最稳妥的方式：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall .
```

这个命令的含义：

- `--force`：覆盖已有工具安装
- `--reinstall`：强制重建工具环境，避免旧版本残留

安装完成后验证：

```bash
skills --help
skills alias
```

## 6. 构建分发包

如果你要生成 wheel 和源码包：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv build
```

产物会出现在 `dist/`：

- `*.whl`
- `*.tar.gz`

构建后可以从 wheel 安装：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall dist/codex_skills_cli-0.1.2-py3-none-any.whl
```

如果版本号变了，把文件名里的版本一起替换。

## 7. 完整示例

假设你已经改完代码，并把版本从 `0.1.2` 改为 `0.1.3`：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v
UV_CACHE_DIR=/tmp/uv-cache uv build
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall .
skills --help
skills alias
```

如果你希望验证安装的就是 wheel，而不是当前源码目录：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall dist/codex_skills_cli-0.1.3-py3-none-any.whl
skills --help
```

## 8. 故障排查

### 8.1 安装后命令还是旧行为

先确认 PATH 上实际命令：

```bash
type -a skills
command -V skills
```

如果 shell 里有旧的 `skills()` 函数，会覆盖真正的二进制。当前 shell 可先执行：

```bash
unset -f skills
hash -r
```

然后再运行：

```bash
skills --help
```

### 8.2 `uv tool install` 后还是像旧版本

优先使用：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv tool install --force --reinstall .
```

如果仍然可疑，检查已安装版本：

```bash
head -n 1 "$(command -v skills)"
```

以及项目版本号是否已更新。

### 8.3 网络受限环境

如果环境里不能访问 PyPI，`uv` 可能无法拉取构建依赖或重新解析依赖。

这时优先做法是：

- 先在可联网环境完成 `uv sync --dev`
- 或先构建 wheel
- 再在目标环境安装现成 wheel
