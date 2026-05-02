"""Tab management -- mirrors iterm2.Tab.

Each tab lives inside a window and contains one or more sessions (panes).
Tabs support splitting into multiple panes arranged in a layout tree.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from meshterm.connection import Connection
    from meshterm.session import MeshTermSession


class MeshTermTab:
    """A single tab within a terminal window.

    Mirrors iterm2.Tab with the same property/method patterns.

    Properties:
        tab_id: str                         -- Unique tab identifier
        sessions: list[MeshTermSession]     -- All panes in this tab
        current_session: MeshTermSession    -- The focused pane
        title: str                          -- Tab title

    Usage:
        tab = window.current_tab
        await tab.async_set_title("Build")
        new_pane = await tab.async_split_pane(vertical=True)
        await tab.async_select_pane_in_direction("left")
    """

    def __init__(self, connection: "Connection", data: dict):
        self._connection = connection
        self._tab_id: str = data.get("tab_id", "")
        self._title: str = data.get("title", "")
        self._current_session_id: str = data.get("current_session_id", "")

        from meshterm.session import MeshTermSession
        self._sessions: list[MeshTermSession] = [
            MeshTermSession(connection, s) for s in data.get("sessions", [])
        ]

    # ── Properties ──

    @property
    def tab_id(self) -> str:
        return self._tab_id

    @property
    def sessions(self) -> list["MeshTermSession"]:
        return list(self._sessions)

    @property
    def current_session(self) -> Optional["MeshTermSession"]:
        for s in self._sessions:
            if s.session_id == self._current_session_id:
                return s
        return self._sessions[0] if self._sessions else None

    @property
    def title(self) -> str:
        return self._title

    # ── Methods ──

    async def async_activate(self) -> None:
        """Make this the active tab in its window.

        Mirrors: await tab.async_activate()
        """
        await self._connection.async_call(
            "tab.activate", tab_id=self._tab_id
        )

    async def async_close(self) -> None:
        """Close this tab and all its sessions.

        Mirrors: await tab.async_close()
        """
        await self._connection.async_call(
            "tab.close", tab_id=self._tab_id
        )

    async def async_set_title(self, title: str) -> None:
        """Set the tab title.

        Mirrors: await tab.async_set_title("My Tab")
        """
        await self._connection.async_call(
            "tab.set_title", tab_id=self._tab_id, title=title
        )
        self._title = title

    async def async_split_pane(
        self,
        vertical: bool = True,
        profile: str | None = None,
        command: str | None = None,
        before: bool = False,
    ) -> "MeshTermSession":
        """Split the current pane to create a new session.

        Args:
            vertical: True = side-by-side split, False = top/bottom.
            profile: Profile for the new session. None = default.
            command: Command to run. None = shell.
            before: If True, new pane goes left/above instead of right/below.

        Returns:
            The newly created MeshTermSession.

        Mirrors: new = await session.async_split_pane(vertical=True)
        Note: In iTerm2 this is on Session, but meshterm puts it on Tab
        for clearer ownership. Session also has a convenience wrapper.
        """
        from meshterm.session import MeshTermSession
        data = await self._connection.async_call(
            "tab.split_pane",
            tab_id=self._tab_id,
            session_id=self._current_session_id,
            vertical=vertical,
            profile=profile,
            command=command,
            before=before,
        )
        session = MeshTermSession(self._connection, data)
        self._sessions.append(session)
        return session

    async def async_select_pane_in_direction(self, direction: str) -> None:
        """Move focus to an adjacent pane.

        Args:
            direction: "left", "right", "up", or "down".

        Mirrors: await tab.async_select_pane_in_direction("left")
        """
        if direction not in ("left", "right", "up", "down"):
            raise ValueError(f"Invalid direction: {direction!r}")
        await self._connection.async_call(
            "tab.select_pane_in_direction",
            tab_id=self._tab_id,
            direction=direction,
        )

    def __repr__(self) -> str:
        return f"MeshTermTab(id={self._tab_id!r}, sessions={len(self._sessions)})"
