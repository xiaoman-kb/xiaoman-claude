import subprocess
import threading
import time

from .config import WORKDIR


class BackgroundManager:
    def __init__(self):
        self.tasks = {}
        self.notification_queue = []
        self.lock = threading.Lock()

    def run(self, command: str) -> str:
        task_id = str(time.time_ns())
        self.tasks[task_id] = {"status": "running", "command": command}
        thread = threading.Thread(target=self.execute, args=(task_id, command), daemon=True)
        thread.start()
        return f"Background task {task_id} started"

    def execute(self, task_id: str, command: str):
        try:
            r = subprocess.run(command, shell=True, cwd=WORKDIR, capture_output=True, text=True, timeout=300)
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Command timed out(300s)"
            status = "timeout"
        except Exception as e:
            output = f"Error: {str(e)}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "Command completed without output"
        with self.lock:
            self.notification_queue.append({
                "task_id": task_id,
                "status": status,
                "command": command[:80],
                "result": output[:500],
            })

    def check(self, task_id: str = None) -> str:
        if task_id:
            t = self.tasks.get(task_id)
            if not t:
                return f"Unknown task {task_id}"
            return f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
        lines = []
        for tid, t in self.tasks.items():
            lines.append(f"[{tid}:{t['status']}] {t['command'][:60]}")
        return "\n".join(lines) if lines else "No background tasks running"

    def drain_notifications(self) -> list:
        with self.lock:
            notifications = list(self.notification_queue)
            self.notification_queue.clear()
        return notifications
