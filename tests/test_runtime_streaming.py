from types import SimpleNamespace
import json

import xiaoman_agent.runtime as runtime_mod
from xiaoman_agent.cancel import TurnCancellation
from xiaoman_agent.runtime import (
    clip_tool_output,
    collect_stream_text,
    sanitize_messages_for_api,
    should_render_main_history_tail,
    should_print_final_stream_text,
    should_refresh_stream_view,
)
from xiaoman_agent.ui import STRUCTURED_TOOL_NAMES, get_input_hint_text, set_input_bar_state


class FakeTextEvent:
    type = "content_block_delta"
    delta = SimpleNamespace(text="hello")


class FakeTextEvent2:
    type = "content_block_delta"
    delta = SimpleNamespace(text=" world")


class FakeIgnoreEvent:
    type = "message_start"


def test_collect_stream_text_combines_text_deltas():
    result = collect_stream_text([FakeTextEvent(), FakeIgnoreEvent(), FakeTextEvent2()])
    assert result == "hello world"


def test_clip_tool_output_keeps_recent_tail():
    text = "\n".join(f"line {i}" for i in range(30))
    clipped = clip_tool_output(text, max_lines=6, max_chars=80)
    assert "line 0" not in clipped
    assert "line 29" in clipped


def test_should_print_final_stream_text_skips_duplicate_after_live_render():
    assert should_print_final_stream_text("hello", stream_rendered=True) is False
    assert should_print_final_stream_text("hello", stream_rendered=False) is True
    assert should_print_final_stream_text("   ", stream_rendered=False) is False


def test_should_refresh_stream_view_throttles_small_chunks():
    assert should_refresh_stream_view("", "你好", 0) is False
    assert should_refresh_stream_view("你好。", "", 0) is True
    assert should_refresh_stream_view("第一行\n", "", 0) is True
    assert should_refresh_stream_view("1234567890123456789012345", "", 0, min_chars=20) is True


def test_main_should_not_render_history_tail_again():
    assert should_render_main_history_tail() is False


def test_sanitize_messages_for_api_removes_surrogates():
    messages = [{"role": "user", "content": "bad-\udce2-text"}]
    cleaned = sanitize_messages_for_api(messages)
    dumped = json.dumps(cleaned, ensure_ascii=False)
    assert "\\udce2" not in dumped
    assert cleaned[0]["content"].startswith("bad-")


def test_bash_is_not_classified_as_structured_output():
    assert "bash" not in STRUCTURED_TOOL_NAMES


def test_task_list_remains_structured_output():
    assert "task_list" in STRUCTURED_TOOL_NAMES


def test_input_bar_state_defaults_back_to_idle_after_manual_reset():
    set_input_bar_state("busy")
    assert get_input_hint_text() == "esc 可中断"
    set_input_bar_state("idle")
    assert get_input_hint_text() == "? 查看快捷命令"


def test_turn_cancellation_starts_not_cancelled():
    state = TurnCancellation()
    assert state.is_cancelled() is False


def test_turn_cancellation_can_cancel_and_reset():
    state = TurnCancellation()
    state.cancel()
    assert state.is_cancelled() is True
    state.reset()
    assert state.is_cancelled() is False


def test_stream_result_marks_cancellation():
    result = runtime_mod.make_stream_result("partial", cancelled=True, response=None, events=[])
    assert result["text"] == "partial"
    assert result["cancelled"] is True


def test_stream_result_defaults_to_not_cancelled():
    result = runtime_mod.make_stream_result("done", cancelled=False, response=None, events=[])
    assert result["text"] == "done"
    assert result["cancelled"] is False


def test_create_streamed_response_stops_when_cancelled(monkeypatch):
    class FakeLive:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, *_args, **_kwargs):
            return None

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="hello"),
            )
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text=" world"),
            )

        def get_final_message(self):
            return "final-response"

    monkeypatch.setattr("xiaoman_agent.runtime.Live", lambda *args, **kwargs: FakeLive())
    monkeypatch.setattr("xiaoman_agent.runtime.CLIENT.messages.stream", lambda **_: FakeStream())

    calls = {"count": 0}

    def is_cancelled():
        calls["count"] += 1
        return calls["count"] >= 2

    result = runtime_mod.create_streamed_response([], is_cancelled=is_cancelled)

    assert result["cancelled"] is True
    assert result["text"] == "hello"


def test_create_streamed_response_returns_complete_result_when_not_cancelled(monkeypatch):
    class FakeLive:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, *_args, **_kwargs):
            return None

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text="hello"),
            )
            yield SimpleNamespace(
                type="content_block_delta",
                delta=SimpleNamespace(text=" world"),
            )

        def get_final_message(self):
            return "final-response"

    monkeypatch.setattr("xiaoman_agent.runtime.Live", lambda *args, **kwargs: FakeLive())
    monkeypatch.setattr("xiaoman_agent.runtime.CLIENT.messages.stream", lambda **_: FakeStream())

    result = runtime_mod.create_streamed_response([], is_cancelled=lambda: False)

    assert result["cancelled"] is False
    assert result["text"] == "hello world"


class DummyListener:
    def __init__(self, state):
        self.state = state
        self.started = 0
        self.stopped = 0
        self.active = True

    def start(self):
        self.started += 1
        return True

    def stop(self):
        self.stopped += 1


def test_run_turn_starts_and_stops_listener():
    state = TurnCancellation()
    listener = DummyListener(state)
    calls = []

    def work():
        calls.append("work")
        return "done"

    result = runtime_mod.run_with_turn_cancellation(state, listener, work)

    assert result == "done"
    assert listener.started == 1
    assert listener.stopped == 1
    assert state.is_cancelled() is False


def test_run_turn_resets_cancellation_before_work():
    state = TurnCancellation()
    state.cancel()
    listener = DummyListener(state)

    def work():
        return state.is_cancelled()

    result = runtime_mod.run_with_turn_cancellation(state, listener, work)

    assert result is False


def test_stream_cancel_message_is_printed_without_duplicate_body(monkeypatch):
    printed = []
    monkeypatch.setattr("xiaoman_agent.runtime.print_status", lambda message, style="dim": printed.append((message, style)))

    result = {
        "response": None,
        "text": "partial",
        "events": [],
        "cancelled": True,
        "stream_rendered": True,
    }

    runtime_mod.handle_stream_result(result)

    assert ("response cancelled.", "dim") in printed


def test_wait_cancelled_summary_is_short():
    assert "Team:" not in "Wait cancelled."
