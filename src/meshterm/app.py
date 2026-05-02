"""Application-level API -- mirrors iterm2.App / iterm2.async_get_app().

MeshTermApp is the root object that provides access to all windows,
tabs, and sessions managed by the running meshterm instance.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from meshterm.connection import Connection
    from meshterm.window import MeshTermWindow
    from meshterm.session import MeshTermSession


class MeshTermApp:
    """Root application object for a connected meshterm instance.

    Mirrors iterm2.App -- provides access to windows, tabs, sessions.

    Properties:
        windows: list[MeshTermWindow]     -- All open windows
        current_window: MeshTermWindow    -- The focused window
        pid: int                          -- meshterm process ID

    Usage:
        app = await meshterm.async_get_app(conn)
        print(f"Windows: {len(app.windows)}")
        session = app.current_window.current_tab.current_session
        await session.async_send_text("ls\\n")
    """

    def __init__(self, connection: "Connection", data: dict):
        self._connection = connection
        self._pid: int = data.get("pid", 0)
        self._version: str = data.get("version", "unknown")

        # Build object tree from server snapshot
        from meshterm.window import MeshTermWindow
        self._windows: list[MeshTermWindow] = [
            MeshTermWindow(connection, w) for w in data.get("windows", [])
        ]
        self._current_window_id: str = data.get("current_window_id", "")

    # ── Properties ──

    @property
    def windows(self) -> list["MeshTermWindow"]:
        """All open terminal windows."""
        return list(self._windows)

    @property
    def current_window(self) -> Optional["MeshTermWindow"]:
        """The currently focused window, or None."""
        for w in self._windows:
            if w.window_id == self._current_window_id:
                return w
        return self._windows[0] if self._windows else None

    @property
    def pid(self) -> int:
        """Process ID of the meshterm instance."""
        return self._pid

    @property
    def version(self) -> str:
        """meshterm version string."""
        return self._version

    # ── Methods ──

    async def async_refresh(self) -> None:
        """Re-fetch the application state from the server.

        Call this after creating/closing windows to get updated lists.
        Mirrors iterm2's pattern where the App object caches state.
        """
        data = await self._connection.async_call("app.get_state")
        from meshterm.window import MeshTermWindow
        self._windows = [
            MeshTermWindow(self._connection, w) for w in data.get("windows", [])
        ]
        self._current_window_id = data.get("current_window_id", "")

    async def async_get_variable(self, name: str) -> Optional[str]:
        """Get an application-level variable.

        Available variables:
          - pid: Process ID
          - version: meshterm version
          - uptime: Seconds since start
          - theme: "dark" or "light" (from system)

        Mirrors iterm2 app.async_get_variable().
        """
        return await self._connection.async_call(
            "app.get_variable", name=name
        )

    def get_session_by_id(self, session_id: str) -> Optional["MeshTermSession"]:
        """Find a session by its unique ID across all windows/tabs.

        Convenience method for when you have a session UUID and need
        the object. Searches the cached window tree.
        """
        for window in self._windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    if session.session_id == session_id:
                        return session
        return None


# ── Module-level factory (mirrors iterm2.async_get_app) ──

async def async_get_app(connection: "Connection") -> MeshTermApp:
    """Get the MeshTermApp instance for a connection.

    This is the standard entrypoint after connecting:

        async with meshterm.Connection.unix() as conn:
            app = await meshterm.async_get_app(conn)
            ...

    Mirrors: app = await iterm2.async_get_app(connection)
    """
    data = await connection.async_call("app.get_state")
    return MeshTermApp(connection, data)
