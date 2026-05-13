# Wait Light Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the large `Workspace Overview` panel from the `wait` tool and replace it with a one-line waiting hint plus a short completion summary.

**Architecture:** Keep the change local to `xiaoman_agent/ui.py` by simplifying `live_wait()` rather than branching in runtime. Tests lock the returned summary so `wait` becomes lighter without affecting the rest of the message flow or the `wait(seconds=...)` tool interface.

**Tech Stack:** Python, Rich, pytest

---

## File Map

- Modify: `xiaoman_agent/ui.py`
  - Simplify `live_wait()` so it no longer renders `Workspace Overview` and no longer returns the full workspace snapshot.
- Modify: `tests/test_ui.py`
  - Add wait-specific regression tests for the lighter return text.

## Task 1: Lock The New Wait Output With Tests

**Files:**
- Modify: `tests/test_ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test for a short wait summary**

Add this test to `tests/test_ui.py`:

```python
def test_live_wait_returns_short_summary_without_workspace_dump():
    summary = live_wait(
        seconds=0,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
    )
    assert summary == "Waited 0s."
```

- [ ] **Step 2: Write the failing test for removed dashboard sections**

Add this test to `tests/test_ui.py`:

```python
def test_live_wait_summary_no_longer_contains_workspace_sections():
    summary = live_wait(
        seconds=0,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
    )
    assert "Team:" not in summary
    assert "Tasks:" not in summary
    assert "Worktrees:" not in summary
```

- [ ] **Step 3: Run the focused wait tests to verify failure**

Run:

```bash
pytest -q tests/test_ui.py::test_live_wait_returns_short_summary_without_workspace_dump
```

Expected:

- FAIL because `live_wait()` currently returns the large `Team / Tasks / Worktrees` summary

- [ ] **Step 4: Run the UI test file to verify red state**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- FAIL because the new wait expectations do not match current behavior

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/test_ui.py
git commit -m "test: lock wait light mode behavior"
```

## Task 2: Simplify `live_wait()` In `ui.py`

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Remove overview snapshot rendering from `live_wait()`**

Replace the current snapshot-based implementation in `xiaoman_agent/ui.py` with a lightweight wait path:

```python
def live_wait(
    seconds: int,
    *,
    get_team,
    get_tasks,
    get_worktrees,
    sleep_fn,
):
    duration = max(0, int(seconds))
    flush_pending_console_messages()
    console.print(Text("waiting...", style="dim"))
    for _ in range(duration):
        sleep_fn(1)
    return f"Waited {duration}s."
```

The unused callback arguments remain in the signature for interface compatibility.

- [ ] **Step 2: Run the wait-focused tests and verify green**

Run:

```bash
pytest -q tests/test_ui.py::test_live_wait_returns_short_summary_without_workspace_dump tests/test_ui.py::test_live_wait_summary_no_longer_contains_workspace_sections
```

Expected:

- PASS

- [ ] **Step 3: Run the full UI test file and verify green**

Run:

```bash
pytest -q tests/test_ui.py
```

Expected:

- PASS

- [ ] **Step 4: Run full verification**

Run:

```bash
pytest -q
python -m py_compile agent_loop.py xiaoman_agent/*.py
```

Expected:

- all tests pass
- no Python syntax errors

- [ ] **Step 5: Commit the wait light mode implementation**

```bash
git add xiaoman_agent/ui.py tests/test_ui.py
git commit -m "refactor: simplify wait tool display"
```

## Self-Review

Spec coverage:

- remove `Workspace Overview` during wait: Task 1 + Task 2
- use a one-line waiting hint: Task 2
- shorten the final wait result: Task 1 + Task 2
- keep the tool interface unchanged: Task 2

Placeholder scan:

- no `TODO`, `TBD`, or deferred placeholders remain

Type consistency:

- `live_wait()` keeps the same parameter signature in both the tests and implementation steps
