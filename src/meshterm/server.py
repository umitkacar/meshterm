"""IPC server that runs inside the meshterm process.

This is the counterpart to connection.py (the client). The server
listens on a Unix domain socket and handles JSON-RPC requests by
operating on the terminal's internal state.

Architecture
============

    meshterm process (GUI or headless)
    +----------------------------------+
    |  PTY Manager                     |    manages PTY master fds
    |  VT Parser (pyte)                |    maintains screen state
    |  IPC Server (this module)        |    listens on Unix socket
    +----------------------------------+
         |
         | Unix domain socket
         |
    +----------------------------------+
    |  Client (connection.py)          |    external Python scripts
    |  MeshTermTransport               |    claude-mesh integration
    +----------------------------------+

The server owns the real terminal state. Clients are thin RPC proxies.
This separation means:
  - Multiple clients can connect simultaneously
  - Clients can crash without affecting the terminal
  - The server can expose only safe operations

RPC Method Registry
===================

Each "session.send_text", "window.create", etc. maps to a handler
function. The server dispatches by method name.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from meshterm.connection import (
    _encode_frame,
    _read_frame,
    _HEADER_SIZE,
    _warn_no_auth_once,
    default_socket_path,
    default_cookie_path,
)


# Type alias for RPC handlers
RPCHandler = Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class SessionState:
    """Server-side state for one terminal session.

    Holds the PTY fd, VT parser screen, and metadata.
    The VT parser (pyte.Screen + pyte.Stream) processes all PTY output
    and maintains the rendered screen grid.
    """
    session_id: str
    name: str
    profile: str
    pid: int             # child shell PID
    master_fd: int       # PTY master file descriptor
    tty: str             # /dev/pts/N path
    rows: int = 24
    cols: int = 80
    # screen and stream are initialized by the server when pyte is available
    screen: Any = None   # pyte.Screen instance
    stream: Any = None   # pyte.Stream instance
    user_vars: dict[str, str] = field(default_factory=dict)


class MeshTermServer:
    """Unix domain socket IPC server for meshterm.

    Lifecycle:
        server = MeshTermServer()
        server.register_session(session_state)
        await server.start()
        ...
        await server.stop()

    Or as context manager:
        async with MeshTermServer() as server:
            server.register_session(...)
            await server.serve_forever()
    """

    def __init__(
        self,
        socket_path: str | Path | None = None,
        require_auth: bool = True,
    ):
        self._socket_path = Path(socket_path) if socket_path else default_socket_path()
        self._require_auth = require_auth
        self._cookie: str = ""
        self._server: Optional[asyncio.AbstractServer] = None
        self._sessions: dict[str, SessionState] = {}
        self._windows: dict[str, dict] = {}  # window_id -> window state
        self._handlers: dict[str, RPCHandler] = {}
        self._clients: set[asyncio.StreamWriter] = set()

        self._register_builtin_handlers()

    # ── Session & Window Registration ──

    def register_session(self, state: SessionState) -> None:
        """Register a terminal session with the IPC server.

        Called by the meshterm terminal manager when a new PTY is created.
        Initializes pyte VT parser and starts async PTY output reader.
        """
        # Initialize pyte VT parser for screen state tracking
        try:
            import pyte
            state.screen = pyte.HistoryScreen(state.cols, state.rows, history=10000)
            state.stream = pyte.Stream(state.screen)
        except ImportError:
            # pyte not installed — screen reading will return empty
            pass

        self._sessions[state.session_id] = state

        # Start async PTY output reader if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.add_reader(state.master_fd, self._on_pty_output, state)
        except RuntimeError:
            # No event loop — reader will be started when server starts
            pass

    def _on_pty_output(self, state: SessionState) -> None:
        """Called when PTY master fd has data to read.

        Reads output from the shell, feeds it to pyte VT parser
        to maintain screen state.
        """
        try:
            data = os.read(state.master_fd, 65536)
            if data and state.stream is not None:
                state.stream.feed(data.decode("utf-8", errors="replace"))
        except OSError:
            # PTY closed — remove reader
            try:
                loop = asyncio.get_running_loop()
                loop.remove_reader(state.master_fd)
            except (RuntimeError, ValueError):
                pass

    def unregister_session(self, session_id: str) -> None:
        """Remove a session (after it is closed)."""
        self._sessions.pop(session_id, None)

    def register_window(self, window_id: str, data: dict) -> None:
        """Register a window with the IPC server."""
        self._windows[window_id] = data

    # ── Server Lifecycle ──

    async def start(self) -> None:
        """Start listening on the Unix domain socket.

        Creates the socket directory, generates auth cookie, and
        begins accepting connections.

        Security (F5 + F7 fix — TOCTOU race elimination):
            Both the Unix socket file and the cookie file are created
            while ``umask(0o077)`` is in effect, so the kernel assigns
            mode ``0600`` at creation time — NO race window exists
            between ``start_unix_server`` / file write and ``chmod``.

            The trailing ``os.chmod`` calls remain as belt-and-suspenders
            in case a future Python release changes socket creation
            defaults, but the umask is the primary defense.
        """
        # F4 fix: emit one-time warning if auth is disabled
        if not self._require_auth:
            _warn_no_auth_once("Server")

        # F5 + F7 fix: secure umask BEFORE creating any socket/cookie files.
        # Unix socket mode at creation = 0666 & ~umask.  With umask 0077 the
        # kernel creates the socket with mode 0600 from the start — no TOCTOU
        # race window where another local user could connect. Same applies
        # to the cookie file: O_CREAT mode 0o600 combined with umask 0o077
        # yields 0o600 from creation.
        old_umask = os.umask(0o077)
        try:
            # Ensure socket directory exists with proper permissions
            self._socket_path.parent.mkdir(parents=True, exist_ok=True)
            # Explicit chmod: mkdir may have used more permissive mode if
            # the directory pre-existed with different perms.
            os.chmod(self._socket_path.parent, 0o700)

            # Remove stale socket file
            if self._socket_path.exists():
                self._socket_path.unlink()

            # Generate auth cookie — write via os.open with explicit mode
            # so the file is created atomically at 0o600, not the default
            # 0o644 that Path.write_text would produce.
            if self._require_auth:
                self._cookie = secrets.token_hex(32)
                cookie_path = default_cookie_path()
                cookie_path.parent.mkdir(parents=True, exist_ok=True)
                os.chmod(cookie_path.parent, 0o700)

                # Remove any stale cookie before re-creating
                if cookie_path.exists():
                    cookie_path.unlink()

                # O_CREAT | O_EXCL | O_WRONLY with explicit 0o600 mode —
                # file exists with correct perms from the first byte.
                fd = os.open(
                    str(cookie_path),
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                try:
                    os.write(fd, self._cookie.encode("utf-8"))
                finally:
                    os.close(fd)
                # Belt-and-suspenders chmod (no-op with umask 0077)
                os.chmod(cookie_path, 0o600)

            # Create socket under the same umask — file born with 0600
            self._server = await asyncio.start_unix_server(
                self._handle_client,
                path=str(self._socket_path),
            )

            # Belt-and-suspenders: explicit chmod.  Due to umask 0077 the
            # socket already has mode 0600, but this protects against
            # future Python versions that might change default behavior.
            os.chmod(self._socket_path, 0o600)
        finally:
            os.umask(old_umask)

    async def stop(self) -> None:
        """Stop the server and clean up."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Close all client connections
        for writer in list(self._clients):
            writer.close()
        self._clients.clear()

        # Clean up socket file
        if self._socket_path.exists():
            self._socket_path.unlink()

    async def serve_forever(self) -> None:
        """Run the server until cancelled."""
        if not self._server:
            await self.start()
        await self._server.serve_forever()

    # ── Client Handling ──

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single client connection."""
        self._clients.add(writer)
        try:
            # First frame must be handshake
            frame = await _read_frame(reader)
            if frame.get("method") != "handshake":
                await self._send_error(writer, 0, -32600, "Expected handshake")
                return

            # Verify auth cookie
            if self._require_auth:
                client_cookie = frame.get("params", {}).get("cookie", "")
                if not secrets.compare_digest(client_cookie, self._cookie):
                    await self._send_error(writer, 0, -32001, "Invalid cookie")
                    return

            # Send handshake response
            response = {
                "jsonrpc": "2.0",
                "result": {"status": "connected", "server_version": "0.2.1"},
                "id": 0,
            }
            writer.write(_encode_frame(response))
            await writer.drain()

            # Process RPC requests
            while True:
                frame = await _read_frame(reader)
                await self._dispatch(writer, frame)

        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass  # Client disconnected
        finally:
            self._clients.discard(writer)
            writer.close()

    async def _dispatch(
        self,
        writer: asyncio.StreamWriter,
        frame: dict,
    ) -> None:
        """Dispatch a JSON-RPC request to the appropriate handler."""
        method = frame.get("method", "")
        params = frame.get("params", {})
        req_id = frame.get("id")  # None for notifications

        handler = self._handlers.get(method)
        if not handler:
            if req_id is not None:
                await self._send_error(writer, req_id, -32601, f"Method not found: {method}")
            return

        try:
            result = await handler(**params)
            if req_id is not None:
                response = {"jsonrpc": "2.0", "result": result, "id": req_id}
                writer.write(_encode_frame(response))
                await writer.drain()
        except Exception as e:
            if req_id is not None:
                await self._send_error(writer, req_id, -32000, str(e))

    async def _send_error(
        self,
        writer: asyncio.StreamWriter,
        req_id: int,
        code: int,
        message: str,
    ) -> None:
        response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": req_id,
        }
        writer.write(_encode_frame(response))
        await writer.drain()

    # ── Broadcast events to all clients ──

    async def broadcast_event(self, event: str, params: dict) -> None:
        """Send a notification to all connected clients.

        Used for events like session.created, focus.changed, etc.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": event,
            "params": params,
        }
        frame = _encode_frame(notification)
        dead_clients = set()
        for writer in self._clients:
            try:
                writer.write(frame)
                await writer.drain()
            except Exception:
                dead_clients.add(writer)
        self._clients -= dead_clients

    # ── Built-in RPC Handlers ──

    def _register_builtin_handlers(self) -> None:
        """Register the core RPC method handlers."""
        self._handlers["app.get_state"] = self._h_app_get_state
        self._handlers["app.get_variable"] = self._h_app_get_variable
        self._handlers["session.send_text"] = self._h_session_send_text
        self._handlers["session.send_key"] = self._h_session_send_key
        self._handlers["session.get_screen_contents"] = self._h_session_get_screen_contents
        self._handlers["session.get_scrollback"] = self._h_session_get_scrollback
        self._handlers["session.set_name"] = self._h_session_set_name
        self._handlers["session.activate"] = self._h_session_activate
        self._handlers["session.close"] = self._h_session_close
        self._handlers["session.split_pane"] = self._h_session_split_pane
        self._handlers["session.get_variable"] = self._h_session_get_variable
        self._handlers["session.set_variable"] = self._h_session_set_variable
        self._handlers["session.set_grid_size"] = self._h_session_set_grid_size
        self._handlers["window.create"] = self._h_window_create
        self._handlers["window.activate"] = self._h_window_activate
        self._handlers["window.close"] = self._h_window_close
        self._handlers["window.create_tab"] = self._h_window_create_tab
        self._handlers["window.set_title"] = self._h_window_set_title
        self._handlers["window.set_position"] = self._h_window_set_position
        self._handlers["window.set_size"] = self._h_window_set_size
        self._handlers["window.set_fullscreen"] = self._h_window_set_fullscreen
        self._handlers["window.set_tabs"] = self._h_window_set_tabs
        self._handlers["tab.activate"] = self._h_tab_activate
        self._handlers["tab.close"] = self._h_tab_close
        self._handlers["tab.set_title"] = self._h_tab_set_title
        self._handlers["tab.split_pane"] = self._h_tab_split_pane
        self._handlers["tab.select_pane_in_direction"] = self._h_tab_select_pane_direction
        self._handlers["subscribe"] = self._h_subscribe

    def _get_session(self, session_id: str) -> SessionState:
        state = self._sessions.get(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")
        return state

    # ── Handler Implementations (stubs for the API design) ──
    # These show the interface contract. Full implementation requires
    # the PTY manager and VT parser, which are part of the terminal core.

    async def _h_app_get_state(self) -> dict:
        """Return full application state tree."""
        return {
            "pid": os.getpid(),
            "version": "0.2.1",
            "current_window_id": next(iter(self._windows), ""),
            "windows": list(self._windows.values()),
        }

    async def _h_app_get_variable(self, name: str) -> Optional[str]:
        var_map = {
            "pid": str(os.getpid()),
            "version": "0.2.1",
            "theme": "dark",
        }
        return var_map.get(name)

    # F3 security: hard limit to prevent PTY DoS (1 MiB is generous for any
    # legitimate send_text call — interactive input is bytes, not megabytes).
    _MAX_SEND_TEXT_BYTES = 1024 * 1024  # 1 MiB

    async def _h_session_send_text(
        self,
        session_id: str,
        text: str,
        suppress_broadcast: bool = False,
    ) -> None:
        """Write text to the session's PTY master fd.

        F3 fix: enforces _MAX_SEND_TEXT_BYTES (1 MiB) hard limit to prevent
        a malicious or buggy client from flooding the PTY buffer. Terminal
        escape injection is NOT filtered here — that would break legitimate
        uses like ANSI color codes and control keys. Length limit is the
        pragmatic first line of defense.
        """
        state = self._get_session(session_id)
        encoded = text.encode("utf-8")
        if len(encoded) > self._MAX_SEND_TEXT_BYTES:
            raise ValueError(
                f"send_text payload too large: {len(encoded)} bytes "
                f"(max {self._MAX_SEND_TEXT_BYTES})"
            )
        os.write(state.master_fd, encoded)

    async def _h_session_send_key(
        self,
        session_id: str,
        key: str,
        modifiers: list[str] | None = None,
    ) -> None:
        """Translate a named key to bytes and write to PTY.

        Key translation table (subset):
          Return    -> \\r
          Escape    -> \\x1b
          Tab       -> \\t
          Backspace -> \\x7f
          Up        -> \\x1b[A
          Down      -> \\x1b[B
          Right     -> \\x1b[C
          Left      -> \\x1b[D
          ctrl+c    -> \\x03
          ctrl+d    -> \\x04
          ctrl+z    -> \\x1a
        """
        state = self._get_session(session_id)

        key_map = {
            "Return": "\r",
            "Escape": "\x1b",
            "Tab": "\t",
            "Backspace": "\x7f",
            "Delete": "\x1b[3~",
            "Up": "\x1b[A",
            "Down": "\x1b[B",
            "Right": "\x1b[C",
            "Left": "\x1b[D",
            "Home": "\x1b[H",
            "End": "\x1b[F",
            "PageUp": "\x1b[5~",
            "PageDown": "\x1b[6~",
        }

        # Add F-keys
        for i in range(1, 13):
            key_map[f"F{i}"] = f"\x1bO{chr(ord('P') + i - 1)}" if i <= 4 else f"\x1b[{i + 10}~"

        mods = set(modifiers or [])
        if "ctrl" in mods and len(key) == 1:
            # ctrl+letter = chr(ord(letter) - 64)
            byte = chr(ord(key.upper()) - 64)
            os.write(state.master_fd, byte.encode("utf-8"))
        elif key in key_map:
            os.write(state.master_fd, key_map[key].encode("utf-8"))
        elif len(key) == 1:
            os.write(state.master_fd, key.encode("utf-8"))

    async def _h_session_get_screen_contents(self, session_id: str) -> dict:
        """Read current screen from the VT parser.

        Implementation uses pyte.Screen which maintains the rendered grid:

            import pyte
            screen = pyte.Screen(80, 24)
            stream = pyte.Stream(screen)
            stream.feed(pty_output)  # called on every PTY read
            # screen.display is a list of 24 strings, each 80 chars
        """
        state = self._get_session(session_id)

        if state.screen is not None:
            # pyte screen is available
            lines = []
            for i, text in enumerate(state.screen.display):
                lines.append({
                    "string": text.rstrip(),
                    "hard_eol": True,
                })
            return {
                "lines": lines,
                "cursor_row": state.screen.cursor.y,
                "cursor_col": state.screen.cursor.x,
                "rows": state.rows,
                "cols": state.cols,
                "alternate_screen_active": (
                    hasattr(state.screen, "in_alternate_screen")
                    and state.screen.in_alternate_screen
                ),
            }

        # Fallback: no VT parser, return empty
        return {
            "lines": [],
            "cursor_row": 0,
            "cursor_col": 0,
            "rows": state.rows,
            "cols": state.cols,
            "alternate_screen_active": False,
        }

    async def _h_session_get_scrollback(
        self,
        session_id: str,
        lines: int = -1,
        offset: int = 0,
    ) -> dict:
        """Read scrollback from the VT parser's history.

        pyte.HistoryScreen maintains a deque of scrolled-off lines.
        """
        state = self._get_session(session_id)

        if state.screen is not None and hasattr(state.screen, "history"):
            history_lines = []
            # pyte.HistoryScreen stores scrolled-off lines in history.top
            for hist_line in state.screen.history.top:
                text = "".join(hist_line[col].data for col in sorted(hist_line.keys()))
                history_lines.append({"string": text.rstrip(), "hard_eol": True})

            if lines > 0:
                history_lines = history_lines[-lines:]
            if offset > 0:
                history_lines = history_lines[offset:]

            return {"lines": history_lines}

        return {"lines": []}

    async def _h_session_set_name(self, session_id: str, name: str) -> None:
        state = self._get_session(session_id)
        state.name = name

    async def _h_session_activate(self, session_id: str) -> None:
        # Focus this session in the GUI
        raise NotImplementedError("_h_session_activate planned for v0.2")

    async def _h_session_close(
        self,
        session_id: str,
        force: bool = False,
    ) -> None:
        """Close session: send SIGHUP (or SIGKILL if force) to child."""
        import signal
        state = self._get_session(session_id)
        sig = signal.SIGKILL if force else signal.SIGHUP
        try:
            os.kill(state.pid, sig)
        except ProcessLookupError:
            pass
        os.close(state.master_fd)
        self.unregister_session(session_id)
        await self.broadcast_event("session.closed", {"session_id": session_id})

    async def _h_session_split_pane(
        self,
        session_id: str,
        vertical: bool = True,
        profile: str | None = None,
        command: str | None = None,
    ) -> dict:
        """Create a new PTY and register as a split pane.

        The actual pane layout is managed by the terminal's GUI layer.
        This handler creates the PTY and returns the new session data.
        """
        raise NotImplementedError("session.split_pane not yet implemented — planned for v0.2.0")

    async def _h_session_get_variable(
        self,
        session_id: str,
        name: str,
    ) -> Optional[str]:
        state = self._get_session(session_id)
        builtin_vars = {
            "name": state.name,
            "pid": str(state.pid),
            "tty": state.tty,
            "columns": str(state.cols),
            "rows": str(state.rows),
        }
        if name in builtin_vars:
            return builtin_vars[name]
        if name.startswith("user."):
            return state.user_vars.get(name)
        return None

    async def _h_session_set_variable(
        self,
        session_id: str,
        name: str,
        value: str,
    ) -> None:
        state = self._get_session(session_id)
        state.user_vars[name] = value

    async def _h_session_set_grid_size(
        self,
        session_id: str,
        rows: int,
        cols: int,
    ) -> None:
        """Resize PTY via ioctl(TIOCSWINSZ) and update VT parser."""
        import fcntl
        import termios
        state = self._get_session(session_id)
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(state.master_fd, termios.TIOCSWINSZ, winsize)
        state.rows = rows
        state.cols = cols
        if state.screen is not None:
            state.screen.resize(rows, cols)

    async def _h_window_create(self, profile: str | None = None, command: str | None = None) -> dict:
        raise NotImplementedError("_h_window_create planned for v0.2")

    async def _h_window_activate(self, window_id: str) -> None:
        raise NotImplementedError("_h_window_activate planned for v0.2")

    async def _h_window_close(self, window_id: str, force: bool = False) -> None:
        raise NotImplementedError("_h_window_close planned for v0.2")

    async def _h_window_create_tab(self, window_id: str, **kwargs) -> dict:
        raise NotImplementedError("_h_window_create_tab planned for v0.2")

    async def _h_window_set_title(self, window_id: str, title: str) -> None:
        raise NotImplementedError("_h_window_set_title planned for v0.2")

    async def _h_window_set_position(self, window_id: str, x: int, y: int) -> None:
        raise NotImplementedError("_h_window_set_position planned for v0.2")

    async def _h_window_set_size(self, window_id: str, width: int, height: int) -> None:
        raise NotImplementedError("_h_window_set_size planned for v0.2")

    async def _h_window_set_fullscreen(self, window_id: str, fullscreen: bool) -> None:
        raise NotImplementedError("_h_window_set_fullscreen planned for v0.2")

    async def _h_window_set_tabs(self, window_id: str, tab_ids: list[str]) -> None:
        raise NotImplementedError("_h_window_set_tabs planned for v0.2")

    async def _h_tab_activate(self, tab_id: str) -> None:
        raise NotImplementedError("_h_tab_activate planned for v0.2")

    async def _h_tab_close(self, tab_id: str) -> None:
        raise NotImplementedError("_h_tab_close planned for v0.2")

    async def _h_tab_set_title(self, tab_id: str, title: str) -> None:
        raise NotImplementedError("_h_tab_set_title planned for v0.2")

    async def _h_tab_split_pane(self, tab_id: str, session_id: str, **kwargs) -> dict:
        raise NotImplementedError("_h_tab_split_pane planned for v0.2")

    async def _h_tab_select_pane_direction(self, tab_id: str, direction: str) -> None:
        raise NotImplementedError("_h_tab_select_pane_direction planned for v0.2")

    async def _h_subscribe(self, event: str) -> dict:
        return {"subscribed": event}

    # ── Context Manager ──

    async def __aenter__(self) -> "MeshTermServer":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()
