"""IPC connection to a running meshterm instance.

Design Decision: Unix Domain Socket with JSON-RPC 2.0
=====================================================

Why NOT the alternatives:

  - D-Bus: Heavy dependency, complex API, not available in containers.
    Adds dbus-python or pydbus as a hard requirement. Overkill for
    single-application IPC.

  - TCP: Opens a network port. Requires authentication to prevent
    remote access. Unnecessary complexity for local-only control.

  - Named pipes (FIFO): Unidirectional. We need request/response.
    Would need two FIFOs + our own framing protocol.

Why Unix Domain Socket:

  1. Same pattern as iTerm2 (WebSocket over UDS) -- familiar to users
  2. Filesystem-based auth: socket file permissions control access
  3. No network exposure: cannot be reached from remote machines
  4. Bidirectional: full request/response over a single connection
  5. Fast: kernel-level IPC, no TCP overhead
  6. Works everywhere: Linux, macOS, containers, WSL

Socket location:
  $XDG_RUNTIME_DIR/meshterm/ipc.sock   (preferred, tmpfs, per-user)
  /tmp/meshterm-$UID/ipc.sock          (fallback)

Protocol: JSON-RPC 2.0 over length-prefixed frames
  Frame: [4-byte big-endian length][JSON payload]
  This avoids delimiter scanning and handles binary-safe payloads.

Authentication: Cookie-based (like iTerm2)
  The server writes a random cookie to ~/.config/meshterm/auth_cookie
  with mode 0600. Clients must send this cookie in the handshake.
  This prevents other users on the same machine from connecting.

  For single-user dev machines, MESHTERM_NO_AUTH=1 disables cookie check.
  F4 fix: when MESHTERM_NO_AUTH=1 is detected, a RuntimeWarning is
  emitted so operators are aware that any local process can control
  terminals through the meshterm socket.
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ------------------------------------------------------------------ #
# F4 fix: NO_AUTH warning helper
# Emitted once per process when MESHTERM_NO_AUTH=1 is detected.
# Module-level flag prevents warning spam for callers that open many
# connections in sequence.
# ------------------------------------------------------------------ #

_NO_AUTH_WARNED = False


def _warn_no_auth_once(context: str = "Connection") -> None:
    """Emit a one-time RuntimeWarning when auth bypass is active.

    Args:
        context: Short label naming the caller ("Connection" or "Server")
                 for clearer warning messages.

    Design:
        - RuntimeWarning (not DeprecationWarning) because this is a live
          security posture issue, not a deprecated API.
        - Guarded by module-level flag so repeated connects don't spam.
        - stacklevel=3 points the warning at the caller of unix()/start(),
          not at this helper or the Connection/Server internals.
    """
    global _NO_AUTH_WARNED
    if _NO_AUTH_WARNED:
        return
    _NO_AUTH_WARNED = True
    warnings.warn(
        f"meshterm {context} running WITHOUT authentication "
        "(MESHTERM_NO_AUTH=1). Any local process on this machine can "
        "control terminals through the meshterm socket. Use this ONLY "
        "on single-user dev machines that you fully trust.",
        RuntimeWarning,
        stacklevel=3,
    )


# ------------------------------------------------------------------ #
# Frame encoding: [4-byte big-endian length][JSON-RPC payload]
# ------------------------------------------------------------------ #

_HEADER_FMT = "!I"  # network byte order, unsigned 4 bytes
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)
_MAX_FRAME = 16 * 1024 * 1024  # 16 MiB safety limit


def _encode_frame(obj: dict) -> bytes:
    payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return struct.pack(_HEADER_FMT, len(payload)) + payload


async def _read_frame(reader: asyncio.StreamReader) -> dict:
    header = await reader.readexactly(_HEADER_SIZE)
    (length,) = struct.unpack(_HEADER_FMT, header)
    if length > _MAX_FRAME:
        raise ConnectionError(f"Frame too large: {length} bytes")
    payload = await reader.readexactly(length)
    return json.loads(payload)


# ------------------------------------------------------------------ #
# Socket path resolution
# ------------------------------------------------------------------ #

def default_socket_path() -> Path:
    """Determine the IPC socket path.

    Follows XDG Base Directory spec:
      1. $MESHTERM_SOCKET         (explicit override)
      2. $XDG_RUNTIME_DIR/meshterm/ipc.sock
      3. /tmp/meshterm-$UID/ipc.sock
    """
    env_path = os.environ.get("MESHTERM_SOCKET")
    if env_path:
        return Path(env_path)

    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        return Path(xdg) / "meshterm" / "ipc.sock"

    return Path(f"/tmp/meshterm-{os.getuid()}") / "ipc.sock"


def default_cookie_path() -> Path:
    """Path to the authentication cookie file."""
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_dir / "meshterm" / "auth_cookie"


# ------------------------------------------------------------------ #
# Connection class
# ------------------------------------------------------------------ #

@dataclass
class _PendingRequest:
    """Tracks an in-flight JSON-RPC request."""
    future: asyncio.Future
    method: str


class Connection:
    """Async connection to a running meshterm IPC server.

    Mirrors iterm2.Connection -- the object you pass to every API call.

    Usage:
        # Connect via Unix socket (standard)
        async with Connection.unix() as conn:
            app = await meshterm.async_get_app(conn)

        # Connect to explicit path
        async with Connection.unix("/tmp/my-meshterm.sock") as conn:
            ...

        # Connect without auth (dev mode)
        async with Connection.unix(authenticate=False) as conn:
            ...
    """

    def __init__(self):
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._request_id: int = 0
        self._pending: dict[int, _PendingRequest] = {}
        self._subscriptions: dict[str, list[asyncio.Queue]] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._connected: bool = False

    # ── Factory constructors ──

    @classmethod
    async def unix(
        cls,
        path: str | Path | None = None,
        authenticate: bool = True,
    ) -> "Connection":
        """Connect to meshterm via Unix domain socket.

        Args:
            path: Socket path. None = auto-detect.
            authenticate: Send auth cookie on connect. Set False for
                          dev/testing or when MESHTERM_NO_AUTH=1.

        Returns:
            Connected Connection instance.

        Raises:
            ConnectionError: Cannot reach the meshterm server.
            PermissionError: Auth cookie missing or invalid.
        """
        conn = cls()
        sock_path = Path(path) if path else default_socket_path()

        if not sock_path.exists():
            raise ConnectionError(
                f"meshterm socket not found at {sock_path}. "
                f"Is meshterm running? Start it with: meshterm --start-server"
            )

        try:
            conn._reader, conn._writer = await asyncio.open_unix_connection(
                str(sock_path)
            )
        except OSError as e:
            raise ConnectionError(f"Cannot connect to {sock_path}: {e}")

        # Handshake: send client hello with optional auth
        no_auth_env = os.environ.get("MESHTERM_NO_AUTH", "0") == "1"
        should_auth = authenticate and not no_auth_env

        # F4 fix: visible warning when auth is disabled at runtime
        if no_auth_env:
            _warn_no_auth_once("Connection")

        cookie = ""
        if should_auth:
            cookie_path = default_cookie_path()
            if not cookie_path.exists():
                raise PermissionError(
                    f"Auth cookie not found at {cookie_path}. "
                    f"Set MESHTERM_NO_AUTH=1 for development."
                )
            cookie = cookie_path.read_text().strip()

        hello = {
            "jsonrpc": "2.0",
            "method": "handshake",
            "params": {
                "client_version": "0.2.1",
                "cookie": cookie,
            },
            "id": 0,
        }
        conn._writer.write(_encode_frame(hello))
        await conn._writer.drain()

        response = await _read_frame(conn._reader)
        if "error" in response:
            raise PermissionError(
                f"Authentication failed: {response['error'].get('message', 'unknown')}"
            )

        conn._connected = True
        conn._listen_task = asyncio.create_task(conn._listen_loop())
        return conn

    # ── Core RPC methods ──

    async def async_call(self, method: str, **params: Any) -> Any:
        """Send a JSON-RPC request and wait for the response.

        This is the fundamental RPC primitive. All API methods
        (send_text, get_screen_contents, etc.) are built on this.

        Args:
            method: RPC method name (e.g., "session.send_text").
            **params: Method parameters.

        Returns:
            The "result" field from the JSON-RPC response.

        Raises:
            ConnectionError: Not connected.
            RuntimeError: Server returned an error.
        """
        if not self._connected:
            raise ConnectionError("Not connected to meshterm")

        self._request_id += 1
        req_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = _PendingRequest(future=future, method=method)

        self._writer.write(_encode_frame(request))
        await self._writer.drain()

        result = await future

        if isinstance(result, dict) and "__error__" in result:
            raise RuntimeError(f"RPC error in {method}: {result['__error__']}")

        return result

    async def async_notify(self, method: str, **params: Any) -> None:
        """Send a JSON-RPC notification (no response expected).

        Used for fire-and-forget operations like sending keystrokes.
        """
        if not self._connected:
            raise ConnectionError("Not connected to meshterm")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            # No "id" field = notification
        }
        self._writer.write(_encode_frame(notification))
        await self._writer.drain()

    async def subscribe(self, event: str) -> asyncio.Queue:
        """Subscribe to server-pushed events.

        Args:
            event: Event name (e.g., "session.created", "focus.changed").

        Returns:
            Queue that receives event payloads.
        """
        if event not in self._subscriptions:
            self._subscriptions[event] = []
            await self.async_call("subscribe", event=event)

        queue: asyncio.Queue = asyncio.Queue()
        self._subscriptions[event].append(queue)
        return queue

    # ── Internal listener ──

    async def _listen_loop(self) -> None:
        """Background task: read frames and dispatch to pending futures."""
        try:
            while self._connected:
                frame = await _read_frame(self._reader)

                # JSON-RPC response (has "id")
                if "id" in frame and frame["id"] in self._pending:
                    pending = self._pending.pop(frame["id"])
                    if "error" in frame:
                        pending.future.set_result(
                            {"__error__": frame["error"].get("message", str(frame["error"]))}
                        )
                    else:
                        pending.future.set_result(frame.get("result"))

                # Server notification (no "id", has "method")
                elif "method" in frame and "id" not in frame:
                    event = frame["method"]
                    if event in self._subscriptions:
                        for queue in self._subscriptions[event]:
                            await queue.put(frame.get("params", {}))

        except (asyncio.IncompleteReadError, ConnectionResetError):
            self._connected = False
        except asyncio.CancelledError:
            pass

    # ── Lifecycle ──

    async def async_disconnect(self) -> None:
        """Cleanly disconnect from the meshterm server."""
        self._connected = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        # Fail any pending requests
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_exception(
                    ConnectionError("Disconnected from meshterm")
                )
        self._pending.clear()

    @property
    def connected(self) -> bool:
        return self._connected

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, *args) -> None:
        await self.async_disconnect()
