# xiaoman-claude

A terminal multi-agent development assistant built through learning, migration, and engineering iteration.

This project started after I worked through [`learn-claude-code`](https://github.com/shareAI-lab/learn-claude-code) and then kept going: from learning the ideas, to migrating the core patterns, to turning them into a more personal, runnable, and extensible terminal system.

It is not a direct copy of the course code. It is the version that grew out of understanding concepts like agent loops, tool use, team protocol, autonomous agents, context compaction, and git worktree isolation, then shaping those ideas into a project with its own structure and trade-offs.

## Why This Project Is Interesting

- It records the path from learning an agent system to engineering a personal one.
- It supports persistent teammates instead of only one-shot subagents.
- It combines a task board with git worktree isolation for parallel execution.
- It pushes the terminal UX toward a product-like experience with Rich message flow and streaming.
- It already includes skills, compact, background execution, wait, and foreground cancellation.
- It has been split into focused modules, making it easier to extend and easier to study.

## Core Capabilities

- Lead agent loop with model calls, tool orchestration, and streaming responses
- Persistent teammates with inbox-based communication and team protocols
- Task board support with ownership, dependencies, and task metadata
- Git worktree isolation for parallel task execution
- Rich terminal UI with message-flow output and lightweight tool events
- `wait` support for observation-friendly loops
- `Esc` cancellation for supported foreground work such as waiting and streamed responses
- Skills loading for reusable working modes
- Context compaction for keeping long sessions manageable
- Background execution support for longer-running operations

## Quick Start

### Requirements

- Python 3.10+
- Git
- Anthropic API key

### Install

```bash
git clone https://github.com/xiaoman-kb/xiaoman-claude.git
cd xiaoman-claude
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Then edit `.env` and set your real API key:

```env
ANTHROPIC_API_KEY=your_real_key
ANTHROPIC_BASE_URL=
MODEL_ID=claude-sonnet-4-20250514
```

### Run

```bash
python agent_loop.py
```

## Runtime Experience

When running, the CLI is designed to feel more like a usable terminal product than a raw script dump:

- message-flow oriented output instead of heavy boxed logs everywhere
- lightweight tool event rendering
- streamed assistant responses
- waiting support for observing progress
- `Esc` cancellation for the current supported foreground task without exiting the whole CLI

## Architecture Overview

- `agent_loop.py`: tiny entrypoint that boots the runtime
- `xiaoman_agent/runtime.py`: main orchestration loop, model calls, tool execution, streaming, and turn lifecycle
- `xiaoman_agent/team.py`: teammate lifecycle, inbox protocol, approvals, and team coordination
- `xiaoman_agent/tasks.py`: task board, ownership, dependencies, and task state
- `xiaoman_agent/worktrees.py`: git worktree creation, binding, and isolated execution support
- `xiaoman_agent/ui.py`: Rich-based terminal rendering, message flow, wait rendering, and input presentation
- `xiaoman_agent/cancel.py`: foreground cancellation state and `Esc` listener logic
- `xiaoman_agent/skills.py`: loading and exposing reusable skills
- `xiaoman_agent/compact.py`: context compaction behavior
- `xiaoman_agent/background.py`: background execution support

## Repository Structure

```text
xiaoman-claude/
|- agent_loop.py
|- requirements.txt
|- .env.example
|- xiaoman_agent/
|  |- runtime.py
|  |- team.py
|  |- tasks.py
|  |- worktrees.py
|  |- ui.py
|  |- cancel.py
|  |- skills.py
|  |- compact.py
|  \- ...
|- tests/
|- docs/
\- skills/
```

## Where to Start Reading

If you want to understand the repository from top to bottom, read in this order:

1. `agent_loop.py`
2. `xiaoman_agent/runtime.py`
3. `xiaoman_agent/team.py`
4. `xiaoman_agent/tasks.py`
5. `xiaoman_agent/worktrees.py`
6. `xiaoman_agent/ui.py`

## Acknowledgement

This project was shaped by my learning journey through [`learn-claude-code`](https://github.com/shareAI-lab/learn-claude-code).

What started as a learning process around agent loops, tool use, team protocols, autonomous agents, and worktree isolation gradually became a separate project with its own structure, UI direction, and engineering trade-offs.

## Roadmap

- Broaden cancellation support beyond the current foreground-only scope
- Improve recovery flows for team and worktree state
- Add screenshots or demo recordings for the terminal experience
- Improve configuration templates and startup guidance
- Add richer shortcuts and built-in help inside the CLI
- Expand tests around teammate protocols and worktree isolation

This repository is both a working terminal agent harness and a record of how learned ideas can be turned into a personal system.
