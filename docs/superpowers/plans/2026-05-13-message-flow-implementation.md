# Message Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the middle terminal area with a Claude Code-like mixed message flow while preserving structured rendering for task, worktree, inbox, and detail outputs.

**Architecture:** Keep `xiaoman_agent/ui.py` as the rendering hub, but introduce a classification-first message-flow path for ordinary events and assistant text. `xiaoman_agent/runtime.py` stays thin and only chooses whether an output should render as an event line or as a structured block.

**Tech Stack:** Python, Rich, pytest

---

## File Map

- Modify: `xiaoman_agent/ui.py`
  - Add message-flow helpers for assistant text, tool events, system status, and structured-result classification.
  - Keep existing buffering logic for teammate output and active input.
- Modify: `xiaoman_agent/runtime.py`
  - Route ordinary tool output through the new event-line renderer.
  - Keep structured output tools on the table/JSON path.
- Modify: `tests/test_ui.py`
  - Add regression tests for classification, assistant text rendering, and event-line formatting.
- Modify: `tests/test_runtime_streaming.py`
  - Add focused tests for runtime classification behavior if helper functions are introduced there.

## Task 1: Lock The Message-Flow Boundary With Tests

**Files:**
- Modify: `tests/test_ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests for ordinary tool event lines**

Add these tests to `tests/test_ui.py`:

```python
from rich.text import Text

from xiaoman_agent.ui import (
    build_structured_tool_renderable,
    format_tool_event_lines,
    render_to_text,
)


def test_plain_tool_output_renders_as_event_lines():
    lines = format_tool_event_lines("bash", "Done", actor="lead")
    assert len(lines) == 2
    assert isinstance(lines[0], Text)
    assert "Bash" in lines[0].plain
    assert "Done" in lines[1].plain


def test_structured_tool_output_still_uses_table_rendering():
    rendered = build_structured_tool_renderable("task_list", "[ ] 1: setup repo")
    text = render_to_text(rendered)
    assert "Tasks" in text
    assert "setup repo" in text
```

- [ ] **Step 2: Run the UI test file to verify failure**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- FAIL because `build_structured_tool_renderable` and `format_tool_event_lines` do not exist yet

- [ ] **Step 3: Write the failing test for assistant plain-text rendering**

Add this test to `tests/test_ui.py`:

```python
from rich.console import Group

from xiaoman_agent.ui import build_assistant_text_renderable


def test_assistant_text_renderable_is_not_panel():
    renderable = build_assistant_text_renderable("Hello\n\nWorld")
    assert isinstance(renderable, Group)
    text = render_to_text(renderable)
    assert "Hello" in text
    assert "World" in text
    assert "Assistant" not in text
```

- [ ] **Step 4: Run the focused assistant test to verify failure**

Run:

```bash
pytest -q tests/test_ui.py::test_assistant_text_renderable_is_not_panel
```

Expected:

- FAIL because `build_assistant_text_renderable` does not exist yet

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/test_ui.py
git commit -m "test: lock message flow rendering behavior"
```

## Task 2: Implement Message-Flow Rendering In `ui.py`

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Add structured-tool classification constants**

In `xiaoman_agent/ui.py`, add a shared constant near the top:

```python
STRUCTURED_TOOL_NAMES = {
    "task_list",
    "list_teammates",
    "todo",
    "worktree_list",
    "read_inbox",
    "task_get",
    "worktree_status",
    "worktree_events",
    "shutdown_response",
}
```

- [ ] **Step 2: Add helper to format ordinary tool output as event lines**

Add this implementation to `xiaoman_agent/ui.py`:

```python
def _format_event_summary(output: Any, max_lines: int = 2, max_chars: int = 160) -> str:
    clipped = render_tool_window_text(str(output).splitlines(), max_lines=max_lines)
    clipped = " | ".join(part.strip() for part in clipped.splitlines() if part.strip())
    return (clipped or "(no output)")[:max_chars]


def format_tool_event_lines(tool_name: str, output: Any, actor: str | None = None) -> list[Text]:
    title = f"{actor + ' · ' if actor else ''}{tool_name}"
    title = title.replace("bash", "Bash", 1).replace("read_file", "ReadFile", 1)
    summary = _format_event_summary(output)
    status_style = "red" if str(output).startswith("Error") else "green"
    return [
        Text.assemble(("• ", "cyan"), (title, "bold white")),
        Text.assemble(("  └ ", "dim"), (summary, status_style)),
    ]
```

- [ ] **Step 3: Add helper for structured-only renderables**

Add this implementation to `xiaoman_agent/ui.py`:

```python
def build_structured_tool_renderable(tool_name: str, output: Any, actor: str | None = None):
    text = str(output)
    if tool_name == "task_list":
        return _build_task_table(text)
    if tool_name == "list_teammates":
        return _build_teammate_table(text)
    if tool_name == "todo":
        return _build_todo_table(text)
    if tool_name == "worktree_list":
        return _build_worktree_table(text)
    return _build_json_panel(tool_name, text)
```

- [ ] **Step 4: Replace assistant panel rendering with plain-text group rendering**

Replace the current assistant render path in `xiaoman_agent/ui.py` with:

```python
def build_assistant_text_renderable(text: str):
    normalized = (text or "").strip()
    lines = normalized.splitlines() or [" "]
    return Group(*[Text(line) if line else Text("") for line in lines])


def print_text_response(text: str):
    if not (text or "").strip():
        return
    flush_pending_console_messages()
    console.print(build_assistant_text_renderable(text))
```

- [ ] **Step 5: Update `print_tool_result()` to use event lines by default**

Update `print_tool_result()` in `xiaoman_agent/ui.py` to:

```python
def print_tool_result(tool_name: str, output: Any, actor: str | None = None):
    flush_pending_console_messages()
    if tool_name in STRUCTURED_TOOL_NAMES:
        console.print(build_structured_tool_renderable(tool_name, output, actor=actor))
        return
    for line in format_tool_event_lines(tool_name, output, actor=actor):
        console.print(line)
```

- [ ] **Step 6: Reuse the shared summary helper for teammate events**

Update teammate formatting to share `_format_event_summary()`:

```python
def format_teammate_event_line(name: str, tool_name: str, output: Any, max_lines: int = 2, max_chars: int = 160) -> Text:
    summary = _format_event_summary(output, max_lines=max_lines, max_chars=max_chars)
    return Text.assemble(
        ("• ", "cyan"),
        (name, "bold cyan"),
        (" · ", "dim"),
        (tool_name, "bold yellow"),
        (" -> ", "dim"),
        (summary, "red" if str(output).startswith("Error") else "white"),
    )
```

- [ ] **Step 7: Run the UI test file and verify green**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- PASS

- [ ] **Step 8: Commit the UI implementation**

```bash
git add xiaoman_agent/ui.py tests/test_ui.py
git commit -m "feat: add message flow UI rendering"
```

## Task 3: Keep Runtime Thin And Use The New UI Paths

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Modify: `tests/test_runtime_streaming.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing test for ordinary runtime tool rendering**

Add this test to `tests/test_runtime_streaming.py`:

```python
from xiaoman_agent.ui import STRUCTURED_TOOL_NAMES


def test_bash_is_not_classified_as_structured_output():
    assert "bash" not in STRUCTURED_TOOL_NAMES


def test_task_list_remains_structured_output():
    assert "task_list" in STRUCTURED_TOOL_NAMES
```

- [ ] **Step 2: Run the focused runtime test to verify failure if the constant is not exported yet**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_bash_is_not_classified_as_structured_output
```

Expected:

- FAIL before `STRUCTURED_TOOL_NAMES` is available for import

- [ ] **Step 3: Remove assistant panel-only imports from runtime**

Update the import list in `xiaoman_agent/runtime.py` so it no longer depends on panel-specific assistant rendering helpers. Keep:

```python
from .ui import console, input_prompt, live_wait, print_overview, print_status, print_text_response, print_tool_result
```

and remove any imports that only existed for the old assistant panel path.

- [ ] **Step 4: Keep runtime rendering calls thin**

Keep the existing event/render calls in `agent_loop()` and `main()` but ensure they use the new `ui.py` implementation without extra panel logic:

```python
print_tool_result(block.name, clip_tool_output(str(output)), actor="lead")
...
print_text_response(streamed_text)
```

No additional runtime-side branching should be added here unless required to preserve structured outputs.

- [ ] **Step 5: Run the runtime test file and verify green**

Run:

```bash
pytest -q tests/test_runtime_streaming.py
```

Expected:

- PASS

- [ ] **Step 6: Run full verification**

Run:

```bash
pytest -q
python -m py_compile agent_loop.py xiaoman_agent/*.py
```

Expected:

- all tests pass
- no Python syntax errors

- [ ] **Step 7: Commit the runtime integration**

```bash
git add xiaoman_agent/runtime.py tests/test_runtime_streaming.py
git commit -m "refactor: route runtime through message flow rendering"
```

## Self-Review

Spec coverage:

- message-flow tool rendering: Task 1 + Task 2
- assistant plain text rendering: Task 1 + Task 2
- structured output preservation: Task 1 + Task 2 + Task 3
- teammate event compatibility: Task 2
- runtime integration without behavior changes: Task 3

Placeholder scan:

- no `TODO`, `TBD`, or deferred implementation markers remain

Type consistency:

- `STRUCTURED_TOOL_NAMES`, `build_structured_tool_renderable`, `format_tool_event_lines`, and `build_assistant_text_renderable` are defined in `ui.py` and referenced consistently in tests and runtime tasks
