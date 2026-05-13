# Homepage Polish Design

## Goal

Polish the GitHub-facing homepage for `xiaoman-claude` by adding two terminal screenshots to `README.md` and defining stronger repository metadata for the GitHub project page.

The result should make the repository feel more like a real product homepage while staying honest to the current implementation.

## Scope

This design covers:

- adding two existing screenshots to the README
- choosing a side-by-side image layout
- normalizing screenshot filenames to stable English names
- lightly tightening the README opening section around the visual presentation
- defining recommended GitHub repository metadata:
  - description
  - tagline
  - topics

This design does not cover:

- creating new screenshots
- redesigning the full README structure
- changing runtime behavior
- adding badges, GIF recordings, or architecture diagrams

## Current Inputs

Two screenshots already exist under `docs/image/` and should be reused instead of generating new assets.

The current README already has:

- a title
- a one-line positioning statement
- origin/evolution paragraphs
- capability and architecture sections

So this work is a homepage polish pass, not a rewrite.

## Design Decisions

### 1. Image Layout

Use a side-by-side layout near the top of the README.

Placement:

1. title
2. one-line positioning
3. side-by-side screenshots
4. origin and evolution story

This keeps the first screen visually strong on GitHub while preserving the narrative directly below it.

The layout should use HTML image tags inside a centered paragraph so width can be controlled more reliably than plain Markdown tables.

## 2. Screenshot Naming

Rename the two screenshot files from timestamp-based Chinese names to stable English names:

- `docs/image/workspace-overview.png`
- `docs/image/message-flow.png`

Reasons:

- safer README references
- cleaner diffs
- easier future replacement
- more readable public repository layout

## 3. Image Meaning

The two images should represent two different aspects of the project:

- `workspace-overview.png`: task board, teammate status, and worktree-oriented coordination
- `message-flow.png`: conversational terminal UX, streamed content, and product-like CLI interaction

This pairing tells the reader that the repository is not only a backend harness, but also a visible terminal product.

## 4. README Editing Boundary

README changes should stay focused and minimal.

Required changes:

- insert the image block near the top
- add short alt text
- optionally add one short caption line introducing the screenshots

Avoid:

- rewriting sections that are already working
- adding marketing-heavy copy
- changing the existing project narrative

## 5. GitHub Homepage Metadata

Define a recommended repository presentation set for the GitHub settings page.

### Description

Use a short description that fits GitHub repository cards:

`A terminal multi-agent development assistant built from learning, migration, and engineering iteration.`

### Tagline

Use a more memorable short line for the repository homepage and sharing contexts:

`From learning agent systems to building a personal multi-agent terminal harness.`

### Topics

Use topics that reflect the real codebase and discovery surface:

- `ai-agent`
- `multi-agent`
- `claude`
- `anthropic`
- `terminal-ui`
- `rich`
- `python`
- `git-worktree`
- `developer-tools`
- `agentic-workflow`

These topics should favor discoverability without claiming unsupported areas such as web UI, cloud platform, or general framework status.

## Error Handling And Constraints

- If the screenshot directory already contains the target English filenames, reuse them instead of duplicating files.
- If README image rendering looks too large on GitHub, prefer width control changes rather than layout redesign.
- If side-by-side rendering collapses on narrow screens, that is acceptable as long as GitHub desktop rendering remains clear.

## Verification

The work is considered correct when:

- both screenshots exist under stable README paths
- `README.md` references both images successfully
- the top of the README reads naturally with the new image block
- `git status` shows only intended homepage-related changes before commit
- the recommended GitHub description, tagline, and topics are ready to hand to the user

## Acceptance Criteria

This design succeeds when:

- the README top section becomes visually stronger immediately
- the two screenshots communicate both coordination and interaction
- the repository metadata suggestions are concise and reusable
- the change stays polish-level and does not bloat the README
