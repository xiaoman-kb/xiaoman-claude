# Bilingual README Design

## Goal

Add a complete Chinese README for `xiaoman-claude` while keeping the current English README as the default GitHub homepage entry.

The bilingual documentation should make the repository easier to understand for Chinese readers without weakening the existing English-facing open source presentation.

## Scope

This design covers:

- adding a full `README.zh-CN.md`
- keeping `README.md` as the default landing file
- adding language-switch links near the top of both README files
- mirroring the overall structure and meaning of the English README in Chinese
- reusing the existing screenshots instead of creating new assets

This design does not cover:

- adding badge rows
- changing repository code
- changing project positioning
- adding new screenshots or diagrams

## Current State

The repository currently has:

- an English `README.md`
- two screenshots under `docs/image/`
- no Chinese README
- no language switch links

The current English README already presents the project well, so this work should extend it rather than rewrite it.

## Approaches Considered

### Option 1: Add `README.zh-CN.md` and keep English as default

Pros:

- GitHub homepage remains internationally readable
- Chinese readers get a complete native-language document
- follows a common bilingual open source convention
- lowest disruption to current repository presentation

Cons:

- two README files must be kept in sync over time

### Option 2: Replace root README with Chinese and move English to `README.en.md`

Pros:

- Chinese readers land directly on localized content

Cons:

- weakens English-first discoverability on GitHub
- adds unnecessary churn to the current repository presentation

### Option 3: Put Chinese README under `docs/`

Pros:

- keeps root cleaner

Cons:

- much lower visibility
- language switching feels less natural

## Decision

Use Option 1.

Create `README.zh-CN.md`, keep `README.md` as the primary landing file, and add top-level language links in both documents.

## Document Structure

The Chinese README should closely mirror the English README structure:

1. title
2. one-line positioning
3. screenshot block
4. origin and evolution story
5. why this project is interesting
6. core capabilities
7. quick start
8. runtime experience
9. architecture overview
10. repository structure
11. where to start reading
12. acknowledgement
13. roadmap
14. GitHub homepage settings
15. closing line

This keeps both versions aligned and easier to maintain.

## Language Switch Design

Each README should include a lightweight language switch line near the top, directly below the title:

- in `README.md`: `English | [简体中文](README.zh-CN.md)`
- in `README.zh-CN.md`: `[English](README.md) | 简体中文`

The active language should remain plain text and the inactive language should be a link.

## Translation Direction

The Chinese README should be a natural Chinese adaptation, not a rigid line-by-line literal translation.

It should preserve:

- the learning -> migration -> own version narrative
- the current scope of features
- the current project positioning
- the practical quick-start path

It should avoid:

- over-translating code/file names
- adding claims that do not exist in the English README
- becoming much longer than the English file without need

## Screenshot Reuse

Reuse the same two images:

- `docs/image/workspace-overview.png`
- `docs/image/message-flow.png`

The screenshot block should stay near the top in both README files so the bilingual versions feel equivalent.

## Editing Boundaries

Only these files should change:

- `README.md`
- `README.zh-CN.md`
- spec/plan documentation files for this work

No code, tests, or runtime configuration should be changed.

## Verification

The work is correct when:

- `README.zh-CN.md` exists
- both README files contain language-switch links
- both README files reference the same two screenshots successfully
- the Chinese README keeps the same major sections as the English README
- git status after the changes shows only intended documentation edits before commit

## Acceptance Criteria

This design succeeds when:

- Chinese readers can read a complete repository introduction in their own language
- English readers still land on the current polished README by default
- language switching is obvious and lightweight
- the repository maintains a professional GitHub presentation
