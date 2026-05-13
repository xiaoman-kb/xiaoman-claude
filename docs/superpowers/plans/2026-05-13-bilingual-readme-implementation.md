# Bilingual README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete `README.zh-CN.md`, add language-switch links to both README files, and push the bilingual documentation update to GitHub.

**Architecture:** Keep `README.md` as the default English landing page, add a full Chinese mirror document with equivalent structure, and use lightweight top-level language links in both files. Reuse the existing screenshot block and project narrative so the two documents stay aligned.

**Tech Stack:** Markdown, Git, existing repository screenshots under `docs/image/`

---

### Task 1: Add language-switch links to the English README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write a failing content check for the English README language link**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
needle = "[简体中文](README.zh-CN.md)"
raise SystemExit(0 if needle in text else f"Missing: {needle}")
PY
```

Expected: FAIL because the English README does not yet contain the Chinese-language switch link.

- [ ] **Step 2: Add the top language switch line to `README.md`**

Insert this block immediately below the title:

```md
# xiaoman-claude

English | [简体中文](README.zh-CN.md)
```

The top of the file should then begin like this:

```md
# xiaoman-claude

English | [简体中文](README.zh-CN.md)

A terminal multi-agent development assistant built through learning, migration, and engineering iteration.
```

- [ ] **Step 3: Run the language-link check again**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
needle = "[简体中文](README.zh-CN.md)"
raise SystemExit(0 if needle in text else f"Missing: {needle}")
PY
```

Expected: PASS with exit code 0.

- [ ] **Step 4: Preview the README head to verify the order**

Run:

```bash
python - <<'PY'
from pathlib import Path
for i, line in enumerate(Path("README.md").read_text().splitlines()[:10], start=1):
    print(f"{i:>2}: {line}")
PY
```

Expected: title first, language switch second, one-line project description next.

- [ ] **Step 5: Commit the English README language link**

```bash
git add README.md
git commit -m "docs: add readme language switch links"
```

### Task 2: Create the complete Chinese README

**Files:**
- Create: `README.zh-CN.md`
- Verify: `docs/image/workspace-overview.png`
- Verify: `docs/image/message-flow.png`

- [ ] **Step 1: Write a failing existence/content check for the Chinese README**

Run:

```bash
python - <<'PY'
from pathlib import Path
path = Path("README.zh-CN.md")
if not path.exists():
    raise SystemExit("Missing: README.zh-CN.md")
text = path.read_text()
required = [
    "[English](README.md) | 简体中文",
    "## 核心能力",
    "## 快速开始",
]
missing = [item for item in required if item not in text]
raise SystemExit(0 if not missing else f"Missing markers: {missing}")
PY
```

Expected: FAIL because `README.zh-CN.md` does not exist yet.

- [ ] **Step 2: Create `README.zh-CN.md` with a full Chinese mirror structure**

Create the file with this complete content:

```md
# xiaoman-claude

[English](README.md) | 简体中文

一个通过学习、迁移和工程化迭代逐步构建出来的终端多 Agent 开发助手。

<p align="center">
  <img src="docs/image/workspace-overview.png" alt="展示队友、任务和 worktree 的工作区总览" width="48%" />
  <img src="docs/image/message-flow.png" alt="展示流式输出与消息流交互的终端界面" width="48%" />
</p>

终端截图：左侧是工作区协同总览，右侧是消息流式交互体验。

这个项目开始于我完整学习 [`learn-claude-code`](https://github.com/shareAI-lab/learn-claude-code) 之后，并在此基础上继续往前走：从理解核心思路，到迁移关键模式，再到把它做成一个更个人化、可运行、可扩展的终端系统。

它不是课程代码的直接拷贝，而是我在真正理解 agent loop、tool use、team protocol、autonomous agents、context compaction 和 git worktree isolation 这些机制之后，重新整理、工程化并逐步演化出来的版本。

## 这个项目为什么有意思

- 它记录了一个 Agent 系统从“学习样例”走向“个人工程实现”的过程。
- 它支持持续存在的队友 Agent，而不只是一次性的 subagent。
- 它把任务板和 git worktree 隔离结合在一起，支持并行协作。
- 它把终端体验往更像产品的方向推进，包括 Rich 消息流界面和流式输出。
- 它已经包含 skills、compact、后台执行、wait 和前台可取消能力。
- 它已经按职责拆成更聚焦的模块，更容易继续扩展，也更适合学习。

## 核心能力

- 主 Agent 循环，负责模型调用、工具编排和流式回复
- 持久化队友机制，支持基于 inbox 的通信和 team protocol
- 任务板能力，支持 owner、依赖关系和任务元数据
- 基于 git worktree 的并行任务隔离
- 使用 Rich 构建的终端 UI，支持消息流输出和轻量工具事件
- `wait` 工具，适合观察式工作流
- `Esc` 中断当前支持的前台任务，例如等待和流式回复
- skills 加载机制，用于复用工作模式
- context compact，上下文压缩能力
- 后台执行支持，适合较长时间运行的操作

## 快速开始

### 环境要求

- Python 3.10+
- Git
- Anthropic API Key

### 安装

```bash
git clone https://github.com/xiaoman-kb/xiaoman-claude.git
cd xiaoman-claude
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

然后编辑 `.env`，填入你自己的真实 API Key：

```env
ANTHROPIC_API_KEY=your_real_key
ANTHROPIC_BASE_URL=
MODEL_ID=claude-sonnet-4-20250514
```

### 运行

```bash
python agent_loop.py
```

## 运行体验

运行时，这个 CLI 的目标不是简单输出一堆原始日志，而是更像一个真正可用的终端产品：

- 以消息流为主，而不是到处都是厚重的大框日志
- 工具事件采用更轻量的呈现方式
- 支持助手回复流式输出
- 支持等待观察，让 lead 不必过早打断任务
- 支持 `Esc` 中断当前已支持的前台任务，而不是直接退出整个 CLI

## 架构概览

- `agent_loop.py`：很薄的入口文件，只负责启动 runtime
- `xiaoman_agent/runtime.py`：主编排循环、模型调用、工具执行、流式输出和 turn 生命周期
- `xiaoman_agent/team.py`：队友生命周期、inbox 协议、审批流程和团队协作
- `xiaoman_agent/tasks.py`：任务板、owner、依赖关系和任务状态
- `xiaoman_agent/worktrees.py`：git worktree 创建、绑定和隔离执行支持
- `xiaoman_agent/ui.py`：基于 Rich 的终端渲染、消息流、等待态和输入展示
- `xiaoman_agent/cancel.py`：前台取消状态和 `Esc` 监听逻辑
- `xiaoman_agent/skills.py`：skills 的加载与暴露
- `xiaoman_agent/compact.py`：上下文压缩行为
- `xiaoman_agent/background.py`：后台执行支持

## 仓库结构

```text
xiaoman-claude/
|- agent_loop.py
|- requirements.txt
|- .env.example
|- xiaoman_agent/
|  |- runtime.py
|  |- team.py
|  |- tasks.py
|  |- worktrees.py
|  |- ui.py
|  |- cancel.py
|  |- skills.py
|  |- compact.py
|  \- ...
|- tests/
|- docs/
\- skills/
```

## 建议的阅读顺序

如果你想从上到下理解这个仓库，可以按下面顺序阅读：

1. `agent_loop.py`
2. `xiaoman_agent/runtime.py`
3. `xiaoman_agent/team.py`
4. `xiaoman_agent/tasks.py`
5. `xiaoman_agent/worktrees.py`
6. `xiaoman_agent/ui.py`

## 致谢

这个项目的形成，离不开我对 [`learn-claude-code`](https://github.com/shareAI-lab/learn-claude-code) 的系统学习。

最开始只是围绕 agent loop、tool use、team protocol、autonomous agents 和 worktree isolation 的学习过程，但后来它逐步演化成了一个具有自己结构、UI 方向和工程取舍的独立项目。

## Roadmap

- 把取消机制扩展到更多前台任务之外的场景
- 改进 team 和 worktree 状态的恢复流程
- 增加更多终端效果截图或演示录屏
- 完善配置模板和启动引导
- 增加更丰富的快捷命令和内置帮助
- 补充更多围绕 team protocol 和 worktree isolation 的测试

## GitHub 首页设置建议

如果你希望仓库首页和 README 的整体气质保持一致，可以使用下面这组设置：

- Description: `A terminal multi-agent development assistant built from learning, migration, and engineering iteration.`
- Tagline: `From learning agent systems to building a personal multi-agent terminal harness.`
- Topics: `ai-agent`, `multi-agent`, `claude`, `anthropic`, `terminal-ui`, `rich`, `python`, `git-worktree`, `developer-tools`, `agentic-workflow`

这个仓库既是一个真正可运行的终端 Agent harness，也是“把学到的想法做成自己系统”的一份过程记录。
```

- [ ] **Step 3: Run the Chinese README existence/content check again**

Run:

```bash
python - <<'PY'
from pathlib import Path
path = Path("README.zh-CN.md")
if not path.exists():
    raise SystemExit("Missing: README.zh-CN.md")
text = path.read_text()
required = [
    "[English](README.md) | 简体中文",
    "## 核心能力",
    "## 快速开始",
]
missing = [item for item in required if item not in text]
raise SystemExit(0 if not missing else f"Missing markers: {missing}")
PY
```

Expected: PASS with exit code 0.

- [ ] **Step 4: Verify the screenshot references exist**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in [
    Path("docs/image/workspace-overview.png"),
    Path("docs/image/message-flow.png"),
]:
    if not path.exists():
        raise SystemExit(f"Missing asset: {path}")
print("OK")
PY
```

Expected: `OK`

- [ ] **Step 5: Commit the Chinese README**

```bash
git add README.zh-CN.md
git commit -m "docs: add chinese readme"
```

### Task 3: Verify bilingual README consistency and push

**Files:**
- Verify: `README.md`
- Verify: `README.zh-CN.md`

- [ ] **Step 1: Check editor diagnostics for both README files**

Use the editor diagnostics tool for:

- `file:///mnt/d/job_project/xiaoman-claude/README.md`
- `file:///mnt/d/job_project/xiaoman-claude/README.zh-CN.md`

Expected: no diagnostics in either file.

- [ ] **Step 2: Run a final bilingual README verification script**

Run:

```bash
python - <<'PY'
from pathlib import Path
checks = {
    "README.md": [
        "[简体中文](README.zh-CN.md)",
        "docs/image/workspace-overview.png",
        "docs/image/message-flow.png",
    ],
    "README.zh-CN.md": [
        "[English](README.md) | 简体中文",
        "docs/image/workspace-overview.png",
        "docs/image/message-flow.png",
        "## 核心能力",
        "## 快速开始",
        "## 架构概览",
    ],
}
for file_name, markers in checks.items():
    text = Path(file_name).read_text()
    missing = [item for item in markers if item not in text]
    if missing:
        raise SystemExit(f"{file_name} missing: {missing}")
print("OK")
PY
```

Expected: `OK`

- [ ] **Step 3: Verify git status before the final push**

Run:

```bash
git status --short
```

Expected: only documentation-related changes are present if not yet committed, or no output if task-level commits were already performed.

- [ ] **Step 4: Create the final bilingual documentation commit if needed**

```bash
git add README.md README.zh-CN.md
git commit -m "docs: polish bilingual readme presentation"
```

Expected: commit succeeds only if there are uncommitted documentation changes remaining. Skip only if the earlier task-level commits already left the worktree clean.

- [ ] **Step 5: Push to GitHub**

```bash
git push origin main
```

Expected: remote branch updates successfully.
