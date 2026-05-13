import json
import time

from rich.live import Live

from .cancel import EscListener, TurnCancellation
from .background import BackgroundManager
from .compact import auto_compact, estimate_tokens, micro_compact
from .config import CLIENT, EXCHANGE_LOG_PATH, INBOX_DIR, MODEL, REPO_ROOT, SKILLS_DIR, TASK_DIR, TEAM_DIR, THRESHOLD, WORKDIR, WORKTREES_DIR
from .events import EventBus, append_exchange_log
from .io_tools import run_bash, run_edit, run_read, run_write
from .skills import SkillLoader
from .tasks import TaskManager, TodoManager, claim_task, scan_unclaimed_tasks, task_requires_plan
from .team import MessageBus, TeammateManager, check_shutdown_status, handle_plan_review, handle_shutdown_request
from .ui import build_assistant_renderable, console, input_prompt, live_wait, print_input_footer, print_overview, print_status, print_text_response, print_tool_result, set_input_bar_state
from .worktrees import WorktreeManager, ensure_task_worktree, get_worktree_path


SKILL_LOADER = SkillLoader(SKILLS_DIR)
TODO = TodoManager()
TASKS = TaskManager(TASK_DIR)
WORKTREE_EVENTS = EventBus(WORKTREES_DIR / "events.jsonl")
WORKTREES = WorktreeManager(REPO_ROOT, WORKTREES_DIR, TASKS, WORKTREE_EVENTS)
BG = BackgroundManager()
BUS = MessageBus(INBOX_DIR)
TEAM = TeammateManager(
    TEAM_DIR,
    workdir=WORKDIR,
    client=CLIENT,
    model=MODEL,
    bus=BUS,
    tasks=TASKS,
    worktrees=WORKTREES,
    exchange_log_path=EXCHANGE_LOG_PATH,
    append_exchange_log=append_exchange_log,
    run_bash=run_bash,
    run_read=run_read,
    run_write=run_write,
    run_edit=run_edit,
    scan_unclaimed_tasks=lambda: scan_unclaimed_tasks(TASK_DIR),
    claim_task=lambda task_id, owner: claim_task(TASKS, lambda tid, own: ensure_task_worktree(TASKS, WORKTREES, tid, own), task_id, owner),
    task_requires_plan=task_requires_plan,
    get_worktree_path=lambda name: get_worktree_path(WORKTREES, name),
)

SYSTEM = f"""
You are a coding agent and team lead at {WORKDIR}.Spawn teammates and communicate via inboxes.
Use the todo tool to plan multi-step tasks. Mark in_progress before starting, completed when done.
When teammate work or autonomous task progress needs time, prefer the wait tool to observe instead of intervening immediately.
Prefer tools over prose. Skills available:{SKILL_LOADER.get_descriptions()}"""
SUBAGENT_SYSTEM = f"You are a coding subagent at {WORKDIR}. Complete the given task, then summarize your findings. Skills available:{SKILL_LOADER.get_descriptions()}"


def _claim_for_lead(task_id):
    return claim_task(TASKS, lambda tid, owner: ensure_task_worktree(TASKS, WORKTREES, tid, owner), task_id, "lead")


def collect_stream_text(events) -> str:
    chunks = []
    for event in events:
        if getattr(event, "type", "") == "content_block_delta":
            delta = getattr(event, "delta", None)
            text = getattr(delta, "text", "")
            if text:
                chunks.append(text)
    return "".join(chunks)


def clip_tool_output(text: str, max_lines: int = 12, max_chars: int = 1200) -> str:
    tail = text[-max_chars:]
    lines = tail.splitlines()
    return "\n".join(lines[-max_lines:]) if lines else tail


def _sanitize_text(value: str) -> str:
    return value.encode("utf-8", "replace").decode("utf-8")


def _sanitize_structure(value):
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_structure(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_structure(v) for k, v in value.items()}
    return value


def sanitize_messages_for_api(messages: list):
    return [_sanitize_structure(message) for message in messages]


def should_print_final_stream_text(text: str, stream_rendered: bool) -> bool:
    return bool((text or "").strip()) and not stream_rendered


def should_render_main_history_tail() -> bool:
    return False


def should_refresh_stream_view(current_text: str, last_rendered_text: str, chunk_len: int, min_chars: int = 24) -> bool:
    if not current_text.strip():
        return False
    if current_text.endswith(("\n", "。", "！", "？", ".", "!", "?", ":", "：")):
        return True
    if len(current_text) - len(last_rendered_text) >= min_chars:
        return True
    return chunk_len >= min_chars


def make_stream_result(text: str, *, cancelled: bool, response, events: list, stream_rendered: bool = False):
    return {
        "response": response,
        "text": text,
        "events": events,
        "cancelled": cancelled,
        "stream_rendered": stream_rendered,
    }


def create_streamed_response(messages: list, is_cancelled=lambda: False):
    events = []
    text_chunks = []
    last_rendered_text = ""
    stream_rendered = False
    response = None
    cancelled = False
    safe_messages = sanitize_messages_for_api(messages)
    with Live(build_assistant_renderable(""), console=console, refresh_per_second=6, transient=False, auto_refresh=False) as live:
        with CLIENT.messages.stream(model=MODEL, system=SYSTEM, messages=safe_messages, tools=PARENT_TOOLS, max_tokens=8000) as stream:
            for event in stream:
                if is_cancelled():
                    cancelled = True
                    break
                events.append(event)
                if getattr(event, "type", "") == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    text = getattr(delta, "text", "")
                    if text:
                        text_chunks.append(text)
                        current_text = "".join(text_chunks)
                        if should_refresh_stream_view(current_text, last_rendered_text, len(text)):
                            live.update(build_assistant_renderable(current_text), refresh=True)
                            last_rendered_text = current_text
                            stream_rendered = True
            if not cancelled:
                response = stream.get_final_message()
        final_text = "".join(text_chunks)
        if final_text.strip() and final_text != last_rendered_text:
            live.update(build_assistant_renderable(final_text), refresh=True)
            stream_rendered = True
    return make_stream_result(final_text, cancelled=cancelled, response=response, events=events, stream_rendered=stream_rendered)


def handle_stream_result(result: dict):
    streamed_text = result["text"]
    stream_rendered = result.get("stream_rendered", False)
    if result.get("cancelled"):
        print_status("response cancelled.", style="dim")
        return None
    if should_print_final_stream_text(streamed_text, stream_rendered):
        print_text_response(streamed_text)
    return result["response"]


def run_with_turn_cancellation(state, listener, work):
    state.reset()
    listener.start()
    try:
        return work()
    finally:
        listener.stop()
        state.reset()


def run_lead_tool(name: str, args: dict, *, is_cancelled=lambda: False):
    if name == "wait":
        return live_wait(
            max(0, min(int(args.get("seconds", 5)), 30)),
            get_team=TEAM.list_all,
            get_tasks=TASKS.list_all,
            get_worktrees=WORKTREES.list_all,
            sleep_fn=time.sleep,
            is_cancelled=is_cancelled,
        )
    handler = TOOL_HANDLERS.get(name)
    return handler(**args) if handler else f"Unknown tool: {name}"


TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "wait": lambda **kw: live_wait(
        max(0, min(int(kw.get("seconds", 5)), 30)),
        get_team=TEAM.list_all,
        get_tasks=TASKS.list_all,
        get_worktrees=WORKTREES.list_all,
        sleep_fn=time.sleep,
    ),
    "todo": lambda **kw: TODO.update(kw["items"]),
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
    "compact": lambda **kw: "Manual compression requested",
    "task_create": lambda **kw: TASKS.create(kw["subject"], kw.get("description", "")),
    "task_update": lambda **kw: TASKS.update(kw["task_id"], kw.get("status"), kw.get("addBlockedBy"), kw.get("removeBlockedBy")),
    "task_list": lambda **kw: TASKS.list_all(),
    "task_get": lambda **kw: TASKS.get(kw["task_id"]),
    "task_bind_worktree": lambda **kw: WORKTREES.bind_task(kw["task_id"], kw["worktree"], kw.get("owner", "")),
    "background_run": lambda **kw: BG.run(kw["command"]),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
    "spawn_teammate": lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates": lambda **kw: TEAM.list_all(),
    "send_message": lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox": lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2),
    "broadcast": lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request": lambda **kw: handle_shutdown_request(BUS, kw["teammate"]),
    "shutdown_response": lambda **kw: check_shutdown_status(kw.get("request_id", "")),
    "plan_approval": lambda **kw: handle_plan_review(BUS, kw["request_id"], kw["approve"], kw.get("feedback", "")),
    "idle": lambda **kw: "Lead does not idle.",
    "claim_task": lambda **kw: _claim_for_lead(kw["task_id"]),
    "worktree_create": lambda **kw: WORKTREES.create(kw["name"], kw.get("task_id"), kw.get("base_ref", "HEAD")),
    "worktree_list": lambda **kw: WORKTREES.list_all(),
    "worktree_status": lambda **kw: WORKTREES.status(kw["name"]),
    "worktree_run": lambda **kw: WORKTREES.run(kw["name"], kw["command"]),
    "worktree_keep": lambda **kw: WORKTREES.keep(kw["name"]),
    "worktree_remove": lambda **kw: WORKTREES.remove(kw["name"], kw.get("force", False), kw.get("complete_task", False)),
    "worktree_events": lambda **kw: WORKTREE_EVENTS.list_recent(kw.get("limit", 20)),
}

CHILD_TOOLS = [
    {"name": "bash", "description": "Run a shell command.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "todo", "description": "Update task list. Track progress on multi-step tasks.", "input_schema": {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["id", "text", "status"]}}}, "required": ["items"]}},
    {"name": "load_skill", "description": "Load specialized knowledge by name.", "input_schema": {"type": "object", "properties": {"name": {"type": "string", "description": "Skill name to load"}}, "required": ["name"]}},
]

PARENT_TOOLS = CHILD_TOOLS + [
    {"name": "wait", "description": "Wait for teammates/task progress without intervening, then return a short status summary.", "input_schema": {"type": "object", "properties": {"seconds": {"type": "integer", "description": "How long to wait in seconds (1-30). Default 5."}}}},
    {"name": "task", "description": "Spawn s subagent with fresh context", "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
    {"name": "compact", "description": "Trigger manual conversation compression.", "input_schema": {"type": "object", "properties": {"focus": {"type": "string", "description": "What to preserve in the summary"}}}},
    {"name": "task_create", "description": "Create a new task.", "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "description": {"type": "string"}}, "required": ["subject"]}},
    {"name": "task_update", "description": "Update a task's status or dependencies.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}, "addBlockedBy": {"type": "array", "items": {"type": "integer"}}, "removeBlockedBy": {"type": "array", "items": {"type": "integer"}}}, "required": ["task_id"]}},
    {"name": "task_list", "description": "List all tasks with status summary.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "task_get", "description": "Get full details of a task by ID.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
    {"name": "task_bind_worktree", "description": "Bind a task to an existing worktree.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}, "worktree": {"type": "string"}, "owner": {"type": "string"}}, "required": ["task_id", "worktree"]}},
    {"name": "background_run", "description": "Run command in background thread. Returns task_id immediately.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "check_background", "description": "Check background task status. Omit task_id to list all.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}}},
    {"name": "spawn_teammate", "description": "Spawn a persistent teammate that runs in its own thread.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["name", "role", "prompt"]}},
    {"name": "list_teammates", "description": "List all teammates with name, role, status.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "send_message", "description": "Send a message to a teammate's inbox.", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": ["message", "broadcast", "shutdown_request", "shutdown_response", "plan_approval_response"]}}, "required": ["to", "content"]}},
    {"name": "read_inbox", "description": "Read and drain the lead's inbox.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "broadcast", "description": "Send a message to all teammates.", "input_schema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}},
    {"name": "shutdown_request", "description": "Request a teammate to shut down gracefully. Returns a request_id for tracking.", "input_schema": {"type": "object", "properties": {"teammate": {"type": "string"}}, "required": ["teammate"]}},
    {"name": "shutdown_response", "description": "Check the status of a shutdown request by request_id.", "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}}, "required": ["request_id"]}},
    {"name": "plan_approval", "description": "Approve or reject a teammate's plan. Provide request_id + approve + optional feedback.", "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "feedback": {"type": "string"}}, "required": ["request_id", "approve"]}},
    {"name": "idle", "description": "Enter idle state (for lead -- rarely used).", "input_schema": {"type": "object", "properties": {}}},
    {"name": "claim_task", "description": "Claim a task from the board by ID.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
    {"name": "worktree_create", "description": "Create a git worktree, optionally bind it to a task.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "task_id": {"type": "integer"}, "base_ref": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_list", "description": "List all tracked worktrees.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "worktree_status", "description": "Get worktree metadata by name.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_run", "description": "Run a shell command inside a worktree directory.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "command": {"type": "string"}}, "required": ["name", "command"]}},
    {"name": "worktree_keep", "description": "Keep a worktree for later reuse.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "worktree_remove", "description": "Remove a worktree and optionally complete its bound task.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "force": {"type": "boolean"}, "complete_task": {"type": "boolean"}}, "required": ["name"]}},
    {"name": "worktree_events", "description": "Show recent worktree lifecycle events.", "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
]


def subagent(prompt: str) -> str:
    sub_messages = [{"role": "user", "content": prompt}]
    used_todo = False
    rounds_since_todo = 0
    response = None
    for _ in range(30):
        response = CLIENT.messages.create(model=MODEL, system=SUBAGENT_SYSTEM, messages=sub_messages, tools=CHILD_TOOLS, max_tokens=8000)
        sub_messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "todo":
                    used_todo = True
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)[:50000]})
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            results.append({"type": "text", "text": "<reminder>Update your todos.</reminder>"})
        sub_messages.append({"role": "user", "content": results})
    if not response:
        return "no summary"
    return "".join(b.text for b in response.content if hasattr(b, "text")) or "no summary"


def agent_loop(messages: list):
    state = TurnCancellation()
    listener = EscListener(state)
    set_input_bar_state("busy")
    print_input_footer()

    def work():
        rounds_since_todo = 0
        while True:
            micro_compact(messages)
            notifs = BG.drain_notifications()
            inbox = BUS.read_inbox("lead")
            if inbox:
                messages.append({"role": "user", "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>"})
            if notifs and messages:
                notif_text = "\n".join(f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs)
                messages.append({"role": "user", "content": f"<background-results>\n{notif_text}\n</background-results>"})
            if estimate_tokens(messages) > THRESHOLD:
                print_status("auto-compact triggered", style="yellow")
                messages[:] = auto_compact(messages, CLIENT)
            stream_result = create_streamed_response(messages, is_cancelled=state.is_cancelled)
            response = handle_stream_result(stream_result)
            if stream_result.get("cancelled"):
                return
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                return
            results = []
            used_todo = False
            manual_compact = False
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "todo":
                        used_todo = True
                    if block.name == "compact":
                        manual_compact = True
                        output = "Compressing..."
                    elif block.name == "task":
                        prompt = block.input.get("prompt", "")
                        print_tool_result("task", prompt[:80], actor="lead")
                        output = subagent(prompt)
                    else:
                        try:
                            output = run_lead_tool(block.name, block.input, is_cancelled=state.is_cancelled)
                        except Exception as e:
                            output = f"Error: {e}"
                    print_tool_result(block.name, clip_tool_output(str(output)), actor="lead")
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
            rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
            if rounds_since_todo >= 3:
                results.append({"type": "text", "text": "<reminder>Update your todos.</reminder>"})
            messages.append({"role": "user", "content": results})
            if manual_compact:
                print_status("manual-compact triggered", style="yellow")
                messages[:] = auto_compact(messages, CLIENT)
                return

    try:
        run_with_turn_cancellation(state, listener, work)
    finally:
        set_input_bar_state("idle")


def main():
    history = []
    print_overview(TEAM.list_all(), TASKS.list_all(), WORKTREES.list_all())
    while True:
        try:
            query = input_prompt("xiaoman")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            print_tool_result("list_teammates", TEAM.list_all(), actor="lead")
            continue
        if query.strip() == "/inbox":
            print_tool_result("read_inbox", json.dumps(BUS.read_inbox("lead"), indent=2), actor="lead")
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        if should_render_main_history_tail():
            response_content = history[-1]["content"]
            if isinstance(response_content, list):
                for block in response_content:
                    if hasattr(block, "text"):
                        print_text_response(block.text)
