# Input Bar Design

## Goal

Refine the terminal bottom input area into a Claude Code-like two-line light input bar.

The new bottom area should:

- keep a minimal primary input line
- keep a persistent weak hint line below it
- switch the hint text based on idle vs busy state
- preserve compatibility with the current buffered-output protection

This change only covers the bottom input area. It does not redesign the startup overview or the middle message flow.

## Scope

In scope:

- redesign the terminal input area around `input_prompt()`
- add a two-line visual model: prompt line + weak hint line
- support at least two bottom-bar states: idle and busy
- keep teammate/background buffering safe during active input

Out of scope:

- redesigning the startup overview
- redesigning the middle message flow
- adding a full-screen terminal layout manager
- implementing real keyboard interrupt handling beyond current behavior
- changing tool execution or agent logic

## Desired Experience

The bottom area should feel lighter and more product-like than the current `xiaoman >>` prompt.

Target idle shape:

```text
────────────────────────────────────────
> 
? 查看快捷命令
```

Target busy shape:

```text
────────────────────────────────────────
> 
esc 可中断
```

The key idea is not a heavy status bar. It is a calm, stable input footer with one primary action line and one faint contextual hint.

## Design Summary

Use a two-line light input bar:

- line 1: the actual prompt line, simplified to `> `
- line 2: a weak contextual hint line

The hint line changes with state:

- idle: show a help-style hint
- busy: show an execution/interruption-style hint

This preserves the case-study feel without introducing a fragile full-screen layout.

## Input Bar States

### 1. Idle State

Shown when the system is ready for the next user input.

Display:

```text
> 
? 查看快捷命令
```

Rules:

- the prompt is minimal: `> `
- the hint is low emphasis
- the hint is informational, not interactive UI chrome

### 2. Busy State

Shown while the assistant is actively responding, streaming, or executing tool work for the current turn.

Display:

```text
> 
esc 可中断
```

Rules:

- the text communicates that the session is busy
- it may be informational only in the first implementation
- the UI must not imply a real interrupt shortcut unless the runtime already supports it or the wording is intentionally descriptive

### 3. Return To Idle

After the current turn finishes, the hint line returns to the idle hint.

Rules:

- no sticky busy state after completion
- no extra history lines should be printed just to announce the state reset

## Visual Rules

The input area should remain visually separate from the message flow above it, but lightly.

Rules:

- use a simple divider or spacing before the bottom area
- avoid heavy borders or nested panels
- keep the prompt line visually stronger than the hint line
- keep the hint line dim and secondary

Recommended emphasis hierarchy:

- divider: faint
- prompt line: clear and readable
- hint line: dim

## Module Responsibilities

### `xiaoman_agent/ui.py`

This remains the primary owner of bottom input rendering.

New responsibilities:

- format the prompt line
- format the weak hint line
- expose a small state model for bottom-bar hints
- render the two-line input area before reading input
- render a busy hint during response execution and restore idle afterward

Suggested abstraction boundary:

- a helper that returns the current hint text from a small set of states
- a helper that prints the divider + hint line
- `input_prompt()` remains the single point that initiates user input

### `xiaoman_agent/runtime.py`

Runtime should only signal state transitions, not own layout details.

Expected responsibilities:

- set bottom-bar state to busy when entering a response cycle
- restore bottom-bar state to idle when a turn completes
- avoid direct printing of bottom-bar layout

The rendering logic should stay in `ui.py`.

## State Model

Use a minimal state model. Do not introduce a full terminal layout system.

Minimum states:

- `idle`
- `busy`

Optional future states are intentionally deferred.

Suggested behavior:

- default state is `idle`
- switch to `busy` at the start of `agent_loop()`
- switch back to `idle` on every return path from the turn

## Compatibility With Buffered Output

The current input-safe buffering must remain intact.

Requirements:

- teammate output should still buffer during active input
- printing the bottom hint must not break the buffering contract
- the input bar should not reintroduce mixed prompt/output corruption

This is a hard constraint because the earlier bugfix specifically stabilized input integrity.

## Error Handling

The bottom bar must fail soft.

Rules:

- if state tracking gets out of sync, the UI should fall back to the idle hint
- if the hint cannot be rendered for some reason, input must still work
- no state transition should depend on Rich `Live`

## Testing Strategy

Add focused tests for:

- idle hint text rendering
- busy hint text rendering
- prompt text formatting
- state reset from busy back to idle
- input buffering compatibility remains intact

Verification commands for implementation phase:

- `pytest -q`
- `python -m py_compile agent_loop.py xiaoman_agent/*.py`

## Trade-Offs

Advantages:

- much closer to the Claude Code footer feel
- minimal implementation complexity
- low risk of breaking the current message flow work

Costs:

- the footer is only visually stable, not a true fixed terminal region
- real interrupt semantics are not part of this change
- requires explicit runtime state switching at turn boundaries

## Acceptance Criteria

The design is successful when all of the following are true:

- the prompt no longer uses `xiaoman >>`
- the bottom area uses a two-line light input model
- the hint changes between idle and busy states
- the busy hint resets after each completed turn
- the bottom area does not reintroduce prompt/output mixing

## Open Decisions Resolved

The following decisions are fixed by this design:

- use the two-line light input bar
- keep the implementation lightweight instead of using a full-screen layout
- use text-only weak hints rather than heavy status widgets
- treat interrupt wording as display guidance, not a promise of new runtime behavior
