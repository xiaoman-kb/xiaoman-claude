import json
import threading
import time
from pathlib import Path


_claim_lock = threading.Lock()


def scan_unclaimed_tasks(task_dir: Path) -> list:
    task_dir.mkdir(exist_ok=True)
    unclaimed = []
    for f in sorted(task_dir.glob("task_*.json")):
        task = json.loads(f.read_text())
        if task.get("status") == "pending" and not task.get("owner") and not task.get("blockedBy"):
            unclaimed.append(task)
    return unclaimed


def task_requires_plan(task: dict) -> bool:
    text = f"{task.get('subject', '')} {task.get('description', '')}".lower()
    keywords = ("risky", "refactor", "rewrite", "migration", "breaking", "legacy auth", "architecture", "multi-file")
    return any(k in text for k in keywords)


class TaskManager:
    def __init__(self, task_dir: Path):
        self.dir = task_dir
        self.dir.mkdir(exist_ok=True)
        self._next_id = self._max_id() + 1

    def _max_id(self):
        ids = [int(p.stem.split("_")[1]) for p in self.dir.glob("task_*.json")]
        return max(ids) if ids else 0

    def load(self, task_id: int) -> dict:
        path = self.dir / f"task_{task_id}.json"
        if not path.exists():
            raise ValueError(f"Task {task_id} does not exist")
        return json.loads(path.read_text())

    def save(self, task: dict):
        task["updated_at"] = time.time()
        path = self.dir / f"task_{task['id']}.json"
        path.write_text(json.dumps(task, indent=2, ensure_ascii=False))

    def create(self, subject: str, description: str = "") -> str:
        now = time.time()
        task = {
            "id": self._next_id,
            "subject": subject,
            "description": description,
            "status": "pending",
            "blockedBy": [],
            "owner": "",
            "worktree": "",
            "created_at": now,
            "updated_at": now,
        }
        self.save(task)
        self._next_id += 1
        return json.dumps(task, indent=2, ensure_ascii=False)

    def get(self, task_id: int) -> str:
        return json.dumps(self.load(task_id), indent=2, ensure_ascii=False)

    def update(self, task_id: int, status: str = None, add_blocked_by: list = None, remove_blocked_by: list = None) -> str:
        task = self.load(task_id)
        if status:
            if status not in ["pending", "in_progress", "completed"]:
                raise ValueError(f"Invalid status: {status}")
            task["status"] = status
            if status == "completed":
                self.clear_dependency(task_id)
        if add_blocked_by:
            task["blockedBy"] = list(set(task["blockedBy"] + add_blocked_by))
        if remove_blocked_by:
            task["blockedBy"] = [x for x in task["blockedBy"] if x not in remove_blocked_by]
        self.save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def bind_worktree(self, task_id: int, worktree: str, owner: str = "") -> str:
        task = self.load(task_id)
        task["worktree"] = worktree
        if owner:
            task["owner"] = owner
        if task["status"] == "pending":
            task["status"] = "in_progress"
        self.save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def unbind_worktree(self, task_id: int) -> str:
        task = self.load(task_id)
        task["worktree"] = ""
        self.save(task)
        return json.dumps(task, indent=2, ensure_ascii=False)

    def clear_dependency(self, completed_id: int):
        for f in self.dir.glob("task_*.json"):
            task = json.loads(f.read_text())
            if completed_id in task.get("blockedBy", []):
                task["blockedBy"].remove(completed_id)
                self.save(task)

    def list_all(self) -> str:
        tasks = []
        files = sorted(self.dir.glob("task_*.json"), key=lambda f: int(f.stem.split("_")[1]))
        for f in files:
            tasks.append(json.loads(f.read_text()))
        if not tasks:
            return "No tasks"
        lines = []
        for t in tasks:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
            blocked = f"(blocked by :{t['blockedBy']})" if t.get("blockedBy") else ""
            owner = f" owner={t['owner']}" if t.get("owner") else ""
            worktree = f" wt={t['worktree']}" if t.get("worktree") else ""
            lines.append(f"{marker} {t['id']}: {t['subject']} {blocked}{owner}{worktree}")
        return "\n".join(lines)


def claim_task(task_manager: TaskManager, ensure_task_worktree, task_id: str | int, owner: str) -> str:
    with _claim_lock:
        try:
            task = task_manager.load(int(task_id))
        except Exception:
            return f"Error:Task {task_id} does not exist"
        if task.get("owner"):
            existing_owner = task.get("owner") or "someone else"
            return f"Error: Task {task_id} is already claimed by {existing_owner}"
        if task.get("status") != "pending":
            status = task.get("status")
            return f"Error: Task {task_id} cannot be claimed because its status is '{status}'"
        if task.get("blockedBy"):
            return f"Error: Task {task_id} is blocked by {task.get('blockedBy')}"
        task["owner"] = owner
        task["status"] = "in_progress"
        task_manager.save(task)
        try:
            worktree_name = ensure_task_worktree(int(task_id), owner)
        except Exception as e:
            task["owner"] = ""
            task["status"] = "pending"
            task_manager.save(task)
            return f"Error: Failed to allocate worktree for task {task_id}: {e}"
        task = task_manager.load(int(task_id))
    return f"Claimed task {task_id} for {owner} in worktree {task.get('worktree') or worktree_name}"


class TodoManager:
    def __init__(self):
        self.items = []

    def update(self, items: list) -> str:
        if len(items) > 20:
            raise ValueError("Max 20 todo allowed")
        validated, in_progress_count = [], 0
        for i, item in enumerate(items):
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).lower()
            item_id = str(item.get("id", str(i + 1)))
            if not text:
                raise ValueError(f"Item {item_id} is empty")
            if status not in ["pending", "in_progress", "completed"]:
                raise ValueError(f"Item {item_id} has invalid status {status}")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"], "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time.")
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todo items"
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[item["status"]]
            lines.append(f"{marker} #{item['id']}: {item['text']}")
        done = sum(1 for t in self.items if t["status"] == "completed")
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)
