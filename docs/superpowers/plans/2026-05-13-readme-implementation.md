# README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strong public-facing `README.md` and the minimal safe onboarding files needed to make the repository understandable and runnable from GitHub.

**Architecture:** Treat this as a documentation-first change with one small config-support addition. The README should follow the approved “learning -> migration -> own version” narrative, and `.env.example` should align with the real environment variables loaded by `xiaoman_agent/config.py`.

**Tech Stack:** Markdown, Python CLI project, GitHub repository docs, `python-dotenv`, Anthropic SDK

---

## File Map

- Create: `README.md`
- Create: `.env.example`
- Modify: none
- Verify against: `agent_loop.py`, `xiaoman_agent/config.py`, `requirements.txt`, `.gitignore`

### Task 1: Add a Safe Environment Template

**Files:**
- Create: `/mnt/d/job_project/xiaoman-claude/.env.example`
- Verify against: `/mnt/d/job_project/xiaoman-claude/xiaoman_agent/config.py`

- [ ] **Step 1: Create the environment template**

Write this exact file:

```env
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_BASE_URL=
MODEL_ID=claude-sonnet-4-20250514
```

- [ ] **Step 2: Verify the env keys match the code**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("/mnt/d/job_project/xiaoman-claude/xiaoman_agent/config.py").read_text()
required = ["ANTHROPIC_BASE_URL", "MODEL_ID"]
missing = [key for key in required if key not in text]
print("OK" if not missing else f"MISSING: {missing}")
PY
```

Expected:

```text
OK
```

- [ ] **Step 3: Confirm the new file is not ignored**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude check-ignore .env.example || true
```

Expected:

```text
```

The command should produce no output, meaning `.env.example` will be tracked.

- [ ] **Step 4: Commit the template**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude add .env.example
git -C /mnt/d/job_project/xiaoman-claude commit -m "docs: add example environment file"
```

### Task 2: Write the GitHub README

**Files:**
- Create: `/mnt/d/job_project/xiaoman-claude/README.md`
- Verify against: `/mnt/d/job_project/xiaoman-claude/agent_loop.py`
- Verify against: `/mnt/d/job_project/xiaoman-claude/xiaoman_agent/config.py`
- Verify against: `/mnt/d/job_project/xiaoman-claude/requirements.txt`

- [ ] **Step 1: Create the README content**

Write a `README.md` with this exact structure and close wording:

```md
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
├─ agent_loop.py
├─ requirements.txt
├─ .env.example
├─ xiaoman_agent/
│  ├─ runtime.py
│  ├─ team.py
│  ├─ tasks.py
│  ├─ worktrees.py
│  ├─ ui.py
│  ├─ cancel.py
│  ├─ skills.py
│  ├─ compact.py
│  └─ ...
├─ tests/
├─ docs/
└─ skills/
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
- Add richer shortcuts/help inside the CLI
- Expand tests around teammate protocols and worktree isolation

This repository is both a working terminal agent harness and a record of how learned ideas can be turned into a personal system.
```

- [ ] **Step 2: Validate the required headings exist**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("/mnt/d/job_project/xiaoman-claude/README.md").read_text()
required = [
    "# xiaoman-claude",
    "## Why This Project Is Interesting",
    "## Core Capabilities",
    "## Quick Start",
    "## Runtime Experience",
    "## Architecture Overview",
    "## Repository Structure",
    "## Where to Start Reading",
    "## Acknowledgement",
    "## Roadmap",
]
missing = [item for item in required if item not in text]
print("OK" if not missing else f"MISSING: {missing}")
PY
```

Expected:

```text
OK
```

- [ ] **Step 3: Validate the README references real files**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path("/mnt/d/job_project/xiaoman-claude")
paths = [
    "agent_loop.py",
    "requirements.txt",
    "xiaoman_agent/runtime.py",
    "xiaoman_agent/team.py",
    "xiaoman_agent/tasks.py",
    "xiaoman_agent/worktrees.py",
    "xiaoman_agent/ui.py",
    "xiaoman_agent/cancel.py",
    "xiaoman_agent/skills.py",
    "xiaoman_agent/compact.py",
    "xiaoman_agent/background.py",
    "tests",
    "docs",
    "skills",
]
missing = [p for p in paths if not (root / p).exists()]
print("OK" if not missing else f"MISSING: {missing}")
PY
```

Expected:

```text
OK
```

- [ ] **Step 4: Commit the README**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude add README.md
git -C /mnt/d/job_project/xiaoman-claude commit -m "docs: add project README"
```

### Task 3: Final Review and Publish

**Files:**
- Verify: `/mnt/d/job_project/xiaoman-claude/README.md`
- Verify: `/mnt/d/job_project/xiaoman-claude/.env.example`

- [ ] **Step 1: Review the rendered README locally**

Run:

```bash
python - <<'PY'
from pathlib import Path
for path in ["README.md", ".env.example"]:
    full = Path("/mnt/d/job_project/xiaoman-claude") / path
    print(f"===== {path} =====")
    print(full.read_text()[:1200])
PY
```

Expected:

```text
===== README.md =====
# xiaoman-claude
...
===== .env.example =====
ANTHROPIC_API_KEY=your_api_key_here
...
```

- [ ] **Step 2: Verify git status only contains the intended docs files**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude status --short
```

Expected:

```text
A  .env.example
A  README.md
```

or the same files staged/committed with no unrelated changes introduced by this task.

- [ ] **Step 3: Push the documentation update**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude push
```

Expected:

```text
To https://github.com/xiaoman-kb/xiaoman-claude.git
   <old>..<new>  main -> main
```

- [ ] **Step 4: Confirm the public repository now has onboarding docs**

Open the repository homepage and verify:

```text
- README renders correctly
- the learning -> migration -> own version story is visible near the top
- .env.example is available for cloning users
```

- [ ] **Step 5: Final commit checkpoint**

If Task 1 and Task 2 were committed separately, no extra commit is required here. If they were implemented in one batch, use:

```bash
git -C /mnt/d/job_project/xiaoman-claude add README.md .env.example
git -C /mnt/d/job_project/xiaoman-claude commit -m "docs: add onboarding README and env example"
```

## Self-Review

### Spec Coverage

- Project origin and `learn-claude-code` acknowledgement: covered in Task 2 README content
- Learning -> migration -> own version narrative: covered in Task 2 opening sections and acknowledgement
- Showcase + technical orientation balance: covered in Task 2 section structure
- Practical quick start: covered in Task 1 and Task 2 config/install/run steps
- Architecture and reading order: covered in Task 2 architecture and reading sections
- Roadmap and strong ending: covered in Task 2 roadmap and closing line

### Placeholder Scan

- No `TODO`, `TBD`, or undefined future text remains in the plan steps
- README content is fully written instead of described abstractly
- `.env.example` content is fully specified

### Type and Name Consistency

- Environment variable names match `xiaoman_agent/config.py`
- Repository paths referenced in the README match current file names
- The repo URL matches the configured public repository
