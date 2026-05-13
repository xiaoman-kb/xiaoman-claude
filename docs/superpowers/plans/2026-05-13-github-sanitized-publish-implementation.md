# GitHub Sanitized Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a safe public version of `xiaoman-claude` for GitHub by excluding sensitive local state, then configure the target remote and push when authentication allows.

**Architecture:** Keep the local workspace intact while defining a strict publish boundary with `.gitignore` and Git tracking rules. Verify that secrets and runtime state are excluded, then configure `origin` to the approved GitHub repository and attempt a push.

**Tech Stack:** Git, Python project files, shell verification commands

---

## File Structure

- Create: `/mnt/d/job_project/xiaoman-claude/.gitignore`
  - Defines the publish boundary for secrets, caches, runtime state, and generated artifacts.
- Modify: `/mnt/d/job_project/xiaoman-claude/docs/superpowers/plans/2026-05-13-github-sanitized-publish-implementation.md`
  - This plan file only.
- No source feature files should be modified unless secret/path sanitization in a kept file is required.

### Task 1: Add Safe Publish Ignore Rules

**Files:**
- Create: `/mnt/d/job_project/xiaoman-claude/.gitignore`
- Test: shell verification only

- [ ] **Step 1: Write the target ignore rules**

Create `/mnt/d/job_project/xiaoman-claude/.gitignore` with:

```gitignore
.env
.team/
.tasks/
.worktrees/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
.DS_Store
```

- [ ] **Step 2: Verify the ignore file starts from a missing or different state**

Run:

```bash
test -f /mnt/d/job_project/xiaoman-claude/.gitignore && cat /mnt/d/job_project/xiaoman-claude/.gitignore || echo "MISSING"
```

Expected before implementation:

```text
MISSING
```

Or a different file content than the target ignore list above.

- [ ] **Step 3: Create the `.gitignore` file**

Write exactly:

```gitignore
.env
.team/
.tasks/
.worktrees/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
.DS_Store
```

- [ ] **Step 4: Verify ignored paths resolve correctly**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude check-ignore -v .env .team/exchange_log.jsonl .tasks/task_1.json .worktrees/index.json __pycache__/agent_loop.cpython-313.pyc
```

Expected:

```text
.gitignore:1:.env .env
.gitignore:2:.team/ .team/exchange_log.jsonl
.gitignore:3:.tasks/ .tasks/task_1.json
.gitignore:4:.worktrees/ .worktrees/index.json
.gitignore:5:__pycache__/ __pycache__/agent_loop.cpython-313.pyc
```

- [ ] **Step 5: Commit**

```bash
git -C /mnt/d/job_project/xiaoman-claude add .gitignore
git -C /mnt/d/job_project/xiaoman-claude commit -m "chore: add sanitized publish ignore rules"
```

### Task 2: Verify No Sensitive Runtime State Is in the Publish Set

**Files:**
- Modify: none unless sanitization is required in a kept file
- Test: shell verification only

- [ ] **Step 1: Run a tracked-file secret scan over kept publishable files**

Run:

```bash
python - <<'PY'
from pathlib import Path
import re

root = Path("/mnt/d/job_project/xiaoman-claude")
allowed = [root / "agent_loop.py", root / "requirements.txt", root / "xiaoman_agent", root / "tests", root / "docs", root / "skills"]
patterns = [
    re.compile(r"ANTHROPIC_API_KEY\s*=\s*.+"),
    re.compile(r"ghp_[A-Za-z0-9]+"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"sk-[A-Za-z0-9]+"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
]
hits = []
for path in allowed:
    if not path.exists():
        continue
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    for file in files:
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                hits.append(str(file))
                break
if hits:
    print("\n".join(hits))
    raise SystemExit(1)
print("CLEAN")
PY
```

Expected:

```text
CLEAN
```

- [ ] **Step 2: Verify excluded runtime directories are not staged**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude status --short
```

Expected:

```text
No entries for .env, .team, .tasks, .worktrees, or __pycache__
```

- [ ] **Step 3: If a kept file contains a real secret or unsafe path, sanitize minimally**

If the scan fails, update only the specific kept file that contains unsafe content.

Use a minimal replacement style like:

```text
ANTHROPIC_API_KEY=your_api_key_here
```

Or replace machine-local paths with neutral examples like:

```text
/path/to/workspace/project
```

Do not edit excluded runtime files for publication purposes; exclusion already handles them.

- [ ] **Step 4: Re-run the tracked-file secret scan**

Run the same verification command from Step 1.

Expected:

```text
CLEAN
```

- [ ] **Step 5: Commit**

```bash
git -C /mnt/d/job_project/xiaoman-claude add agent_loop.py requirements.txt xiaoman_agent tests docs skills
git -C /mnt/d/job_project/xiaoman-claude commit -m "chore: sanitize tracked publishable files"
```

### Task 3: Define the Public Repository Tracking Set

**Files:**
- Modify: Git index only
- Test: shell verification only

- [ ] **Step 1: Stage only the approved public files**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude add agent_loop.py requirements.txt xiaoman_agent tests docs skills .gitignore
```

- [ ] **Step 2: Verify the tracked set matches the intended public boundary**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude status --short
```

Expected:

```text
Only publishable files/directories appear as staged content
No .env, .team, .tasks, .worktrees, or cache artifacts appear
```

- [ ] **Step 3: Verify runtime-only files remain ignored**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude ls-files --others --ignored --exclude-standard
```

Expected:

```text
Includes .env, .team/*, .tasks/*, .worktrees/*, __pycache__/* and similar ignored runtime artifacts
```

- [ ] **Step 4: Create the public repository commit**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude commit -m "chore: prepare sanitized public repository"
```

Expected:

```text
[main|master <sha>] chore: prepare sanitized public repository
```

- [ ] **Step 5: Verify the commit content**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude show --stat --oneline HEAD
```

Expected:

```text
Shows only approved public files
Does not include runtime state directories or .env
```

### Task 4: Configure GitHub Remote and Attempt Push

**Files:**
- Modify: Git config only
- Test: shell verification only

- [ ] **Step 1: Check current remotes before changing anything**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude remote -v
```

Expected:

```text
No remote yet, or output that can be safely replaced with the approved GitHub target
```

- [ ] **Step 2: Set the GitHub remote to the approved repository**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude remote remove origin 2>/dev/null || true
git -C /mnt/d/job_project/xiaoman-claude remote add origin https://github.com/xiaoman-kb/xiaoman-claude.git
```

- [ ] **Step 3: Verify the remote**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude remote -v
```

Expected:

```text
origin  https://github.com/xiaoman-kb/xiaoman-claude.git (fetch)
origin  https://github.com/xiaoman-kb/xiaoman-claude.git (push)
```

- [ ] **Step 4: Attempt the first push**

Run:

```bash
git -C /mnt/d/job_project/xiaoman-claude branch -M main
git -C /mnt/d/job_project/xiaoman-claude push -u origin main
```

Expected:

One of:

```text
Branch 'main' set up to track remote branch 'main' from 'origin'
```

Or an authentication prompt/failure indicating the user must complete GitHub login manually.

- [ ] **Step 5: If push is blocked by authentication, stop with exact next-step instructions**

Report exactly:

```text
Remote is configured and the sanitized commit is ready.
GitHub authentication is still required on this machine before push can complete.
```

Do not claim upload success unless the push command actually succeeds.

## Spec Coverage Check

- Dual-version publish boundary: Task 1, Task 3
- Publish `skills/`: Task 2, Task 3
- Exclude `.env`, `.team`, `.tasks`, `.worktrees`, caches: Task 1, Task 3
- Scan kept files for secrets/path leaks: Task 2
- Configure remote to `xiaoman-kb/xiaoman-claude`: Task 4
- Push or leave repo ready for authenticated push: Task 4

## Self-Review Notes

- No placeholder steps remain.
- The plan does not require modifying feature code unless a kept file actually contains unsafe publishable content.
- Every command is concrete and scoped to `/mnt/d/job_project/xiaoman-claude`.
