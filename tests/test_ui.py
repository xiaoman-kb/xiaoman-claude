from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from xiaoman_agent.cancel import TurnCancellation
from xiaoman_agent.ui import (
    build_assistant_text_renderable,
    build_input_footer_renderable,
    build_overview_renderable,
    build_structured_tool_renderable,
    build_tool_renderable,
    emit_teammate_event,
    flush_pending_console_messages,
    format_teammate_event_line,
    format_tool_event_lines,
    get_input_hint_text,
    get_input_prompt_text,
    get_pending_console_message_count,
    set_input_bar_state,
    set_input_active,
    live_wait,
    render_to_text,
)


def test_list_teammates_renders_table_like_output():
    output = "alice:idle\nbob:working task=1 wt=task-1-bob"
    rendered = build_tool_renderable("list_teammates", output)
    text = render_to_text(rendered)
    assert "Teammates" in text
    assert "alice" in text
    assert "task-1-bob" in text


def test_task_list_renders_table_like_output():
    output = "[ ] 1: setup repo \n[>] 2: refactor auth (blocked by :[1]) owner=bob wt=task-2-bob"
    rendered = build_tool_renderable("task_list", output)
    text = render_to_text(rendered)
    assert "Tasks" in text
    assert "setup repo" in text
    assert "task-2-bob" in text


def test_plain_tool_output_falls_back_to_panel():
    rendered = build_tool_renderable("bash", "hello world")
    text = render_to_text(rendered)
    assert "Bash" in text
    assert "hello world" in text


def test_plain_tool_output_renders_as_event_lines():
    lines = format_tool_event_lines("bash", "Done", actor="lead")
    assert len(lines) == 2
    assert isinstance(lines[0], Text)
    assert "Bash" in lines[0].plain
    assert "Done" in lines[1].plain


def test_structured_tool_output_still_uses_table_rendering():
    rendered = build_structured_tool_renderable("task_list", "[ ] 1: setup repo")
    text = render_to_text(rendered)
    assert "Tasks" in text
    assert "setup repo" in text


def test_assistant_text_renderable_is_not_panel():
    renderable = build_assistant_text_renderable("Hello\n\nWorld")
    assert isinstance(renderable, Markdown)
    text = render_to_text(renderable)
    assert "Hello" in text
    assert "World" in text
    assert "Assistant" not in text


def test_assistant_text_renderable_uses_markdown_rendering():
    renderable = build_assistant_text_renderable("## 标题\n\n- 列表项\n\n**加粗**")
    assert isinstance(renderable, Markdown)
    text = render_to_text(renderable)
    assert "标题" in text
    assert "列表项" in text
    assert "加粗" in text


def test_input_prompt_text_is_minimal():
    assert get_input_prompt_text() == "> "


def test_idle_hint_text_matches_design():
    set_input_bar_state("idle")
    assert get_input_hint_text() == "? 查看快捷命令"


def test_busy_hint_text_matches_design():
    set_input_bar_state("busy")
    assert get_input_hint_text() == "esc 可中断"


def test_input_footer_renderable_contains_hint_text():
    set_input_bar_state("idle")
    renderable = build_input_footer_renderable()
    text = render_to_text(renderable)
    assert "? 查看快捷命令" in text


def test_invalid_input_bar_state_falls_back_to_idle_hint():
    set_input_bar_state("unexpected")
    assert get_input_hint_text() == "? 查看快捷命令"


def test_build_overview_renderable_contains_sections():
    rendered = build_overview_renderable(
        team_output="alice:idle",
        task_output="[ ] 1: setup repo",
        worktree_output="[]",
    )
    text = render_to_text(rendered)
    assert "Workspace Overview" in text
    assert "Teammates" in text
    assert "Tasks" in text
    assert "Worktrees" in text


def test_live_wait_returns_short_summary_without_workspace_dump():
    summary = live_wait(
        seconds=0,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
    )
    assert summary == "Waited 0s."


def test_live_wait_summary_no_longer_contains_workspace_sections():
    summary = live_wait(
        seconds=0,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
    )
    assert "Team:" not in summary
    assert "Tasks:" not in summary
    assert "Worktrees:" not in summary


def test_live_wait_returns_cancelled_when_flag_is_raised():
    state = TurnCancellation()

    def cancel_after_first_tick(_seconds):
        state.cancel()

    summary = live_wait(
        seconds=5,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=cancel_after_first_tick,
        is_cancelled=state.is_cancelled,
    )

    assert summary == "Wait cancelled."


def test_live_wait_returns_normal_summary_when_not_cancelled():
    summary = live_wait(
        seconds=1,
        get_team=lambda: "alice:idle",
        get_tasks=lambda: "[ ] 1: setup repo",
        get_worktrees=lambda: "[]",
        sleep_fn=lambda _seconds: None,
        is_cancelled=lambda: False,
    )

    assert summary == "Waited 1s."


def test_format_teammate_event_line_is_compact():
    line = format_teammate_event_line("bob", "bash", "line1\nline2\nline3")
    assert "bob" in line.plain
    assert "bash" in line.plain
    assert "line3" in line.plain
    assert "line1" not in line.plain
    assert "\n" not in line.plain


def test_emit_teammate_event_buffers_while_input_active(monkeypatch):
    printed = []
    monkeypatch.setattr("xiaoman_agent.ui.console.print", lambda message: printed.append(message))

    set_input_active(True)
    try:
        emit_teammate_event("bob", "bash", "hello")
        assert printed == []
        assert get_pending_console_message_count() == 1
    finally:
        set_input_active(False)
        flush_pending_console_messages()

    assert len(printed) == 1
    assert "bob" in printed[0].plain
    assert get_pending_console_message_count() == 0
