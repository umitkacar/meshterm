"""Window management -- mirrors iterm2.Window.

Each MeshTermWindow represents one OS-level terminal window.
Windows contain tabs, tabs contain sessions (panes).
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from meshterm.connection import Connection
    from meshterm.tab import MeshTermTab


class MeshTermWindow:
    """A single terminal window.

    Mirrors iterm2.Window with the same property/method patterns.

    Properties:
        window_id: str                  -- Unique window identifier
        tabs: list[MeshTermTab]         -- Tabs in this window
        current_tab: MeshTermTab        -- The active tab
        title: str                      -- Window title
        position: tuple[int, int]       -- (x, y) screen position
        size: tuple[int, int]           -- (width, height) in pixels

    Usage:
        window = app.current_window
        tab = await window.async_create_tab()
        await window.async_set_title("Build Server")
        await window.async_set_position(100, 200)
        await window.async_close()
    """

    def __init__(self, connection: "Connection", data: dict):
        self._connection = connection
        self._window_id: str = data.get("window_id", "")
        self._title: str = data.get("title", "")
        self._position: tuple[int, int] = tuple(data.get("position", [0, 0]))
        self._size: tuple[int, int] = tuple(data.get("size", [800, 600]))
        self._fullscreen: bool = data.get("fullscreen", False)
        self._current_tab_id: str = data.get("current_tab_id", "")

        from meshterm.tab import MeshTermTab
        self._tabs: list[MeshTermTab] = [
            MeshTermTab(connection, t) for t in data.get("tabs", [])
        ]

    # ── Properties ──

    @property
    def window_id(self) -> str:
        return self._window_id

    @property
    def tabs(self) -> list["MeshTermTab"]:
        return list(self._tabs)

    @property
    def current_tab(self) -> Optional["MeshTermTab"]:
        for t in self._tabs:
            if t.tab_id == self._current_tab_id:
                return t
        return self._tabs[0] if self._tabs else None

    @property
    def title(self) -> str:
        return self._title

    @property
    def position(self) -> tuple[int, int]:
        return self._position

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    # ── Static factory ──

    @classmethod
    async def async_create(
        cls,
        connection: "Connection",
        profile: str | None = None,
        command: str | None = None,
    ) -> "MeshTermWindow":
        """Create a new terminal window.

        Args:
            connection: Active meshterm connection.
            profile: Profile name for the initial session. None = default.
            command: Command to run in the initial session. None = shell.

        Returns:
            The newly created MeshTermWindow.

        Mirrors: await iterm2.Window.async_create(connection, profile="Name")
        """
        data = await connection.async_call(
            "window.create",
            profile=profile,
            command=command,
        )
        return cls(connection, data)

    # ── Methods ──

    async def async_activate(self) -> None:
        """Bring this window to front and focus it.

        Mirrors: await window.async_activate()
        """
        await self._connection.async_call(
            "window.activate", window_id=self._window_id
        )

    async def async_close(self, force: bool = False) -> None:
        """Close this window and all its tabs/sessions.

        Args:
            force: If True, skip confirmation for unsaved sessions.

        Mirrors: await window.async_close()
        """
        await self._connection.async_call(
            "window.close", window_id=self._window_id, force=force
        )

    async def async_create_tab(
        self,
        profile: str | None = None,
        command: str | None = None,
        index: int | None = None,
    ) -> "MeshTermTab":
        """Create a new tab in this window.

        Args:
            profile: Profile name. None = default.
            command: Command to run. None = shell.
            index: Tab position. None = append at end.

        Returns:
            The newly created MeshTermTab.

        Mirrors: await window.async_create_tab(profile="Name")
        """
        from meshterm.tab import MeshTermTab
        data = await self._connection.async_call(
            "window.create_tab",
            window_id=self._window_id,
            profile=profile,
            command=command,
            index=index,
        )
        tab = MeshTermTab(self._connection, data)
        self._tabs.append(tab)
        return tab

    async def async_set_title(self, title: str) -> None:
        """Set the window title.

        Mirrors: not in iTerm2 Window API directly, but useful for Linux WM.
        """
        await self._connection.async_call(
            "window.set_title", window_id=self._window_id, title=title
        )
        self._title = title

    async def async_set_position(self, x: int, y: int) -> None:
        """Move the window to (x, y) screen coordinates."""
        await self._connection.async_call(
            "window.set_position", window_id=self._window_id, x=x, y=y
        )
        self._position = (x, y)

    async def async_set_size(self, width: int, height: int) -> None:
        """Resize the window to (width, height) in pixels."""
        await self._connection.async_call(
            "window.set_size",
            window_id=self._window_id,
            width=width,
            height=height,
        )
        self._size = (width, height)

    async def async_set_fullscreen(self, fullscreen: bool) -> None:
        """Toggle fullscreen mode.

        Mirrors: await window.async_set_fullscreen(True)
        """
        await self._connection.async_call(
            "window.set_fullscreen",
            window_id=self._window_id,
            fullscreen=fullscreen,
        )
        self._fullscreen = fullscreen

    async def async_set_tabs(self, tabs: list["MeshTermTab"]) -> None:
        """Reorder tabs in this window.

        Mirrors: await window.async_set_tabs([tab1, tab2])
        """
        tab_ids = [t.tab_id for t in tabs]
        await self._connection.async_call(
            "window.set_tabs", window_id=self._window_id, tab_ids=tab_ids
        )
        self._tabs = list(tabs)

    def __repr__(self) -> str:
        return f"MeshTermWindow(id={self._window_id!r}, tabs={len(self._tabs)})"
