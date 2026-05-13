# README Design

## Goal

Create a strong GitHub-facing `README.md` for `xiaoman-claude` that feels impressive, honest, and technically grounded.

The README should present the project as:

- a real terminal multi-agent harness
- a personal system built through learning, migration, and engineering iteration
- a project shaped by studying `learn-claude-code`, then evolving into its own version

The document should balance showcase value and technical clarity.

## Project Positioning

The README must frame the project as:

- starting from learning `learn-claude-code`
- moving through migration and reimplementation of core ideas
- ending as a more personal, engineered, runnable terminal system

It must not present the repository as:

- a simple clone
- a direct copy of course code
- an unrelated project with no learning lineage

The correct tone is:

- respectful to the original learning source
- confident about the current repository’s independent shape
- explicit about the transformation from learning artifact to personal system

## Audience

The README should work for two audiences at the same time:

- people landing on the GitHub page who want to quickly understand why the project is interesting
- developers who want to understand what is in the repository and where to start reading

This means the README should not be pure marketing and should not be pure internal engineering documentation.

## Style Direction

Use a balanced style:

- first part feels like a strong open-source project homepage
- middle part shows concrete capabilities and how to run it
- later part explains architecture and repository layout

The tone should feel:

- ambitious but not inflated
- technical but readable
- personal but not diary-like

## Core Narrative

The README should clearly tell this story:

1. the project began after studying `learn-claude-code`
2. the learning was not left at the “course demo” stage
3. key ideas were migrated into a separate project
4. the system was then refactored, extended, debugged, and productized into a more personal terminal harness

This story is not a side note. It is one of the repository’s main strengths and should appear near the top of the README.

## Structure

The README should use this overall structure:

1. title and one-sentence positioning
2. origin and evolution story
3. “why this project is interesting”
4. core capabilities
5. quick start
6. runtime experience
7. architecture overview
8. repository structure
9. “where to start reading”
10. acknowledgement
11. roadmap
12. closing line

This order is important because it moves from attraction to understanding to depth.

## Section Requirements

### 1. Title and One-Sentence Positioning

The opening must quickly answer:

- what this repository is
- why it matters

The one-sentence positioning should present the project as a terminal multi-agent development assistant or harness, not just a Python script collection.

### 2. Origin and Evolution Story

This section must explicitly mention:

- `learn-claude-code`
- the progression from learning to migration to independent version

It should explain that the repository emerged from understanding concepts such as:

- agent loop
- tool use
- team protocol
- autonomous agents
- worktree isolation
- context compact

The wording should make clear that this repository is an evolved result of that learning process.

### 3. Why This Project Is Interesting

This section should use concise bullets that highlight the real differentiators already present in the repository.

The bullets should focus on:

- learning-to-engineering transformation
- persistent teammates instead of only one-shot subagents
- task board plus worktree isolation
- richer terminal UX with message flow and streaming
- skills, compact, background, wait, and foreground cancellation
- modularized code structure that is suitable for study and extension

These bullets must map to real implemented capabilities, not aspirational claims.

### 4. Core Capabilities

This section should enumerate the project’s current capabilities in a more explicit way than the previous “interesting” section.

The capabilities should reflect the actual codebase, including:

- lead agent loop and tool orchestration
- persistent teammate workflows and inbox protocol
- task board and dependency handling
- git worktree isolation
- Rich terminal UI and streaming output
- `wait`
- `Esc` cancellation for supported foreground work
- skills loading
- context compaction
- background execution support

### 5. Quick Start

This section should optimize for the shortest real path to running the project.

It should include:

- requirements
- install steps
- environment configuration
- startup command

The instructions should stay practical and minimal.

If the repository lacks a safe example env file, the README should still describe safe environment variables using explicit safe example values such as `your_api_key_here`.

### 6. Runtime Experience

This section should describe what using the CLI feels like, not just what commands exist.

It should mention:

- message-flow UI
- lightweight tool events
- waiting behavior
- streaming
- foreground cancellation behavior

The goal is to make the project feel alive and product-like.

### 7. Architecture Overview

This section should explain the major modules in short, responsibility-driven bullets.

It should cover:

- `runtime`
- `team`
- `tasks`
- `worktrees`
- `ui`
- `cancel`
- `skills`
- `compact`
- `background`

Each module explanation should be short and clear rather than deeply internal.

### 8. Repository Structure

This section should include a short directory tree for orientation.

The tree should be shallow enough to read quickly.

It should help a new reader map the repository without overwhelming them with every file.

### 9. Where to Start Reading

This section should recommend a reading order for developers who want to understand the codebase.

The reading order should start from the entrypoint and move toward the core orchestration modules.

### 10. Acknowledgement

This section must explicitly thank or acknowledge `learn-claude-code` as the project’s learning origin.

The tone should be:

- respectful
- honest
- non-defensive

It should reinforce that the repository is shaped by that learning process while still having its own engineering identity.

### 11. Roadmap

This section should include a short list of realistic next steps.

It should make the repository feel active and evolving.

The roadmap should stay grounded in plausible future improvements such as:

- broader cancellation support
- stronger recovery flows
- better screenshots or demos
- safer config templates
- richer shortcuts/help
- more protocol/worktree tests

### 12. Closing Line

The final line should give the README a strong ending.

It should reinforce that the repository is both:

- a working terminal agent harness
- a record of turning learned ideas into a personal system

## What the README Must Avoid

The README must avoid:

- pretending the project came from nowhere
- overstating capabilities that do not exist
- turning the whole file into an implementation document
- writing only generic feature bullets with no real substance
- sounding like a course assignment submission
- burying the source inspiration so deeply that the lineage becomes unclear

## Key Messages to Preserve

The final README should make these messages obvious:

- this project was built through serious learning and migration work
- it is more than a toy demo
- it already contains non-trivial multi-agent, task, UI, and isolation ideas
- it is readable as both a usable project and a learning-oriented codebase

## Acceptance Criteria

The README design is successful when all of the following are true:

- the project origin in `learn-claude-code` is clearly acknowledged
- the “learning -> migration -> own version” story is visible near the top
- the README feels impressive without sounding fake
- the core capabilities match the current repository
- the quick start stays practical
- the architecture section helps technical readers orient themselves
- the ending leaves the repository feeling active and intentional

## Open Decisions Resolved

The following decisions are fixed by this design:

- use a balanced README style instead of purely product or purely engineering writing
- emphasize the transformation from learning to migration to independent version
- include both showcase sections and technical orientation sections
- explicitly acknowledge `learn-claude-code`
