import json
import re
import threading
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


console = Console()
_console_state_lock = threading.Lock()
_input_active = False
_pending_console_messages: list[Any] = []
_input_bar_state = "idle"
STRUCTURED_TOOL_NAMES = {
    "task_list",
    "list_teammates",
    "todo",
    "worktree_list",
    "read_inbox",
    "task_get",
    "worktree_status",
    "worktree_events",
    "shutdown_response",
}


def render_to_text(renderable: Any, width: int = 100) -> str:
    capture_console = Console(record=True, width=width)
    capture_console.print(renderable)
    return capture_console.export_text()


def render_tool_window_text(lines: list[str], max_lines: int = 12) -> str:
    recent = lines[-max_lines:]
    return "\n".join(recent)


def _format_event_summary(output: Any, max_lines: int = 2, max_chars: int = 160) -> str:
    clipped = render_tool_window_text(str(output).splitlines(), max_lines=max_lines)
    clipped = " | ".join(part.strip() for part in clipped.splitlines() if part.strip())
    return (clipped or "(no output)")[:max_chars]


def _format_tool_label(tool_name: str, actor: str | None = None) -> str:
    labels = {
        "bash": "Bash",
        "read_file": "ReadFile",
        "write_file": "WriteFile",
        "edit_file": "EditFile",
        "read_inbox": "ReadInbox",
    }
    label = labels.get(tool_name, tool_name)
    return f"{actor + ' · ' if actor else ''}{label}"


def set_input_bar_state(state: str):
    global _input_bar_state
    _input_bar_state = state if state in {"idle", "busy"} else "idle"


def get_input_hint_text() -> str:
    if _input_bar_state == "busy":
        return "esc 可中断"
    return "? 查看快捷命令"


def get_input_prompt_text() -> str:
    return "> "


def build_input_footer_renderable():
    divider = Text("─" * 40, style="dim")
    hint = Text(get_input_hint_text(), style="dim")
    return Group(divider, hint)


def print_input_footer():
    flush_pending_console_messages()
    console.print(build_input_footer_renderable())


def set_input_active(active: bool):
    global _input_active
    with _console_state_lock:
        _input_active = active


def get_pending_console_message_count() -> int:
    with _console_state_lock:
        return len(_pending_console_messages)


def flush_pending_console_messages() -> int:
    with _console_state_lock:
        if _input_active or not _pending_console_messages:
            return 0
        pending = list(_pending_console_messages)
        _pending_console_messages.clear()
    for message in pending:
        console.print(message)
    return len(pending)


def _emit_console_message(message: Any) -> bool:
    with _console_state_lock:
        if _input_active:
            _pending_console_messages.append(message)
            return False
    console.print(message)
    return True


def _shorten_path(path: str) -> str:
    marker = ".worktrees/"
    if marker in path:
        return path[path.index(marker) :]
    return path


def _build_task_table(output: str, active_only: bool = False, max_items: int | None = None) -> Table:
    table = Table(title="Tasks", show_lines=False)
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("ID", style="magenta")
    table.add_column("Subject", style="white")
    table.add_column("Meta", style="yellow")
    rows = 0
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(\[[^\]]+\])\s+(\d+):\s+(.*)$", line)
        if not m:
            table.add_row("?", "", line, "")
            continue
        status, task_id, rest = m.groups()
        if active_only and status not in {"[ ]", "[>]"}:
            continue
        subject = rest
        meta_parts = []
        for token in (" owner=", " wt="):
            idx = subject.find(token)
            if idx != -1:
                meta_parts.append(subject[idx + 1 :].strip())
                subject = subject[:idx].rstrip()
        blocked = re.search(r"(\(blocked by .*\))", subject)
        if blocked:
            meta_parts.insert(0, blocked.group(1))
            subject = subject.replace(blocked.group(1), "").strip()
        table.add_row(status, task_id, subject, " | ".join(meta_parts))
        rows += 1
        if max_items and rows >= max_items:
            break
    return table


def _build_teammate_table(output: str, active_only: bool = False, max_items: int | None = None) -> Table:
    table = Table(title="Teammates")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Task", style="magenta")
    table.add_column("Worktree", style="yellow")
    rows = 0
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^([^:]+):([^\s]+)\s*(.*)$", line)
        if not m:
            table.add_row(line, "", "", "")
            continue
        name, status, extra = m.groups()
        if active_only and status not in {"idle", "working"}:
            continue
        task = ""
        worktree = ""
        for part in extra.split():
            if part.startswith("task="):
                task = part.split("=", 1)[1]
            elif part.startswith("wt="):
                worktree = part.split("=", 1)[1]
        table.add_row(name, status, task, worktree)
        rows += 1
        if max_items and rows >= max_items:
            break
    return table


def _build_todo_table(output: str) -> Table:
    table = Table(title="Todo")
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("ID", style="magenta")
    table.add_column("Task", style="white")
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("("):
            continue
        m = re.match(r"^(\[[^\]]+\])\s+#([^:]+):\s+(.*)$", line)
        if not m:
            continue
        status, item_id, text = m.groups()
        table.add_row(status, item_id, text)
    return table


def _build_worktree_table(output: str, active_only: bool = False, max_items: int | None = None):
    try:
        data = json.loads(output)
    except Exception:
        return Panel(output, title="Worktrees", border_style="blue")
    items = data.get("worktrees") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return Panel(output, title="Worktrees", border_style="blue")
    table = Table(title="Worktrees")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Task", style="magenta")
    table.add_column("Branch", style="yellow")
    table.add_column("Path", style="white")
    rows = 0
    for item in items:
        status = str(item.get("status", ""))
        if active_only and status not in {"active", "kept"}:
            continue
        table.add_row(
            str(item.get("name", "")),
            status,
            str(item.get("task_id", "")),
            str(item.get("branch", "")),
            _shorten_path(str(item.get("path", ""))),
        )
        rows += 1
        if max_items and rows >= max_items:
            break
    return table


def build_overview_renderable(
    team_output: str,
    task_output: str,
    worktree_output: str,
    compact: bool = False,
    max_items: int = 8,
):
    return Panel(
        Group(
            _build_teammate_table(team_output, active_only=compact, max_items=max_items),
            _build_task_table(task_output, active_only=compact, max_items=max_items),
            _build_worktree_table(worktree_output, active_only=compact, max_items=max_items),
        ),
        title="Workspace Overview",
        border_style="cyan",
    )


def _build_json_panel(title: str, output: str):
    try:
        normalized = json.dumps(json.loads(output), indent=2, ensure_ascii=False)
    except Exception:
        normalized = output
    return Panel(Syntax(normalized, "json", word_wrap=True), title=title, border_style="blue")


def build_structured_tool_renderable(tool_name: str, output: Any, actor: str | None = None):
    text = str(output)
    if tool_name == "task_list":
        return _build_task_table(text)
    if tool_name == "list_teammates":
        return _build_teammate_table(text)
    if tool_name == "todo":
        return _build_todo_table(text)
    if tool_name == "worktree_list":
        return _build_worktree_table(text)
    return _build_json_panel(tool_name, text)


def format_tool_event_lines(tool_name: str, output: Any, actor: str | None = None) -> list[Text]:
    title = _format_tool_label(tool_name, actor=actor)
    summary = _format_event_summary(output)
    status_style = "red" if str(output).startswith("Error") else "green"
    return [
        Text.assemble(("• ", "cyan"), (title, "bold white")),
        Text.assemble(("  └ ", "dim"), (summary, status_style)),
    ]


def build_tool_renderable(tool_name: str, output: Any, actor: str | None = None):
    if tool_name in STRUCTURED_TOOL_NAMES:
        return build_structured_tool_renderable(tool_name, output, actor=actor)
    return Group(*format_tool_event_lines(tool_name, output, actor=actor))


def build_tool_window_renderable(tool_name: str, output: Any, actor: str | None = None, max_lines: int = 12, max_chars: int = 1200):
    text = str(output)
    clipped = text[-max_chars:]
    clipped = render_tool_window_text(clipped.splitlines(), max_lines=max_lines)
    title = f"{actor + ' · ' if actor else ''}{tool_name}"
    border = "red" if text.startswith("Error") else "green"
    return Panel(clipped or "(no output)", title=title, border_style=border)


def print_tool_result(tool_name: str, output: Any, actor: str | None = None):
    flush_pending_console_messages()
    if tool_name in STRUCTURED_TOOL_NAMES:
        console.print(build_structured_tool_renderable(tool_name, output, actor=actor))
        return
    for line in format_tool_event_lines(tool_name, output, actor=actor):
        console.print(line)


def format_teammate_event_line(name: str, tool_name: str, output: Any, max_lines: int = 2, max_chars: int = 160) -> Text:
    clipped = _format_event_summary(output, max_lines=max_lines, max_chars=max_chars)
    return Text.assemble(
        ("• ", "cyan"),
        (name, "bold cyan"),
        (" · ", "dim"),
        (tool_name, "bold yellow"),
        (" -> ", "dim"),
        (clipped, "red" if str(output).startswith("Error") else "white"),
    )


def emit_teammate_event(name: str, tool_name: str, output: Any) -> bool:
    return _emit_console_message(format_teammate_event_line(name, tool_name, output))


def build_assistant_text_renderable(text: str):
    normalized = (text or "").strip()
    return Markdown(normalized or " ")


def build_assistant_renderable(text: str):
    return build_assistant_text_renderable(text)


def print_text_response(text: str):
    if not (text or "").strip():
        return
    flush_pending_console_messages()
    console.print(build_assistant_text_renderable(text))


def print_status(message: str, style: str = "blue"):
    flush_pending_console_messages()
    console.print(Text(message, style=style))


def print_overview(team_output: str, task_output: str, worktree_output: str):
    flush_pending_console_messages()
    console.print(build_overview_renderable(team_output, task_output, worktree_output, compact=True, max_items=8))


def live_wait(
    seconds: int,
    *,
    get_team,
    get_tasks,
    get_worktrees,
    sleep_fn,
    is_cancelled=lambda: False,
):
    duration = max(0, int(seconds))
    flush_pending_console_messages()
    console.print(Text("waiting...", style="dim"))
    for _ in range(duration * 10):
        if is_cancelled():
            return "Wait cancelled."
        sleep_fn(0.1)
    if is_cancelled():
        return "Wait cancelled."
    return f"Waited {duration}s."


def input_prompt(label: str = "xiaoman") -> str:
    flush_pending_console_messages()
    console.print(build_input_footer_renderable())
    set_input_active(True)
    try:
        return console.input("[bold cyan]> [/]")
    finally:
        set_input_active(False)
        flush_pending_console_messages()
