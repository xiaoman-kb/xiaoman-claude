import json
import re
import subprocess
import uuid
from pathlib import Path

from .events import EventBus
from .tasks import TaskManager


class WorktreeManager:
    def __init__(self, repo_root: Path, worktrees_dir: Path, tasks: TaskManager, events: EventBus):
        self.repo_root = repo_root
        self.dir = worktrees_dir
        self.tasks = tasks
        self.events = events
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"worktrees": []}, indent=2))

    def _ensure_repo(self):
        if not (self.repo_root / ".git").exists():
            raise RuntimeError(f"No git repository detected at {self.repo_root}")

    def _load_index(self) -> dict:
        return json.loads(self.index_path.read_text() or '{"worktrees": []}')

    def _save_index(self, data: dict):
        self.index_path.write_text(json.dumps(data, indent=2))

    def find(self, name: str) -> dict | None:
        index = self._load_index()
        for wt in index["worktrees"]:
            if wt["name"] == name:
                return wt
        return None

    def _update_entry(self, entry: dict):
        index = self._load_index()
        for i, wt in enumerate(index["worktrees"]):
            if wt["name"] == entry["name"]:
                index["worktrees"][i] = entry
                self._save_index(index)
                return
        raise ValueError(f"Worktree {entry['name']} not found")

    def _run_git(self, args: list[str]) -> str:
        self._ensure_repo()
        r = subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stdout + r.stderr).strip() or "git command failed")
        return (r.stdout + r.stderr).strip()

    def create(self, name: str, task_id: int | None = None, base_ref: str = "HEAD") -> str:
        return self.create_with_owner(name, task_id=task_id, owner="", base_ref=base_ref)

    def create_with_owner(self, name: str, task_id: int | None = None, owner: str = "", base_ref: str = "HEAD") -> str:
        if not re.match(r"^[A-Za-z0-9._-]+$", name):
            raise ValueError("Invalid worktree name")
        if self.find(name):
            raise ValueError(f"Worktree {name} already exists")
        if task_id is not None:
            self.tasks.load(task_id)
        path = self.dir / name
        branch = f"wt/{name}"
        self.events.emit("worktree.create.before", task={"id": task_id} if task_id is not None else None, worktree={"name": name, "path": str(path), "branch": branch})
        try:
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])
            index = self._load_index()
            entry = {
                "name": name,
                "path": str(path),
                "branch": branch,
                "task_id": task_id,
                "status": "active",
            }
            index["worktrees"].append(entry)
            self._save_index(index)
            if task_id is not None:
                self.tasks.bind_worktree(task_id, name, owner)
            self.events.emit("worktree.create.after", task={"id": task_id} if task_id is not None else None, worktree=entry)
            return json.dumps(entry, indent=2, ensure_ascii=False)
        except Exception as e:
            self.events.emit("worktree.create.failed", task={"id": task_id} if task_id is not None else None, worktree={"name": name}, error=str(e))
            raise

    def bind_task(self, task_id: int, name: str, owner: str = "") -> str:
        entry = self.find(name)
        if not entry:
            raise ValueError(f"Worktree {name} does not exist")
        entry["task_id"] = task_id
        self._update_entry(entry)
        return self.tasks.bind_worktree(task_id, name, owner)

    def list_all(self) -> str:
        items = self._load_index()["worktrees"]
        if not items:
            return "No worktrees"
        return json.dumps(items, indent=2, ensure_ascii=False)

    def status(self, name: str) -> str:
        entry = self.find(name)
        if not entry:
            return f"Worktree {name} not found"
        return json.dumps(entry, indent=2, ensure_ascii=False)

    def run(self, name: str, command: str) -> str:
        entry = self.find(name)
        if not entry:
            raise ValueError(f"Worktree {name} does not exist")
        path = Path(entry["path"])
        if not path.exists():
            raise ValueError(f"Worktree path missing: {path}")
        r = subprocess.run(command, shell=True, cwd=path, capture_output=True, text=True, timeout=300)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"

    def keep(self, name: str) -> str:
        entry = self.find(name)
        if not entry:
            raise ValueError(f"Worktree {name} does not exist")
        entry["status"] = "kept"
        self._update_entry(entry)
        self.events.emit("worktree.keep", task={"id": entry.get("task_id")} if entry.get("task_id") is not None else None, worktree=entry)
        return f"Kept worktree {name}"

    def remove(self, name: str, force: bool = False, complete_task: bool = False) -> str:
        entry = self.find(name)
        if not entry:
            raise ValueError(f"Worktree {name} does not exist")
        wt_path = entry["path"]
        self.events.emit("worktree.remove.before", task={"id": entry.get("task_id")} if entry.get("task_id") is not None else None, worktree=entry)
        try:
            args = ["worktree", "remove", wt_path]
            if force:
                args.append("--force")
            self._run_git(args)
            task_info = None
            if complete_task and entry.get("task_id") is not None:
                task_info = json.loads(self.tasks.update(entry["task_id"], status="completed"))
                self.tasks.unbind_worktree(entry["task_id"])
                self.events.emit("task.completed", task=task_info, worktree={"name": name, "status": "removed"})
            elif entry.get("task_id") is not None:
                self.tasks.unbind_worktree(entry["task_id"])
            index = self._load_index()
            index["worktrees"] = [wt for wt in index["worktrees"] if wt["name"] != name]
            self._save_index(index)
            removed_entry = dict(entry)
            removed_entry["status"] = "removed"
            self.events.emit("worktree.remove.after", task=task_info or ({"id": entry.get("task_id")} if entry.get("task_id") is not None else None), worktree=removed_entry)
            return f"Removed worktree {name}"
        except Exception as e:
            self.events.emit("worktree.remove.failed", task={"id": entry.get('task_id')} if entry.get("task_id") is not None else None, worktree=entry, error=str(e))
            raise


def make_worktree_name(task_id: int, owner: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", f"task-{task_id}-{owner}".lower()).strip("-")
    return base[:40] or f"task-{task_id}"


def ensure_task_worktree(task_manager: TaskManager, worktrees: WorktreeManager, task_id: int, owner: str) -> str:
    task = task_manager.load(task_id)
    existing = task.get("worktree")
    if existing:
        return existing
    base_name = make_worktree_name(task_id, owner)
    try_names = [base_name, f"{base_name}-{uuid.uuid4().hex[:4]}"]
    last_error = None
    for name in try_names:
        try:
            worktrees.create_with_owner(name, task_id=task_id, owner=owner)
            return name
        except Exception as e:
            last_error = e
    raise last_error


def get_worktree_path(worktrees: WorktreeManager, name: str) -> Path | None:
    entry = worktrees.find(name)
    if not entry:
        return None
    return Path(entry["path"])
