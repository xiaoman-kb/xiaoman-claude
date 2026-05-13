# Rich Streaming UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `agent_loop.py` 增加精简启动总览、主模型真实流式回复，以及工具输出滑动窗口渲染。

**Architecture:** 在 `xiaoman_agent/ui.py` 中集中实现 Rich 渲染与 streaming/live 辅助函数；在 `xiaoman_agent/runtime.py` 中接入 Anthropic streaming 响应与工具窗口；保持业务 handler 不变，仅替换终端输出层。 启动总览和 `wait` 共享同一套概览渲染，但启动页做活跃项过滤与限条数，工具输出则进入固定窗口缓存。

**Tech Stack:** Python, Anthropic SDK, Rich

---

### Task 1: 扩展 UI 渲染层

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: 写失败测试，覆盖精简总览与工具滑动窗口**

```python
from xiaoman_agent.ui import build_overview_renderable, render_tool_window_text


def test_overview_filters_and_limits_rows():
    rendered = build_overview_renderable(
        team_output="alice:idle\nbob:shutdown\ncharlie:working",
        task_output="[ ] 1: setup\n[x] 2: done\n[>] 3: refactor owner=alice",
        worktree_output='[{"name":"a","status":"active","task_id":1,"branch":"wt/a","path":"/tmp/a"},{"name":"b","status":"removed","task_id":2,"branch":"wt/b","path":"/tmp/b"}]',
        compact=True,
        max_items=5,
    )
    text = render_to_text(rendered)
    assert "bob" not in text
    assert "done" not in text
    assert "removed" not in text
    assert "alice" in text
    assert "refactor" in text


def test_tool_window_keeps_recent_lines_only():
    text = render_tool_window_text([f"line {i}" for i in range(20)], max_lines=5)
    assert "line 0" not in text
    assert "line 19" in text
```

- [ ] **Step 2: 运行测试，确认红灯**

Run: `pytest -q tests/test_ui.py`
Expected: FAIL，提示 `build_overview_renderable` 缺少参数或 `render_tool_window_text` 未定义。

- [ ] **Step 3: 在 `ui.py` 中实现最小渲染功能**

```python
def render_tool_window_text(lines: list[str], max_lines: int = 12) -> str:
    recent = lines[-max_lines:]
    return "\n".join(recent)


def build_overview_renderable(team_output: str, task_output: str, worktree_output: str, compact: bool = False, max_items: int = 8):
    team_table = _build_teammate_table(team_output, active_only=compact, max_items=max_items)
    task_table = _build_task_table(task_output, active_only=compact, max_items=max_items)
    worktree_table = _build_worktree_table(worktree_output, active_only=compact, max_items=max_items)
    return Panel(Group(team_table, task_table, worktree_table), title="Workspace Overview", border_style="cyan")
```

- [ ] **Step 4: 运行测试，确认绿灯**

Run: `pytest -q tests/test_ui.py`
Expected: PASS

### Task 2: 为主模型接入真实流式回复

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: 写失败测试，覆盖流式聚合逻辑**

```python
from xiaoman_agent.runtime import collect_stream_text


class FakeTextEvent:
    type = "content_block_delta"
    delta = type("Delta", (), {"text": "hello"})()


class FakeTextEvent2:
    type = "content_block_delta"
    delta = type("Delta", (), {"text": " world"})()


def test_collect_stream_text_combines_text_deltas():
    result = collect_stream_text([FakeTextEvent(), FakeTextEvent2()])
    assert result == "hello world"
```

- [ ] **Step 2: 运行测试，确认红灯**

Run: `pytest -q tests/test_runtime_streaming.py`
Expected: FAIL，提示 `collect_stream_text` 未定义。

- [ ] **Step 3: 实现最小流式收集函数与主循环接入**

```python
def collect_stream_text(events) -> str:
    chunks = []
    for event in events:
        if getattr(event, "type", "") == "content_block_delta":
            delta = getattr(event, "delta", None)
            text = getattr(delta, "text", "")
            if text:
                chunks.append(text)
    return "".join(chunks)
```

```python
with CLIENT.messages.stream(model=MODEL, system=SYSTEM, messages=messages, tools=PARENT_TOOLS, max_tokens=8000) as stream:
    response = stream.get_final_message()
    text_chunks = []
    for event in stream:
        ...  # append delta text and refresh rich panel
```

- [ ] **Step 4: 运行测试，确认绿灯**

Run: `pytest -q tests/test_runtime_streaming.py`
Expected: PASS

### Task 3: 为工具输出接入滑动窗口面板

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Modify: `xiaoman_agent/runtime.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: 写失败测试，覆盖窗口裁剪**

```python
from xiaoman_agent.runtime import clip_tool_output


def test_clip_tool_output_keeps_recent_tail():
    text = "\n".join(f"line {i}" for i in range(30))
    clipped = clip_tool_output(text, max_lines=6, max_chars=80)
    assert "line 0" not in clipped
    assert "line 29" in clipped
```

- [ ] **Step 2: 运行测试，确认红灯**

Run: `pytest -q tests/test_runtime_streaming.py`
Expected: FAIL，提示 `clip_tool_output` 未定义。

- [ ] **Step 3: 实现最小窗口裁剪和工具输出 live 面板**

```python
def clip_tool_output(text: str, max_lines: int = 12, max_chars: int = 1200) -> str:
    tail = text[-max_chars:]
    lines = tail.splitlines()
    return "\n".join(lines[-max_lines:])
```

```python
print_tool_result(block.name, clip_tool_output(str(output)), actor="lead")
```

- [ ] **Step 4: 运行测试，确认绿灯**

Run: `pytest -q tests/test_runtime_streaming.py`
Expected: PASS

### Task 4: 验证整体验证链路

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `tests/test_runtime_streaming.py`

- [ ] **Step 1: 运行 UI 与 streaming 测试**

Run: `pytest -q tests/test_ui.py tests/test_runtime_streaming.py`
Expected: PASS

- [ ] **Step 2: 运行全量测试**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 3: 运行编译检查**

Run: `python -m py_compile agent_loop.py xiaoman_agent/*.py tests/*.py`
Expected: no output

- [ ] **Step 4: 进行导入烟雾验证**

Run: `python - <<'PY'
import agent_loop
from xiaoman_agent.runtime import collect_stream_text, clip_tool_output
print('IMPORT_OK')
print(collect_stream_text([]))
print(clip_tool_output('a\nb\nc'))
PY`
Expected: 输出 `IMPORT_OK`
