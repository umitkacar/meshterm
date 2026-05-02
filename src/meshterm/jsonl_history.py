"""
jsonl_history.py — Claude Code Conversation History Reader

The KILLER FEATURE that iTerm2 API doesn't have: semantic access to
Claude Code's internal conversation log (thinking tokens, tool calls with
arguments, subagent invocations, permission changes, etc.).

Each Claude Code session persists its entire conversation to:
    ~/.claude/projects/<PROJECT-SLUG>/<UUID>.jsonl

Each line is a JSON entry with one of these types:
    - user             : user prompt or tool result
    - assistant        : model response (text + thinking + tool_use blocks)
    - system           : system messages / reminders
    - attachment       : file contents read into context
    - file-history-snapshot : file state snapshots
    - permission-mode  : permission mode changes
    - queue-operation  : task queue operations

This module provides structured access to these semantic events.

Usage:
    from meshterm import JsonlHistory

    hist = JsonlHistory.from_uuid("d647c698-ffa4-424e-b5ef-d452a053ba8f")
    print(f"Total entries: {len(hist)}")
    print(f"Tool calls: {hist.tool_call_counts()}")
    for tc in hist.tool_calls(name="Bash"):
        print(tc.arguments.get("command", "")[:60])

    # Or attach to LibtmuxSession via UUID match
    from meshterm.libtmux_session import LibtmuxApp
    app = LibtmuxApp()
    pane = app.get_session_by_name("forge")
    if pane:
        hist = JsonlHistory.from_uuid(pane.uuid)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional


CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class ToolCall:
    """One tool invocation by Claude: name, arguments, optional result, timestamp."""

    name: str
    arguments: dict[str, Any]
    call_id: str = ""
    timestamp: Optional[str] = None
    result: Optional[str] = None
    is_error: bool = False

    def arg(self, key: str, default: Any = None) -> Any:
        return self.arguments.get(key, default)

    def __repr__(self) -> str:
        arg_preview = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(self.arguments.items())[:2])
        return f"ToolCall({self.name}, {arg_preview})"


@dataclass
class ThinkingBlock:
    """Extended thinking block (chain-of-thought)."""

    text: str
    timestamp: Optional[str] = None

    @property
    def preview(self) -> str:
        return self.text[:120] + ("..." if len(self.text) > 120 else "")


@dataclass
class Message:
    """User or assistant message with unified structure."""

    role: str  # "user" or "assistant"
    content: str = ""  # flat text for easy display
    raw_content: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    thinking: list[ThinkingBlock] = field(default_factory=list)
    timestamp: Optional[str] = None
    uuid: str = ""


class JsonlHistory:
    """Parsed Claude Code conversation history from a JSONL file."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"JSONL not found: {self.path}")
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # skip malformed lines

    # ----- factory helpers -----

    @classmethod
    def from_uuid(cls, session_uuid: str, projects_dir: Optional[Path] = None) -> "JsonlHistory":
        """Find JSONL by session UUID anywhere under ~/.claude/projects/."""
        root = projects_dir or CLAUDE_PROJECTS_DIR
        matches = list(root.rglob(f"{session_uuid}*.jsonl"))
        if not matches:
            raise FileNotFoundError(
                f"No JSONL for UUID {session_uuid} under {root}"
            )
        return cls(matches[0])

    @classmethod
    def list_sessions(cls, projects_dir: Optional[Path] = None) -> list[tuple[str, Path, int]]:
        """List all available sessions as (uuid, path, size_bytes) tuples."""
        root = projects_dir or CLAUDE_PROJECTS_DIR
        out: list[tuple[str, Path, int]] = []
        for p in root.rglob("*.jsonl"):
            uuid = p.stem
            try:
                out.append((uuid, p, p.stat().st_size))
            except OSError:
                pass
        out.sort(key=lambda x: -x[2])  # biggest first
        return out

    # ----- basic access -----

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.entries)

    def type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self.entries:
            t = e.get("type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    # ----- semantic extraction -----

    def tool_calls(self, name: Optional[str] = None) -> list[ToolCall]:
        """All tool calls, optionally filtered by name (e.g. 'Bash')."""
        out: list[ToolCall] = []
        # Build a map of tool_use_id → result (for pairing)
        results: dict[str, tuple[str, bool]] = {}
        for e in self.entries:
            if e.get("type") == "user":
                msg = e.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tid = block.get("tool_use_id", "")
                            rc = block.get("content", "")
                            if isinstance(rc, list):
                                rc = "\n".join(
                                    b.get("text", "") for b in rc if isinstance(b, dict)
                                )
                            results[tid] = (str(rc), bool(block.get("is_error", False)))

        # Now extract tool_use blocks and pair with results
        for e in self.entries:
            if e.get("type") != "assistant":
                continue
            msg = e.get("message", {})
            content = msg.get("content", [])
            ts = e.get("timestamp") or msg.get("timestamp")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tc_name = block.get("name", "")
                if name and tc_name != name:
                    continue
                tid = block.get("id", "")
                result_text, is_err = results.get(tid, (None, False))
                out.append(
                    ToolCall(
                        name=tc_name,
                        arguments=block.get("input", {}) or {},
                        call_id=tid,
                        timestamp=ts,
                        result=result_text,
                        is_error=is_err,
                    )
                )
        return out

    def tool_call_counts(self) -> dict[str, int]:
        """Count calls per tool name — quick summary."""
        counts: dict[str, int] = {}
        for tc in self.tool_calls():
            counts[tc.name] = counts.get(tc.name, 0) + 1
        return counts

    def thinking_blocks(self) -> list[ThinkingBlock]:
        """All extended-thinking blocks (chain-of-thought)."""
        out: list[ThinkingBlock] = []
        for e in self.entries:
            if e.get("type") != "assistant":
                continue
            msg = e.get("message", {})
            content = msg.get("content", [])
            ts = e.get("timestamp") or msg.get("timestamp")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    out.append(ThinkingBlock(text=block.get("thinking", ""), timestamp=ts))
        return out

    def user_messages(self) -> list[Message]:
        return [m for m in self._messages() if m.role == "user" and m.content]

    def assistant_messages(self) -> list[Message]:
        return [m for m in self._messages() if m.role == "assistant"]

    def _messages(self) -> list[Message]:
        out: list[Message] = []
        for e in self.entries:
            etype = e.get("type", "")
            if etype not in ("user", "assistant"):
                continue
            msg = e.get("message", {})
            raw = msg.get("content", [])
            blocks = raw if isinstance(raw, list) else [{"type": "text", "text": str(raw)}]
            text_parts: list[str] = []
            tcalls: list[ToolCall] = []
            thinks: list[ThinkingBlock] = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "thinking":
                    thinks.append(ThinkingBlock(text=block.get("thinking", "")))
                elif btype == "tool_use":
                    raw_input: Any = block.get("input", {}) or {}
                    tool_args: dict[str, Any] = (
                        raw_input if isinstance(raw_input, dict) else {}
                    )
                    tcalls.append(
                        ToolCall(
                            name=block.get("name", ""),
                            arguments=tool_args,
                            call_id=block.get("id", ""),
                        )
                    )
            out.append(
                Message(
                    role=etype,
                    content=" ".join(text_parts).strip(),
                    raw_content=blocks,
                    tool_calls=tcalls,
                    thinking=thinks,
                    timestamp=e.get("timestamp") or msg.get("timestamp"),
                    uuid=e.get("uuid", "") or msg.get("id", ""),
                )
            )
        return out

    # ----- summaries -----

    def summary(self) -> dict[str, Any]:
        """One-shot summary: counts, tool usage, first/last message."""
        msgs = self._messages()
        user_msgs = [m for m in msgs if m.role == "user" and m.content]
        asst_msgs = [m for m in msgs if m.role == "assistant"]
        return {
            "path": str(self.path),
            "size_bytes": self.path.stat().st_size,
            "total_entries": len(self.entries),
            "type_counts": self.type_counts(),
            "tool_call_counts": self.tool_call_counts(),
            "user_message_count": len(user_msgs),
            "assistant_message_count": len(asst_msgs),
            "thinking_block_count": len(self.thinking_blocks()),
            "first_user_message": user_msgs[0].content[:200] if user_msgs else None,
            "last_assistant_message": asst_msgs[-1].content[:200] if asst_msgs else None,
        }

    def print_summary(self) -> None:
        s = self.summary()
        print(f"JSONL: {s['path']}")
        print(f"  Size: {s['size_bytes']:,} bytes")
        print(f"  Entries: {s['total_entries']}")
        print(f"  Types: {s['type_counts']}")
        print(f"  Tool calls: {s['tool_call_counts']}")
        print(f"  Messages: {s['user_message_count']} user, {s['assistant_message_count']} assistant")
        print(f"  Thinking blocks: {s['thinking_block_count']}")
        if s['first_user_message']:
            print(f"  First user msg: {s['first_user_message'][:100]}")
        if s['last_assistant_message']:
            print(f"  Last assistant msg: {s['last_assistant_message'][:100]}")
