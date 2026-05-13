# GitHub Sanitized Publish Design

## Goal

Publish a safe public version of `xiaoman-claude` to GitHub while preserving the current local working state.

The public version must exclude secrets, local runtime state, task/worktree artifacts, caches, and private logs.

The local workspace should remain usable after the cleanup.

## Repository Target

GitHub target repository:

- `https://github.com/xiaoman-kb/xiaoman-claude.git`

## Publishing Mode

Use a “dual-version” publishing approach:

- keep the current local project as the working copy
- publish only the sanitized public version to GitHub

This is not a destructive export. The intent is to define what Git tracks and publishes, not to erase all local state from the machine.

## Scope

In scope:

- define which files and directories are safe to publish
- exclude sensitive or local-only state from GitHub
- add or update `.gitignore` to enforce the boundary
- remove already discovered secret-bearing runtime files from the publish set
- scan the kept files for secrets and local-path leaks
- configure Git remote and prepare push to GitHub

Out of scope:

- redesigning the project structure
- removing local runtime artifacts from the machine if they are only being ignored
- rotating external credentials outside the repository
- rewriting unrelated source code

## Public Version Contents

The public GitHub version should keep:

- `agent_loop.py`
- `xiaoman_agent/`
- `tests/`
- `docs/`
- `requirements.txt`
- `skills/`

These are treated as publishable project assets.

## Excluded Contents

The public GitHub version must exclude:

- `.env`
- `.team/`
- `.tasks/`
- `.worktrees/`
- `__pycache__/`
- `*.pyc`

Also exclude any other machine-local cache or generated state discovered during cleanup.

## Sensitive Data Findings Already Known

The current workspace already contains at least these risks:

- `.env`
- `.team/exchange_log.jsonl` contains a real API key value
- `.team/`, `.tasks/`, and `.worktrees/` contain local paths, inbox data, task state, and worktree metadata

These must not be part of the published GitHub version.

## Sanitization Rules

### Secrets

The published version must not contain:

- API keys
- auth tokens
- private credentials
- private inbox/message logs

If a kept file contains a real secret, sanitize the file before publishing or exclude it if it is not required.

### Local Path Leakage

The published version should avoid leaking machine-specific absolute paths where practical.

Logs and runtime state files are the main source of this risk and are already excluded by design.

If a kept source or doc file contains a local absolute path that is not essential, replace it with a neutral example or workspace-relative form.

### Runtime State

The public repository must not include:

- inbox state
- task state
- exchange logs
- worktree indices
- worktree event history

These are local operational artifacts, not source assets.

## `.gitignore` Policy

Add a repository `.gitignore` that at minimum ignores:

- `.env`
- `.team/`
- `.tasks/`
- `.worktrees/`
- `__pycache__/`
- `*.pyc`

The ignore file should be explicit and conservative. It should protect the public repository boundary going forward.

## Local Preservation Policy

The cleanup should preserve the developer’s local environment as much as possible.

Preferred behavior:

- ignore sensitive/runtime files rather than deleting them unless deletion is necessary for safety
- only delete files if they are accidental publish artifacts and not needed for the user’s local workflow

If a file must be removed from the repository view, prefer Git exclusion and safe cleanup over destructive local deletion.

## Git Publishing Flow

The publish flow should be:

1. define public tracking boundaries
2. add `.gitignore`
3. verify sensitive files are excluded
4. scan kept files for leaked secrets or unsafe paths
5. configure `origin` to the provided GitHub repository
6. prepare a clean commit for the public version
7. attempt push

If authentication is required, the user may need to complete GitHub login interactively.

## Error Handling

The publish process must fail safely.

Rules:

- do not upload before the secret scan is clean enough for the chosen publish boundary
- do not delete unrelated local files destructively without need
- if GitHub authentication blocks push, stop after preparing the repository and tell the user exactly what remains
- if remote configuration conflicts with an existing remote, surface that clearly before changing it

## Verification Strategy

Before push, verify:

- excluded directories are ignored by Git
- no `.env` is staged
- no `.team/`, `.tasks/`, or `.worktrees/` contents are staged
- no obvious API key or token remains in kept tracked files
- `git remote -v` points to the intended repository

Recommended verification commands during implementation:

- `git status --short`
- `git check-ignore -v .env .team .tasks .worktrees`
- secret grep over kept files
- `git remote -v`

## Trade-Offs

Advantages:

- safe public repository boundary
- local working environment remains available
- future accidental secret publication risk is reduced by `.gitignore`

Costs:

- local runtime history is intentionally not represented on GitHub
- if the user wants to recreate runtime state elsewhere, they must do so from source

## Acceptance Criteria

The design is successful when all of the following are true:

- the GitHub version contains only the intended public files
- known sensitive files are excluded
- no real API key is left in the published tracked set
- local runtime state is not uploaded
- the repository remote points to `xiaoman-kb/xiaoman-claude`
- push is completed or the repository is left ready for the user to authenticate and push

## Open Decisions Resolved

The following decisions are fixed by this design:

- use the dual-version approach
- publish `skills/`
- exclude `.env`, `.team/`, `.tasks/`, `.worktrees/`, caches, and compiled artifacts
- keep the focus on safe publication rather than broader repo refactoring
