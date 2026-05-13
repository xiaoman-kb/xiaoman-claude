# Agent Loop Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前单文件 `agent_loop.py` 按职责拆分为清晰模块，同时保持现有功能可用，并顺手优化少量命名与边界。

**Architecture:** 采用“薄入口 + 多模块”的方式保留现有运行行为。`agent_loop.py` 退化为组装层与入口，核心能力拆到 `xiaoman_agent/` 包下，按配置、任务、团队、worktree、技能、压缩、后台、循环分别收纳。整个重构以“接口先稳定，再迁移实现”为原则，避免一次性重写逻辑。

**Tech Stack:** Python 3、Anthropic SDK、dotenv、JSON 文件持久化、git worktree、threading

---

## File Structure

**Create**
- `xiaoman_agent/__init__.py`
- `xiaoman_agent/config.py`
- `xiaoman_agent/events.py`
- `xiaoman_agent/io_tools.py`
- `xiaoman_agent/tasks.py`
- `xiaoman_agent/worktrees.py`
- `xiaoman_agent/background.py`
- `xiaoman_agent/skills.py`
- `xiaoman_agent/compact.py`
- `xiaoman_agent/team.py`
- `xiaoman_agent/runtime.py`
- `tests/test_smoke_imports.py`

**Modify**
- `agent_loop.py`
- `requirements.txt`（仅在缺测试依赖时再改，默认不动）

**Responsibilities**
- `config.py`：环境变量、路径常量、模型客户端、提示词模板
- `events.py`：`EventBus` 与交流日志追加
- `io_tools.py`：`run_bash`、`safe_path`、`run_read/write/edit`
- `tasks.py`：`TodoManager`、`TaskManager`、任务扫描/认领/风险判定
- `worktrees.py`：`WorktreeManager`、worktree 命名与绑定辅助
- `background.py`：后台任务执行与通知队列
- `skills.py`：`SkillLoader`
- `compact.py`：`estimate_tokens`、`micro_compact`、`auto_compact`
- `team.py`：`MessageBus`、协议处理、`TeammateManager`
- `runtime.py`：`TOOL_HANDLERS` 组装、`subagent()`、`agent_loop()`、`main()`
- `agent_loop.py`：兼容入口，只负责调用 `xiaoman_agent.runtime.main`

### Task 1: 建立包结构与配置模块

**Files:**
- Create: `xiaoman_agent/__init__.py`
- Create: `xiaoman_agent/config.py`
- Modify: `agent_loop.py`
- Test: `tests/test_smoke_imports.py`

- [ ] **Step 1: 写一个最小导入测试**

```python
from xiaoman_agent import config


def test_config_exports_exist():
    assert config.WORKDIR is not None
    assert config.REPO_ROOT is not None
    assert config.MODEL is not None
```

- [ ] **Step 2: 运行测试并确认当前失败**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xiaoman_agent'
```

- [ ] **Step 3: 创建包入口**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/__init__.py
"""Modular runtime package for xiaoman agent loop."""
```

- [ ] **Step 4: 提取配置到 `config.py`**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/config.py
import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


def detect_repo_root(cwd: Path) -> Path | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode != 0:
            return None
        root = Path(r.stdout.strip())
        return root if root.exists() else None
    except Exception:
        return None


WORKDIR = Path.cwd()
REPO_ROOT = detect_repo_root(WORKDIR) or WORKDIR
MODEL = os.getenv("MODEL_ID")
CLIENT = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TASK_DIR = REPO_ROOT / ".tasks"
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
WORKTREES_DIR = REPO_ROOT / ".worktrees"
EXCHANGE_LOG_PATH = TEAM_DIR / "exchange_log.jsonl"
THRESHOLD = 50000
KEEP_RECENT = 3
POLL_INTERVAL = 5
IDLE_TIMEOUT = 60
PRESERVE_RESULT_TOOLS = {"read_file"}
```

- [ ] **Step 5: 将 `agent_loop.py` 顶部改为从新配置模块导入**

```python
from xiaoman_agent.config import (
    CLIENT as client,
    EXCHANGE_LOG_PATH,
    IDLE_TIMEOUT,
    INBOX_DIR,
    KEEP_RECENT,
    MODEL,
    POLL_INTERVAL,
    PRESERVE_RESULT_TOOLS,
    REPO_ROOT,
    SKILLS_DIR,
    TASK_DIR,
    TEAM_DIR,
    THRESHOLD,
    TRANSCRIPT_DIR,
    WORKDIR,
    WORKTREES_DIR,
)
```

- [ ] **Step 6: 重新运行导入测试**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
1 passed
```

### Task 2: 提取基础工具与事件模块

**Files:**
- Create: `xiaoman_agent/events.py`
- Create: `xiaoman_agent/io_tools.py`
- Modify: `agent_loop.py`
- Test: `tests/test_smoke_imports.py`

- [ ] **Step 1: 为工具模块增加简单行为测试**

```python
from pathlib import Path

from xiaoman_agent.io_tools import safe_path


def test_safe_path_resolves_inside_base(tmp_path: Path):
    p = safe_path("a.txt", base_dir=tmp_path)
    assert p == tmp_path / "a.txt"
```

- [ ] **Step 2: 运行测试并确认当前失败**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xiaoman_agent.io_tools'
```

- [ ] **Step 3: 提取事件模块**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/events.py
import json
import threading
import time
from pathlib import Path


EXCHANGE_LOG_LOCK = threading.Lock()


def append_exchange_log(log_path: Path, entry: dict):
    log_path.parent.mkdir(exist_ok=True, parents=True)
    payload = {"timestamp": time.time(), **entry}
    with EXCHANGE_LOG_LOCK:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class EventBus:
    def __init__(self, event_log_path: Path):
        self.path = event_log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")
```

- [ ] **Step 4: 提取 IO 工具**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/io_tools.py
import subprocess
from pathlib import Path

from .config import WORKDIR


def safe_path(p: str, base_dir: Path | None = None) -> Path:
    root = (base_dir or WORKDIR).resolve()
    path = (root / p).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path {p} is outside the working directory.")
    return path
```

- [ ] **Step 5: 从入口文件移除对应重复实现并改用导入**

```python
from xiaoman_agent.events import EventBus, append_exchange_log
from xiaoman_agent.io_tools import run_bash, run_edit, run_read, run_write, safe_path
```

- [ ] **Step 6: 运行测试与语法检查**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
python -m py_compile /mnt/d/job_project/xiaoman-claude/agent_loop.py
```

Expected:

```text
tests/test_smoke_imports.py::test_safe_path_resolves_inside_base PASSED
```

### Task 3: 提取任务与 worktree 子系统

**Files:**
- Create: `xiaoman_agent/tasks.py`
- Create: `xiaoman_agent/worktrees.py`
- Modify: `agent_loop.py`
- Test: `tests/test_smoke_imports.py`

- [ ] **Step 1: 为任务-worktree 绑定写一个最小回归测试**

```python
import json

from xiaoman_agent.tasks import TaskManager


def test_task_bind_worktree(tmp_path):
    tasks = TaskManager(tmp_path / ".tasks")
    task = json.loads(tasks.create("demo", "desc"))
    bound = json.loads(tasks.bind_worktree(task["id"], "demo-lane", "alice"))
    assert bound["worktree"] == "demo-lane"
    assert bound["owner"] == "alice"
    assert bound["status"] == "in_progress"
```

- [ ] **Step 2: 运行测试并确认当前失败**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xiaoman_agent.tasks'
```

- [ ] **Step 3: 提取 `TaskManager`、`scan_unclaimed_tasks`、`claim_task`、`task_requires_plan`**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/tasks.py
class TaskManager:
    ...


def scan_unclaimed_tasks(task_dir: Path) -> list:
    ...


def task_requires_plan(task: dict) -> bool:
    ...
```

- [ ] **Step 4: 提取 `WorktreeManager` 及辅助函数**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/worktrees.py
class WorktreeManager:
    ...


def ensure_task_worktree(task_id: int, owner: str, tasks: TaskManager, worktrees: WorktreeManager) -> str:
    ...
```

- [ ] **Step 5: 在入口层完成装配**

```python
TASKS = TaskManager(TASK_DIR)
WORKTREE_EVENTS = EventBus(WORKTREES_DIR / "events.jsonl")
WORKTREES = WorktreeManager(REPO_ROOT, WORKTREES_DIR, TASKS, WORKTREE_EVENTS)
```

- [ ] **Step 6: 运行测试与 worktree 烟雾验证**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
python -m py_compile /mnt/d/job_project/xiaoman-claude/agent_loop.py
```

Expected:

```text
2 passed
```

### Task 4: 提取队友、协议与后台模块

**Files:**
- Create: `xiaoman_agent/background.py`
- Create: `xiaoman_agent/team.py`
- Modify: `agent_loop.py`
- Test: `tests/test_smoke_imports.py`

- [ ] **Step 1: 增加团队模块导入测试**

```python
from xiaoman_agent.team import MessageBus


def test_message_bus_class_exists():
    assert MessageBus is not None
```

- [ ] **Step 2: 运行测试并确认当前失败**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xiaoman_agent.team'
```

- [ ] **Step 3: 提取 `BackgroundManager`**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/background.py
class BackgroundManager:
    ...
```

- [ ] **Step 4: 提取 `MessageBus`、协议状态与 `TeammateManager`**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/team.py
shutdown_requests = {}
plan_requests = {}


class MessageBus:
    ...


class TeammateManager:
    ...
```

- [ ] **Step 5: 将 `agent_loop.py` 中对应逻辑替换为导入与实例化**

```python
from xiaoman_agent.background import BackgroundManager
from xiaoman_agent.team import (
    MessageBus,
    TeammateManager,
    handle_plan_review,
    handle_shutdown_request,
    plan_requests,
    shutdown_requests,
    _check_shutdown_status,
)
```

- [ ] **Step 6: 运行测试与语法检查**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
python -m py_compile /mnt/d/job_project/xiaoman-claude/agent_loop.py
```

Expected:

```text
3 passed
```

### Task 5: 提取压缩、技能与运行时入口

**Files:**
- Create: `xiaoman_agent/compact.py`
- Create: `xiaoman_agent/skills.py`
- Create: `xiaoman_agent/runtime.py`
- Modify: `agent_loop.py`
- Test: `tests/test_smoke_imports.py`

- [ ] **Step 1: 增加运行时入口导入测试**

```python
from xiaoman_agent.runtime import main


def test_runtime_main_exists():
    assert callable(main)
```

- [ ] **Step 2: 运行测试并确认当前失败**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
```

Expected:

```text
E   ModuleNotFoundError: No module named 'xiaoman_agent.runtime'
```

- [ ] **Step 3: 提取压缩与技能模块**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/compact.py
def estimate_tokens(messages: list) -> int:
    return len(str(messages)) // 4
```

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/skills.py
class SkillLoader:
    ...
```

- [ ] **Step 4: 新建运行时模块，集中 `TOOL_HANDLERS`、`subagent()`、`agent_loop()`、`main()`**

```python
# /mnt/d/job_project/xiaoman-claude/xiaoman_agent/runtime.py
def main():
    history = []
    while True:
        try:
            query = input("\033[36mxiaoman >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
```

- [ ] **Step 5: 将根入口缩减为兼容壳**

```python
# /mnt/d/job_project/xiaoman-claude/agent_loop.py
from xiaoman_agent.runtime import main


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 完整回归检查**

Run:

```bash
pytest /mnt/d/job_project/xiaoman-claude/tests/test_smoke_imports.py -v
python -m py_compile /mnt/d/job_project/xiaoman-claude/agent_loop.py
python -m py_compile /mnt/d/job_project/xiaoman-claude/xiaoman_agent/*.py
```

Expected:

```text
4 passed
```

## Self-Review

- **Spec coverage:** 覆盖了配置、工具、任务、worktree、团队、后台、压缩、技能、主循环与入口拆分，没有遗漏当前主要职责。
- **Placeholder scan:** 计划中未使用 `TBD/TODO/以后再做` 这类占位描述。
- **Type consistency:** 统一沿用现有命名：`TaskManager`、`WorktreeManager`、`TeammateManager`、`BackgroundManager`、`SkillLoader`、`agent_loop`。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-agent-loop-decoupling.md`. Two execution options:

**1. Subagent-Driven (recommended)** - 我按任务逐个派新子代理执行，每步之间做检查，风险更低

**2. Inline Execution** - 我在当前会话直接按任务顺序重构，速度更快，但上下文压力更大

Which approach?
