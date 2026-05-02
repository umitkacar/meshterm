"""libtmux-based session wrapper — PRIMARY backend (DECISION.md).

Direct libtmux API calls, no custom PTY, no Unix socket server.
This is the simple, proven approach: meshterm API → libtmux → tmux.

Maps iTerm2 Session API to libtmux Pane API:
  iTerm2 session.async_send_text() → libtmux pane.send_keys()
  iTerm2 session.get_screen_contents() → libtmux pane.capture_pane()
  iTerm2 session.session_id → meshterm UUID (mapped to pane.pane_id)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import libtmux


# ── Screen content (reused from session.py) ──

@dataclass
class ScreenLine:
    """One line of terminal screen content."""
    string: str
    hard_eol: bool = True


@dataclass
class ScreenContents:
    """Captured screen state — mirrors iTerm2 ScreenContents."""
    lines: list[ScreenLine] = field(default_factory=list)
    cursor_x: int = 0
    cursor_y: int = 0
    scrollback_lines: int = 0

    @property
    def number_of_lines(self) -> int:
        return len(self.lines)

    def line(self, index: int) -> ScreenLine:
        return self.lines[index]


# ── Key constants (from RAMAS, field-tested) ──

class Key:
    ENTER = "Enter"
    ESC = "Escape"
    CTRL_C = "C-c"
    TAB = "Tab"
    BACKSPACE = "BSpace"


# ── Timing (from RAMAS controller.py, calibrated) ──

@dataclass
class Delays:
    after_text: float = 1.0
    after_esc: float = 0.2
    after_ctrl_c: float = 0.1


class LibtmuxSession:
    """libtmux-based session — wraps a single tmux pane.

    This is the PRIMARY meshterm backend per DECISION.md.
    No custom PTY, no Unix socket server. Just libtmux.

    Usage:
        app = LibtmuxApp()
        session = app.create_session("worker-1")
        session.send_text("echo hello")
        session.send_key(Key.ENTER)
        screen = session.read_screen()
        print(screen.lines[0].string)
    """

    def __init__(self, pane: libtmux.Pane, session_uuid: str | None = None):
        self._pane = pane
        self._uuid = session_uuid or str(uuid.uuid4())
        self._delays = Delays()
        self._last_screen: list[str] | None = None

    # ── Factories (NEW in v0.2 — convenience lookups) ──

    @classmethod
    def from_name(cls, session_name: str, session_uuid: str | None = None) -> "LibtmuxSession":
        """Create a LibtmuxSession from a tmux session name.

        This is the natural entry point when you already know the session name
        (e.g. "forge") and don't want to walk the libtmux.Server tree manually.

        Raises RuntimeError if no session with that name exists.
        """
        server = libtmux.Server()
        matching = [s for s in server.sessions if s.name == session_name]
        if not matching:
            raise RuntimeError(
                f"No tmux session named '{session_name}'. "
                f"Available: {[s.name for s in server.sessions]}"
            )
        pane = matching[0].active_window.active_pane
        return cls(pane=pane, session_uuid=session_uuid)

    @classmethod
    def from_pane_id(cls, pane_id: str, session_uuid: str | None = None) -> "LibtmuxSession":
        """Create from a direct tmux pane id like '%3'."""
        server = libtmux.Server()
        for s in server.sessions:
            for w in s.windows:
                for p in w.panes:
                    if p.pane_id == pane_id:
                        return cls(pane=p, session_uuid=session_uuid)
        raise RuntimeError(f"Pane id '{pane_id}' not found")

    # ── Identity ──

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def pane_id(self) -> str:
        return self._pane.pane_id

    @property
    def name(self) -> str:
        return self._pane.pane_title or ""

    @property
    def current_command(self) -> str:
        return self._pane.pane_current_command or ""

    @property
    def pid(self) -> int:
        return int(self._pane.pane_pid or 0)

    @property
    def tty(self) -> str:
        return self._pane.pane_tty or ""

    @property
    def cwd(self) -> str:
        return self._pane.pane_current_path or ""

    # ── Text injection (Feature 1) ──

    def send_text(self, text: str, enter: bool = False) -> None:
        """Send text to terminal. Default: NO enter (safe).

        Mirrors: session.async_send_text(text)
        """
        self._pane.send_keys(text, enter=enter)

    # ── Key injection (Feature 2) ──

    def send_key(self, key: str) -> None:
        """Send special key. Use Key constants.

        Mirrors: session.async_send_text("\\r") etc.
        """
        self._pane.send_keys(key, enter=False)

    # ── Reliable send command (RAMAS pattern) ──

    def send_command(self, command: str, delay: float | None = None) -> None:
        """Send text + wait + Enter. The proven RAMAS pattern.

        Mirrors: text → sleep(1.0) → \\r
        """
        d = delay if delay is not None else self._delays.after_text
        self.send_text(command, enter=False)
        time.sleep(d)
        self.send_key(Key.ENTER)

    # ── Screen reading (Feature 3) ──

    def read_screen(self) -> ScreenContents:
        """Capture visible screen content.

        Mirrors: session.async_get_screen_contents()
        """
        raw_lines = self._pane.capture_pane()
        lines = [ScreenLine(string=line) for line in raw_lines]

        # Cursor position via display_message workaround
        try:
            cursor_info = self._pane.display_message(
                "#{cursor_x} #{cursor_y}", get_option=True
            )
            if cursor_info and " " in cursor_info:
                parts = cursor_info.split()
                cx, cy = int(parts[0]), int(parts[1])
            else:
                cx, cy = 0, 0
        except Exception:
            cx, cy = 0, 0

        self._last_screen = raw_lines
        return ScreenContents(
            lines=lines,
            cursor_x=cx,
            cursor_y=cy,
        )

    def read_screen_text(self) -> str:
        """Read screen as plain text string."""
        return "\n".join(self._pane.capture_pane())

    # ── Screen diffing (meshterm extra) ──

    def screen_diff(self) -> dict:
        """Compare current screen with last read.

        Returns dict with added_lines, removed_lines, is_idle.
        """
        current = self._pane.capture_pane()
        prev = self._last_screen or []
        self._last_screen = current

        added = [l for l in current if l not in prev]
        removed = [l for l in prev if l not in current]

        return {
            "added": added,
            "removed": removed,
            "is_idle": len(added) == 0 and len(removed) == 0,
            "lines_changed": len(added) + len(removed),
        }

    # ── wait_for pattern (meshterm extra) ──

    def wait_for(
        self,
        pattern: str,
        timeout: float = 30.0,
        interval: float = 0.5,
    ) -> str | None:
        """Wait until screen contains pattern. Returns matching line or None.

        Mirrors: no iTerm2 equivalent (meshterm innovation)
        """
        import re
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            lines = self._pane.capture_pane()
            for line in lines:
                if re.search(pattern, line):
                    return line
            time.sleep(interval)
        return None

    # ── Interrupt (RAMAS L3 pattern) ──

    def interrupt(self, message: str = "") -> None:
        """Send ESC to interrupt, optionally follow with message."""
        self.send_key(Key.ESC)
        time.sleep(self._delays.after_esc)
        if message:
            self.send_command(message)

    def emergency_stop(self) -> None:
        """Ctrl+C + ESC — kill process and clear input."""
        self.send_key(Key.CTRL_C)
        time.sleep(self._delays.after_ctrl_c)
        self.send_key(Key.ESC)
        time.sleep(self._delays.after_esc)

    # ── Session metadata (Feature 6) ──

    @property
    def metadata(self) -> dict:
        return {
            "uuid": self._uuid,
            "pane_id": self.pane_id,
            "name": self.name,
            "command": self.current_command,
            "pid": self.pid,
            "tty": self.tty,
            "cwd": self.cwd,
        }

    def set_name(self, name: str) -> None:
        """Set pane title."""
        self._pane.set_title(name)

    # ── Cleanup ──

    def close(self) -> None:
        """Kill this pane."""
        self._pane.kill()

    def __repr__(self) -> str:
        return f"LibtmuxSession(uuid={self._uuid[:8]}..., cmd={self.current_command})"


class LibtmuxApp:
    """libtmux-based app — manages tmux server and sessions.

    This is the PRIMARY meshterm backend per DECISION.md.

    Usage:
        app = LibtmuxApp()
        sessions = app.list_sessions()
        session = app.create_session("worker-1")
        found = app.get_session_by_uuid(uuid)
    """

    def __init__(self, server: libtmux.Server | None = None):
        self._server = server or libtmux.Server()
        self._uuid_map: dict[str, str] = {}  # uuid → pane_id

    @property
    def server(self) -> libtmux.Server:
        return self._server

    def create_session(
        self,
        name: str = "",
        command: str | None = None,
    ) -> LibtmuxSession:
        """Create a new tmux session with a pane.

        Mirrors: Window.async_create() + tab + session
        """
        session_name = name or f"meshterm-{int(time.time())}"
        tmux_session = self._server.new_session(
            session_name=session_name,
            window_name=name or "main",
        )
        pane = tmux_session.active_window.active_pane
        sess = LibtmuxSession(pane)

        # Track UUID mapping
        self._uuid_map[sess.uuid] = pane.pane_id

        if command:
            sess.send_command(command)

        return sess

    def list_sessions(self) -> list[LibtmuxSession]:
        """List all tmux panes as meshterm sessions.

        Mirrors: app.windows[].tabs[].sessions enumeration
        """
        sessions = []
        for tmux_session in self._server.sessions:
            for window in tmux_session.windows:
                for pane in window.panes:
                    # Check if we already have a UUID for this pane
                    existing_uuid = None
                    for uid, pid in self._uuid_map.items():
                        if pid == pane.pane_id:
                            existing_uuid = uid
                            break
                    sess = LibtmuxSession(pane, session_uuid=existing_uuid)
                    if existing_uuid is None:
                        self._uuid_map[sess.uuid] = pane.pane_id
                    sessions.append(sess)
        return sessions

    def get_session_by_uuid(self, uuid: str) -> LibtmuxSession | None:
        """Find session by UUID."""
        pane_id = self._uuid_map.get(uuid)
        if not pane_id:
            return None
        # Find the actual pane
        for tmux_session in self._server.sessions:
            for window in tmux_session.windows:
                for pane in window.panes:
                    if pane.pane_id == pane_id:
                        return LibtmuxSession(pane, session_uuid=uuid)
        return None

    def get_session_by_name(self, name: str) -> LibtmuxSession | None:
        """Find session by name (searches pane titles and session names)."""
        for tmux_session in self._server.sessions:
            if name.lower() in tmux_session.session_name.lower():
                pane = tmux_session.active_window.active_pane
                return LibtmuxSession(pane)
            for window in tmux_session.windows:
                for pane in window.panes:
                    title = pane.pane_title or ""
                    if name.lower() in title.lower():
                        return LibtmuxSession(pane)
        return None

    def close(self) -> None:
        """Kill all meshterm-created sessions."""
        for tmux_session in self._server.sessions:
            if tmux_session.session_name.startswith("meshterm-"):
                try:
                    tmux_session.kill()
                except Exception:
                    pass
