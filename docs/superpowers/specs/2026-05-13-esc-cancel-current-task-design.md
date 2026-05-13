# Esc Cancel Current Task Design

## Goal

Add real `Esc` cancellation for the current foreground task without exiting the CLI process.

This design only covers two foreground activities:

- `wait`
- lead-model streaming response generation

The purpose is to make the bottom hint `esc 可中断` truthful for these two cases while keeping the overall program alive and ready for the next input.

## Scope

In scope:

- detect the `Esc` key in the Linux terminal while a foreground task is running
- cancel the current `wait` invocation
- cancel the current lead-model streaming response
- return control to the normal input loop after cancellation
- keep already rendered partial assistant text when a streamed response is cancelled

Out of scope:

- cancelling `bash`
- cancelling `worktree_run`
- cancelling background tasks
- cancelling teammate thread work
- Windows-specific input handling
- redesigning unrelated UI areas

## User Intent

The user does not want `Esc` to terminate the entire program.

The intended behavior is:

- if the current foreground task is waiting, `Esc` stops that wait
- if the current foreground task is streaming a response, `Esc` stops that response
- after that, the program remains usable and returns to the input prompt

This is “cancel current task”, not “quit application”.

## Desired Experience

### Wait

If the lead is in a `wait` period:

```text
waiting...
```

When `Esc` is pressed:

```text
wait cancelled.
```

Then the CLI returns to the normal prompt.

### Streaming response

If the lead is currently streaming a response:

- already streamed content remains visible
- further generation stops quickly after `Esc`

Then a lightweight hint is shown:

```text
response cancelled.
```

Then the CLI returns to the normal prompt.

## Design Summary

Introduce a per-turn cancellation controller with a real `Esc` listener.

The design has three pieces:

1. a lightweight cancellation state object for the current foreground turn
2. a Linux terminal listener that watches for `Esc`
3. cooperative cancellation checks inside `wait` and streaming generation

The listener does not directly terminate the process. It only marks the current turn as cancelled.

Foreground work then stops itself at defined safe checkpoints.

## Architecture

### 1. Turn-scoped cancellation state

Each foreground `agent_loop()` turn gets a fresh cancellation scope.

This scope should support:

- clear/reset at the start of a turn
- mark-cancelled when `Esc` is detected
- read-only checks from running foreground operations

Important rule:

- cancellation state must be per turn, not sticky across future turns

This prevents one `Esc` press from leaking into later requests.

### 2. Esc listener

Add a small Linux-only terminal listener that runs while a foreground turn is active.

Implementation approach:

- use `termios`
- use `tty`
- use `select`
- run the listener in a lightweight background thread

Responsibilities:

- watch standard input for key presses
- detect the single-byte `Esc` key
- set the current turn cancellation flag

Non-responsibilities:

- do not print full UI output
- do not raise `KeyboardInterrupt`
- do not terminate the process

### 3. Cooperative cancellation

Foreground operations check the cancellation flag and stop gracefully.

This is cooperative cancellation, not forced process termination.

That is the main reason this design excludes shell tools for now.

## Wait Cancellation Design

`wait` currently sleeps for a duration and returns a summary.

To support responsive cancellation:

- replace single large sleep spans with small polling intervals
- after each short interval, check the cancellation state

Recommended polling granularity:

- `0.1s` to `0.2s`

Behavior:

- if no cancellation occurs, `wait` finishes normally
- if cancellation occurs, `wait` stops early and returns `Wait cancelled.`

UI behavior:

- continue using the lightweight waiting presentation
- after cancellation, emit a small completion line rather than an exception dump

## Streaming Cancellation Design

Lead-model streaming currently loops over stream events and updates the rendered assistant text.

To support cancellation:

- check the cancellation state during event consumption
- if cancelled, stop consuming new stream events
- exit the streaming context cleanly

Behavior:

- keep already collected text chunks
- do not discard text already rendered to the terminal
- stop additional model generation as soon as the cooperative stop path can run
- return a cancellation outcome that the runtime can distinguish from a normal completion

User-visible result:

- partial answer remains visible
- a short weak hint such as `response cancelled.` is shown
- the program returns to the prompt

## Runtime Flow

### Turn start

When a new lead turn begins:

- create or reset the current-turn cancellation scope
- start the `Esc` listener
- mark the input bar as busy

### Turn end

When the turn ends normally or by cancellation:

- stop the `Esc` listener
- clear the turn cancellation state
- mark the input bar as idle
- return to normal prompt handling

### Failure safety

If the `Esc` listener cannot start:

- foreground work must still run normally
- the UI should not claim real `Esc` cancellation is available unless the listener is active

## UI Rules

The current busy hint says:

- `esc 可中断`

After implementation, this text becomes accurate for the supported foreground activities.

Cancellation result messages should remain lightweight:

- `wait cancelled.`
- `response cancelled.`

Rules:

- no stack traces
- no large panels
- no application exit

## Unsupported Cases

This design intentionally does not support:

- killing an already running shell subprocess
- stopping `worktree_run`
- stopping teammate internal tool execution
- cancelling background jobs that have already started

Reason:

- those cases require process-level or thread-level interruption and cleanup
- they are riskier and should be designed separately

## Error Handling

The cancellation system must fail soft.

Rules:

- if terminal raw-mode setup fails, the program should continue without `Esc` cancellation
- if the listener thread fails, the current turn should still complete normally
- cleanup logic must restore terminal settings
- cancellation should never leave the CLI stuck in raw mode

## Module Responsibilities

### `xiaoman_agent/ui.py`

UI owns the visible hints and any helper text related to cancellation.

Responsibilities:

- reflect whether foreground work is in a cancel-capable busy state
- render lightweight cancellation result messages

### `xiaoman_agent/runtime.py`

Runtime owns foreground turn lifecycle and cancellation wiring.

Responsibilities:

- create/reset per-turn cancellation state
- start and stop the listener around lead turns
- pass cancellation checks into `wait` and streaming code
- distinguish cancelled streaming from normal streaming completion

### New terminal-cancellation helper module

A dedicated helper module is recommended for the low-level terminal listener logic.

Responsibilities:

- raw terminal setup/restore
- `Esc` detection
- turn-scoped cancellation flag management

This keeps low-level input handling out of `ui.py` and reduces coupling inside `runtime.py`.

## Testing Strategy

Add focused tests for:

- cancellation state resets cleanly between turns
- `wait` returns normal output when not cancelled
- `wait` returns cancellation output when the cancel flag is raised
- streaming code reports cancellation distinctly from normal completion
- partial streamed text is preserved on cancellation
- terminal cleanup runs on listener shutdown

Verification commands for implementation phase:

- `pytest -q`
- `python -m py_compile agent_loop.py xiaoman_agent/*.py`

## Trade-Offs

Advantages:

- real `Esc` behavior for foreground tasks
- matches the user’s expectation of “cancel current task”
- avoids killing the whole application
- keeps scope small enough for a focused implementation

Costs:

- Linux terminal handling becomes more complex
- requires careful cleanup of raw terminal mode
- does not yet cover shell subprocess cancellation

## Acceptance Criteria

The design is successful when all of the following are true:

- pressing `Esc` during `wait` stops the wait early
- pressing `Esc` during lead streaming stops further response generation
- the CLI does not exit after cancellation
- the next prompt still works normally
- partial streamed content remains visible after response cancellation
- supported cancellation is limited to the agreed scope and does not claim more than it implements

## Open Decisions Resolved

The following decisions are fixed by this design:

- `Esc` means “cancel current foreground task”, not “quit the app”
- the first supported targets are `wait` and lead streaming only
- cancellation is cooperative, not forced subprocess termination
- cancellation state is scoped to one foreground turn
