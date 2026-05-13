# Input Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current `xiaoman >>` prompt with a two-line light input bar that shows a minimal `> ` prompt plus idle/busy hint text without breaking buffered output behavior.

**Architecture:** Keep all footer rendering logic in `xiaoman_agent/ui.py`, where prompt formatting, divider rendering, and hint state live together. `xiaoman_agent/runtime.py` only flips the footer state between `idle` and `busy` at turn boundaries, so layout logic does not leak into runtime control flow.

**Tech Stack:** Python, Rich, pytest

---

## File Map

- Modify: `xiaoman_agent/ui.py`
  - Add a tiny footer state model, prompt/hint render helpers, and the new two-line input bar rendering path.
- Modify: `xiaoman_agent/runtime.py`
  - Switch footer state to `busy` when a turn starts and restore `idle` on every return path.
- Modify: `tests/test_ui.py`
  - Add regression tests for prompt text, idle/busy hints, and footer rendering.
- Modify: `tests/test_runtime_streaming.py`
  - Add runtime tests for state transitions only if helper functions are exported or directly testable.

## Task 1: Lock Footer Behavior With Tests

**Files:**
- Modify: `tests/test_ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests for footer hint state and prompt format**

Add these tests to `tests/test_ui.py`:

```python
from xiaoman_agent.ui import (
    build_input_footer_renderable,
    get_input_prompt_text,
    get_input_hint_text,
    set_input_bar_state,
)


def test_input_prompt_text_is_minimal():
    assert get_input_prompt_text() == "> "


def test_idle_hint_text_matches_design():
    set_input_bar_state("idle")
    assert get_input_hint_text() == "? 查看快捷命令"


def test_busy_hint_text_matches_design():
    set_input_bar_state("busy")
    assert get_input_hint_text() == "esc 可中断"
```

- [ ] **Step 2: Run the focused UI tests to verify failure**

Run:

```bash
pytest -q tests/test_ui.py::test_input_prompt_text_is_minimal
```

Expected:

- FAIL because the new footer helper functions do not exist yet

- [ ] **Step 3: Write the failing test for two-line footer rendering**

Add this test to `tests/test_ui.py`:

```python
def test_input_footer_renderable_contains_prompt_and_hint():
    set_input_bar_state("idle")
    renderable = build_input_footer_renderable()
    text = render_to_text(renderable)
    assert ">" in text
    assert "? 查看快捷命令" in text
```

- [ ] **Step 4: Write the failing test for buffered-output compatibility**

Add this test to `tests/test_ui.py`:

```python
def test_invalid_input_bar_state_falls_back_to_idle_hint():
    set_input_bar_state("unexpected")
    assert get_input_hint_text() == "? 查看快捷命令"
```

- [ ] **Step 5: Run the full UI test file to verify failure**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- FAIL because footer state/render helpers are not implemented yet

- [ ] **Step 6: Commit the red tests**

```bash
git add tests/test_ui.py
git commit -m "test: lock input bar footer behavior"
```

## Task 2: Implement The Two-Line Input Bar In `ui.py`

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Add a minimal footer state variable**

Near the existing console state fields in `xiaoman_agent/ui.py`, add:

```python
_input_bar_state = "idle"
```

- [ ] **Step 2: Add footer state setters and hint helpers**

Add these functions to `xiaoman_agent/ui.py`:

```python
def set_input_bar_state(state: str):
    global _input_bar_state
    _input_bar_state = state if state in {"idle", "busy"} else "idle"


def get_input_hint_text() -> str:
    if _input_bar_state == "busy":
        return "esc 可中断"
    return "? 查看快捷命令"


def get_input_prompt_text() -> str:
    return "> "
```

- [ ] **Step 3: Add a footer render helper**

Add this helper to `xiaoman_agent/ui.py`:

```python
def build_input_footer_renderable():
    divider = Text("─" * 40, style="dim")
    hint = Text(get_input_hint_text(), style="dim")
    return Group(divider, hint)
```

This helper intentionally renders the divider and the weak hint line only. The actual input cursor remains owned by `console.input(...)`.

- [ ] **Step 4: Update `input_prompt()` to use the new footer**

Replace the current `input_prompt()` body in `xiaoman_agent/ui.py` with:

```python
def input_prompt(label: str = "xiaoman") -> str:
    flush_pending_console_messages()
    console.print(build_input_footer_renderable())
    set_input_active(True)
    try:
        return console.input("[bold cyan]> [/]")
    finally:
        set_input_active(False)
        flush_pending_console_messages()
```

The `label` argument may remain for compatibility, but it is no longer used for visible prompt text.

- [ ] **Step 5: Run the UI test file and verify green**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- PASS

- [ ] **Step 6: Commit the UI footer implementation**

```bash
git add xiaoman_agent/ui.py tests/test_ui.py
git commit -m "feat: add two-line input bar footer"
```

## Task 3: Drive Footer State From Runtime

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Modify: `tests/test_runtime_streaming.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing runtime state test**

Add this test to `tests/test_runtime_streaming.py`:

```python
from xiaoman_agent.ui import get_input_hint_text, set_input_bar_state


def test_input_bar_state_defaults_back_to_idle_after_manual_reset():
    set_input_bar_state("busy")
    assert get_input_hint_text() == "esc 可中断"
    set_input_bar_state("idle")
    assert get_input_hint_text() == "? 查看快捷命令"
```

- [ ] **Step 2: Run the focused runtime test to verify failure if helpers are not yet available**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_input_bar_state_defaults_back_to_idle_after_manual_reset
```

Expected:

- FAIL before the footer state helpers are implemented

- [ ] **Step 3: Import the footer state setter in runtime**

Update the `xiaoman_agent/runtime.py` import list so it includes:

```python
from .ui import (
    console,
    input_prompt,
    live_wait,
    print_overview,
    print_status,
    print_text_response,
    print_tool_result,
    set_input_bar_state,
)
```

- [ ] **Step 4: Set footer state to busy at the start of each turn**

At the beginning of `agent_loop(messages: list)` in `xiaoman_agent/runtime.py`, add:

```python
set_input_bar_state("busy")
```

- [ ] **Step 5: Restore idle state on every return path**

Before each `return` inside `agent_loop(messages: list)`, ensure:

```python
set_input_bar_state("idle")
```

This includes:

- normal non-tool response exit
- manual compact exit
- any other explicit return from the loop

- [ ] **Step 6: Run the runtime test file and verify green**

Run:

```bash
pytest -q tests/test_runtime_streaming.py
```

Expected:

- PASS

- [ ] **Step 7: Run full verification**

Run:

```bash
pytest -q
python -m py_compile agent_loop.py xiaoman_agent/*.py
```

Expected:

- all tests pass
- no Python syntax errors

- [ ] **Step 8: Commit the runtime integration**

```bash
git add xiaoman_agent/runtime.py tests/test_runtime_streaming.py
git commit -m "refactor: drive input bar state from runtime"
```

## Self-Review

Spec coverage:

- minimal prompt text: Task 1 + Task 2
- idle/busy hint switching: Task 1 + Task 2 + Task 3
- runtime state restoration: Task 3
- compatibility with buffered input behavior: Task 1 + Task 2
- no full-screen layout expansion: preserved by architecture and file map

Placeholder scan:

- no `TODO`, `TBD`, or deferred placeholders remain

Type consistency:

- `set_input_bar_state`, `get_input_hint_text`, `get_input_prompt_text`, and `build_input_footer_renderable` are defined in `ui.py` and referenced consistently in the tests and runtime task steps
