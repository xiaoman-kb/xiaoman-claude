import json
import threading
import time
import uuid
from pathlib import Path

from .config import IDLE_TIMEOUT, POLL_INTERVAL, VALID_MSG_TYPES
from .ui import emit_teammate_event


shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()


class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(exist_ok=True, parents=True)

    def send(self, sender: str, to: str, content: str, msg_type: str = "message", extra: dict = None) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Invalid message type {msg_type},valid:{VALID_MSG_TYPES}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Message[{msg_type}] sent to {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text().strip().splitlines():
            if line:
                messages.append(json.loads(line))
        inbox_path.write_text("")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"Broadcasted to {count} teammates"


def handle_shutdown_request(bus: MessageBus, teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    with _tracker_lock:
        shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    bus.send("lead", teammate, "Please shut down gracefully.", "shutdown_request", {"request_id": req_id})
    return f"Shutdown request sent to {teammate} ({req_id})(status:pending)"


def handle_plan_review(bus: MessageBus, request_id: str, approve: bool, feedback: str = "") -> str:
    with _tracker_lock:
        req = plan_requests.get(request_id)
    if not req:
        return f"Invalid plan request {request_id}"
    with _tracker_lock:
        req["status"] = "approved" if approve else "rejected"
    bus.send(
        "lead",
        req["from"],
        feedback,
        "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"Plan request {request_id} {req['status']} for {req['from']}"


def check_shutdown_status(request_id: str) -> str:
    with _tracker_lock:
        return json.dumps(shutdown_requests.get(request_id, {"error": "not found"}))


def make_identity_block(name: str, role: str, team_name: str) -> dict:
    return {
        "role": role,
        "content": f"<identity>You are '{name}', role: {role}, team: {team_name}. Continue your work.</identity>",
    }


class TeammateManager:
    def __init__(
        self,
        team_dir: Path,
        *,
        workdir,
        client,
        model,
        bus,
        tasks,
        worktrees,
        exchange_log_path,
        append_exchange_log,
        run_bash,
        run_read,
        run_write,
        run_edit,
        scan_unclaimed_tasks,
        claim_task,
        task_requires_plan,
        get_worktree_path,
    ):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True, parents=True)
        self.config_path = self.dir / "config.json"
        self.config = self.load_config()
        self.threads = {}
        self.workdir = workdir
        self.client = client
        self.model = model
        self.bus = bus
        self.tasks = tasks
        self.worktrees = worktrees
        self.exchange_log_path = exchange_log_path
        self.append_exchange_log = append_exchange_log
        self.run_bash = run_bash
        self.run_read = run_read
        self.run_write = run_write
        self.run_edit = run_edit
        self.scan_unclaimed_tasks = scan_unclaimed_tasks
        self.claim_task = claim_task
        self.task_requires_plan = task_requires_plan
        self.get_worktree_path = get_worktree_path

    def load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def save_config(self):
        self.config_path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False))

    def find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self.find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
            member["task_id"] = None
            member["worktree"] = ""
        else:
            member = {"name": name, "role": role, "status": "working", "task_id": None, "worktree": ""}
            self.config["members"].append(member)
        self.save_config()
        thread = threading.Thread(target=self.teammate_loop, args=(name, role, prompt), daemon=True)
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def teammate_loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        sys_prompt = (
            f"You are {name}, a {role} in the team:{team_name} at {self.workdir}. "
            "Use send_message to communicate with the lead when needed. "
            "Use idle tool when you have no more work. You will auto-claim new tasks. "
            "When you are assigned or claim a task, you work inside that task's dedicated git worktree lane. "
            "All bash/read/write/edit tools operate in your current lane automatically, so do not try to work in another teammate's lane. "
            "When you finish a claimed task, either (a) mark it completed and keep the lane with worktree_keep for review, or (b) remove the lane with worktree_remove(force=true, complete_task=true) only when discarding the lane is acceptable. "
            "Hard rules: "
            "1) If the task is risky, destructive, architecture-changing, refactoring-heavy, or could affect multiple files/modules, "
            "you MUST call plan_approval before doing any real work. "
            "2) Before approval, you MUST NOT run bash, write_file, edit_file, or make any workspace changes except read_file and communication tools. "
            "3) After submitting plan_approval, stop execution and wait for lead feedback through inbox messages. "
            "4) Only continue implementation after you receive an explicit approval message for the same request. "
            "5) If the plan is rejected, revise the plan or ask for clarification; do not implement anyway. "
            "6) If you receive shutdown_request, you MUST respond with shutdown_response."
        )
        messages = [{"role": "user", "content": prompt}]
        tools = self.teammate_tools()
        should_exit = False
        approval_state = {
            "required": any(k in prompt.lower() for k in ("risky", "refactor", "rewrite", "migration", "breaking", "legacy auth")),
            "waiting_request_id": None,
            "approved": False,
        }
        workspace_state = {"task_id": None, "worktree": "", "cwd": None}
        while True:
            resume = False
            for _ in range(50):
                inbox = self.bus.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self.set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                    if msg.get("type") == "plan_approval_response" and msg.get("request_id") == approval_state["waiting_request_id"]:
                        approval_state["waiting_request_id"] = None
                        approval_state["approved"] = bool(msg.get("approve"))
                if should_exit:
                    break
                if approval_state["waiting_request_id"]:
                    time.sleep(0.2)
                    continue
                try:
                    response = self.client.messages.create(
                        model=self.model,
                        system=sys_prompt,
                        messages=messages,
                        tools=tools,
                        max_tokens=8000,
                    )
                except Exception:
                    break
                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = []
                idle_requested = False
                for block in response.content:
                    if block.type == "tool_use":
                        if block.name == "idle":
                            idle_requested = True
                            output = "Entering idle phase. Will poll for new tasks."
                        else:
                            try:
                                output = self.exec(name, block.name, block.input, approval_state, workspace_state)
                            except Exception as e:
                                output = f"Error: {e}"
                        emit_teammate_event(name, block.name, output)
                        self.append_exchange_log(
                            self.exchange_log_path,
                            {"event": "tool_exec", "agent": name, "tool": block.name, "preview": str(output)[:120]},
                        )
                        results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
                        if block.name == "shutdown_response" and block.input.get("approve"):
                            should_exit = True
                messages.append({"role": "user", "content": results})
                if idle_requested:
                    break
            if should_exit:
                self.set_status(name, "shutdown")
                return
            self.set_status(name, "idle")
            polls = IDLE_TIMEOUT // max(POLL_INTERVAL, 1)
            for _ in range(polls):
                time.sleep(POLL_INTERVAL)
                inbox = self.bus.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self.set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = self.scan_unclaimed_tasks()
                if unclaimed:
                    task = unclaimed[0]
                    result = self.claim_task(task["id"], name)
                    if result.startswith("Error:"):
                        continue
                    claimed = self.tasks.load(task["id"])
                    approval_state["required"] = self.task_requires_plan(claimed)
                    approval_state["waiting_request_id"] = None
                    approval_state["approved"] = False
                    workspace_state["task_id"] = claimed["id"]
                    workspace_state["worktree"] = claimed.get("worktree", "")
                    workspace_state["cwd"] = self.get_worktree_path(claimed["worktree"]) if claimed.get("worktree") else None
                    self.set_assignment(name, claimed["id"], claimed.get("worktree", ""))
                    task_prompt = (
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                        f"{task.get('description', '')}\n"
                        f"worktree={claimed.get('worktree', '')}</auto-claimed>"
                    )
                    if len(messages) <= 3:
                        messages.insert(0, make_identity_block(name, role, team_name))
                        messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                    messages.append({"role": "user", "content": task_prompt})
                    messages.append({"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                    resume = True
                    break
            if not resume:
                self.set_status(name, "shutdown")
                return
            self.set_status(name, "working")

    def set_status(self, name, status: str):
        member = self.find_member(name)
        if member:
            member["status"] = status
            self.save_config()

    def set_assignment(self, name: str, task_id: int | None, worktree: str):
        member = self.find_member(name)
        if member:
            member["task_id"] = task_id
            member["worktree"] = worktree
            self.save_config()

    def teammate_tools(self) -> list:
        return [
            {"name": "bash", "description": "Run a shell command.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
            {"name": "read_file", "description": "Read file contents.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "write_file", "description": "Write content to file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "edit_file", "description": "Replace exact text in file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
            {"name": "send_message", "description": "Send message to a teammate.", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)}}, "required": ["to", "content"]}},
            {"name": "read_inbox", "description": "Read and drain your inbox.", "input_schema": {"type": "object", "properties": {}}},
            {"name": "shutdown_response", "description": "Respond to a shutdown request. Approve to shut down, reject to keep working.", "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "reason": {"type": "string"}}, "required": ["request_id", "approve"]}},
            {"name": "plan_approval", "description": "Submit a plan for lead approval. Provide plan text.", "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}, "required": ["plan"]}},
            {"name": "idle", "description": "Signal that you have no more work. Enters idle polling phase.", "input_schema": {"type": "object", "properties": {}}},
            {"name": "claim_task", "description": "Claim a task from the task board by ID.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
            {"name": "task_get", "description": "Get details of a task by ID.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
            {"name": "task_update", "description": "Update task status or dependencies.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}, "addBlockedBy": {"type": "array", "items": {"type": "integer"}}, "removeBlockedBy": {"type": "array", "items": {"type": "integer"}}}, "required": ["task_id"]}},
            {"name": "worktree_keep", "description": "Keep the current or named worktree for review.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}}},
            {"name": "worktree_remove", "description": "Remove the current or named worktree. Use complete_task=true when finished.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "force": {"type": "boolean"}, "complete_task": {"type": "boolean"}}}},
        ]

    def exec(self, sender: str, tool_name: str, args: dict, approval_state: dict | None = None, workspace_state: dict | None = None) -> str:
        if approval_state and approval_state.get("required") and not approval_state.get("approved"):
            if tool_name in {"bash", "write_file", "edit_file"}:
                return "Blocked: plan approval required before execution."
        base_dir = workspace_state.get("cwd") if workspace_state else None
        if tool_name == "bash":
            return self.run_bash(args["command"], cwd=base_dir)
        if tool_name == "read_file":
            return self.run_read(args["path"], base_dir=base_dir)
        if tool_name == "write_file":
            return self.run_write(args["path"], args["content"], base_dir=base_dir)
        if tool_name == "edit_file":
            return self.run_edit(args["path"], args["old_text"], args["new_text"], base_dir=base_dir)
        if tool_name == "send_message":
            return self.bus.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return json.dumps(self.bus.read_inbox(sender), indent=2)
        if tool_name == "shutdown_response":
            req_id = args["request_id"]
            approve = args["approve"]
            with _tracker_lock:
                if req_id in shutdown_requests:
                    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
            self.bus.send(sender, "lead", args.get("reason", ""), "shutdown_response", {"request_id": req_id, "approve": approve})
            return f"Shutdown {'approved' if approve else 'rejected'}"
        if tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            req_id = str(uuid.uuid4())[:8]
            with _tracker_lock:
                plan_requests[req_id] = {"from": sender, "plan": plan_text, "status": "pending"}
            if approval_state is not None:
                approval_state["waiting_request_id"] = req_id
                approval_state["approved"] = False
            self.bus.send(sender, "lead", plan_text, "plan_approval_response", {"request_id": req_id, "plan": plan_text})
            return f"Plan approval request {req_id} sent to lead,Waiting for approval"
        if tool_name == "claim_task":
            result = self.claim_task(args["task_id"], sender)
            if not result.startswith("Error:") and workspace_state is not None:
                task = self.tasks.load(args["task_id"])
                if approval_state is not None:
                    approval_state["required"] = self.task_requires_plan(task)
                    approval_state["waiting_request_id"] = None
                    approval_state["approved"] = False
                workspace_state["task_id"] = task["id"]
                workspace_state["worktree"] = task.get("worktree", "")
                workspace_state["cwd"] = self.get_worktree_path(task["worktree"]) if task.get("worktree") else None
                self.set_assignment(sender, task["id"], task.get("worktree", ""))
            return result
        if tool_name == "task_get":
            return self.tasks.get(args["task_id"])
        if tool_name == "task_update":
            return self.tasks.update(args["task_id"], args.get("status"), args.get("addBlockedBy"), args.get("removeBlockedBy"))
        if tool_name == "worktree_keep":
            name = args.get("name") or (workspace_state.get("worktree") if workspace_state else "")
            if not name:
                return "Error: No current worktree"
            result = self.worktrees.keep(name)
            if workspace_state and workspace_state.get("worktree") == name:
                if workspace_state.get("task_id") is not None:
                    self.set_assignment(sender, None, "")
                workspace_state["task_id"] = None
                workspace_state["worktree"] = ""
                workspace_state["cwd"] = None
            return result
        if tool_name == "worktree_remove":
            name = args.get("name") or (workspace_state.get("worktree") if workspace_state else "")
            if not name:
                return "Error: No current worktree"
            result = self.worktrees.remove(name, args.get("force", False), args.get("complete_task", False))
            if workspace_state and workspace_state.get("worktree") == name:
                self.set_assignment(sender, None, "")
                workspace_state["task_id"] = None
                workspace_state["worktree"] = ""
                workspace_state["cwd"] = None
            return result
        return f"Unknown tool:{tool_name}"

    def list_all(self):
        if not self.config["members"]:
            return "No members yet"
        lines = []
        for m in self.config["members"]:
            suffix = f" task={m['task_id']}" if m.get("task_id") else ""
            wt = f" wt={m['worktree']}" if m.get("worktree") else ""
            lines.append(f"{m['name']}:{m['status']}{suffix}{wt}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]
