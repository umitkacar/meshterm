"""Unit tests for meshterm.jsonl_history — Claude Code conversation reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meshterm.jsonl_history import JsonlHistory, ToolCall, ThinkingBlock, Message


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Write a list of dict entries as JSONL (one JSON object per line)."""
    with path.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


@pytest.fixture
def simple_jsonl(tmp_path: Path) -> Path:
    """A small fixture JSONL with user + assistant messages, tool_use, thinking."""
    p = tmp_path / "session.jsonl"
    entries = [
        {"type": "system", "content": "Session start"},
        {
            "type": "user",
            "message": {
                "content": [{"type": "text", "text": "Run pytest and tell me the result"}],
            },
            "timestamp": "2026-04-12T20:00:00Z",
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "I should use Bash to run pytest..."},
                    {"type": "text", "text": "Running pytest now."},
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "Bash",
                        "input": {"command": "pytest tests/ -q"},
                    },
                ],
            },
            "timestamp": "2026-04-12T20:00:05Z",
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "content": "157 passed",
                        "is_error": False,
                    }
                ],
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "157 tests passed."},
                    {
                        "type": "tool_use",
                        "id": "call_2",
                        "name": "Read",
                        "input": {"file_path": "/tmp/log.txt"},
                    },
                ]
            },
        },
        {"type": "attachment", "content": "file contents"},
    ]
    _write_jsonl(p, entries)
    return p


@pytest.fixture
def malformed_jsonl(tmp_path: Path) -> Path:
    """Fixture with some malformed lines to verify graceful skipping."""
    p = tmp_path / "malformed.jsonl"
    with p.open("w") as f:
        f.write('{"type": "user", "message": {"content": "hi"}}\n')
        f.write('{ this is not valid json\n')  # malformed
        f.write('\n')  # blank line
        f.write('{"type": "assistant", "message": {"content": []}}\n')
    return p


# ── Basic loading ─────────────────────────────────────────────────────────────


class TestLoading:
    def test_load_from_path(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        assert len(h) == 6

    def test_load_raises_if_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            JsonlHistory(tmp_path / "does-not-exist.jsonl")

    def test_malformed_lines_skipped(self, malformed_jsonl: Path):
        h = JsonlHistory(malformed_jsonl)
        # 4 lines, 1 malformed + 1 blank → 2 valid
        assert len(h) == 2

    def test_iter(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        types = [e.get("type") for e in h]
        assert types == ["system", "user", "assistant", "user", "assistant", "attachment"]


# ── type_counts and tool_call_counts ──────────────────────────────────────────


class TestCounts:
    def test_type_counts(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        counts = h.type_counts()
        assert counts == {
            "system": 1,
            "user": 2,
            "assistant": 2,
            "attachment": 1,
        }

    def test_tool_call_counts(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        tc = h.tool_call_counts()
        assert tc == {"Bash": 1, "Read": 1}


# ── tool_calls extraction ─────────────────────────────────────────────────────


class TestToolCalls:
    def test_all_tool_calls(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        calls = h.tool_calls()
        assert len(calls) == 2
        assert all(isinstance(c, ToolCall) for c in calls)

    def test_filter_by_name(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        bash_calls = h.tool_calls(name="Bash")
        assert len(bash_calls) == 1
        assert bash_calls[0].name == "Bash"
        assert bash_calls[0].arguments["command"] == "pytest tests/ -q"

    def test_tool_call_arg_helper(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        tc = h.tool_calls(name="Bash")[0]
        assert tc.arg("command") == "pytest tests/ -q"
        assert tc.arg("missing", "default") == "default"

    def test_tool_call_result_pairing(self, simple_jsonl: Path):
        """call_1 has tool_result, call_2 does not."""
        h = JsonlHistory(simple_jsonl)
        calls = h.tool_calls()
        bash = next(c for c in calls if c.name == "Bash")
        read = next(c for c in calls if c.name == "Read")
        assert bash.result == "157 passed"
        assert bash.is_error is False
        assert read.result is None  # no pairing

    def test_filter_nonexistent_name(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        assert h.tool_calls(name="DoesNotExist") == []


# ── thinking_blocks ───────────────────────────────────────────────────────────


class TestThinking:
    def test_extract_thinking(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        thinks = h.thinking_blocks()
        assert len(thinks) == 1
        assert isinstance(thinks[0], ThinkingBlock)
        assert "I should use Bash" in thinks[0].text

    def test_thinking_preview(self):
        tb = ThinkingBlock(text="a" * 200)
        assert len(tb.preview) <= 123  # 120 + "..."
        assert tb.preview.endswith("...")

    def test_thinking_preview_short(self):
        tb = ThinkingBlock(text="short")
        assert tb.preview == "short"


# ── Messages (structured user/assistant) ─────────────────────────────────────


class TestMessages:
    def test_user_messages(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        # Only user messages with non-empty content (tool_result excluded since it has no text)
        users = h.user_messages()
        assert len(users) == 1
        assert "Run pytest" in users[0].content

    def test_assistant_messages(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        assts = h.assistant_messages()
        assert len(assts) == 2
        assert assts[0].role == "assistant"
        # First assistant message has both text and thinking and tool_use
        assert len(assts[0].tool_calls) == 1
        assert len(assts[0].thinking) == 1


# ── summary / print_summary ──────────────────────────────────────────────────


class TestSummary:
    def test_summary_keys(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        s = h.summary()
        expected_keys = {
            "path",
            "size_bytes",
            "total_entries",
            "type_counts",
            "tool_call_counts",
            "user_message_count",
            "assistant_message_count",
            "thinking_block_count",
            "first_user_message",
            "last_assistant_message",
        }
        assert expected_keys.issubset(s.keys())

    def test_summary_values(self, simple_jsonl: Path):
        h = JsonlHistory(simple_jsonl)
        s = h.summary()
        assert s["total_entries"] == 6
        assert s["tool_call_counts"] == {"Bash": 1, "Read": 1}
        assert s["thinking_block_count"] == 1

    def test_print_summary_no_raise(self, simple_jsonl: Path, capsys):
        h = JsonlHistory(simple_jsonl)
        h.print_summary()
        out = capsys.readouterr().out
        assert "JSONL:" in out
        assert "Tool calls:" in out


# ── list_sessions (filesystem scan) ───────────────────────────────────────────


class TestListSessions:
    def test_list_sessions_empty(self, tmp_path: Path):
        # No JSONL files in tmp_path
        result = JsonlHistory.list_sessions(projects_dir=tmp_path)
        assert result == []

    def test_list_sessions_sorted_by_size(self, tmp_path: Path):
        big = tmp_path / "big.jsonl"
        small = tmp_path / "small.jsonl"
        big.write_text('{"type":"user"}\n' * 100)
        small.write_text('{"type":"user"}\n')
        result = JsonlHistory.list_sessions(projects_dir=tmp_path)
        assert len(result) == 2
        assert result[0][2] > result[1][2]  # biggest first

    def test_from_uuid_raises_when_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            JsonlHistory.from_uuid("nonexistent-uuid", projects_dir=tmp_path)
