# Wait Light Mode Design

## Goal

Refine the `wait` tool so that waiting no longer renders the large `Workspace Overview` panel.

The new behavior should:

- show only a lightweight waiting hint during the wait period
- return only a short summary when the wait completes
- preserve the existing `wait` tool semantics and timing behavior

This change only covers the display behavior of `wait`. It does not redesign other structured outputs or the general message flow.

## Scope

In scope:

- change the visual behavior of `live_wait()` in `xiaoman_agent/ui.py`
- remove the large `Workspace Overview` panel from the waiting experience
- shorten the final returned summary from `wait`

Out of scope:

- changing the `wait` tool API
- changing task, teammate, or worktree data models
- changing `task_list`, `list_teammates`, or `worktree_list`
- redesigning the rest of the terminal UI

## Desired Experience

During waiting, the terminal should feel calm and lightweight.

Target behavior:

```text
waiting...
```

After the wait completes:

```text
waited 5s.
```

Or:

```text
waited 5s for teammate progress.
```

The key point is to avoid the large structured dashboard while still making it obvious that the tool is doing something.

## Design Summary

Use a lightweight waiting mode:

- render a single weak status line while waiting
- return a short text summary when done

This replaces the current overview-panel-based waiting display.

## Visual Rules

The wait hint should:

- use weak emphasis
- avoid borders and panels
- avoid tables or grouped dashboards
- feel similar to the new subtle status style

Recommended visible text:

- `waiting...`

The final completion line should stay short and neutral.

## Return Value Rules

The `wait` tool result should no longer embed full `Team / Tasks / Worktrees` sections.

Preferred summaries:

- `Waited 5s.`
- `Waited 5s for teammate progress.`

Rules:

- do not include large structured summaries
- do not dump the current workspace state
- keep the result human-readable and short

## Module Responsibilities

### `xiaoman_agent/ui.py`

UI owns the lightweight waiting presentation.

Responsibilities:

- replace the current `Live(build_overview_renderable(...))` waiting path
- render a single weak waiting line during the wait window
- return a compact completion summary

### `xiaoman_agent/runtime.py`

Runtime should remain unchanged or nearly unchanged.

Responsibilities:

- continue calling `live_wait()` via the existing `wait` tool handler
- avoid adding runtime-specific branching for this display change

## Compatibility

This design must preserve:

- the existing `wait(seconds=...)` tool interface
- the actual wait duration behavior
- compatibility with the current message flow

This design must remove:

- the large `Workspace Overview` panel during wait
- the large final workspace snapshot summary from the `wait` return text

## Error Handling

The lightweight wait mode must fail soft.

Rules:

- if the lightweight render path fails, `wait` should still complete and return a short summary
- waiting display must not depend on full workspace snapshot rendering

## Testing Strategy

Add focused tests for:

- `live_wait(seconds=0, ...)` no longer returns `Team:`
- `live_wait(seconds=0, ...)` no longer returns `Tasks:`
- `live_wait(seconds=0, ...)` no longer returns `Worktrees:`
- the returned summary remains short and includes the wait duration

Verification commands for implementation phase:

- `pytest -q`
- `python -m py_compile agent_loop.py xiaoman_agent/*.py`

## Trade-Offs

Advantages:

- much less visual noise
- closer to the lightweight Claude Code feel
- no change to the `wait` tool contract

Costs:

- less visibility into live workspace state during waiting
- users who want a dashboard must use explicit list/status tools instead

## Acceptance Criteria

The design is successful when all of the following are true:

- waiting no longer shows `Workspace Overview`
- waiting shows only a lightweight status line
- the final `wait` result is short
- the `wait` tool still behaves correctly with the same input interface

## Open Decisions Resolved

The following decisions are fixed by this design:

- use a one-line waiting hint
- keep the final wait summary short
- do not show the large overview panel during waiting
