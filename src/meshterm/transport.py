"""MeshTermTransport -- claude-mesh transport backed by meshterm IPC.

Replaces SSHTransport for local Linux-to-Linux control. Instead of
SSH + tmux, this talks directly to the meshterm IPC server via Unix
domain socket. Zero network overhead, no SSH key management, no
ssh dependency.

Integration point in claude-mesh __init__.py:

    Linux priority order (after meshterm is proven):
      1. MeshTerm IPC (local, direct) -- NEW
      2. SSH + iTerm2 API (remote Mac control) -- PROVEN
      3. Redis Streams (Linux<->Linux fallback) -- PROVEN

Usage:
    from meshterm.transport import MeshTermTransport

    async with MeshTermTransport() as t:
        await t.send("eagle", "task complete")
        screen = await t.read_screen("eagle")
"""

from __future__ import annotations

import asyncio
from typing import Optional

# Import from claude-mesh's transport ABC
# This module lives in the meshterm package but implements the
# claude-mesh Transport interface for seamless integration.
try:
    from claude_mesh.transport.base import (
        CR, CTRL_C, ESC, LF,
        ConnectionError as MeshConnectionError,
        Delays,
        NodeInfo,
        SessionNotFoundError,
        Transport,
        TransportError,
    )
except ImportError:
    raise ImportError(
        "MeshTermTransport requires claude-mesh. "
        "Install it with: pip install claude-mesh"
    )

from meshterm.connection import Connection
from meshterm.app import MeshTermApp, async_get_app


class MeshTermTransport(Transport):
    """claude-mesh transport using meshterm's IPC API.

    Connects to a local meshterm instance via Unix domain socket.
    Maps node codenames to meshterm sessions by name.

    This is the Linux equivalent of ITerm2Transport:
      - ITerm2Transport: macOS, WebSocket to iTerm2
      - MeshTermTransport: Linux, Unix socket to meshterm

    Both implement the same 4 abstract primitives:
      send_text, send_key, read_screen, discover

    Args:
        socket_path: meshterm IPC socket path. None = auto-detect.
        session_map: Codename -> session_id mapping.
                     e.g., {"eagle": "abc-123", "titan": "def-456"}
        delays: Timing constants for terminal interaction.
    """

    def __init__(
        self,
        socket_path: str | None = None,
        session_map: dict[str, str] | None = None,
        delays: Delays | None = None,
    ):
        super().__init__(delays)
        self._socket_path = socket_path
        self._session_map = session_map or {}
        self._connection: Optional[Connection] = None
        self._app: Optional[MeshTermApp] = None

    async def _ensure_connection(self) -> None:
        """Lazy connect to meshterm IPC server."""
        if self._connection is not None and self._connection.connected:
            return

        try:
            self._connection = await Connection.unix(
                path=self._socket_path,
                authenticate=True,
            )
            self._app = await async_get_app(self._connection)
        except FileNotFoundError:
            raise MeshConnectionError(
                "meshterm socket not found. Is meshterm running?"
            )
        except Exception as e:
            raise MeshConnectionError(f"Cannot connect to meshterm: {e}")

    async def _find_session_id(self, target: str) -> str:
        """Find meshterm session ID by node codename.

        Strategy (same as ITerm2Transport):
          1. Check session_map for known UUID
          2. Search all sessions by name containing the codename
        """
        await self._ensure_connection()

        # Strategy 1: Direct lookup
        if target in self._session_map:
            return self._session_map[target]

        # Strategy 2: Search by name
        for window in self._app.windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    if target.lower() in session.name.lower():
                        self._session_map[target] = session.session_id
                        return session.session_id

        raise SessionNotFoundError(
            f"No meshterm session found for '{target}'. "
            f"Known mappings: {list(self._session_map.keys())}"
        )

    # ── Transport Primitives ──

    async def send_text(self, target: str, text: str) -> bool:
        session_id = await self._find_session_id(target)
        await self._connection.async_call(
            "session.send_text",
            session_id=session_id,
            text=text,
        )
        return True

    async def send_key(self, target: str, key: str) -> bool:
        session_id = await self._find_session_id(target)

        # Map claude-mesh key constants to meshterm key names
        key_map = {
            CR: "Return",
            "\r": "Return",
            LF: "\n",     # send as literal newline
            ESC: "Escape",
            "\x1b": "Escape",
            CTRL_C: "c",  # will be sent with ctrl modifier
        }

        mapped = key_map.get(key)
        if key == CTRL_C or key == "\x03":
            await self._connection.async_call(
                "session.send_key",
                session_id=session_id,
                key="c",
                modifiers=["ctrl"],
            )
        elif mapped and mapped in ("Return", "Escape"):
            await self._connection.async_call(
                "session.send_key",
                session_id=session_id,
                key=mapped,
                modifiers=[],
            )
        else:
            # Send as raw text (LF or unknown key)
            await self._connection.async_call(
                "session.send_text",
                session_id=session_id,
                text=key,
            )
        return True

    async def read_screen(self, target: str, lines: int = -1) -> str:
        session_id = await self._find_session_id(target)
        data = await self._connection.async_call(
            "session.get_screen_contents",
            session_id=session_id,
        )

        result = []
        all_lines = data.get("lines", [])
        num = len(all_lines) if lines < 0 else min(lines, len(all_lines))
        for i in range(num):
            text = all_lines[i].get("string", "")
            result.append(text.rstrip())

        return "\n".join(result)

    async def discover(self) -> list[NodeInfo]:
        await self._ensure_connection()
        await self._app.async_refresh()

        nodes = []
        for window in self._app.windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    nodes.append(NodeInfo(
                        name=session.name,
                        node_type="linux",
                        session_id=session.session_id,
                        alive=True,
                    ))
        return nodes

    async def close(self) -> None:
        if self._connection:
            await self._connection.async_disconnect()
            self._connection = None
            self._app = None
