# Esc Cancel Current Task Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real `Esc` cancellation for the current foreground `wait` and lead streaming response without exiting the CLI process.

**Architecture:** Introduce a small Linux terminal cancellation helper that manages a per-turn cancel flag and listener thread. Wire that helper into `runtime.py` so each lead turn gets fresh cancellation scope, then make `live_wait()` and streaming generation stop cooperatively when the flag is raised, while preserving partial streamed text and returning to the prompt.

**Tech Stack:** Python 3, `threading`, `termios`, `tty`, `select`, Rich, pytest

---

## File Structure

- Create: `xiaoman_agent/cancel.py`
  - Owns turn-scoped cancellation state and Linux `Esc` listener lifecycle.
- Modify: `xiaoman_agent/ui.py`
  - Extend `live_wait()` to support cooperative cancellation and lightweight cancellation summaries.
- Modify: `xiaoman_agent/runtime.py`
  - Start/stop per-turn cancellation, pass cancellation checks into foreground work, and surface cancellation results without exiting.
- Modify: `tests/test_ui.py`
  - Add failing tests for `wait` cancellation behavior.
- Modify: `tests/test_runtime_streaming.py`
  - Add failing tests for streaming cancellation state handling and runtime cleanup behavior.

### Task 1: Add Turn Cancellation Helper

**Files:**
- Create: `xiaoman_agent/cancel.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing tests for turn cancellation state**

Add these tests to `tests/test_runtime_streaming.py`:

```python
from xiaoman_agent.cancel import TurnCancellation


def test_turn_cancellation_starts_not_cancelled():
    state = TurnCancellation()
    assert state.is_cancelled() is False


def test_turn_cancellation_can_cancel_and_reset():
    state = TurnCancellation()
    state.cancel()
    assert state.is_cancelled() is True
    state.reset()
    assert state.is_cancelled() is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_turn_cancellation_starts_not_cancelled tests/test_runtime_streaming.py::test_turn_cancellation_can_cancel_and_reset
```

Expected:

```text
FAIL ... ModuleNotFoundError: No module named 'xiaoman_agent.cancel'
```

- [ ] **Step 3: Create the minimal cancellation state module**

Create `xiaoman_agent/cancel.py` with:

```python
import os
import select
import sys
import termios
import threading
import tty


class TurnCancellation:
    def __init__(self):
        self._event = threading.Event()

    def reset(self):
        self._event.clear()

    def cancel(self):
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class EscListener:
    def __init__(self, state: TurnCancellation):
        self.state = state
        self._thread = None
        self._stop = threading.Event()
        self._active = False
        self._started = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> bool:
        if self._started:
            return self._active
        if not sys.stdin.isatty():
            self._started = True
            self._active = False
            return False
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def _run(self):
        fd = sys.stdin.fileno()
        try:
            old = termios.tcgetattr(fd)
        except termios.error:
            self._active = False
            return
        self._active = True
        try:
            tty.setcbreak(fd)
            while not self._stop.is_set():
                ready, _, _ = select.select([fd], [], [], 0.1)
                if not ready:
                    continue
                data = os.read(fd, 1)
                if data == b"\x1b":
                    self.state.cancel()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            self._active = False
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_turn_cancellation_starts_not_cancelled tests/test_runtime_streaming.py::test_turn_cancellation_can_cancel_and_reset
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/cancel.py tests/test_runtime_streaming.py
git commit -m "feat: add turn cancellation state"
```

### Task 2: Add Wait Cancellation Support

**Files:**
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests for wait cancellation**

Add these tests to `tests/test_ui.py`:

```python
from xiaoman_agent.cancel import TurnCancellation


def test_live_wait_returns_cancelled_when_flag_is_raised():
    state = TurnCancellation()

    def cancel_after_first_tick(_seconds):
        state.cancel()

    summary = live_wait(
        seconds=5,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=cancel_after_first_tick,
        is_cancelled=state.is_cancelled,
    )

    assert summary == "Wait cancelled."


def test_live_wait_returns_normal_summary_when_not_cancelled():
    summary = live_wait(
        seconds=1,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
        is_cancelled=lambda: False,
    )

    assert summary == "Waited 1s."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_ui.py::test_live_wait_returns_cancelled_when_flag_is_raised tests/test_ui.py::test_live_wait_returns_normal_summary_when_not_cancelled
```

Expected:

```text
FAIL ... TypeError: live_wait() got an unexpected keyword argument 'is_cancelled'
```

- [ ] **Step 3: Implement minimal cooperative cancellation in `live_wait()`**

Update `xiaoman_agent/ui.py` so `live_wait()` looks like:

```python
def live_wait(
    seconds: int,
    *,
    get_team,
    get_tasks,
    get_worktrees,
    sleep_fn,
    is_cancelled=lambda: False,
):
    duration = max(0, int(seconds))
    flush_pending_console_messages()
    console.print(Text("waiting...", style="dim"))
    for _ in range(duration * 10):
        if is_cancelled():
            return "Wait cancelled."
        sleep_fn(0.1)
    if is_cancelled():
        return "Wait cancelled."
    return f"Waited {duration}s."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest -q tests/test_ui.py::test_live_wait_returns_cancelled_when_flag_is_raised tests/test_ui.py::test_live_wait_returns_normal_summary_when_not_cancelled
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/ui.py tests/test_ui.py
git commit -m "feat: add wait cancellation"
```

### Task 3: Add Streaming Cancellation Result Handling

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing tests for streaming cancellation helpers**

Add these tests to `tests/test_runtime_streaming.py`:

```python
def test_stream_result_marks_cancellation():
    result = make_stream_result("partial", cancelled=True, response=None, events=[])
    assert result["text"] == "partial"
    assert result["cancelled"] is True


def test_stream_result_defaults_to_not_cancelled():
    result = make_stream_result("done", cancelled=False, response=None, events=[])
    assert result["text"] == "done"
    assert result["cancelled"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_stream_result_marks_cancellation tests/test_runtime_streaming.py::test_stream_result_defaults_to_not_cancelled
```

Expected:

```text
FAIL ... NameError: name 'make_stream_result' is not defined
```

- [ ] **Step 3: Add a small stream-result helper in `runtime.py`**

Add this helper near the existing streaming helpers:

```python
def make_stream_result(text: str, *, cancelled: bool, response, events: list):
    return {
        "response": response,
        "text": text,
        "events": events,
        "cancelled": cancelled,
    }
```

Then refactor `create_streamed_response()` to return this shape instead of a tuple.

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_stream_result_marks_cancellation tests/test_runtime_streaming.py::test_stream_result_defaults_to_not_cancelled
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/runtime.py tests/test_runtime_streaming.py
git commit -m "refactor: add stream result helper"
```

### Task 4: Wire Esc Cancellation Into Streaming

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing tests for cancellation-aware streaming**

Add these tests to `tests/test_runtime_streaming.py`:

```python
from types import SimpleNamespace


def test_create_streamed_response_stops_when_cancelled(monkeypatch):
    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="hello"),
            )
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text=" world"),
            )

        def get_final_message(self):
            return "final-response"

    monkeypatch.setattr("xiaoman_agent.runtime.CLIENT.messages.stream", lambda **_: FakeStream())

    calls = {"count": 0}

    def is_cancelled():
        calls["count"] += 1
        return calls["count"] >= 2

    result = create_streamed_response([], is_cancelled=is_cancelled)

    assert result["cancelled"] is True
    assert result["text"] == "hello"


def test_create_streamed_response_returns_complete_result_when_not_cancelled(monkeypatch):
    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="hello"),
            )
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text=" world"),
            )

        def get_final_message(self):
            return "final-response"

    monkeypatch.setattr("xiaoman_agent.runtime.CLIENT.messages.stream", lambda **_: FakeStream())

    result = create_streamed_response([], is_cancelled=lambda: False)

    assert result["cancelled"] is False
    assert result["text"] == "hello world"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_create_streamed_response_stops_when_cancelled tests/test_runtime_streaming.py::test_create_streamed_response_returns_complete_result_when_not_cancelled
```

Expected:

```text
FAIL ... TypeError: create_streamed_response() got an unexpected keyword argument 'is_cancelled'
```

- [ ] **Step 3: Implement cancellation-aware streaming**

Update `create_streamed_response()` in `xiaoman_agent/runtime.py` so it accepts `is_cancelled=lambda: False` and checks it inside the event loop:

```python
def create_streamed_response(messages: list, is_cancelled=lambda: False):
    events = []
    text_chunks = []
    last_rendered_text = ""
    stream_rendered = False
    response = None
    cancelled = False
    safe_messages = sanitize_messages_for_api(messages)
    with Live(build_assistant_renderable(""), console=console, refresh_per_second=6, transient=False, auto_refresh=False) as live:
        with CLIENT.messages.stream(model=MODEL, system=SYSTEM, messages=safe_messages, tools=PARENT_TOOLS, max_tokens=8000) as stream:
            for event in stream:
                if is_cancelled():
                    cancelled = True
                    break
                events.append(event)
                if getattr(event, "type", "") == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    text = getattr(delta, "text", "")
                    if text:
                        text_chunks.append(text)
                        current_text = "".join(text_chunks)
                        if should_refresh_stream_view(current_text, last_rendered_text, len(text)):
                            live.update(build_assistant_renderable(current_text), refresh=True)
                            last_rendered_text = current_text
                            stream_rendered = True
            if not cancelled:
                response = stream.get_final_message()
        final_text = "".join(text_chunks)
        if final_text.strip() and final_text != last_rendered_text:
            live.update(build_assistant_renderable(final_text), refresh=True)
            stream_rendered = True
    result = make_stream_result(final_text, cancelled=cancelled, response=response, events=events)
    result["stream_rendered"] = stream_rendered
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_create_streamed_response_stops_when_cancelled tests/test_runtime_streaming.py::test_create_streamed_response_returns_complete_result_when_not_cancelled
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/runtime.py tests/test_runtime_streaming.py
git commit -m "feat: support esc cancellation for streaming"
```

### Task 5: Wire Esc Listener Around Lead Turns

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Test: `tests/test_runtime_streaming.py`

- [ ] **Step 1: Write the failing tests for runtime turn lifecycle**

Add these tests to `tests/test_runtime_streaming.py`:

```python
class DummyListener:
    def __init__(self, state):
        self.state = state
        self.started = 0
        self.stopped = 0
        self.active = True

    def start(self):
        self.started += 1
        return True

    def stop(self):
        self.stopped += 1


def test_run_turn_starts_and_stops_listener():
    state = TurnCancellation()
    listener = DummyListener(state)
    calls = []

    def work():
        calls.append("work")
        return "done"

    result = run_with_turn_cancellation(state, listener, work)

    assert result == "done"
    assert listener.started == 1
    assert listener.stopped == 1
    assert state.is_cancelled() is False


def test_run_turn_resets_cancellation_before_work():
    state = TurnCancellation()
    state.cancel()
    listener = DummyListener(state)

    def work():
        return state.is_cancelled()

    result = run_with_turn_cancellation(state, listener, work)

    assert result is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_run_turn_starts_and_stops_listener tests/test_runtime_streaming.py::test_run_turn_resets_cancellation_before_work
```

Expected:

```text
FAIL ... NameError: name 'run_with_turn_cancellation' is not defined
```

- [ ] **Step 3: Implement turn lifecycle helper and runtime wiring**

Add this helper to `xiaoman_agent/runtime.py`:

```python
def run_with_turn_cancellation(state, listener, work):
    state.reset()
    listener.start()
    try:
        return work()
    finally:
        listener.stop()
        state.reset()
```

Then wire `agent_loop()` to use a fresh `TurnCancellation` plus `EscListener`, and pass `state.is_cancelled` into:

```python
create_streamed_response(messages, is_cancelled=state.is_cancelled)
```

and:

```python
live_wait(..., is_cancelled=state.is_cancelled)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_run_turn_starts_and_stops_listener tests/test_runtime_streaming.py::test_run_turn_resets_cancellation_before_work
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/runtime.py tests/test_runtime_streaming.py
git commit -m "feat: wire esc cancellation into lead turns"
```

### Task 6: Surface Cancellation Messages and Final Verification

**Files:**
- Modify: `xiaoman_agent/runtime.py`
- Modify: `xiaoman_agent/ui.py`
- Test: `tests/test_runtime_streaming.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests for visible cancellation messages**

Add these tests to `tests/test_runtime_streaming.py`:

```python
def test_stream_cancel_message_is_printed_without_duplicate_body(monkeypatch):
    printed = []
    monkeypatch.setattr("xiaoman_agent.runtime.print_status", lambda message, style="dim": printed.append((message, style)))

    result = {
        "response": None,
        "text": "partial",
        "events": [],
        "cancelled": True,
        "stream_rendered": True,
    }

    handle_stream_result(result)

    assert ("response cancelled.", "dim") in printed


def test_wait_cancelled_summary_is_short():
    assert "Team:" not in "Wait cancelled."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest -q tests/test_runtime_streaming.py::test_stream_cancel_message_is_printed_without_duplicate_body tests/test_runtime_streaming.py::test_wait_cancelled_summary_is_short
```

Expected:

```text
FAIL ... NameError: name 'handle_stream_result' is not defined
```

- [ ] **Step 3: Implement result handling and complete runtime integration**

Add this helper to `xiaoman_agent/runtime.py`:

```python
def handle_stream_result(result: dict):
    streamed_text = result["text"]
    stream_rendered = result.get("stream_rendered", False)
    if result.get("cancelled"):
        print_status("response cancelled.", style="dim")
        return None
    if should_print_final_stream_text(streamed_text, stream_rendered):
        print_text_response(streamed_text)
    return result["response"]
```

Update the streaming call site in `agent_loop()` to use:

```python
stream_result = create_streamed_response(messages, is_cancelled=state.is_cancelled)
response = handle_stream_result(stream_result)
if stream_result.get("cancelled"):
    break
```

Ensure `wait` tool results already return `Wait cancelled.` when cancelled and continue through existing tool result rendering.

- [ ] **Step 4: Run focused tests and full verification**

Run:

```bash
pytest -q tests/test_ui.py tests/test_runtime_streaming.py
python -m py_compile agent_loop.py xiaoman_agent/*.py
pytest -q
```

Expected:

```text
all selected tests pass
all files compile
full test suite passes
```

- [ ] **Step 5: Commit**

```bash
git add xiaoman_agent/cancel.py xiaoman_agent/ui.py xiaoman_agent/runtime.py tests/test_ui.py tests/test_runtime_streaming.py
git commit -m "feat: support esc cancellation for foreground tasks"
```

## Spec Coverage Check

- Real `Esc` detection in Linux terminal: Task 1, Task 5
- Turn-scoped cancellation state: Task 1, Task 5
- Cancel `wait`: Task 2
- Cancel lead streaming: Task 3, Task 4, Task 6
- Preserve partial streamed text: Task 4, Task 6
- Return to normal prompt without exiting CLI: Task 5, Task 6
- Keep scope away from shell subprocess cancellation: all tasks intentionally avoid changes to `io_tools.py` and `worktrees.py`

## Self-Review Notes

- No placeholder steps remain.
- Every behavior in the approved spec maps to at least one task.
- Function and helper names are consistent across later tasks: `TurnCancellation`, `EscListener`, `make_stream_result`, `run_with_turn_cancellation`, `handle_stream_result`.
