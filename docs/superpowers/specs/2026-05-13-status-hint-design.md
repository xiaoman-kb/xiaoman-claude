# Status Hint Design

## Goal

Refine transient status messages into a weak status-hint flow that matches the lighter Claude Code terminal feel.

The new status hints should:

- feel weaker than assistant prose and tool events
- avoid bordered panels and heavy visual treatment
- present short, readable stage-oriented wording
- preserve compatibility with the current message flow and input buffering fixes

This change only covers status hints such as thinking, waiting, and context compression messages. It does not redesign the startup overview, middle conversation content types, or the bottom input bar.

## Scope

In scope:

- standardize transient status messages into one weak-hint rendering path
- define which messages count as status hints
- give status hints lighter wording and lighter visual weight
- keep runtime responsible only for signaling when a status hint should be shown

Out of scope:

- redesigning assistant prose
- redesigning tool event lines
- redesigning teammate event lines
- redesigning the bottom input bar
- adding a live-updating full-screen status region

## Desired Experience

Status hints should read like quiet auxiliary guidance, not like logs or event rows.

Target examples:

```text
thinking...
waiting for teammate progress...
compressing context...
```

These lines should feel present but not demanding. They should be easy to ignore when the user is scanning for the main result.

## Design Summary

Add a dedicated weak status-hint rendering path.

The status-hint flow is a distinct message-stream element, separate from:

- assistant text
- tool event lines
- teammate event lines
- structured result blocks

This keeps the terminal hierarchy clear:

- assistant text remains primary content
- tool and teammate event lines remain secondary activity
- status hints become low-emphasis supporting context

## What Counts As A Status Hint

The following messages should use the new weak-hint path:

- thinking-stage messages
- waiting-stage messages
- compacting/compressing-stage messages
- existing internal status notices such as:
  - `auto-compact triggered`
  - `manual-compact triggered`

Future messages should use the same path if they describe transient stage progress rather than content or results.

The following should not use the status-hint path:

- assistant explanations or conclusions
- tool execution lines such as `• Bash(...)`
- teammate activity lines
- structured task/worktree/inbox outputs

## Wording Rules

Status hints should use short, user-facing wording.

Preferred qualities:

- lower-case where it feels natural
- brief and stage-oriented
- descriptive, not implementation-heavy

Examples:

- `thinking...`
- `waiting for teammate progress...`
- `compressing context...`

Mapping guidance:

- `auto-compact triggered` -> `compressing context...`
- `manual-compact triggered` -> `compressing context...`

The intent is to reduce “internal implementation smell” in the UI and replace it with human-readable progress cues.

## Visual Rules

Status hints should be visually weaker than every other line type in the middle stream.

Rules:

- no border
- no prefix like `[STATUS]`
- no bullets by default
- no bright colors
- use dim or similarly weak emphasis

Status hints should be readable, but they should visually recede behind:

- assistant prose
- tool event lines
- teammate event lines

## Module Responsibilities

### `xiaoman_agent/ui.py`

UI owns the status-hint appearance.

New responsibilities:

- provide a dedicated render helper for weak status hints
- keep all status styling in one place
- avoid duplicating the status visual style across runtime

Suggested abstraction:

- a helper that normalizes raw internal status text into user-facing hint text
- a helper that renders the final weak hint line
- `print_status(...)` may become a wrapper around this behavior, or the new helper may live beside it

### `xiaoman_agent/runtime.py`

Runtime should only choose when a status hint is emitted.

Responsibilities:

- continue signaling compact-related transitions
- optionally signal other stage transitions only where useful
- avoid hardcoding status styling or terminal emphasis

The runtime must not own wording style beyond choosing from known status cases.

## Mapping Strategy

Use a small normalization layer between internal status triggers and visible wording.

Recommended cases:

- compact-related raw messages -> `compressing context...`
- explicit waiting hint -> `waiting for teammate progress...`
- explicit thinking hint -> `thinking...`

If a status message is not recognized, the system may fall back to the original text in weak style rather than failing.

## Compatibility With Existing Message Flow

This design must preserve the current message-flow work.

Requirements:

- status hints do not turn back into panels
- status hints do not merge into assistant text blocks
- status hints do not steal the tool-event formatting path
- input buffering and queued teammate output remain unaffected

## Error Handling

Status hints must fail soft.

Rules:

- unknown status text may fall back to weakly styled raw text
- if normalization fails, output should still render as plain weak text
- no status rendering failure should block assistant output or input prompt behavior

## Testing Strategy

Add focused tests for:

- raw compact-trigger messages normalize to `compressing context...`
- weak status rendering produces plain low-emphasis text, not a panel
- unknown status messages still render
- existing message-flow tests continue to pass

Verification commands for implementation phase:

- `pytest -q`
- `python -m py_compile agent_loop.py xiaoman_agent/*.py`

## Trade-Offs

Advantages:

- closer to the Claude Code feel
- lower visual noise
- clearer separation between content, actions, and transient state

Costs:

- some raw internal wording becomes less explicit
- requires a small normalization layer rather than printing raw status strings directly

## Acceptance Criteria

The design is successful when all of the following are true:

- transient status messages use a dedicated weak-hint style
- compact-related messages no longer show raw `triggered` wording
- status hints are visibly lighter than tool events and assistant prose
- no panels are introduced for status hints
- existing message flow and input safety behavior remain intact

## Open Decisions Resolved

The following decisions are fixed by this design:

- use a weak status-hint flow instead of bold phase labels
- keep status hints as one distinct stream element
- normalize implementation-heavy compact wording into user-facing wording
- do not add a separate live status region in this step
