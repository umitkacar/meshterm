"""Session (pane) control -- mirrors iterm2.Session.

MeshTermSession is the workhorse: send text, read screen, manage the PTY.

Screen Reading Architecture
===========================

On Linux, there is no single "get screen contents" API like iTerm2 provides.
meshterm solves this with a layered approach inside the server process:

  Layer 1 - PTY Ring Buffer (primary, always available):
    The meshterm server owns the PTY master fd. All output flows through
    the server. We maintain a ring buffer of the last N lines of output
    (configurable, default 10,000 lines). This captures raw bytes before
    any terminal emulation.

  Layer 2 - Virtual Terminal State (VT parser):
    We run a headless VT100/xterm parser (based on vte or a pure-Python
    terminal state machine) that processes escape sequences and maintains
    the logical screen grid: rows x cols of characters with attributes.
    This is what get_screen_contents() returns -- the actual rendered
    screen as the user would see it.

  Layer 3 - Alternate Screen Buffer:
    Programs like vim, less, htop switch to the alternate screen buffer.
    The VT parser tracks this. get_screen_contents() returns whichever
    buffer is currently active. get_scrollback() returns the normal
    buffer's scrollback even when alternate screen is active.

Implementation options for the VT parser:
  a) pyte (pure Python, ~2000 LOC, MIT license) -- recommended for v1
  b) VTE widget (GTK, C library) -- if meshterm has a GUI
  c) Custom parser -- only if pyte proves insufficient

The server-side implementation lives in server.py. This module
(session.py) is the client-side proxy that issues RPC calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from meshterm.connection import Connection


# ── Screen content data structures ──

@dataclass
class ScreenLine:
    """A single line of screen content with optional attributes.

    Mirrors iterm2's ScreenContents.line() return value.

    Attributes:
        string: The text content of this line.
        hard_eol: True if this line ends with a real newline (not just
                  wrapping). Mirrors iTerm2's hard_eol property.
        line_number: 0-based line index from top of visible area.
    """
    string: str
    hard_eol: bool = True
    line_number: int = 0

    def __str__(self) -> str:
        return self.string


@dataclass
class ScreenContents:
    """Complete screen state for a session.

    Mirrors iterm2's ScreenContents object returned by
    session.async_get_screen_contents().

    Usage:
        contents = await session.async_get_screen_contents()
        for line in contents.lines:
            print(line.string)

        # Access by index
        first_line = contents.line(0)

        # Get cursor position
        print(f"Cursor at row={contents.cursor_row}, col={contents.cursor_col}")
    """
    lines: list[ScreenLine] = field(default_factory=list)
    cursor_row: int = 0
    cursor_col: int = 0
    rows: int = 24
    cols: int = 80
    alternate_screen_active: bool = False

    @property
    def number_of_lines(self) -> int:
        return len(self.lines)

    def line(self, index: int) -> ScreenLine:
        """Get a specific line by index.

        Mirrors: contents.line(i)
        """
        if 0 <= index < len(self.lines):
            return self.lines[index]
        return ScreenLine(string="", line_number=index)

    @property
    def text(self) -> str:
        """Full screen as a single string with newlines."""
        return "\n".join(line.string for line in self.lines)


# ── Session class ──

class MeshTermSession:
    """A terminal session (pane) with a running PTY.

    Mirrors iterm2.Session -- the primary interface for terminal interaction.

    Properties:
        session_id: str     -- Unique session identifier (UUID)
        name: str           -- Display name
        profile: str        -- Profile used to create this session
        pid: int            -- PID of the shell process in this session
        tty: str            -- PTY device path (e.g., /dev/pts/3)

    Key methods:
        async_send_text()           -- Type text into the terminal
        async_get_screen_contents() -- Read the visible screen
        async_get_scrollback()      -- Read scrollback buffer
        async_split_pane()          -- Create a split pane
        async_set_variable()        -- Set a user variable
        async_get_variable()        -- Get a session variable

    Usage:
        session = app.current_window.current_tab.current_session
        await session.async_send_text("ls -la\\n")
        contents = await session.async_get_screen_contents()
        for line in contents.lines:
            print(line.string)
    """

    def __init__(self, connection: "Connection", data: dict):
        self._connection = connection
        self._session_id: str = data.get("session_id", "")
        self._name: str = data.get("name", "")
        self._profile: str = data.get("profile", "default")
        self._pid: int = data.get("pid", 0)
        self._tty: str = data.get("tty", "")

    # ── Properties ──

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def pid(self) -> int:
        """PID of the child process (shell) in this session."""
        return self._pid

    @property
    def tty(self) -> str:
        """PTY slave device path, e.g. /dev/pts/3."""
        return self._tty

    # ── Text Operations ──

    async def async_send_text(
        self,
        text: str,
        suppress_broadcast: bool = False,
    ) -> None:
        """Send text to this session as if typed by the user.

        The text is written to the PTY master fd on the server side.
        Special characters (\\n, \\r, \\x1b, \\x03) are sent as-is --
        the PTY handles translation.

        Args:
            text: Text to inject. Include "\\n" for Enter.
            suppress_broadcast: If True, do not broadcast to other
                                sessions in broadcast mode.

        Mirrors: await session.async_send_text("command\\n")
        """
        await self._connection.async_call(
            "session.send_text",
            session_id=self._session_id,
            text=text,
            suppress_broadcast=suppress_broadcast,
        )

    async def async_send_key(
        self,
        key: str,
        modifiers: list[str] | None = None,
    ) -> None:
        """Send a named key with optional modifiers.

        Args:
            key: Key name -- "Return", "Escape", "Tab", "Up", "Down",
                 "Left", "Right", "Backspace", "Delete", "Home", "End",
                 "PageUp", "PageDown", "F1"-"F12", or a single character.
            modifiers: List of modifiers -- "ctrl", "alt", "shift", "super".

        Usage:
            await session.async_send_key("Return")
            await session.async_send_key("c", modifiers=["ctrl"])
            await session.async_send_key("Escape")
        """
        await self._connection.async_call(
            "session.send_key",
            session_id=self._session_id,
            key=key,
            modifiers=modifiers or [],
        )

    # ── Screen Reading ──

    async def async_get_screen_contents(self) -> ScreenContents:
        """Read the current visible screen content.

        Returns the rendered terminal screen as the user sees it,
        after processing all escape sequences (colors, cursor moves,
        alternate screen, etc.).

        Server-side implementation:
          1. The VT parser (pyte) maintains the screen state grid
          2. This RPC serializes the current grid to lines
          3. Alternate screen buffer is returned if active

        Returns:
            ScreenContents with lines, cursor position, and dimensions.

        Mirrors: contents = await session.async_get_screen_contents()
        """
        data = await self._connection.async_call(
            "session.get_screen_contents",
            session_id=self._session_id,
        )
        lines = [
            ScreenLine(
                string=l.get("string", ""),
                hard_eol=l.get("hard_eol", True),
                line_number=i,
            )
            for i, l in enumerate(data.get("lines", []))
        ]
        return ScreenContents(
            lines=lines,
            cursor_row=data.get("cursor_row", 0),
            cursor_col=data.get("cursor_col", 0),
            rows=data.get("rows", 24),
            cols=data.get("cols", 80),
            alternate_screen_active=data.get("alternate_screen_active", False),
        )

    async def async_get_scrollback(
        self,
        lines: int = -1,
        offset: int = 0,
    ) -> list[ScreenLine]:
        """Read scrollback buffer content.

        Unlike get_screen_contents (which returns the visible screen),
        this returns historical output that has scrolled off-screen.

        Works even when alternate screen (vim, less) is active --
        returns the normal buffer's scrollback.

        Args:
            lines: Number of lines to return. -1 = all available.
            offset: Start from this line (0 = most recent).

        Returns:
            List of ScreenLine objects from scrollback.
        """
        data = await self._connection.async_call(
            "session.get_scrollback",
            session_id=self._session_id,
            lines=lines,
            offset=offset,
        )
        return [
            ScreenLine(
                string=l.get("string", ""),
                hard_eol=l.get("hard_eol", True),
                line_number=i,
            )
            for i, l in enumerate(data.get("lines", []))
        ]

    # ── Session Management ──

    async def async_set_name(self, name: str) -> None:
        """Set the display name of this session.

        Mirrors: await session.async_set_name("Name")
        """
        await self._connection.async_call(
            "session.set_name",
            session_id=self._session_id,
            name=name,
        )
        self._name = name

    async def async_activate(self) -> None:
        """Make this the active (focused) session in its tab.

        Mirrors: await session.async_activate()
        """
        await self._connection.async_call(
            "session.activate", session_id=self._session_id
        )

    async def async_close(self, force: bool = False) -> None:
        """Close this session (kills the shell process).

        Args:
            force: If True, send SIGKILL instead of SIGHUP.

        Mirrors: await session.async_close()
        """
        await self._connection.async_call(
            "session.close",
            session_id=self._session_id,
            force=force,
        )

    async def async_split_pane(
        self,
        vertical: bool = True,
        profile: str | None = None,
        command: str | None = None,
    ) -> "MeshTermSession":
        """Split this session to create a new adjacent pane.

        Convenience wrapper -- delegates to the parent tab's split.

        Args:
            vertical: True = side-by-side, False = top/bottom.
            profile: Profile for new session. None = default.
            command: Command to run. None = shell.

        Returns:
            The newly created MeshTermSession.

        Mirrors: new = await session.async_split_pane(vertical=True)
        """
        data = await self._connection.async_call(
            "session.split_pane",
            session_id=self._session_id,
            vertical=vertical,
            profile=profile,
            command=command,
        )
        return MeshTermSession(self._connection, data)

    # ── Variables ──

    async def async_get_variable(self, name: str) -> Optional[str]:
        """Get a session variable.

        Built-in variables:
          - path: Current working directory
          - name: Session name
          - hostname: Connected host (from shell integration)
          - username: Current user
          - pid: Shell PID
          - tty: PTY device path
          - columns: Terminal width
          - rows: Terminal height
          - title: Terminal title (set by escape sequences)
          - user.*: User-defined variables

        Mirrors: path = await session.async_get_variable("path")
        """
        return await self._connection.async_call(
            "session.get_variable",
            session_id=self._session_id,
            name=name,
        )

    async def async_set_variable(self, name: str, value: str) -> None:
        """Set a user-defined session variable.

        Variable names must start with "user." to avoid conflicts
        with built-in variables.

        Mirrors: await session.async_set_variable("user.custom", "value")
        """
        if not name.startswith("user."):
            raise ValueError(
                f"Custom variables must start with 'user.': got {name!r}"
            )
        await self._connection.async_call(
            "session.set_variable",
            session_id=self._session_id,
            name=name,
            value=value,
        )

    # ── Resize ──

    async def async_set_grid_size(self, rows: int, cols: int) -> None:
        """Resize the terminal grid (rows x columns).

        This sends SIGWINCH to the child process and updates the
        PTY window size via ioctl(TIOCSWINSZ).

        Args:
            rows: Number of rows (lines).
            cols: Number of columns.
        """
        await self._connection.async_call(
            "session.set_grid_size",
            session_id=self._session_id,
            rows=rows,
            cols=cols,
        )

    def __repr__(self) -> str:
        return (
            f"MeshTermSession(id={self._session_id!r}, "
            f"name={self._name!r}, pid={self._pid})"
        )
