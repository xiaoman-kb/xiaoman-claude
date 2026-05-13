# Homepage Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two side-by-side terminal screenshots to the top of `README.md`, normalize their filenames, and prepare polished GitHub homepage metadata for the repository.

**Architecture:** Keep the change surface small and documentation-focused. Reuse the existing screenshots under `docs/image/`, rename them to stable English filenames, insert a centered HTML image block near the top of `README.md`, and add a short metadata section to the README that gives the repository owner copy-ready GitHub homepage settings.

**Tech Stack:** Markdown, HTML-in-Markdown, Git, repository assets under `docs/image/`

---

### Task 1: Normalize screenshot asset names

**Files:**
- Modify: `docs/image/`
- Verify: `docs/image/workspace-overview.png`
- Verify: `docs/image/message-flow.png`

- [ ] **Step 1: Inspect the current screenshot filenames**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path("docs/image")
for path in sorted(root.glob("*")):
    print(path.name)
PY
```

Expected: two screenshot filenames are printed from `docs/image/`, currently using timestamp-based Chinese names.

- [ ] **Step 2: Rename the workspace overview screenshot**

Run:

```bash
mv "docs/image/屏幕截图 2026-05-13 231146.png" "docs/image/workspace-overview.png"
```

Expected: the first screenshot is renamed in place with no duplicate created.

- [ ] **Step 3: Rename the message flow screenshot**

Run:

```bash
mv "docs/image/屏幕截图 2026-05-13 231028.png" "docs/image/message-flow.png"
```

Expected: the second screenshot is renamed in place with no duplicate created.

- [ ] **Step 4: Verify the normalized asset names**

Run:

```bash
python - <<'PY'
from pathlib import Path
expected = {
    "workspace-overview.png",
    "message-flow.png",
}
actual = {p.name for p in Path("docs/image").glob("*.png")}
print(sorted(actual))
missing = expected - actual
raise SystemExit(f"Missing: {sorted(missing)}" if missing else 0)
PY
```

Expected: both English filenames are present and the command exits successfully.

- [ ] **Step 5: Commit the asset rename**

```bash
git add docs/image
git commit -m "docs: normalize homepage screenshot names"
```

### Task 2: Add a side-by-side screenshot block to README

**Files:**
- Modify: `README.md`
- Verify: `docs/image/workspace-overview.png`
- Verify: `docs/image/message-flow.png`

- [ ] **Step 1: Write a focused README test by checking for the image block markers**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
required = [
    '<p align="center">',
    'docs/image/workspace-overview.png',
    'docs/image/message-flow.png',
]
missing = [item for item in required if item not in text]
raise SystemExit(f"Missing markers: {missing}" if missing else 0)
PY
```

Expected: FAIL before editing `README.md` because the image block markers do not exist yet.

- [ ] **Step 2: Insert the minimal top-of-file image block**

Update `README.md` by placing the following block after the one-line project positioning statement and before the origin/evolution story:

```md
<p align="center">
  <img src="docs/image/workspace-overview.png" alt="Workspace overview with teammates, tasks, and worktrees" width="48%" />
  <img src="docs/image/message-flow.png" alt="Message-flow terminal UI with streamed assistant output" width="48%" />
</p>

Terminal snapshots: workspace coordination on the left, message-flow interaction on the right.
```

The top section should read in this order:

```md
# xiaoman-claude

A terminal multi-agent development assistant built through learning, migration, and engineering iteration.

<p align="center">
  <img src="docs/image/workspace-overview.png" alt="Workspace overview with teammates, tasks, and worktrees" width="48%" />
  <img src="docs/image/message-flow.png" alt="Message-flow terminal UI with streamed assistant output" width="48%" />
</p>

Terminal snapshots: workspace coordination on the left, message-flow interaction on the right.

This project started after I worked through [`learn-claude-code`](https://github.com/shareAI-lab/learn-claude-code) ...
```

- [ ] **Step 3: Run the README marker check again**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
required = [
    '<p align="center">',
    'docs/image/workspace-overview.png',
    'docs/image/message-flow.png',
]
missing = [item for item in required if item not in text]
raise SystemExit(f"Missing markers: {missing}" if missing else 0)
PY
```

Expected: PASS with exit code 0.

- [ ] **Step 4: Verify the top portion of the README reads cleanly**

Run:

```bash
python - <<'PY'
from pathlib import Path
for i, line in enumerate(Path("README.md").read_text().splitlines()[:18], start=1):
    print(f"{i:>2}: {line}")
PY
```

Expected: the title, one-line positioning, image block, caption line, and origin paragraph appear in the intended order.

- [ ] **Step 5: Commit the README image block**

```bash
git add README.md
git commit -m "docs: add homepage screenshots to readme"
```

### Task 3: Add GitHub homepage metadata guidance to README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write a failing content check for repository metadata guidance**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
required = [
    "## GitHub Homepage Settings",
    "Description:",
    "Tagline:",
    "Topics:",
]
missing = [item for item in required if item not in text]
raise SystemExit(f"Missing metadata section markers: {missing}" if missing else 0)
PY
```

Expected: FAIL before editing because the section does not exist yet.

- [ ] **Step 2: Add a concise GitHub homepage metadata section near the end of README**

Insert the following section after `## Roadmap` and before the closing line:

```md
## GitHub Homepage Settings

If you want the repository page to match the README tone, use:

- Description: `A terminal multi-agent development assistant built from learning, migration, and engineering iteration.`
- Tagline: `From learning agent systems to building a personal multi-agent terminal harness.`
- Topics: `ai-agent`, `multi-agent`, `claude`, `anthropic`, `terminal-ui`, `rich`, `python`, `git-worktree`, `developer-tools`, `agentic-workflow`
```

Keep the existing closing line after this new section.

- [ ] **Step 3: Run the metadata content check again**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
required = [
    "## GitHub Homepage Settings",
    "Description:",
    "Tagline:",
    "Topics:",
]
missing = [item for item in required if item not in text]
raise SystemExit(f"Missing metadata section markers: {missing}" if missing else 0)
PY
```

Expected: PASS with exit code 0.

- [ ] **Step 4: Check the Roadmap, metadata section, and closing line ordering**

Run:

```bash
python - <<'PY'
from pathlib import Path
lines = Path("README.md").read_text().splitlines()
for i, line in enumerate(lines[-20:], start=len(lines)-19):
    print(f"{i:>3}: {line}")
PY
```

Expected: `## Roadmap`, then `## GitHub Homepage Settings`, then the final closing line appear in that order.

- [ ] **Step 5: Commit the metadata guidance**

```bash
git add README.md
git commit -m "docs: add github homepage metadata guidance"
```

### Task 4: Verify diagnostics, git state, and final output

**Files:**
- Verify: `README.md`
- Verify: `docs/image/workspace-overview.png`
- Verify: `docs/image/message-flow.png`

- [ ] **Step 1: Check editor diagnostics for the modified README**

Use the editor diagnostics tool for:

`file:///mnt/d/job_project/xiaoman-claude/README.md`

Expected: no diagnostics.

- [ ] **Step 2: Run a final repository verification script**

Run:

```bash
python - <<'PY'
from pathlib import Path
readme = Path("README.md").read_text()
required = [
    "docs/image/workspace-overview.png",
    "docs/image/message-flow.png",
    "## GitHub Homepage Settings",
]
missing = [item for item in required if item not in readme]
if missing:
    raise SystemExit(f"README missing: {missing}")
for path in [
    Path("docs/image/workspace-overview.png"),
    Path("docs/image/message-flow.png"),
]:
    if not path.exists():
        raise SystemExit(f"Missing asset: {path}")
print("OK")
PY
```

Expected: `OK`

- [ ] **Step 3: Verify git status before the final commit**

Run:

```bash
git status --short
```

Expected: only `README.md` and the renamed screenshot files are changed if the previous commit steps were intentionally skipped, or no output if all task-level commits were performed already.

- [ ] **Step 4: Create the final polish commit if needed**

```bash
git add README.md docs/image
git commit -m "docs: polish github homepage presentation"
```

Expected: commit succeeds if there are uncommitted homepage-related changes. Skip this step only if the earlier task commits already left the worktree clean.

- [ ] **Step 5: Push the branch after verification**

```bash
git push origin main
```

Expected: remote branch updates successfully.
