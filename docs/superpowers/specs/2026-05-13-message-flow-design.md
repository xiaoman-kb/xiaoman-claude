# Message Flow Design

## Goal

Refactor the terminal middle area from a panel-heavy UI into a Claude Code-like mixed message flow.

The new middle area should feel like a chronological conversation stream:

- user input appears as a simple prompt line
- assistant replies appear as plain text blocks instead of a permanent panel style
- tool execution appears as lightweight event lines
- teammate activity joins the same stream instead of rendering as a separate subsystem
- only strongly structured results keep table or block rendering

This work changes presentation, not agent logic, protocol logic, or tool semantics.

## Scope

In scope:

- redesign the middle message stream in `xiaoman_agent/ui.py`
- route runtime and teammate output through a shared message-flow renderer
- reduce visual noise from repeated panels
- preserve buffered output behavior during active input
- keep structured views for task, worktree, inbox, and detail-style outputs

Out of scope:

- redesigning the startup overview card
- redesigning the bottom input bar
- changing tool behavior, task logic, team protocol, or streaming API behavior
- changing transcript format or exchange log format

## Desired Experience

The terminal should read like one continuous timeline instead of multiple competing widgets.

Example target interaction:

```text
> 新建一个 xiaoman 文件夹

• Bash(mkdir /d/xiaoman)
  └ Done

已在 D 盘创建了 xiaoman 文件夹。

> 随便在里面创建几个测试文件

Thinking...
• Bash(touch a.txt b.txt c.txt)
  └ Done

已创建 3 个测试文件：a.txt、b.txt、c.txt
```

Structured outputs still use compact blocks when they are genuinely easier to scan that way:

```text
> 看看当前任务

[Tasks]
[>] 1: setup repo
[ ] 2: refactor auth
```

## Design Summary

Use a mixed rendering model:

- default to a linear message flow for conversation, tool execution, teammate activity, and transient system status
- preserve structured rendering only for data that loses clarity when flattened into plain lines

This keeps the Claude Code-like rhythm without throwing away the project's task and worktree readability.

## Render Categories

### 1. Prompt Lines

User input remains a single prompt-style line.

Format:

```text
> 用户输入
```

Rules:

- no panel
- no extra decoration
- keep visual separation with a blank line after submission

### 2. Assistant Text

Assistant replies become plain text message blocks instead of the current `Assistant` panel.

Rules:

- short replies print as plain wrapped text
- longer replies print as one plain text block with paragraph spacing preserved
- markdown structure may still be interpreted lightly, but should not force a bordered panel
- assistant text remains visually distinct through spacing, not a heavy border

### 3. Tool Event Lines

Normal tool activity becomes lightweight event lines.

Format:

```text
• Bash(mkdir /d/xiaoman)
  └ Done
```

Or:

```text
• ReadFile(src/app.py)
  └ 42 lines loaded
```

Or on failure:

```text
• Bash(pytest -q)
  └ Error: command exited with code 1
```

Rules:

- one line for tool invocation
- one indented follow-up line for status or compact summary
- no panel for standard short outputs
- truncate long raw output into a compact summary instead of dumping everything inline

### 4. Teammate Event Lines

Teammate events share the same flow style as tool events.

Format:

```text
• frontend-dev · bash -> npm test
• backend-dev · write_file -> updated api/routes.py
```

Rules:

- no teammate panel
- no separate visual lane
- preserve current buffering behavior so background output does not interrupt active input
- keep teammate lines compact and status-oriented

### 5. System Status Lines

Ephemeral system notices appear as weak status lines.

Examples:

```text
Thinking...
Waiting 5s for teammate progress...
Newspapering...
```

Rules:

- visually muted
- no border
- not treated as assistant prose

### 6. Structured Result Blocks

Keep compact block rendering only for outputs where structure is the main value.

Preserve structured rendering for:

- `task_list`
- `worktree_list`
- `list_teammates`
- `todo`
- `read_inbox`
- `task_get`
- `worktree_status`
- `worktree_events`
- other future outputs that are primarily tabular, JSON-like, or detail records

Rules:

- use tables or syntax-highlighted blocks
- keep them compact
- reserve bordered panels for true structure, not for every routine event

## Classification Rules

Introduce an explicit UI classification layer instead of letting each caller decide ad hoc.

The renderer should classify output into one of:

- `prompt`
- `assistant_text`
- `tool_event`
- `teammate_event`
- `system_status`
- `structured_result`

Decision logic:

- if a tool belongs to the structured tool set, render as `structured_result`
- if the payload is plain execution progress, render as `tool_event`
- if the payload is teammate activity, render as `teammate_event`
- if the payload is assistant prose, render as `assistant_text`

This avoids drifting back toward mixed, inconsistent UI behavior.

## Changes To Existing Modules

### `xiaoman_agent/ui.py`

Add a message-flow renderer layer as the main abstraction.

Expected responsibilities:

- render prompt lines
- render plain assistant text
- render tool event lines
- render teammate event lines
- render muted system status lines
- continue rendering structured tables and JSON blocks
- keep console buffering and flushing behavior

Expected refactor direction:

- split current `print_tool_result()` into:
  - a message-flow path for ordinary events
  - a structured path for preserved table/block outputs
- replace `build_assistant_renderable()` panel-first behavior with plain-text message-flow rendering
- keep helper functions for structured renderables where they are still useful

### `xiaoman_agent/runtime.py`

Shift runtime calls from panel-first UI usage to classification-first UI usage.

Expected responsibilities:

- when a tool finishes, send either:
  - an event-line render request
  - or a structured-result render request
- print assistant final text through the new plain-text assistant renderer
- keep current buffering safety and streaming safeguards intact

No behavior changes to:

- tool execution
- streaming transport
- background notifications
- task logic

### `xiaoman_agent/team.py`

Keep teammate buffering behavior but standardize the visible output format.

Expected result:

- teammate events remain buffered during active input
- once flushed, they appear in the same message-flow style as main tool events

## Migration Strategy

Implement in small, low-risk steps:

1. convert ordinary tool outputs from panel rendering to event-line rendering
2. convert assistant text output from panel rendering to plain message-flow text
3. keep structured output tools on existing table/JSON rendering paths
4. unify teammate event formatting with the new event-line style
5. tighten tests so ordinary tools cannot regress back to panel-heavy rendering

This keeps the working UI stable while changing only one display class at a time.

## Error Handling

Rendering must remain robust even if outputs are malformed or unexpectedly large.

Rules:

- large plain outputs should be summarized, not dumped inline
- structured rendering failures should fall back to plain text blocks
- buffered teammate events must still flush safely after input ends
- message rendering should not reintroduce duplicate output or input-line corruption

## Testing Strategy

Add focused tests around the UI classification boundary.

Required coverage:

- ordinary tools render as event lines rather than panels
- structured tools still render as tables or JSON blocks
- assistant text renders without a permanent panel wrapper
- teammate events stay buffered during active input
- buffered teammate events flush in order after input ends
- long plain outputs are clipped into compact summaries

Verification commands for implementation phase:

- `pytest -q`
- `python -m py_compile agent_loop.py xiaoman_agent/*.py`

## Trade-Offs

Advantages:

- much closer to the Claude Code interaction feel
- lower visual noise
- clearer event chronology
- less competition between main agent output and teammate output

Costs:

- less obvious visual separation than bordered panels
- requires a clearer classification layer in the UI code
- some existing helpers may need to be renamed or split for consistency

## Acceptance Criteria

The design is successful when all of the following are true:

- the middle area reads as a single chronological stream
- ordinary tool usage no longer creates frequent bordered panels
- assistant replies no longer render inside a default permanent panel
- structured tools still remain easy to scan
- teammate events appear as compact stream items
- active input is not interrupted by background output

## Open Decisions Resolved

The following decisions are fixed by this design:

- use the mixed model rather than fully flattening all content
- prioritize message flow for ordinary interaction
- preserve structure only where it clearly improves readability
- do not redesign startup overview or bottom input in this task
